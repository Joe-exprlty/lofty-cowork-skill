/**
 * Showing SMS Worker - Durable Object alarm scheduler
 * ----------------------------------------------------
 * Fires the post-showing feedback text at the exact moment a showing starts.
 *
 * Architecture (per-showing Durable Object alarms):
 *   1. When a showing is booked, prepare_showing in lofty_api.py POSTs to
 *      /enqueue. This Worker writes the entry to KV at queue:<showing_key>
 *      (the listing index, used by list_pending_showings) AND creates a
 *      ShowingTimer Durable Object instance keyed by showing_key. The DO
 *      stores the entry payload and calls state.storage.setAlarm(send_at).
 *   2. Cloudflare wakes the DO at send_at to the second, no polling. The
 *      DO's alarm() handler runs, sends the SMS via Lofty, marks the KV
 *      entry as "sent" for audit, then deleteAll()s its own storage.
 *   3. Cancellation: DELETE /queue/<key> removes the KV entry AND tells the
 *      DO to deleteAlarm() and self-cleanup.
 *   4. Listing pending showings: GET /queue?lead_id=<id> reads the KV index.
 *      DO instances cannot be enumerated, so KV is the source of truth for
 *      "what is queued". The DO is the precision scheduler, KV is the index.
 *
 * Why DO alarms beat the older cron approach:
 *   - Cron-driven Workers wake every minute (1,440/day idle) regardless of
 *     work. DO alarms wake exactly once per showing, at the right moment.
 *   - Precision goes from "within a minute" to "within a few seconds".
 *   - No catch-up window logic, no stale checks, no per-minute KV scan.
 *   - Requires Workers Paid plan ($5/month) because DOs are paid-only.
 *
 * SETUP (see references/workers_setup.md Tier 3 section for the full walkthrough):
 *   1. Cloudflare Workers Paid plan enabled on the deploying account.
 *   2. KV namespace bound as QUEUE (default name: SHOWING_SMS_QUEUE).
 *   3. Durable Object class ShowingTimer bound as SHOWING_DO. Auto-created
 *      on first deploy via the [[migrations]] block in wrangler.showing-sms.toml.
 *   4. Secret: LOFTY_API_KEY (same value as the jotform-to-lofty Worker).
 *   5. Env var: OWNER_FIRST_NAME (the first name that appears in the SMS body;
 *      defaults to "your agent" if unset).
 *   6. Deploy: wrangler deploy -c wrangler.showing-sms.toml
 */

const LOFTY_API_BASE = "https://api.lofty.com/v1.0";
const AUDIT_RETENTION_DAYS = 30;
const ENQUEUE_REQUIRED_FIELDS = [
  "lead_id",
  "send_at",
  "short_url",
  "property_short_address",
];

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (request.method === "GET" && url.pathname === "/") {
      return jsonResponse({
        status: "ok",
        service: "showing-sms",
        architecture: "durable-object-alarms",
      });
    }

    // List queue contents (auth-gated). Optionally filter to a single lead's
    // pending entries via ?lead_id=<id>. Used by lofty_api.py
    // list_pending_showings so cancel_showing can find the right key without
    // re-hitting the MLS.
    if (request.method === "GET" && url.pathname === "/queue") {
      if (!isAuthorized(request, env)) {
        return jsonResponse({ error: "unauthorized" }, 401);
      }
      const leadIdParam = url.searchParams.get("lead_id");
      const leadIdFilter = leadIdParam ? Number(leadIdParam) : null;

      const listing = await env.QUEUE.list({ prefix: "queue:" });
      const entries = [];
      for (const k of listing.keys) {
        const raw = await env.QUEUE.get(k.name);
        const value = raw ? JSON.parse(raw) : null;
        if (leadIdFilter !== null) {
          if (!value) continue;
          if (Number(value.lead_id) !== leadIdFilter) continue;
          if (value.status !== "pending") continue;
        }
        entries.push({ key: k.name, value });
      }
      return jsonResponse({ count: entries.length, entries });
    }

    // Get a single queue entry by showing_key (auth-gated). Returns 404 when
    // missing so callers can distinguish "not queued" from "Worker error".
    if (request.method === "GET" && url.pathname.startsWith("/queue/")) {
      if (!isAuthorized(request, env)) {
        return jsonResponse({ error: "unauthorized" }, 401);
      }
      const showingKey = url.pathname.slice("/queue/".length);
      if (!showingKey) return jsonResponse({ error: "missing key" }, 400);
      const raw = await env.QUEUE.get(kvKeyFor(showingKey));
      if (!raw) return jsonResponse({ error: "not found" }, 404);
      return jsonResponse({ key: kvKeyFor(showingKey), value: JSON.parse(raw) });
    }

    // Enqueue a new pending SMS (called by lofty_api.py prepare_showing).
    // Writes the entry to KV (listing index) AND schedules a Durable Object
    // alarm. Cloudflare wakes the DO at send_at, no polling involved.
    if (request.method === "POST" && url.pathname === "/enqueue") {
      if (!isAuthorized(request, env)) {
        return jsonResponse({ error: "unauthorized" }, 401);
      }
      let body;
      try {
        body = await request.json();
      } catch (e) {
        return jsonResponse({ error: "invalid JSON" }, 400);
      }
      const validation = validateEnqueueBody(body);
      if (validation.error) {
        return jsonResponse({ error: validation.error }, 400);
      }

      // Dedup key: if caller provides showing_key, we upsert under it. That way
      // rescheduling the same showing (same lead + property) updates the entry
      // and reschedules the alarm instead of creating a duplicate. Otherwise
      // generate a fresh uuid.
      const showingKey = body.showing_key || crypto.randomUUID();
      const kvKey = kvKeyFor(showingKey);
      const entry = buildQueueEntry(showingKey, body);

      // Write KV index FIRST so list_pending_showings reflects reality even
      // if the DO call fails (caller will see error and retry).
      await env.QUEUE.put(kvKey, JSON.stringify(entry));

      // Then schedule the DO alarm. If this throws, surface the error so the
      // caller knows the KV row exists but the alarm isn't set.
      try {
        const id = env.SHOWING_DO.idFromName(showingKey);
        const stub = env.SHOWING_DO.get(id);
        const r = await stub.fetch("https://do.internal/schedule", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(entry),
        });
        if (!r.ok) {
          const text = await r.text();
          return jsonResponse({
            error: "DO scheduling failed",
            kv_row_written: true,
            do_status: r.status,
            do_body: text,
          }, 500);
        }
      } catch (e) {
        return jsonResponse({
          error: "DO scheduling threw",
          kv_row_written: true,
          message: String(e),
        }, 500);
      }

      return jsonResponse({ status: "ok", showing_key: showingKey, kv_key: kvKey });
    }

    // Delete a queue entry (for cancellations). Auth-gated.
    // Removes both the KV index row AND the DO alarm so the SMS won't fire.
    if (request.method === "DELETE" && url.pathname.startsWith("/queue/")) {
      if (!isAuthorized(request, env)) {
        return jsonResponse({ error: "unauthorized" }, 401);
      }
      const showingKey = url.pathname.slice("/queue/".length);
      if (!showingKey) return jsonResponse({ error: "missing key" }, 400);

      // KV first, cheaper and the listing index is what consumers read.
      await env.QUEUE.delete(kvKeyFor(showingKey));

      // Then cancel the DO alarm. If the DO doesn't exist, this is still
      // safe: the stub creates a fresh DO that immediately self-deletes.
      try {
        const id = env.SHOWING_DO.idFromName(showingKey);
        const stub = env.SHOWING_DO.get(id);
        await stub.fetch("https://do.internal/cancel", { method: "POST" });
      } catch (e) {
        return jsonResponse({
          error: "DO cancel threw",
          kv_row_deleted: true,
          message: String(e),
        }, 500);
      }

      return jsonResponse({ status: "ok", deleted: showingKey });
    }

    return jsonResponse({ error: "not found" }, 404);
  },
};

/**
 * ShowingTimer - one Durable Object instance per showing.
 *
 * Stores the queue entry in DO storage, sets an alarm for send_at, and
 * fires alarm() when Cloudflare wakes it at the right moment. After
 * sending, marks the KV index entry as "sent" and deletes its own state.
 *
 * Lifecycle:
 *   /schedule -> store entry, setAlarm(send_at)
 *   /cancel   -> deleteAlarm, deleteAll
 *   alarm()   -> send SMS, mark KV "sent", deleteAll
 */
export class ShowingTimer {
  constructor(state, env) {
    this.state = state;
    this.env = env;
  }

  async fetch(request) {
    const url = new URL(request.url);

    if (request.method === "POST" && url.pathname === "/schedule") {
      let entry;
      try {
        entry = await request.json();
      } catch (e) {
        return jsonResponse({ error: "invalid JSON" }, 400);
      }
      const sendAtMs = Date.parse(entry.send_at);
      if (isNaN(sendAtMs)) {
        return jsonResponse({ error: "invalid send_at" }, 400);
      }
      await this.state.storage.put("entry", entry);
      // setAlarm replaces any prior alarm, so reschedules are upserts.
      await this.state.storage.setAlarm(sendAtMs);
      return jsonResponse({ status: "ok", scheduled_for: entry.send_at });
    }

    if (request.method === "POST" && url.pathname === "/cancel") {
      await this.state.storage.deleteAlarm();
      await this.state.storage.deleteAll();
      return jsonResponse({ status: "ok", cancelled: true });
    }

    return jsonResponse({ error: "not found" }, 404);
  }

  // Cloudflare wakes the DO at the alarm time. Send the SMS, mark KV
  // for audit, then clean up. No catch-up logic needed: if Cloudflare
  // missed the alarm (extremely rare), it fires as soon as the platform
  // recovers, which is fine for showing-feedback texts.
  async alarm() {
    const entry = await this.state.storage.get("entry");
    if (!entry) {
      // Nothing to send: someone cancelled between alarm fire and now,
      // or storage is corrupt. Either way, just clean up.
      await this.state.storage.deleteAll();
      return;
    }

    const kvKey = kvKeyFor(entry.showing_key);

    try {
      // Re-fetch the lead so we have current phone (defensive against
      // mid-week edits in Lofty).
      const lead = await fetchLead(this.env.LOFTY_API_KEY, entry.lead_id);
      if (!lead) {
        await markKv(this.env, kvKey, entry, "skipped_no_lead");
        await this.state.storage.deleteAll();
        return;
      }
      const phone = (lead.phones && lead.phones[0]) || entry.phone;
      if (!phone) {
        await markKv(this.env, kvKey, entry, "skipped_no_phone");
        await this.state.storage.deleteAll();
        return;
      }

      const firstName = (lead.firstName || entry.buyer_first_name || "there").trim();
      const ownerFirstName = (this.env.OWNER_FIRST_NAME || "your agent").trim();
      const message = buildSmsBody(
        firstName,
        ownerFirstName,
        entry.property_short_address,
        entry.short_url
      );
      const smsResult = await sendLoftySms(
        this.env.LOFTY_API_KEY,
        entry.lead_id,
        message
      );

      entry.status = "sent";
      entry.sent_at = new Date().toISOString();
      entry.sms_result = smsResult;
      entry.sent_to_phone = phone;
      entry.sent_message = message;

      await this.env.QUEUE.put(kvKey, JSON.stringify(entry), {
        expirationTtl: AUDIT_RETENTION_DAYS * 86400,
      });
    } catch (e) {
      entry.status = "error";
      entry.error = String(e);
      entry.errored_at = new Date().toISOString();
      await this.env.QUEUE.put(kvKey, JSON.stringify(entry));
    } finally {
      // Always release DO storage so the instance hibernates and bills zero.
      await this.state.storage.deleteAll();
    }
  }
}

// ---------- helpers (module-scope, lift-friendly for tests) ----------

function isAuthorized(request, env) {
  const auth = request.headers.get("Authorization") || "";
  return Boolean(env.LOFTY_API_KEY) && auth === "Bearer " + env.LOFTY_API_KEY;
}

function kvKeyFor(showingKey) {
  return `queue:${showingKey}`;
}

function validateEnqueueBody(body) {
  if (!body || typeof body !== "object") {
    return { error: "body must be a JSON object" };
  }
  for (const f of ENQUEUE_REQUIRED_FIELDS) {
    if (!body[f]) return { error: `missing field: ${f}` };
  }
  const sendAtMs = Date.parse(body.send_at);
  if (isNaN(sendAtMs)) {
    return { error: "invalid send_at timestamp" };
  }
  return { ok: true, sendAtMs };
}

function buildQueueEntry(showingKey, body) {
  return {
    showing_key: showingKey,
    send_at: body.send_at,
    lead_id: body.lead_id,
    phone: body.phone || "",
    buyer_first_name: body.buyer_first_name || "",
    short_url: body.short_url,
    property_short_address: body.property_short_address,
    status: "pending",
    created_at: new Date().toISOString(),
  };
}

async function markKv(env, kvKey, entry, status) {
  entry.status = status;
  entry.skipped_at = new Date().toISOString();
  await env.QUEUE.put(kvKey, JSON.stringify(entry), {
    expirationTtl: AUDIT_RETENTION_DAYS * 86400,
  });
}

function buildSmsBody(firstName, ownerFirstName, propertyShortAddress, shortUrl) {
  return `Hi ${firstName}, it's ${ownerFirstName}. Quick feedback form for ${propertyShortAddress} while it's fresh. Takes 2 min: ${shortUrl}`;
}

async function fetchLead(apiKey, leadId) {
  const r = await fetch(`${LOFTY_API_BASE}/leads/${leadId}`, {
    method: "GET",
    headers: {
      Authorization: "token " + apiKey,
      Accept: "application/json",
    },
  });
  if (r.status === 404) return null;
  if (!r.ok) {
    throw new Error(`Lofty getLead ${r.status}: ${await r.text()}`);
  }
  const body = await r.json();
  // Lofty wraps single-lead responses in {"lead": {...}}
  return body.lead || body;
}

async function sendLoftySms(apiKey, leadId, content) {
  const r = await fetch(`${LOFTY_API_BASE}/message/sms/send`, {
    method: "POST",
    headers: {
      Authorization: "token " + apiKey,
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({ leadId: Number(leadId), content }),
  });
  const text = await r.text();
  if (!r.ok) {
    throw new Error(`Lofty sendSms ${r.status}: ${text}`);
  }
  try {
    return JSON.parse(text);
  } catch (e) {
    return { raw: text };
  }
}

function jsonResponse(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

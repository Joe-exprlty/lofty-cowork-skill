/**
 * Leads Index Worker (Tier 4)
 * ----------------------------------------------------
 * Keeps a live mirror of the agent's Lofty leads inside Cloudflare KV,
 * updated via Lofty webhook list 2 (Lead Info: create/update/delete).
 *
 * Why this exists:
 *   Lofty's /v1.0/leads endpoint silently ignores the `keyword` and
 *   `sortField` query parameters. That breaks find_client for any lead
 *   outside the 25 most recently created leads, and breaks the early-stop
 *   logic in get_all_leads_by_visit / get_recent_visits_from_index.
 *
 *   Rather than keep polling a broken endpoint, this Worker flips the
 *   data flow: Lofty pushes events to it via webhook, the Worker keeps
 *   its own index in KV, and the Python client (lofty_api.py) reads from
 *   that index when LOFTY_LEADS_INDEX_SOURCE=worker is set. The index
 *   stays current in real time (delivery SLA is 1-5 minutes per Lofty's
 *   docs) without any polling and without burning agent rate quota.
 *
 *   When LOFTY_LEADS_INDEX_SOURCE is unset or anything other than
 *   "worker", the Python client falls back to data/leads_index.json built
 *   by scripts/refresh_leads_index.py. So this Worker is OPTIONAL: a kit
 *   user can skip the Tier 4 setup entirely and rely on the local file.
 *
 * Tier 4 fits Cloudflare's free Workers plan for any realtor-scale CRM:
 *   - 100k Worker requests/day (typical use: ~50-200/day)
 *   - 1k KV writes/day (content-diff check below keeps this low)
 *   - 100k KV reads/day (Python client caches /export)
 *   - 1 GB KV storage (~1 KB per lead, so 1M leads of headroom)
 * No Workers Paid plan needed. That's Tier 3 only.
 *
 * EFFICIENCY FEATURES (write-side cost controls):
 *   1. Action gating: create/delete always process; updates fall through
 *      to a diff check.
 *   2. Content diff: skip the KV write if none of the find_client-relevant
 *      fields changed. Most "update" events are noise from Lofty's UI
 *      (a tag added, a touch on lastActivity); skipping them saves writes
 *      against the 1k/day free cap.
 *   3. Stage exclusion: DNC / Archived / Agents / Vendors are removed
 *      from KV instead of stored. find_client no longer has to filter
 *      at read time, and excluded leads do not consume KV storage.
 *   4. last_seen_at timestamp stamped on every write so reconciliation
 *      sweeps can detect drift.
 *   5. Skip metrics in _meta:index so the agent can see how noisy the
 *      webhook stream actually is (visible at GET /stats).
 *
 * ROUTES:
 *   GET  /                          Health check. Returns JSON. No auth.
 *   GET  /stats                     Lead count, last event time, skip
 *                                   counters. No auth, no PII.
 *   POST /webhook/<secret>          Lofty webhook receiver. Secret in
 *                                   path prevents random POSTs from
 *                                   injecting fake events.
 *   GET  /export                    Return the full index as JSON.
 *                                   Auth: Authorization: Bearer <EXPORT_API_KEY>
 *                                   Used by lofty_api.py to pull live
 *                                   data on demand.
 *   GET  /lead/<leadId>             Return one lead by ID.
 *                                   Auth: Authorization: Bearer <EXPORT_API_KEY>
 *   POST /bulk-import               Replace the KV index with a fresh
 *                                   scan. Body: { leads: [...] } in the
 *                                   shape produced by refresh_leads_index.py.
 *                                   Auth: Authorization: Bearer <EXPORT_API_KEY>
 *                                   Used on first-time bootstrap and for
 *                                   periodic reconciliation.
 *
 * KV SCHEMA (namespace binding name: LEADS):
 *   lead:<leadId>         JSON of the normalized lead (plus last_seen_at).
 *   _meta:index           { lastEventAt, lastBootstrapAt, eventCount,
 *                           bootstrapCount, skippedNoChange,
 *                           skippedStageExcluded, deletedViaStage }
 *   _meta:ids             JSON array of all leadId strings currently in
 *                         KV (maintained on every write; enables fast
 *                         /export without KV.list pagination).
 *
 * SETUP (see references/workers_setup.md Tier 4 section for the full walkthrough):
 *   1. KV namespace bound as LEADS (default name: LEADS_INDEX).
 *   2. Secret: LOFTY_API_KEY (same value as the jotform-to-lofty and
 *      showing-sms Workers).
 *   3. Secret: WEBHOOK_SECRET (random string; becomes the path segment
 *      on /webhook/<secret>).
 *   4. Secret: EXPORT_API_KEY (random string; the Bearer token the
 *      Python client uses to call /export, /lead/<id>, /bulk-import).
 *   5. Deploy: npx wrangler deploy -c wrangler.leads-index.toml
 *   6. Bootstrap the index from the local file:
 *        python3 scripts/refresh_leads_index.py --push-to-worker
 *   7. Wire Lofty webhook list 2 to the Worker URL:
 *        python3 scripts/lofty_api.py webhook-create 2 \
 *          https://<your-worker>.workers.dev/webhook/<WEBHOOK_SECRET>
 *   8. Set LOFTY_LEADS_INDEX_SOURCE=worker and LEADS_INDEX_WORKER_URL=
 *      https://<your-worker>.workers.dev in your .env so lofty_api.py
 *      reads from the live KV index instead of the local file.
 *
 * EDITING THE CONSTANTS BELOW:
 *   EXCLUDED_STAGES mirrors the safety-rule default that find_client
 *   already filters at read time. If your brokerage uses different stage
 *   names for "do not store these," edit the set below before deploying.
 *
 *   DIFF_FIELDS controls which lead fields trigger a KV write on update.
 *   Adding fields that find_client does not use just costs you writes;
 *   removing fields find_client DOES use causes silently stale data.
 *   Change carefully.
 */

const LOFTY_API_BASE = "https://api.lofty.com/v1.0";

// Stages that should never live in KV. Mirrors the default exclusion list
// that find_client uses at read time, so the filter moves from read-time
// to write-time. Edit if your brokerage uses different stage names.
const EXCLUDED_STAGES = new Set([
  "DNC",
  "Archived",
  "Agents / Vendors",
]);

// The only fields find_client and downstream consumers actually read.
// The content-diff check hashes these. Change this list carefully: if a
// new field becomes load-bearing for find_client and it is not on this
// list, updates to it will be silently dropped until the next bootstrap.
const DIFF_FIELDS = [
  "firstName",
  "lastName",
  "emails",
  "phones",
  "stage",
  "stageId",
  "tags",
  "score",
  "leadSource",
  "source",
  "assignedUserId",
];

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;
    const method = request.method;

    try {
      // Health check.
      if (method === "GET" && path === "/") {
        return jsonResponse({
          status: "ok",
          service: "leads-index",
          host: url.host,
        });
      }

      // Public stats (no PII, safe to expose).
      if (method === "GET" && path === "/stats") {
        return await handleStats(env);
      }

      // Webhook receiver.
      if (method === "POST" && path.startsWith("/webhook/")) {
        const secret = path.slice("/webhook/".length);
        if (!env.WEBHOOK_SECRET || secret !== env.WEBHOOK_SECRET) {
          return jsonResponse({ error: "forbidden" }, 403);
        }
        return await handleWebhook(request, env, ctx);
      }

      // Export full index (Bearer auth).
      if (method === "GET" && path === "/export") {
        if (!isAuthorized(request, env)) {
          return jsonResponse({ error: "unauthorized" }, 401);
        }
        return await handleExport(env);
      }

      // Single lead lookup (Bearer auth).
      if (method === "GET" && path.startsWith("/lead/")) {
        if (!isAuthorized(request, env)) {
          return jsonResponse({ error: "unauthorized" }, 401);
        }
        const leadId = path.slice("/lead/".length);
        return await handleLeadLookup(env, leadId);
      }

      // Bulk import from Python client (Bearer auth).
      if (method === "POST" && path === "/bulk-import") {
        if (!isAuthorized(request, env)) {
          return jsonResponse({ error: "unauthorized" }, 401);
        }
        return await handleBulkImport(request, env);
      }

      return jsonResponse({ error: "not_found", path, method }, 404);
    } catch (err) {
      console.error("Worker error:", err && err.stack || err);
      return jsonResponse({ error: "internal", message: String(err) }, 500);
    }
  },
};

// ══════════════════════════════════════════════════════════
//  HANDLERS
// ══════════════════════════════════════════════════════════

async function handleStats(env) {
  const metaJson = await env.LEADS.get("_meta:index");
  const meta = metaJson ? JSON.parse(metaJson) : {};
  const idsJson = await env.LEADS.get("_meta:ids");
  const ids = idsJson ? JSON.parse(idsJson) : [];
  return jsonResponse({
    status: "ok",
    count: ids.length,
    lastEventAt: meta.lastEventAt || null,
    lastBootstrapAt: meta.lastBootstrapAt || null,
    eventCount: meta.eventCount || 0,
    skippedNoChange: meta.skippedNoChange || 0,
    skippedStageExcluded: meta.skippedStageExcluded || 0,
    deletedViaStage: meta.deletedViaStage || 0,
    bootstrapCount: meta.bootstrapCount || 0,
  });
}

async function handleWebhook(request, env, ctx) {
  let payload = null;
  try {
    payload = await request.json();
  } catch {
    return jsonResponse({ error: "invalid_json" }, 400);
  }

  // Lofty's webhook payload shape for list 2 covers two known forms:
  //   A. Rich: { leadId, event: "create"|"update"|"delete", lead: {...} }
  //   B. Minimal (like list 3): { leadId, updateTime } plus maybe an
  //      event type. In this case we fetch the lead from the API.
  // Either way, normalize to { leadId, event } and reconcile.
  const events = Array.isArray(payload) ? payload : [payload];
  const results = [];
  const metaDeltas = {
    eventCount_delta: events.length,
    skippedNoChange_delta: 0,
    skippedStageExcluded_delta: 0,
    deletedViaStage_delta: 0,
    lastEventAt: nowIso(),
  };

  for (const evt of events) {
    const leadId = extractLeadId(evt);
    if (!leadId) {
      results.push({ skipped: "no_leadId", evt });
      continue;
    }
    const eventType = extractEventType(evt);

    try {
      // Layer 1: action gating. Deletes always process.
      if (eventType === "delete" || eventType === "deleted") {
        await deleteLead(env, leadId);
        results.push({ leadId, event: "delete", ok: true });
        continue;
      }

      // For create/update (or unknown), fetch the authoritative lead.
      // Keeps the worker agnostic to webhook payload shape.
      const lead = await fetchLeadFromLofty(env, leadId);
      if (!lead || !lead.leadId) {
        // Lofty returned 404 or a bad shape. Treat as a delete so KV
        // does not hang on to a ghost entry.
        await deleteLead(env, leadId);
        results.push({ leadId, event: eventType || "update",
                       ok: true, note: "lofty_404_treated_as_delete" });
        continue;
      }

      // Layer 3 (applied before diff): stage exclusion. Excluded leads
      // do not belong in KV. If one is already there (e.g. stage just
      // changed to DNC), drop it now.
      if (EXCLUDED_STAGES.has(lead.stage)) {
        const existing = await env.LEADS.get(`lead:${leadId}`);
        if (existing) {
          await deleteLead(env, leadId);
          metaDeltas.deletedViaStage_delta += 1;
          results.push({ leadId, event: "stage_excluded_delete",
                         stage: lead.stage, ok: true });
        } else {
          metaDeltas.skippedStageExcluded_delta += 1;
          results.push({ leadId, event: "stage_excluded_skip",
                         stage: lead.stage, ok: true });
        }
        continue;
      }

      // Layer 2: content diff. Skip the KV write if none of the
      // find_client-relevant fields changed.
      const existingRaw = await env.LEADS.get(`lead:${leadId}`);
      if (existingRaw) {
        let existing = null;
        try { existing = JSON.parse(existingRaw); } catch {}
        if (existing && diffFieldsEqual(existing, lead)) {
          metaDeltas.skippedNoChange_delta += 1;
          results.push({ leadId, event: "no_change_skip", ok: true });
          continue;
        }
      }

      await upsertLead(env, lead);
      results.push({ leadId, event: eventType || "upsert", ok: true });
    } catch (err) {
      results.push({ leadId, ok: false, error: String(err) });
    }
  }

  ctx.waitUntil(updateMeta(env, metaDeltas));
  return jsonResponse({ received: events.length, results });
}

async function handleExport(env) {
  const idsJson = await env.LEADS.get("_meta:ids");
  const ids = idsJson ? JSON.parse(idsJson) : [];
  const metaJson = await env.LEADS.get("_meta:index");
  const meta = metaJson ? JSON.parse(metaJson) : {};

  // Fetch leads in parallel batches. KV is eventually consistent but
  // fast. Batch size kept small to stay safely inside CPU limits.
  const leads = [];
  const BATCH = 25;
  for (let i = 0; i < ids.length; i += BATCH) {
    const batch = ids.slice(i, i + BATCH);
    const fetched = await Promise.all(
      batch.map((id) => env.LEADS.get(`lead:${id}`))
    );
    for (const raw of fetched) {
      if (!raw) continue;
      try { leads.push(JSON.parse(raw)); } catch {}
    }
  }

  return jsonResponse({
    refreshed_at: nowIso(),
    refreshed_at_epoch_ms: Date.now(),
    count: leads.length,
    source: "leads-index Worker (KV backed)",
    last_event_at: meta.lastEventAt || null,
    last_bootstrap_at: meta.lastBootstrapAt || null,
    leads,
  });
}

async function handleLeadLookup(env, leadId) {
  const raw = await env.LEADS.get(`lead:${leadId}`);
  if (!raw) {
    return jsonResponse({ error: "not_found", leadId }, 404);
  }
  return jsonResponse(JSON.parse(raw));
}

async function handleBulkImport(request, env) {
  let body = null;
  try {
    body = await request.json();
  } catch {
    return jsonResponse({ error: "invalid_json" }, 400);
  }
  const leads = Array.isArray(body) ? body : body.leads;
  if (!Array.isArray(leads)) {
    return jsonResponse({ error: "expected { leads: [...] } or [...]" }, 400);
  }

  // Apply the same stage exclusion at bootstrap time so the initial
  // import does not plant DNC/Archived leads we will never read.
  const ids = [];
  const skippedStage = [];
  const BATCH = 20;
  const now = nowIso();
  for (let i = 0; i < leads.length; i += BATCH) {
    const batch = leads.slice(i, i + BATCH);
    await Promise.all(batch.map((lead) => {
      if (!lead || !lead.leadId) return null;
      if (EXCLUDED_STAGES.has(lead.stage)) {
        skippedStage.push(String(lead.leadId));
        return null;
      }
      const stamped = { ...lead, last_seen_at: now };
      ids.push(String(lead.leadId));
      return env.LEADS.put(`lead:${lead.leadId}`, JSON.stringify(stamped));
    }));
  }

  await env.LEADS.put("_meta:ids", JSON.stringify(ids));
  await updateMeta(env, {
    lastBootstrapAt: now,
    bootstrapCount_delta: 1,
  });

  return jsonResponse({
    imported: ids.length,
    skipped_stage: skippedStage.length,
    skipped_stage_ids: skippedStage,
  });
}

// ══════════════════════════════════════════════════════════
//  LOFTY API
// ══════════════════════════════════════════════════════════

async function fetchLeadFromLofty(env, leadId) {
  if (!env.LOFTY_API_KEY) {
    throw new Error("LOFTY_API_KEY not set");
  }
  const resp = await fetch(`${LOFTY_API_BASE}/leads/${leadId}`, {
    headers: { "Authorization": "token " + env.LOFTY_API_KEY },
  });
  if (resp.status === 404) {
    // Lead was deleted in Lofty between webhook fire and our fetch.
    return null;
  }
  if (!resp.ok) {
    console.error("Lofty fetch failed:", resp.status, await resp.text());
    return null;
  }
  const raw = await resp.json();
  // Lofty wraps single-lead response in { lead: {...} }.
  const lead = raw && raw.lead ? raw.lead : raw;
  return normalizeLead(lead);
}

function normalizeLead(lead) {
  if (!lead || !lead.leadId) return null;
  const first = (lead.firstName || "").trim();
  const last = (lead.lastName || "").trim();
  return {
    leadId: lead.leadId,
    firstName: first,
    lastName: last,
    firstNameLower: first.toLowerCase(),
    lastNameLower: last.toLowerCase(),
    fullNameLower: (first + " " + last).trim().toLowerCase(),
    emails: lead.emails || [],
    phones: lead.phones || [],
    stage: lead.stage || "",
    stageId: lead.stageId || null,
    score: lead.score || 0,
    tags: lead.tags || [],
    leadSource: lead.leadSource || "",
    source: lead.source || "",
    createTime: lead.createTime || "",
    lastVisit: lead.lastVisit || "",
    assignedUser: lead.assignedUser || "",
    assignedUserId: lead.assignedUserId || null,
  };
}

// ══════════════════════════════════════════════════════════
//  DIFF
// ══════════════════════════════════════════════════════════

function diffFieldsEqual(a, b) {
  // Compares only the fields in DIFF_FIELDS. Order-insensitive for arrays.
  for (const field of DIFF_FIELDS) {
    const av = a[field];
    const bv = b[field];
    if (Array.isArray(av) || Array.isArray(bv)) {
      if (!arraysEqualUnordered(av || [], bv || [])) return false;
    } else {
      if ((av || "") !== (bv || "")) return false;
    }
  }
  return true;
}

function arraysEqualUnordered(a, b) {
  if (a.length !== b.length) return false;
  const as = [...a].map(String).sort();
  const bs = [...b].map(String).sort();
  for (let i = 0; i < as.length; i++) {
    if (as[i] !== bs[i]) return false;
  }
  return true;
}

// ══════════════════════════════════════════════════════════
//  KV HELPERS
// ══════════════════════════════════════════════════════════

async function upsertLead(env, lead) {
  const stamped = { ...lead, last_seen_at: nowIso() };
  await env.LEADS.put(`lead:${lead.leadId}`, JSON.stringify(stamped));
  const idsJson = await env.LEADS.get("_meta:ids");
  const ids = idsJson ? JSON.parse(idsJson) : [];
  const idStr = String(lead.leadId);
  if (!ids.includes(idStr)) {
    ids.push(idStr);
    await env.LEADS.put("_meta:ids", JSON.stringify(ids));
  }
}

async function deleteLead(env, leadId) {
  await env.LEADS.delete(`lead:${leadId}`);
  const idsJson = await env.LEADS.get("_meta:ids");
  const ids = idsJson ? JSON.parse(idsJson) : [];
  const filtered = ids.filter((id) => id !== String(leadId));
  if (filtered.length !== ids.length) {
    await env.LEADS.put("_meta:ids", JSON.stringify(filtered));
  }
}

async function updateMeta(env, patch) {
  const current = await env.LEADS.get("_meta:index");
  const meta = current ? JSON.parse(current) : {
    eventCount: 0, bootstrapCount: 0,
    skippedNoChange: 0, skippedStageExcluded: 0, deletedViaStage: 0,
    lastEventAt: null, lastBootstrapAt: null,
  };
  if ("lastEventAt" in patch) meta.lastEventAt = patch.lastEventAt;
  if ("lastBootstrapAt" in patch) meta.lastBootstrapAt = patch.lastBootstrapAt;
  for (const k of ["eventCount", "bootstrapCount", "skippedNoChange",
                    "skippedStageExcluded", "deletedViaStage"]) {
    const deltaKey = k + "_delta";
    if (deltaKey in patch) {
      meta[k] = (meta[k] || 0) + patch[deltaKey];
    }
  }
  await env.LEADS.put("_meta:index", JSON.stringify(meta));
}

// ══════════════════════════════════════════════════════════
//  UTILITIES
// ══════════════════════════════════════════════════════════

function extractLeadId(evt) {
  if (!evt || typeof evt !== "object") return null;
  // Covers shapes Lofty might send: flat leadId, nested in data, or a
  // bare lead object with leadId at top level.
  return evt.leadId || (evt.data && evt.data.leadId) ||
         (evt.lead && evt.lead.leadId) || null;
}

function extractEventType(evt) {
  if (!evt || typeof evt !== "object") return null;
  // Common field names; normalize to lowercase.
  const raw = evt.event || evt.eventType || evt.type || evt.action ||
              (evt.data && (evt.data.event || evt.data.eventType)) || null;
  return raw ? String(raw).toLowerCase() : null;
}

function isAuthorized(request, env) {
  if (!env.EXPORT_API_KEY) return false;
  const header = request.headers.get("Authorization") || "";
  const [scheme, token] = header.split(" ", 2);
  return scheme === "Bearer" && token === env.EXPORT_API_KEY;
}

function jsonResponse(obj, status = 200) {
  return new Response(JSON.stringify(obj, null, 2), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
}

function nowIso() {
  return new Date().toISOString();
}

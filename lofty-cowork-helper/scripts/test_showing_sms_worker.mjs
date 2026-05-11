// Smoke test for the Tier 3 showing_sms_worker.js port.
// Validates the deterministic helper functions that survived the
// production-to-public port: auth check, KV key shape, request
// validation, queue entry build, and SMS body format. These tests run
// in plain Node (no Cloudflare account, no network) and are the Layer 1
// of the Tier 3 test pyramid documented in references/workers_setup.md.
//
// Run: node lofty-cowork-helper/scripts/test_showing_sms_worker.mjs
//
// Layer 2 (wrangler dev --local) and Layer 3 (separate Worker name on a
// Workers Paid account) catch what unit tests cannot: DO alarm timing,
// real KV reads, real Lofty SMS delivery.

import { readFileSync, writeFileSync, unlinkSync, mkdtempSync, rmSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { tmpdir } from "node:os";

const here = dirname(fileURLToPath(import.meta.url));
const workerPath = resolve(here, "..", "workers", "showing_sms_worker.js");

// Lift module-scope helpers out of the Worker source by appending an
// export block. Same trick used by test_worker_parsers.mjs for Tier 2.
const src = readFileSync(workerPath, "utf8");
const wrapper =
  src +
  "\nexport { isAuthorized, kvKeyFor, validateEnqueueBody, " +
  "buildQueueEntry, buildSmsBody, ENQUEUE_REQUIRED_FIELDS };\n";

const tmpDir = mkdtempSync(resolve(tmpdir(), "showing-sms-test-"));
const tmpPath = resolve(tmpDir, "wrapped.mjs");
writeFileSync(tmpPath, wrapper);

let mod;
try {
  mod = await import(tmpPath);
} finally {
  try { unlinkSync(tmpPath); } catch {}
  try { rmSync(tmpDir, { recursive: true, force: true }); } catch {}
}

const {
  isAuthorized,
  kvKeyFor,
  validateEnqueueBody,
  buildQueueEntry,
  buildSmsBody,
  ENQUEUE_REQUIRED_FIELDS,
} = mod;

// ---------- test runner (matches test_worker_parsers.mjs style) ----------

let passed = 0;
let failed = 0;

function assert(name, actual, expected) {
  const ok = JSON.stringify(actual) === JSON.stringify(expected);
  if (ok) {
    console.log(`PASS ${name}`);
    passed++;
  } else {
    console.log(`FAIL ${name}`);
    console.log(`  expected: ${JSON.stringify(expected)}`);
    console.log(`  actual:   ${JSON.stringify(actual)}`);
    failed++;
  }
}

function assertContains(name, actual, needle) {
  const ok = typeof actual === "string" && actual.includes(needle);
  if (ok) {
    console.log(`PASS ${name}`);
    passed++;
  } else {
    console.log(`FAIL ${name}`);
    console.log(`  expected to contain: ${JSON.stringify(needle)}`);
    console.log(`  actual:              ${JSON.stringify(actual)}`);
    failed++;
  }
}

// ---------- isAuthorized ----------

console.log("\n--- isAuthorized ----------");

function fakeRequest(authHeader) {
  return {
    headers: {
      get(name) {
        if (name === "Authorization") return authHeader || null;
        return null;
      },
    },
  };
}

assert(
  "auth.valid-bearer",
  isAuthorized(fakeRequest("Bearer abc123"), { LOFTY_API_KEY: "abc123" }),
  true
);
assert(
  "auth.missing-header",
  isAuthorized(fakeRequest(null), { LOFTY_API_KEY: "abc123" }),
  false
);
assert(
  "auth.wrong-key",
  isAuthorized(fakeRequest("Bearer wrong"), { LOFTY_API_KEY: "abc123" }),
  false
);
assert(
  "auth.token-scheme-rejected",
  isAuthorized(fakeRequest("token abc123"), { LOFTY_API_KEY: "abc123" }),
  false
);
assert(
  "auth.env-key-missing",
  isAuthorized(fakeRequest("Bearer abc123"), {}),
  false
);
assert(
  "auth.env-key-empty-string",
  isAuthorized(fakeRequest("Bearer "), { LOFTY_API_KEY: "" }),
  false
);

// ---------- kvKeyFor ----------

console.log("\n--- kvKeyFor ----------");

assert("kv.basic", kvKeyFor("abc-123"), "queue:abc-123");
assert("kv.uuid-shape", kvKeyFor("8a7b6c5d-1234-5678-9abc-def012345678"),
       "queue:8a7b6c5d-1234-5678-9abc-def012345678");
assert("kv.empty", kvKeyFor(""), "queue:");

// ---------- validateEnqueueBody ----------

console.log("\n--- validateEnqueueBody ----------");

const validBody = {
  lead_id: 1142635515796067,
  send_at: "2026-05-15T14:30:00-07:00",
  short_url: "https://sng.link/abc",
  property_short_address: "11513 SW Bambi Ln",
};

assert(
  "validate.happy-path",
  validateEnqueueBody(validBody).ok,
  true
);
assert(
  "validate.parses-send-at-to-ms",
  typeof validateEnqueueBody(validBody).sendAtMs,
  "number"
);
assert(
  "validate.rejects-null-body",
  validateEnqueueBody(null).error,
  "body must be a JSON object"
);
assert(
  "validate.rejects-string-body",
  validateEnqueueBody("nope").error,
  "body must be a JSON object"
);

for (const field of ENQUEUE_REQUIRED_FIELDS) {
  const missing = { ...validBody };
  delete missing[field];
  assert(
    `validate.missing-${field}`,
    validateEnqueueBody(missing).error,
    `missing field: ${field}`
  );
}

assert(
  "validate.invalid-send-at",
  validateEnqueueBody({ ...validBody, send_at: "not a date" }).error,
  "invalid send_at timestamp"
);

// ---------- buildQueueEntry ----------

console.log("\n--- buildQueueEntry ----------");

const entry = buildQueueEntry("test-key-123", {
  lead_id: 1142635515796067,
  send_at: "2026-05-15T14:30:00-07:00",
  short_url: "https://sng.link/abc",
  property_short_address: "11513 SW Bambi Ln",
  phone: "503-555-0100",
  buyer_first_name: "Jack",
});

assert("entry.showing_key", entry.showing_key, "test-key-123");
assert("entry.send_at", entry.send_at, "2026-05-15T14:30:00-07:00");
assert("entry.lead_id", entry.lead_id, 1142635515796067);
assert("entry.short_url", entry.short_url, "https://sng.link/abc");
assert("entry.property_short_address", entry.property_short_address, "11513 SW Bambi Ln");
assert("entry.phone", entry.phone, "503-555-0100");
assert("entry.buyer_first_name", entry.buyer_first_name, "Jack");
assert("entry.status-pending", entry.status, "pending");
assert("entry.created_at-present", typeof entry.created_at, "string");

// Missing optionals default to empty strings (preserves prior wire shape).
const entryWithoutOptionals = buildQueueEntry("k", {
  lead_id: 1,
  send_at: "2026-05-15T14:30:00-07:00",
  short_url: "https://x",
  property_short_address: "addr",
});
assert("entry.phone-default-empty", entryWithoutOptionals.phone, "");
assert("entry.buyer-name-default-empty", entryWithoutOptionals.buyer_first_name, "");

// ---------- buildSmsBody ----------

console.log("\n--- buildSmsBody ----------");

const body = buildSmsBody("Jack", "Joe", "11513 SW Bambi Ln", "https://sng.link/abc");
assertContains("sms.contains-client-name", body, "Hi Jack");
assertContains("sms.contains-owner-name", body, "it's Joe");
assertContains("sms.contains-address", body, "11513 SW Bambi Ln");
assertContains("sms.contains-url", body, "https://sng.link/abc");
assertContains("sms.contains-time-cue", body, "2 min");
assert(
  "sms.full-format",
  body,
  "Hi Jack, it's Joe. Quick feedback form for 11513 SW Bambi Ln while it's fresh. Takes 2 min: https://sng.link/abc"
);

// Owner name is configurable. Default-fallback case (env unset) handled
// by the alarm() caller; here we just verify the parameter flows through.
const bodyDifferentOwner = buildSmsBody("Sarah", "Pat", "12 Main St", "https://x");
assertContains("sms.different-owner", bodyDifferentOwner, "it's Pat");

// ---------- summary ----------

console.log(`\n${passed} passed, ${failed} failed.`);
if (failed > 0) {
  console.log("Showing-SMS smoke test FAILED.");
  process.exit(1);
}
console.log("All Tier 3 parser smoke tests passed.");

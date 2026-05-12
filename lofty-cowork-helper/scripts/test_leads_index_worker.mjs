// Smoke test for the Tier 4 leads_index_worker.js port.
// Validates the deterministic helper functions that survived the
// production-to-public port: Bearer auth check, lead/event extraction
// from variable webhook payload shapes, lead normalization, content-diff
// field comparison, and array equality. These tests run in plain Node
// (no Cloudflare account, no network) and are Layer 1 of the Tier 4 test
// pyramid documented in references/workers_setup.md.
//
// Run: node lofty-cowork-helper/scripts/test_leads_index_worker.mjs
//
// Layer 2 (wrangler deploy to a staging Worker name + curl smoke test)
// and Layer 3 (real Lofty webhook list 2 + KV round trip via the Python
// client) catch what unit tests cannot: KV consistency timing, real
// webhook payload shape, and end-to-end pickup by lofty_api.py with
// LOFTY_LEADS_INDEX_SOURCE=worker.

import { readFileSync, writeFileSync, unlinkSync, mkdtempSync, rmSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { tmpdir } from "node:os";

const here = dirname(fileURLToPath(import.meta.url));
const workerPath = resolve(here, "..", "workers", "leads_index_worker.js");

// Lift module-scope helpers out of the Worker source by appending an
// export block. Same trick used by test_worker_parsers.mjs (Tier 2) and
// test_showing_sms_worker.mjs (Tier 3).
const src = readFileSync(workerPath, "utf8");
const wrapper =
  src +
  "\nexport { isAuthorized, extractLeadId, extractEventType, " +
  "normalizeLead, diffFieldsEqual, arraysEqualUnordered, " +
  "EXCLUDED_STAGES, DIFF_FIELDS };\n";

const tmpDir = mkdtempSync(resolve(tmpdir(), "leads-index-test-"));
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
  extractLeadId,
  extractEventType,
  normalizeLead,
  diffFieldsEqual,
  arraysEqualUnordered,
  EXCLUDED_STAGES,
  DIFF_FIELDS,
} = mod;

// ---------- test runner (matches test_showing_sms_worker.mjs style) ----------

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

function makeRequest(authHeader) {
  // Minimal Request shim: only the headers.get() method is exercised by
  // isAuthorized, so a hand-rolled Map-backed object is enough.
  return {
    headers: {
      get(name) {
        if (name === "Authorization" || name === "authorization") {
          return authHeader || null;
        }
        return null;
      },
    },
  };
}

// ══════════════════════════════════════════════════════════
//  isAuthorized
// ══════════════════════════════════════════════════════════

console.log("\n--- isAuthorized ----------");

assert(
  "auth.valid-bearer",
  isAuthorized(makeRequest("Bearer test-secret-123"), { EXPORT_API_KEY: "test-secret-123" }),
  true
);

assert(
  "auth.missing-header",
  isAuthorized(makeRequest(null), { EXPORT_API_KEY: "test-secret-123" }),
  false
);

assert(
  "auth.wrong-key",
  isAuthorized(makeRequest("Bearer wrong-key"), { EXPORT_API_KEY: "test-secret-123" }),
  false
);

assert(
  "auth.token-scheme-rejected",
  isAuthorized(makeRequest("token test-secret-123"), { EXPORT_API_KEY: "test-secret-123" }),
  false
);

assert(
  "auth.env-key-missing",
  isAuthorized(makeRequest("Bearer anything"), {}),
  false
);

assert(
  "auth.env-key-empty-string",
  isAuthorized(makeRequest("Bearer "), { EXPORT_API_KEY: "" }),
  false
);

// ══════════════════════════════════════════════════════════
//  extractLeadId
// ══════════════════════════════════════════════════════════

console.log("\n--- extractLeadId ----------");

assert(
  "extractLeadId.flat",
  extractLeadId({ leadId: "12345", event: "update" }),
  "12345"
);

assert(
  "extractLeadId.nested-in-data",
  extractLeadId({ data: { leadId: "67890" }, event: "update" }),
  "67890"
);

assert(
  "extractLeadId.nested-in-lead",
  extractLeadId({ lead: { leadId: "11111", firstName: "Jane" } }),
  "11111"
);

assert(
  "extractLeadId.numeric-passes-through",
  extractLeadId({ leadId: 42 }),
  42
);

assert(
  "extractLeadId.null-input",
  extractLeadId(null),
  null
);

assert(
  "extractLeadId.no-leadId-anywhere",
  extractLeadId({ event: "update", someOther: "field" }),
  null
);

// ══════════════════════════════════════════════════════════
//  extractEventType
// ══════════════════════════════════════════════════════════

console.log("\n--- extractEventType ----------");

assert("extractEventType.event-field", extractEventType({ event: "Update" }), "update");
assert("extractEventType.eventType-field", extractEventType({ eventType: "DELETE" }), "delete");
assert("extractEventType.type-field", extractEventType({ type: "Create" }), "create");
assert("extractEventType.action-field", extractEventType({ action: "UPDATE" }), "update");
assert("extractEventType.nested-data-event", extractEventType({ data: { event: "delete" } }), "delete");
assert("extractEventType.missing", extractEventType({ leadId: "x" }), null);
assert("extractEventType.null-input", extractEventType(null), null);

// ══════════════════════════════════════════════════════════
//  normalizeLead
// ══════════════════════════════════════════════════════════

console.log("\n--- normalizeLead ----------");

const richLead = normalizeLead({
  leadId: "999",
  firstName: "  Jane  ",
  lastName: "  Smith  ",
  emails: ["jane@example.com"],
  phones: ["+15035551212"],
  stage: "Active Buyer",
  stageId: 100,
  score: 80,
  tags: ["motivated"],
  leadSource: "Zillow",
  source: "web",
  createTime: "2026-01-01T00:00:00Z",
  lastVisit: "2026-05-01T00:00:00Z",
  assignedUser: "Agent A",
  assignedUserId: 42,
});

assert("normalizeLead.leadId-preserved", richLead.leadId, "999");
assert("normalizeLead.firstName-trimmed", richLead.firstName, "Jane");
assert("normalizeLead.lastName-trimmed", richLead.lastName, "Smith");
assert("normalizeLead.firstNameLower", richLead.firstNameLower, "jane");
assert("normalizeLead.lastNameLower", richLead.lastNameLower, "smith");
assert("normalizeLead.fullNameLower", richLead.fullNameLower, "jane smith");
assert("normalizeLead.emails-passthrough", richLead.emails, ["jane@example.com"]);
assert("normalizeLead.phones-passthrough", richLead.phones, ["+15035551212"]);
assert("normalizeLead.stage", richLead.stage, "Active Buyer");
assert("normalizeLead.stageId", richLead.stageId, 100);
assert("normalizeLead.score", richLead.score, 80);
assert("normalizeLead.tags", richLead.tags, ["motivated"]);
assert("normalizeLead.assignedUserId", richLead.assignedUserId, 42);

const sparseLead = normalizeLead({ leadId: "1", firstName: "Bob" });
assert("normalizeLead.sparse.firstName", sparseLead.firstName, "Bob");
assert("normalizeLead.sparse.lastName-default", sparseLead.lastName, "");
assert("normalizeLead.sparse.emails-default", sparseLead.emails, []);
assert("normalizeLead.sparse.phones-default", sparseLead.phones, []);
assert("normalizeLead.sparse.stage-default", sparseLead.stage, "");
assert("normalizeLead.sparse.stageId-default-null", sparseLead.stageId, null);
assert("normalizeLead.sparse.score-default-zero", sparseLead.score, 0);
assert("normalizeLead.sparse.tags-default", sparseLead.tags, []);
assert("normalizeLead.sparse.fullNameLower", sparseLead.fullNameLower, "bob");

assert("normalizeLead.null-input", normalizeLead(null), null);
assert("normalizeLead.missing-leadId", normalizeLead({ firstName: "no id" }), null);

// ══════════════════════════════════════════════════════════
//  diffFieldsEqual
// ══════════════════════════════════════════════════════════

console.log("\n--- diffFieldsEqual ----------");

const baseLead = {
  leadId: "1",
  firstName: "Jane",
  lastName: "Smith",
  emails: ["jane@example.com"],
  phones: ["+15035551212"],
  stage: "Active Buyer",
  stageId: 100,
  tags: ["motivated", "buyer"],
  score: 80,
  leadSource: "Zillow",
  source: "web",
  assignedUserId: 42,
  // Fields NOT in DIFF_FIELDS that should NOT cause a diff:
  lastVisit: "2026-05-01T00:00:00Z",
  createTime: "2026-01-01T00:00:00Z",
  last_seen_at: "2026-05-11T20:00:00Z",
};

const sameLead = { ...baseLead };
assert("diffFieldsEqual.identical", diffFieldsEqual(baseLead, sameLead), true);

const nonDiffChange = { ...baseLead, lastVisit: "2026-05-11T12:00:00Z" };
assert(
  "diffFieldsEqual.non-diff-field-changes-ignored",
  diffFieldsEqual(baseLead, nonDiffChange),
  true
);

const lastSeenChange = { ...baseLead, last_seen_at: "2026-05-11T21:00:00Z" };
assert(
  "diffFieldsEqual.last_seen_at-not-in-diff",
  diffFieldsEqual(baseLead, lastSeenChange),
  true
);

const tagsReordered = { ...baseLead, tags: ["buyer", "motivated"] };
assert(
  "diffFieldsEqual.tag-reorder-equal",
  diffFieldsEqual(baseLead, tagsReordered),
  true
);

const stageChange = { ...baseLead, stage: "Past Client" };
assert("diffFieldsEqual.stage-change-detected", diffFieldsEqual(baseLead, stageChange), false);

const phoneAdded = { ...baseLead, phones: ["+15035551212", "+15035551213"] };
assert("diffFieldsEqual.phone-added-detected", diffFieldsEqual(baseLead, phoneAdded), false);

const tagAdded = { ...baseLead, tags: ["motivated", "buyer", "new-tag"] };
assert("diffFieldsEqual.tag-added-detected", diffFieldsEqual(baseLead, tagAdded), false);

const scoreChange = { ...baseLead, score: 90 };
assert("diffFieldsEqual.score-change-detected", diffFieldsEqual(baseLead, scoreChange), false);

const firstNameChange = { ...baseLead, firstName: "Janet" };
assert("diffFieldsEqual.firstName-change-detected", diffFieldsEqual(baseLead, firstNameChange), false);

// ══════════════════════════════════════════════════════════
//  arraysEqualUnordered
// ══════════════════════════════════════════════════════════

console.log("\n--- arraysEqualUnordered ----------");

assert("arraysEqual.same-order", arraysEqualUnordered(["a", "b", "c"], ["a", "b", "c"]), true);
assert("arraysEqual.reordered", arraysEqualUnordered(["a", "b", "c"], ["c", "a", "b"]), true);
assert("arraysEqual.different-length", arraysEqualUnordered(["a", "b"], ["a", "b", "c"]), false);
assert("arraysEqual.different-content", arraysEqualUnordered(["a", "b"], ["a", "c"]), false);
assert("arraysEqual.empty-both", arraysEqualUnordered([], []), true);
assert("arraysEqual.empty-one-side", arraysEqualUnordered([], ["a"]), false);
assert(
  "arraysEqual.numeric-string-coerced",
  arraysEqualUnordered([1, 2, 3], ["1", "2", "3"]),
  true
);

// ══════════════════════════════════════════════════════════
//  Constants (sanity check on the safety-rule defaults)
// ══════════════════════════════════════════════════════════

console.log("\n--- constants ----------");

assert(
  "EXCLUDED_STAGES.has-DNC",
  EXCLUDED_STAGES.has("DNC"),
  true
);

assert(
  "EXCLUDED_STAGES.has-Archived",
  EXCLUDED_STAGES.has("Archived"),
  true
);

assert(
  "EXCLUDED_STAGES.has-Agents-Vendors",
  EXCLUDED_STAGES.has("Agents / Vendors"),
  true
);

assert(
  "EXCLUDED_STAGES.active-buyer-not-excluded",
  EXCLUDED_STAGES.has("Active Buyer"),
  false
);

assert(
  "DIFF_FIELDS.includes-stage",
  DIFF_FIELDS.includes("stage"),
  true
);

assert(
  "DIFF_FIELDS.includes-phones",
  DIFF_FIELDS.includes("phones"),
  true
);

assert(
  "DIFF_FIELDS.does-not-include-last_seen_at",
  DIFF_FIELDS.includes("last_seen_at"),
  false
);

assert(
  "DIFF_FIELDS.does-not-include-lastVisit",
  DIFF_FIELDS.includes("lastVisit"),
  false
);

// ══════════════════════════════════════════════════════════
//  Summary
// ══════════════════════════════════════════════════════════

console.log(`\n${passed} passed, ${failed} failed.`);
if (failed > 0) {
  console.error("FAIL: Tier 4 leads-index Worker smoke tests failed.");
  process.exit(1);
}
console.log("All Tier 4 leads-index Worker smoke tests passed.");

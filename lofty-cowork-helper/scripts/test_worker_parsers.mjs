// Smoke test for the jotform_to_lofty_worker.js parser refactor.
// Verifies both the legacy alias-only path AND the new qid-based
// JOTFORM_FIELD_MAP path produce the same routing decisions.
//
// Run: node lofty-cowork-helper/scripts/test_worker_parsers.mjs
//
// This test is read-only and makes no network calls. It synthesizes
// fake Jotform POST payloads and walks them through the Worker's
// parseJotformPost + writeFeedbackRow row-builder logic.

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const workerPath = resolve(here, "..", "workers", "jotform_to_lofty_worker.js");

// Pull out the helper functions we want to test by evaluating the
// Worker source in an isolated context. The Worker uses `export
// default` for the fetch handler, but the helpers are module-scope
// `function` declarations we can lift via a small wrapper.
const src = readFileSync(workerPath, "utf8");
const wrapper =
  src
    .replace(/export default \{/, "const __default = {")
    .replace(/^};?\s*$/m, "};") +
  "\nexport { parseJotformPost, getFieldIdMap, reverseFieldIdMap, " +
  "parseRating, parseText, parseTagList, RATING_FIELDS, TEXT_FIELDS, " +
  "TAG_FIELDS, fieldByColumn, valueByPurpose };\n";

import { writeFileSync, unlinkSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";

// Write the wrapper to a process-scoped tmp dir so the mounted
// repo's permissions don't matter.
const tmpDir = mkdtempSync(resolve(tmpdir(), "worker-test-"));
const tmpPath = resolve(tmpDir, "wrapped.mjs");
writeFileSync(tmpPath, wrapper);

let mod;
try {
  mod = await import(tmpPath);
} finally {
  try { unlinkSync(tmpPath); } catch {}
  try { rmSync(tmpDir, { recursive: true, force: true }); } catch {}
}

// ----- Build a synthetic Jotform POST body in the rawRequest shape -----

function jotformBody(fields) {
  // fields is { qid: { name: string, value: any } }
  const raw = {};
  Object.entries(fields).forEach(([qid, { name, value }]) => {
    raw[`q${qid}_${name}`] = value;
  });
  return new URLSearchParams({ rawRequest: JSON.stringify(raw) });
}

function makeRequest(body) {
  return new Request("http://example/", {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body,
  });
}

// ----- Test data: a legacy form (alias-style names) and a fresh form (snake_case names) -----

const LEGACY_FIELDS = {
  3: { name: "firstReaction",  value: "5" },
  4: { name: "howDid",         value: "4" },
  5: { name: "whatAbout",      value: "3" },
  6: { name: "conditionAnd",   value: "5" },
  7: { name: "atThe",          value: "4" },
  8: { name: "doesThis",       value: "5" },
  9: { name: "whatStood",      value: "Loved the south-facing yard." },
  10: { name: "areThere",      value: "Neighbor mentioned a leaky shed roof." },
  11: { name: "whatYouLoved",  value: ["Yard / outdoor space", "Natural light"] },
  12: { name: "dealbreakers",  value: "Street noise" },
};

const FRESH_FIELDS = {
  21: { name: "first_reaction",      value: "5" },
  22: { name: "daily_life_fit",      value: "4" },
  23: { name: "neighborhood_rating", value: "3" },
  24: { name: "condition_rating",    value: "5" },
  25: { name: "value_rating",        value: "4" },
  26: { name: "short_list",          value: "5" },
  27: { name: "standout_text",       value: "Loved the south-facing yard." },
  28: { name: "memory_notes",        value: "Neighbor mentioned a leaky shed roof." },
  29: { name: "loved_tags",          value: ["Yard / outdoor space", "Natural light"] },
  30: { name: "dealbreaker_tags",    value: "Street noise" },
};

// Field map matching the FRESH_FIELDS layout.
const FRESH_FIELD_MAP = {
  "21": "first_reaction",
  "22": "daily_life_fit",
  "23": "neighborhood_rating",
  "24": "condition_rating",
  "25": "value_rating",
  "26": "short_list",
  "27": "standout_text",
  "28": "memory_notes",
  "29": "loved_tags",
  "30": "dealbreaker_tags",
};

// ----- Run both paths and compare what the parsers extract -----

async function extractedRow(body, fieldMap) {
  const req = makeRequest(body);
  const submission = await mod.parseJotformPost(req);
  const purposeToQid = mod.reverseFieldIdMap(fieldMap);

  const out = {};
  mod.RATING_FIELDS.forEach((f) => {
    out[f.column] = mod.parseRating(submission, f.aliases, f.column, purposeToQid);
  });
  mod.TEXT_FIELDS.forEach((f) => {
    out[f.column] = mod.parseText(submission, f.aliases, f.column, purposeToQid) || null;
  });
  mod.TAG_FIELDS.forEach((f) => {
    const tags = mod.parseTagList(submission, f.aliases, f.column, purposeToQid);
    out[f.column] = tags.length > 0 ? tags : null;
  });
  return out;
}

const legacyRow = await extractedRow(jotformBody(LEGACY_FIELDS), {});
const freshRowAliasOnly = await extractedRow(jotformBody(FRESH_FIELDS), {});
const freshRowWithMap = await extractedRow(jotformBody(FRESH_FIELDS), FRESH_FIELD_MAP);

const expected = {
  first_reaction: 5,
  daily_life_fit: 4,
  neighborhood_rating: 3,
  condition_rating: 5,
  value_rating: 4,
  short_list: 5,
  standout_text: "Loved the south-facing yard.",
  memory_notes: "Neighbor mentioned a leaky shed roof.",
  loved_tags: ["Yard / outdoor space", "Natural light"],
  dealbreaker_tags: ["Street noise"],
};

function assertEqual(label, actual, want) {
  const aStr = JSON.stringify(actual);
  const wStr = JSON.stringify(want);
  if (aStr !== wStr) {
    console.error(`FAIL ${label}: got ${aStr}, want ${wStr}`);
    process.exitCode = 1;
  } else {
    console.log(`PASS ${label}`);
  }
}

console.log("--- Legacy form (no field map, falls back to aliases) ---");
Object.entries(expected).forEach(([k, v]) => assertEqual(`legacy.${k}`, legacyRow[k], v));

console.log("\n--- Fresh form (snake_case names; map empty) ---");
Object.entries(expected).forEach(([k, v]) => assertEqual(`fresh-aliasonly.${k}`, freshRowAliasOnly[k], v));

console.log("\n--- Fresh form (snake_case names; field map populated, qid wins) ---");
Object.entries(expected).forEach(([k, v]) => assertEqual(`fresh-withmap.${k}`, freshRowWithMap[k], v));

// One more case: when the fresh form has DIFFERENT unique names (so
// the alias path would miss) but the field map covers them, qid
// routing should still work.
const RENAMED_FIELDS = {
  101: { name: "gut_reaction",  value: "5" },
  102: { name: "for_my_life",   value: "4" },
};
const RENAMED_MAP = {
  "101": "first_reaction",
  "102": "daily_life_fit",
};
const renamedRow = await extractedRow(jotformBody(RENAMED_FIELDS), RENAMED_MAP);

console.log("\n--- Form with renamed unique names (qid map is the only way) ---");
assertEqual("renamed.first_reaction", renamedRow.first_reaction, 5);
assertEqual("renamed.daily_life_fit", renamedRow.daily_life_fit, 4);

if (process.exitCode === 1) {
  console.error("\nOne or more assertions failed.");
} else {
  console.log("\nAll parser smoke tests passed.");
}

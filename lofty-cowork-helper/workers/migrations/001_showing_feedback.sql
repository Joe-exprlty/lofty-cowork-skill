-- workers/migrations/001_showing_feedback.sql
-- ---------------------------------------------------------------
-- Phase 2: feedback database. One row per post-showing Jotform
-- submission. The jotform-to-lofty Worker writes here after it
-- writes the Lofty note and (optionally) sends the recap email.
--
-- This migration is applied by:
--   wrangler d1 execute showing_feedback \
--     --file workers/migrations/001_showing_feedback.sql --remote
--
-- Design notes:
--  * lead_id is the Lofty numeric id (matches what prepare_showing
--    uses). Indexed because we query it per buyer.
--  * ratings are stored as INTEGER in the 1-5 range. NULL means
--    the buyer did not answer that question.
--  * loved_tags / dealbreaker_tags / claude_tags are JSON arrays
--    stored as TEXT (D1 has no native JSON type). Use
--    json_each() from the buyer aggregation query.
--  * raw_submission keeps the full parsed Jotform payload for
--    audit. If we decide to add a column later we can backfill
--    from here instead of asking the buyer to refill a form.
-- ---------------------------------------------------------------

CREATE TABLE IF NOT EXISTS showing_feedback (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  submitted_at       TEXT NOT NULL,        -- ISO 8601 UTC, e.g. 2026-04-22T18:03:00Z
  lead_id            INTEGER NOT NULL,     -- Lofty lead id
  property_address   TEXT NOT NULL,        -- full address as shown in Jotform
  showing_date       TEXT,                 -- human string from the form ("April 22, 2026")
  first_reaction     INTEGER,              -- 1-5
  daily_life_fit     INTEGER,              -- 1-5
  neighborhood_rating INTEGER,             -- 1-5
  condition_rating   INTEGER,              -- 1-5
  value_rating       INTEGER,              -- 1-5
  short_list         INTEGER,              -- 1-5
  standout_text      TEXT,                 -- "What stood out" free text
  memory_notes       TEXT,                 -- "Other things to remember" free text
  loved_tags         TEXT,                 -- JSON array, e.g. ["yard","natural light"]
  dealbreaker_tags   TEXT,                 -- JSON array, e.g. ["street noise"]
  claude_tags        TEXT,                 -- JSON array, reserved for future LLM extraction
  raw_submission     TEXT                  -- JSON blob of the full parsed Jotform payload
);

CREATE INDEX IF NOT EXISTS idx_showing_feedback_lead_id
  ON showing_feedback(lead_id);

CREATE INDEX IF NOT EXISTS idx_showing_feedback_submitted_at
  ON showing_feedback(submitted_at);

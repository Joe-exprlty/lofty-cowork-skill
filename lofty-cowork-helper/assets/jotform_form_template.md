# Jotform Form Template (FALLBACK procedure - v1.5 create_form path)

> **Heads up.** As of v1.6 this is the **fallback** path, not the primary one. The primary v1.6 setup uses the **template-clone** flow described in `references/workers_setup.md` (clone a polished public template URL into your Jotform account in one click). Use this `create_form` procedure only if:
> - The template URL is unavailable.
> - Your Jotform account can't clone shared templates.
> - You have a strong reason to build the form from scratch.
>
> The `create_form` agent ships Classic Forms with mediocre visual polish, normalizes hidden field names to lowercase, and does not reliably apply theme colors. It works, but expect to spend 5-10 minutes on follow-up `edit_form` calls. The clone path takes one click.

This file is read at install time by the Easy Mode Tier 2 setup flow when fallback is selected. It contains the natural-language prompt Claude passes to Jotform MCP's `create_form`, the post-creation introspection steps, and the expected shape of `JOTFORM_FIELD_MAP` (the env var the Worker reads to route submissions to the right D1 column).

This file is NOT loaded by the Worker at runtime. It's a setup-time artifact.

## Inputs Easy Mode collects from the user before calling create_form

- `accent_color` (hex string, e.g. `#D4AF37`). Default: read `default_accent_color` from `assets/post_showing_questions.yaml`.
- `text_color` (hex string, e.g. `#1a1a1a`). Default: read `default_text_color` from the YAML.
- `logo_url` (string or null). Default: null. If non-null, must be a publicly fetchable HTTPS URL.

## Step 1: Render the header HTML

Read `assets/post_showing_questions.yaml`. Substitute these tokens in `form_metadata.header_html`:

| Token | Value |
|-------|-------|
| `{{ACCENT_COLOR}}` | the user's accent color hex |
| `{{TEXT_COLOR}}` | the user's text color hex |
| `{{LOGO_HTML}}` | if logo_url is set: `<img src="<logo_url>" alt="" style="max-height:64px;margin:0 auto 12px;display:block;">` ; else: empty string |

The header HTML still contains Jotform-prefill placeholders (`{propertyAddress}`, `{propertyStats}`, `{showingDate}`). Those stay literal; Jotform substitutes them per submission from the prefilled hidden fields.

## Step 2: Compose the create_form description

Pass this natural-language description to `mcp__fb185796-3f32-4d0b-960a-fb8d0869ca9c__create_form`. Inline the rendered header HTML and the desired accent color directly into the description.

```
Create a Jotform form for collecting post-showing property feedback from
real estate buyers. Form title: "Post-Showing Property Feedback".
Form description: "We'd love your honest take. Two minutes, makes a real
difference."

The form should use this branded header HTML at the top:
<RENDERED_HEADER_HTML>

Apply this color theme: primary accent color <ACCENT_COLOR>,
heading text color <TEXT_COLOR>. Buttons, rating stars, and chip
backgrounds should pick up the accent color.

Include these hidden fields (prefilled via URL parameters, never shown
to the buyer): lead_id, client_name, agent_email, propertyAddress,
propertyStats, showingDate, buyer_email.

Then add these visible questions in this exact order:

1. Rating 1-5: "First reaction walking in?" Required. Unique name: first_reaction.

2. Rating 1-5: "How did the home work for your daily life?" Optional. Unique name: daily_life_fit.

3. Rating 1-5: "What about the neighborhood and location?" Optional. Unique name: neighborhood_rating.

4. Rating 1-5: "Condition and move-in readiness?" Optional. Unique name: condition_rating.

5. Rating 1-5: "At the asking price, does this feel like a fair value?" Optional. Unique name: value_rating.

6. Rating 1-5: "Does this home make your short list?" Required. Unique name: short_list.

7. Long text paragraph: "What stood out, good or bad?" Optional. Unique name: standout_text.

8. Long text paragraph: "Anything else to remember about this home?" Optional. Unique name: memory_notes.

9. Multi-select checkboxes (up to 5 selections), prompt: "What you loved (pick up to 5)". Optional. Unique name: loved_tags. Options:
   Open layout, Natural light, Yard / outdoor space, Primary on main,
   Primary suite (upstairs or otherwise), Garage / storage,
   Walkable to amenities, Quiet street, View, Move-in ready,
   Character / charm, Kitchen, Location fit.

10. Multi-select checkboxes (up to 5 selections), prompt: "Dealbreakers (pick up to 5)". Optional. Unique name: dealbreaker_tags. Options:
    Street noise, Small yard, Primary not on main, Garage too small,
    HOA, Too much work needed, Layout chops up, Condition, No view,
    Bad commute, Too close to busy road.

Thank-you message after submission: "Thanks. I'll review this before our next conversation."
```

Capture the `form_id` from the response.

## Step 3: Introspect with fetch

Call `mcp__fb185796-3f32-4d0b-960a-fb8d0869ca9c__fetch` with `id = <form_id>`. The response includes the form's questions array, where each question has `qid` (the numeric field ID), `name` (the unique name), and `text` (the prompt). Capture qid + name + type for each question.

## Step 4: Build JOTFORM_FIELD_MAP

Build a flat object mapping qid -> purpose tag. The purpose tags are the canonical column names (matching the YAML's `purpose` field on each question and the D1 column names). Match by name first; if a question's name doesn't match any expected purpose, fall back to matching by question text against the YAML's prompts.

Expected purposes (these are the only valid values):
- `first_reaction`
- `daily_life_fit`
- `neighborhood_rating`
- `condition_rating`
- `value_rating`
- `short_list`
- `standout_text`
- `memory_notes`
- `loved_tags`
- `dealbreaker_tags`

Resulting shape:

```json
{
  "3": "first_reaction",
  "4": "daily_life_fit",
  "5": "neighborhood_rating",
  "6": "condition_rating",
  "7": "value_rating",
  "8": "short_list",
  "9": "standout_text",
  "10": "memory_notes",
  "11": "loved_tags",
  "12": "dealbreaker_tags"
}
```

Numbers will differ per install. The keys are strings; Jotform's qid is numeric in the fetch response but we store as string to match how the Worker reads them.

## Step 5: Write JOTFORM_FIELD_MAP to wrangler.jotform.toml

Open `workers/wrangler.jotform.toml`. In the `[vars]` block, add or update:

```toml
JOTFORM_FIELD_MAP = '{"3":"first_reaction","4":"daily_life_fit",...}'
```

The value is the JSON-stringified object from step 4. Single-quote the TOML string so embedded double-quotes don't conflict with TOML syntax.

## Step 6: Save form_id to .env

In the user's `.env`, set:

```
JOTFORM_FORM_ID=<form_id_from_step_2>
```

The Python client uses this to build prefilled showing URLs.

## Step 7: Verify with edit_form fixups (only if needed)

Inspect the fetch response from step 3 against the requested structure. Common discrepancies the Jotform agent might introduce:

- Missing hidden fields. Use `edit_form` with: "Add hidden fields named lead_id, client_name, agent_email, propertyAddress, propertyStats, showingDate, buyer_email if any are missing."
- Theme colors not applied. Use `edit_form`: "Set the primary accent color to <ACCENT_COLOR> and the form heading text color to <TEXT_COLOR>."
- Logo missing from header. Use `edit_form`: "Update the form's header to include this HTML: <RENDERED_HEADER_HTML>."

After any edit_form call, re-run fetch and rebuild JOTFORM_FIELD_MAP if any qids changed.

## Step 8: Pass to next install steps

After this template completes, Easy Mode has:

- `form_id` (saved to `.env` as `JOTFORM_FORM_ID`)
- `JOTFORM_FIELD_MAP` (written to `workers/wrangler.jotform.toml` `[vars]`)

The remaining setup steps (D1 creation, secret push, Worker deploy, webhook wire-up) proceed from here per `references/workers_setup.md` Easy Mode walkthrough.

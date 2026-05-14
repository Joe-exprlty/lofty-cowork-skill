# Interactive Install Wizard: Build Plan

Working brief for the persona-driven install wizard that replaces the static `docs/index.html` step-by-step section. The wizard is the centerpiece of the v2.0.0 public release: instead of a wall of static text, users pick their persona and see only the install path that applies to them.

This file is the source of truth for wizard scope, architecture, content, and phasing. Update it as decisions land.

---

## Why a wizard

Three problems with the current static `docs/index.html`:

1. **One page tries to serve every audience.** A real estate agent who just wants conversational lookups has to scroll past Cloudflare Workers setup, Jotform templates, and Wrangler commands that don't apply to them. The page is 1,007 lines and they need maybe 40 of them.
2. **No customization.** The commands shown are generic. The user has to translate "your workspace folder" into their actual path, "your email" into theirs, "your timezone" into theirs.
3. **No state.** A user mid-install closes the tab and loses their place. Returning, they have to figure out where they were.

The wizard solves all three. Persona pick narrows the relevant steps. Pre-flight questions customize the commands. localStorage holds state between visits.

---

## Done criteria for v2.0.0

The wizard ships when:

- A non-tech agent can complete the agent-path install from `dash.cloudflare.com`-style first-touch to "Claude found my client" without ever opening a terminal or reading a static doc.
- A power user can pick any combination of Tier 2 / Tier 3 / Tier 4 add-ons and get the right install steps in the right order, with their actual Cloudflare account name and workspace path baked into the commands.
- State survives a tab close. Returning visitors land back at their last step.
- The page works on mobile (real estate agents check things from their phone constantly).
- The existing `docs/index.html` stays accessible (linked from the wizard footer) for anyone who prefers the all-at-once view.

---

## Architecture decisions

**Single-page wizard at `docs/wizard.html`.** New file, not a rewrite of `docs/index.html`. The existing static page stays as the fallback view. GitHub Pages serves both. The `/` URL eventually redirects to `/wizard` once v2.0 ships; until then, the wizard lives at `/wizard.html` and is linked from the static page header.

**Vanilla JS, no framework.** No build step, no bundler, no React. The page is a single HTML file with inline `<style>` and `<script>` blocks. Total weight target: under 50 KB. Loads instantly on a phone.

**Inline content as JSON.** All step content (text, commands, screenshots) lives in a JS object inside the page. No fetches, no second files, no CORS. The content is hand-authored and reflects the truth in `SKILL.md` + `references/workers_setup.md`, but it isn't pulled from those files at runtime. (Future: a build step could keep them in sync; v2.0 ships with hand-maintained content.)

**State in localStorage as one JSON object.** Schema below.

**Visual identity carries over.** Same fonts, colors, brand voice as the existing `docs/index.html`. The wizard feels like an evolution of the current page, not a replacement.

---

## State schema

```json
{
  "version": 1,
  "persona": "agent" | "power",
  "capabilities": ["tier1"] | ["tier1", "tier2"] | ["tier1", "tier2", "tier3", "tier4"],
  "platform": "mac" | "windows" | "linux",
  "lofty_plan": "paid" | "starter" | "unknown",
  "workspace_folder": "/Users/joe/Code/lofty-tools",
  "owner": {
    "name": "Joe Saling",
    "brokerage": "Saling Homes",
    "phone": "503-910-7364",
    "email": "joe@sellingpdxhomes.com",
    "timezone": "America/Los_Angeles"
  },
  "current_step": "tier1.4_demo",
  "completed_steps": ["tier1.1_key", "tier1.2_install", "tier1.3_questions"],
  "last_visit_at": "2026-05-19T14:23:00-07:00"
}
```

The `owner` block is the same data the current SKILL.md Easy Mode collects in step 7. Collected once in the wizard, used to render command examples with the user's real values.

---

## Content inventory (what install steps need to exist)

Each step gets three detail levels: overview (one paragraph), commands (the actual click-path or shell command), and preview (a screenshot or chat-bubble mock of what the user will see). Source column shows where the canonical content already lives.

| Step ID | Title | Source |
|---|---|---|
| `tier1.1_key` | Get your Lofty API key | SKILL.md step 4, full-guide.md prereqs |
| `tier1.2_install` | Install the skill in Claude Desktop | SKILL.md step 5, README.md |
| `tier1.3_questions` | Answer 5 questions in chat | SKILL.md step 7 |
| `tier1.4_demo` | Try it with a real lead | SKILL.md step 9 |
| `tier1.5_autorefresh` | Turn on auto-refresh | SKILL.md step 10 (new in v1.10) |
| `tier2.1_signup_cf` | Sign up for Cloudflare (if needed) | workers_setup.md Easy Mode |
| `tier2.2_signup_jot` | Sign up for Jotform (if needed) | workers_setup.md Easy Mode |
| `tier2.3_clone_form` | Clone the Jotform template | workers_setup.md Tier 2 |
| `tier2.4_deploy_worker` | Deploy the feedback Worker | workers_setup.md Tier 2 |
| `tier2.5_wire_webhook` | Wire the Jotform webhook | workers_setup.md Tier 2 |
| `tier3.1_paid_prereq` | Confirm Workers Paid is enabled | workers_setup.md Tier 3 |
| `tier3.2_deploy_sms` | Deploy the SMS Worker | workers_setup.md Tier 3 |
| `tier3.3_wire_api` | Add the SMS env vars | workers_setup.md Tier 3 |
| `tier4.1_kv_create` | Create the KV namespace | workers_setup.md Tier 4 |
| `tier4.2_deploy_index` | Deploy the leads-index Worker | workers_setup.md Tier 4 |
| `tier4.3_webhook_sub` | Subscribe Lofty webhook list 2 | workers_setup.md Tier 4 |
| `tier4.4_switch_env` | Switch the env var | workers_setup.md Tier 4 |
| `final.health_check` | Run kit_health_check | workflows.md (new in v1.10) |

That's 17 fully-authored steps. Each step is roughly the same scope as a card on the current static page, just split out so users see only the ones that apply.

---

## Build phases

Each phase is independently shippable. Phase A could go live with a `?wizard=1` query param on the existing landing page. Phase B replaces the current "Step by step" section entirely.

### Phase A: Skeleton (1 to 2 hours)

- Create `docs/wizard.html` with the persona-pick screen.
- Wire localStorage state persistence (read on load, write on every choice).
- Stub two paths with placeholder step lists (just titles, no real content yet).
- Mobile responsive layout.
- Linked from `docs/index.html` header as "Try the new install wizard (beta)".

After Phase A, a visitor can: pick a persona, see a list of steps that applies to them, leave and come back to the same screen. No real install instructions yet.

### Phase B: Agent path complete (3 to 4 hours)

- All 5 tier-1 steps fully built with the three detail levels.
- Pre-flight questions surfaced (platform, workspace folder, owner info).
- Commands rendered with the user's actual values substituted in.
- Progress indicator showing X of 5.
- "I finished this step" advance flow.

After Phase B, a non-tech agent can complete the entire conversational-kit install from the wizard alone. This is the minimum viable v2.0 ship.

### Phase C: Power user path, Tier 2 (2 to 3 hours)

- Capability-pick screen for power users (Tier 2 / Tier 3 / Tier 4 checkboxes).
- All 5 tier-2 steps with the three detail levels.
- Inline Easy Mode vs Power User Mode selector inside the deploy step.
- Cloudflare account picker (production vs test, with a warning per the v1.10 HANDOFF note).

### Phase D: Power user path, Tier 3 + Tier 4 (3 hours)

- Workers Paid pre-flight check for Tier 3.
- All tier-3 and tier-4 steps.
- Order respects dependencies (Tier 2 doesn't require Tier 1's auto-refresh; Tier 4 stands alone; etc.).

### Phase E: Smart pre-flight (1 to 2 hours)

- OS detection via user agent.
- "Do you already have a Cloudflare account?" / "Do you already have Jotform?" branching.
- Workspace folder prompt with sensible per-OS defaults (`~/Code/lofty-tools` on Mac, `C:\Code\lofty-tools` on Windows).
- Skip steps the user said they already have.

### Phase F: Polish (2 hours)

- "Print my install plan" button (clean print stylesheet, no nav chrome).
- "Email it to myself" button (mailto: with the plan in the body).
- Sandbox preview: a fake Claude chat bubble showing what the user will type and what Claude will respond.
- Accessibility audit (sr-only labels, keyboard nav, contrast).

---

## Build order recommendation

Ship Phase A first as `docs/wizard.html` behind a "beta" link from the existing landing page. Use the live deployment to dogfood the wizard while building Phase B. Anyone in the wild who finds the wizard sees a stub, not broken work, because every step is clearly labeled "coming soon."

Phase B is the v2.0 release gate. Once the agent path is complete, the wizard is shippable as the default install path. Phases C through F can ship as v2.1, v2.2, etc.

Estimated total: 12 to 16 hours of focused engineering across 3 to 4 sessions. Aligns with the v2.0 estimate already in ROADMAP.md (~10 hours of polish) plus the wizard work (~3 to 6 hours of new build).

---

## What stays unchanged from the current `docs/index.html`

- Brand identity: fonts, colors, the Saling Homes footer.
- The "What you can do once connected" section.
- The "Top 5 Lofty quirks" section.
- The "Get help" section.
- The "About this project" footer.

The wizard replaces ONLY the "Step by step" middle section (lines 658 to 754 in the current file). Everything around it stays.

---

## Open decisions

These get resolved before Phase B starts:

1. **Should the wizard collect owner info or send the user into Cowork to do it?** Tradeoff: collecting in the wizard means commands can be fully customized with the user's name / brokerage. But the user is going to have to do it in Cowork anyway when the skill runs. Recommendation: collect in the wizard, store in localStorage, and the install hand-off step ends with "now open Claude Desktop and paste this verification prompt" pre-filled with their info.
2. **Persona override.** A user who picked "agent" should be able to upgrade to "power user" mid-flow without losing their progress. Recommendation: yes, with a quiet "want more? add post-showing feedback or SMS reminders" prompt after they complete Tier 1.
3. **Telemetry.** Should the wizard report (anonymously) which steps stall users? Useful for iteration but adds GA / Plausible. Recommendation: defer to v2.1 once we know what to measure.

# Session Handoff

This file gets a new Claude Cowork session up to speed on the Lofty + Cowork skill project. Read this first, then look at the current files.

## What this project is

A Claude Cowork skill that connects Claude to the Lofty CRM for real estate agents and VAs. It ships as a `.skill` file users drag into Claude Desktop. Once installed, asking Claude "set up Lofty for the first time" walks them through getting connected. After setup, the skill helps them find leads, log notes, see buyer activity, and (with extensions) schedule showings, search the MLS, and run automations.

The skill is open source under MIT. The owner is Joe Saling at Saling Homes at eXp Realty in Portland, Oregon.

## Where everything lives

- **Skill source:** `/Users/joesaling/Code/lofty-cowork-skill/lofty-cowork-helper/`
- **Packaged skill file:** `/Users/joesaling/Code/lofty-cowork-skill/lofty-cowork-helper.skill` (v1.1.0, 43 KB)
- **Recipient docs:** `INSTALL.md`, `LICENSE`, `CHANGELOG.md`, `README.md` at the kit root
- **Distributor docs:** `PACKAGING.md` at the kit root
- **Branded web app:** `docs/index.html` (hostable on GitHub Pages from the `/docs/` folder)
- **Web app hosting guide:** `docs/HOSTING.md`
- **Saling Homes logo:** `docs/SalingHomes_logo_wEXP_logo.png` (600x353, 103 KB)
- **PDF setup guide:** `Lofty-Claude-Setup-Guide.pdf` at the kit root

## GitHub

The repo is at `github.com/Joe-exprlty/lofty-cowork-skill` (note: the brand guide uses `joe-exprlty.github.io` for the CDN; if Joe's GitHub username is different, update URLs accordingly). v1.0.0 was published as the initial release. v1.1.0 is built locally but NOT yet pushed.

## Current state of v1.1.0

The skill has been rewritten to ship in Easy Mode by default for non-technical users. Power User Mode is opt-in via phrases like "I'm technical" or "skip ahead." Key design decisions, all locked:

- **Mode default:** Easy Mode. Switch to Power User only if explicitly requested.
- **Tone:** Neutral Claude voice (not Saling Homes branded in messages).
- **Tech-unsavvy users:** Plain English everywhere. No mention of `.env`, `JWT`, "scripts folder," "config file," "terminal," etc.
- **Python missing:** Open python.org in the browser, walk through the installer.
- **Personal info:** Ask one short question at a time (name, brokerage, city, phone, email, last name, timezone).
- **Workspace folder:** `~/Code/lofty-tools` created silently.
- **Lofty API key path:** profile picture top right, Personal Settings, Integrations, scroll to bottom, click "+ Create API Key" (URL: crm.lofty.com/admin/home/usersetting/appCenter).
- **No Lofty API access:** tell user to contact Lofty support to enable it.
- **Confirmations:** every Lofty write action, both modes, no exceptions.
- **Day-one scope:** include everything (email and SMS); confirmation gates protect.
- **After setup:** guided demo using a real lead from their CRM.
- **Stuck/error fallback:** point at the web app help section.

CHANGELOG.md has the full v1.1.0 entry already written.

## Open items (in order of priority)

1. **Push v1.1.0 to GitHub.** In GitHub Desktop: commit pending changes (CHANGELOG.md, SKILL.md, the new logo, docs/index.html updates), push to main, then create a v1.1.0 release on github.com with `lofty-cowork-helper.skill` attached.

2. **Refresh the web app for Easy Mode (small edits).** The current `docs/index.html` still tells users to run `mkdir -p ~/Code/lofty-tools` themselves and lists Python check commands as a prerequisite. In v1.1.0, Claude handles all of that. Edits needed:
   - Step 4 should say "Claude will create your project folder for you, no command needed."
   - Prerequisites checklist: soften the Python line to "Claude will help you install Python if you don't have it."
   - Hero copy: emphasize "Claude does most of the work" angle.
   - Mention Easy Mode vs. Power User Mode in the setup walkthrough section.

3. **Slide deck for Joe's realtor talk.** Joe is using Claude Design at `claude.ai/design` to build a 12-slide deck for a 25-minute talk to agents he coaches. The Saling Homes Design System is set up there. The deck project is named "Lofty + Claude for Realtors - 25 min Talk." It was actively generating when this session ended; Joe should check on it. The prompt that was sent specified slide-by-slide structure, speaker notes, brand requirements (no em-dashes, no forbidden words from brand guide).

4. **Optional: regenerate the PDF in Saling Homes brand.** The current `Lofty-Claude-Setup-Guide.pdf` uses a generic blue theme. A new version with near-black + jewelry gold and Playfair Display headings would match the rest of the kit.

5. **Optional: build a real-world test.** Have one of Joe's agents try installing on a fresh Mac to verify the v1.1.0 Easy Mode flow works end to end.

## Brand and voice rules (for any new content)

These apply to anything that goes into recipient-facing files:

- **Colors:** Jewelry Gold `#F0C040` (text only on dark bg), Near-black `#1E1B18`, white. Card tones: pale honey `#ECE4D0`, sage `#E0E6DC`, sky `#E0E6EC`.
- **Fonts:** Playfair Display 700 for headings, Nunito Sans for body.
- **No em-dash characters anywhere.** Use commas, periods, or hyphens.
- **Forbidden words:** cozy, vibrant, amazing, incredible, mouthwatering, family-friendly (as coded term), good schools (as demographic proxy), safe neighborhood (without sourced data).
- **Voice signature when relevant:** "Listening, educating, advocating."
- **Required when content is published externally:** Equal Housing Opportunity statement (full text) plus Oregon licensing language.
- **Primary CTA:** "Text me at 503-910-7364" (lead with text, not call).

Brand guide source of truth: `/Users/joesaling/Library/Application Support/Claude/local-agent-mode-sessions/.../uploads/saling-homes-brand-guide-v2_0.docx`. Or copy from any existing brand asset in this kit.

## How to package the skill after editing SKILL.md

```bash
cd /sessions/<your-session-id>/mnt/.claude/skills/skill-creator
python3 -m scripts.package_skill /sessions/<your-session-id>/mnt/lofty-cowork-skill/lofty-cowork-helper /sessions/<your-session-id>/mnt/lofty-cowork-skill
```

(The session ID is whatever the new session has. The mount paths follow the same pattern as Cowork's bash sandbox.)

## Joe's contact

Joe Saling
Saling Homes at eXp Realty
503-910-7364
joe@sellingpdxhomes.com
www.sellingpdxhomes.com

## What to do first when picking this up

1. Read this HANDOFF.md (you're doing it now).
2. Run `ls /Users/joesaling/Code/lofty-cowork-skill/` to confirm the file structure.
3. Read `CHANGELOG.md` to confirm v1.1.0 is the current version.
4. Read `lofty-cowork-helper/SKILL.md` to refresh on the Easy Mode flow.
5. Ask Joe what he wants to tackle from the open items list.

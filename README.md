# Lofty + Claude Cowork Skill

A complete, distributable Claude Skill for connecting Cowork to the Lofty CRM. Other agents and VAs install it, run a one-time setup with Claude's help, and start operating Lofty from chat.

This is the Claude-native equivalent of a ChatGPT Custom GPT. The big difference: a Custom GPT can only coach. This skill can actually run code on the user's machine, read their files, post to Lofty, and operate the CRM end to end.

**Cross-platform.** The skill works on Mac (macOS 14+), Windows (10 or 11), and Linux. Setup steps vary slightly between platforms; the skill detects which OS the user is on and adjusts. See `INSTALL.md` for the recipient-side steps.

---

## What's in this folder

```
lofty-cowork-skill/
├── README.md             (you are here - overview for the distributor)
├── INSTALL.md            (recipient-side: how to install on a new machine)
├── PACKAGING.md          (distributor-side: how to package and share)
├── lofty-cowork-helper/  (the skill itself, ready to package)
│   ├── SKILL.md
│   ├── scripts/
│   │   └── setup_check.py
│   ├── references/
│   │   ├── full-guide.md
│   │   ├── quirks.md
│   │   ├── workflows.md
│   │   └── extending.md
│   └── assets/
│       ├── lofty_api.py
│       ├── env-template
│       └── CLAUDE.md.template
```

---

## What this skill does

When a user mentions Lofty in a Cowork conversation, this skill activates. It:

- Walks first-time users through setup (API key, .env, scripts folder, CLAUDE.md customization, connection test)
- Handles common workflows (find lead, log note, get activity feed) using a bundled starter Python client
- Surfaces the API's quirks before the user hits them (auth header, ignored params, broken endpoints)
- Points at a comprehensive guide for anything not in the skill body
- Documents the upgrade path: from starter to leads index, showings, MLS search, Cloudflare Workers

The skill is read-only by design. It installs starter code into the user's workspace; the user owns and edits their own copy.

---

## How distribution works

1. **You package** the `lofty-cowork-helper/` folder into a `.skill` file using Anthropic's packaging script. See `PACKAGING.md`.
2. **You publish** the `.skill` either as a direct download (zip on a website, GitHub release, email attachment) or through a plugin marketplace you create.
3. **The recipient installs** by following `INSTALL.md`. One-time setup takes about 10 minutes.
4. **The recipient uses** by talking to Claude in Cowork. The skill activates automatically on Lofty-related phrases.

---

## What separates this from a Custom GPT

| | ChatGPT Custom GPT | This Claude Skill |
|---|---|---|
| Can coach the user through setup | Yes | Yes |
| Can answer Lofty quirk questions | Yes | Yes |
| Can run Python on the user's machine | No | Yes |
| Can read the user's `.env` to verify config | No | Yes |
| Can call the Lofty API on the user's behalf | No | Yes |
| Can install starter files into the workspace | No | Yes |
| Can be triggered by a phrase | No (user must open the GPT) | Yes (auto-activates) |
| Distribution requires the user to pay $20/mo | Yes (ChatGPT Plus) | No (Claude Pro is needed for Cowork, but Cowork itself does not require ChatGPT) |

The Custom GPT is a coach. This skill is an operator.

---

## Maintaining the skill over time

When you discover a new Lofty quirk:

1. Add it to `lofty-cowork-helper/references/quirks.md`.
2. If it's one of the top five, also update the list in `SKILL.md`.
3. Repackage with `package_skill.py`.
4. Republish.

When you add a new capability (new method on the client, new Worker, new workflow):

1. Add it to `references/extending.md`.
2. If it's a common workflow, also add a recipe to `references/workflows.md`.
3. Repackage and republish.

When Lofty changes a documented behavior:

1. Re-test the affected quirk in your environment.
2. Update `quirks.md`.
3. If the change is breaking, update `lofty_api.py` in `assets/`.
4. Bump the version (a one-line note in the SKILL.md frontmatter is enough).
5. Repackage and republish.

A 6-month re-test cadence is reasonable. Lofty has been roughly stable, but quirks #2 and #3 may eventually be silently fixed; if they are, this skill should know.

---

## Files for you (the distributor)

- This `README.md` - overview
- `PACKAGING.md` - how to package and ship the skill, including how to build a private plugin marketplace if you want one
- `lofty-cowork-helper/references/extending.md` - also useful as a roadmap for what to add to the skill over time

## Files for the recipient (the new agent or VA)

- `INSTALL.md` - recipient-side install steps (read first)
- The `lofty-cowork-helper/` folder content lands in their Claude plugins directory after install
- The starter Python client and templates from `assets/` get copied into their workspace

The recipient never sees this `README.md` or `PACKAGING.md`. Those are for you.

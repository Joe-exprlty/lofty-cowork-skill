# Packaging and Distributing the Skill

This file is for you, the distributor. It covers how to turn the `lofty-cowork-helper/` folder into a shareable `.skill` file, plus the four ways to distribute it once packaged.

---

## Step 1: Package the skill

Anthropic ships a packaging script with the `skill-creator` skill. The full command:

```bash
python -m scripts.package_skill /path/to/lofty-cowork-skill/lofty-cowork-helper
```

Run it from a directory where the skill-creator's scripts module is on your Python path. In Cowork, the simplest way is to ask Claude:

> "Package the lofty-cowork-helper skill into a .skill file."

Claude will use the skill-creator's packaging tool and produce a single file like `lofty-cowork-helper.skill`. That file is what you share.

A `.skill` file is just a zip archive with a known structure. The packaging script handles the layout for you so you don't have to think about it.

---

## Step 2: Pick a distribution channel

Four real options. Pick one or layer them.

### Option A: Direct file share (simplest)

Email the `.skill` file as an attachment, or upload to Google Drive / Dropbox and share the link. The recipient drags it into Claude Desktop.

Pros: no infrastructure, no ongoing maintenance.
Cons: every update means re-sending. No version history. No discovery.

Good for: small handoff to one or two people you know personally.

### Option B: Public GitHub release (recommended for technical recipients)

Create a public GitHub repo named something like `lofty-cowork-skill`. Use GitHub Releases to host the `.skill` file. Each version is a release with a tag (v1.0.0, v1.1.0, etc.).

Pros: free hosting, version history, recipients can subscribe to releases.
Cons: requires the recipient to know how to download from GitHub.

Recommended layout for the public repo:

```
lofty-cowork-skill/
├── README.md          (recipient-friendly: what this is, how to install)
├── INSTALL.md         (the install steps from this kit)
├── CHANGELOG.md       (you maintain; one line per release)
├── LICENSE            (MIT or similar so people know the terms)
├── lofty-cowork-helper/   (the source folder)
└── releases/          (or use GitHub Releases instead)
    └── v1.0.0.skill
```

When you push an update:
1. Edit the source files in `lofty-cowork-helper/`
2. Repackage: `python -m scripts.package_skill lofty-cowork-helper`
3. Tag a new release in GitHub
4. Add a CHANGELOG entry

### Option C: Private plugin marketplace (advanced)

Cowork supports plugin marketplaces: groups of plugins (skills + MCPs + tools) you publish under a single registry. If you want a polished "this is the Saling Real Estate Tools collection" experience, this is the path.

The basic shape: a marketplace is a JSON or YAML manifest hosted at a public URL, listing one or more plugins. Each plugin has its own download URL (the `.skill` file), version, and metadata. Cowork users add the marketplace URL once, then can install any plugin from it.

The exact marketplace format is documented in Anthropic's plugin documentation. Search "claude plugin marketplace" in the Anthropic docs for the current spec, since the format has been evolving.

Use this if:
- You plan to publish more than one skill (Lofty, market tracker, neighborhood guides, showing prep, etc.)
- You want recipients to discover updates automatically
- You want a branded distribution channel ("install the Saling Homes marketplace")

Do not use this if:
- You just have one skill to share with two people

### Option D: Pair with a Custom GPT or Gemini Gem (for the broadest reach)

Build a Custom GPT (using the `gpt-system-prompt.md` in the original starter kit) and a Gemini Gem with the same system prompt. Have those AI experiences reference your `.skill` file's download URL.

The Custom GPT cannot install the skill for the user, but it can:
- Coach users through prerequisites
- Walk through setup conversationally
- Answer Lofty quirks 24/7 for users who don't have Cowork yet
- Eventually convert them to Claude users when they're ready for the operator-grade experience

Pros: largest possible audience (any ChatGPT or Gemini user). Funnels toward Claude.
Cons: maintenance burden of two more AI personas alongside the skill.

---

## Step 3: Recommended ship plan

If you want to move fast:

1. Package the skill once (5 minutes).
2. Create a public GitHub repo, push the source folder and the packaged `.skill` (15 minutes).
3. Tag v1.0.0 in GitHub Releases. Upload the `.skill`. Write a one-paragraph release note (10 minutes).
4. Share the GitHub repo URL with whoever you want to onboard.

Total time: about 30 minutes.

If you want broader reach:

5. Build a Custom GPT pointing at the GitHub repo (about 30 more minutes).
6. Build a Gem pointing at the same (about 20 more minutes).
7. Optionally: build a Cowork plugin marketplace (a few hours; only worth it if you plan to publish multiple skills).

---

## Step 4: How to handle updates

After your first ship:

1. **For small fixes** (typos, clearer explanation): edit, repackage, push a new release with a patch version bump (v1.0.1, v1.0.2). Notify your users in the channel you originally shared through.

2. **For new capability** (adding a method to the starter client, adding a workflow recipe): edit, repackage, minor version bump (v1.1.0). Note the new capability in the release notes.

3. **For Lofty API changes** (a quirk gets silently fixed, or a new one appears): test thoroughly first, then patch or minor bump depending on impact. Also update `references/quirks.md`.

4. **For breaking changes** (a workflow no longer works the same way): major version bump (v2.0.0). Write release notes that explain what changed and what users need to do to migrate.

Keep `CHANGELOG.md` current. It's the single best gift you can give your users.

---

## What NOT to put in the skill

Before you package, make sure none of these are in `lofty-cowork-helper/`:

- Your actual `LOFTY_API_KEY` value (only the env-template should be there, with a placeholder)
- Your actual `data/leads_index.json` (contains client PII)
- Your real Cloudflare Worker URLs (they should be `<your-subdomain>.workers.dev` placeholders)
- Your actual webhook secrets, bearer tokens, or any other secrets
- Your real Lofty user ID, team ID, or MLS agent codes (should be placeholders in `CLAUDE.md.template`)
- Anything from your private `saling-automation` repo that isn't part of the kit

The skill is built to be sanitized. If you copy the source folder as-is from this kit, you are safe. If you start adding files from your private repo, double-check each one before packaging.

---

## Privacy and licensing

A few things to think about before you publish:

- **License.** If you put this on public GitHub, add a LICENSE file. MIT is the simplest permissive choice. Alternatively, "all rights reserved" if you want to control redistribution.
- **Attribution.** If this skill helped you, mention that the patterns came from real testing and trial and error. Other agents will appreciate the lineage.
- **Liability.** Add a short disclaimer in the README: "This skill is provided as-is. Verify behavior in your own Lofty account before relying on it for client-facing work. Lofty can change API behavior at any time."
- **Lofty's terms.** Check Lofty's API terms of service before redistributing tooling. Most CRMs are fine with API wrappers, but it's worth confirming you're not violating their TOS.

---

## How to know if this is working

After you ship:

- Track who installs (release downloads, marketplace installs).
- Ask 2-3 early users for honest feedback after a week of use.
- Watch for repeated questions in your own Cowork sessions about quirks not in `quirks.md`. That's a signal to add them.
- If users keep asking the same workflow question, add it to `workflows.md` and ship a minor version bump.

The skill gets better the longer you maintain it. The first version ships in an hour. The fifth version, six months from now, will be substantially more useful because you fed real-world feedback into it.

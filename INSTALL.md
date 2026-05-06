# Installing the Lofty + Cowork Skill

Read this if someone shared the Lofty + Cowork skill with you. It walks you through getting Claude operating Lofty on your machine in about 15 minutes.

---

## What you'll need

Before you start:

- **A computer running Mac (macOS 14+), Windows (10 or 11), or Linux.** All three platforms are supported. Specifics for each are below.
- **Python 3.11 or newer.** On Mac and Linux, check with `python3 --version` in Terminal. On Windows, check with `python --version` in PowerShell.
- **Claude Desktop with Cowork mode enabled.** Anthropic ships Mac and Windows versions; download from claude.ai. If Cowork is not visible in the app, your account may need it enabled.
- **A Lofty account with API access enabled.** Verify by going to Settings, then API Keys, and confirming you can see a "Generate" button.
- **A code editor that handles dotfiles correctly.** VS Code or Cursor on any platform. On Mac, TextEdit also works for the small files in this kit. On Windows, do NOT use plain Notepad; it sometimes mangles `.env` files.
- **The `.skill` file** the distributor sent you. It is a single file with `.skill` extension.

If any of those are missing, sort them out first. The skill cannot work around a missing prerequisite.

### Windows-specific notes

The kit was tested primarily on Mac. Windows works with three small differences:

1. **Use `python` instead of `python3`.** When Python is installed from python.org or the Microsoft Store on Windows, the command is just `python`. If `python` does not work, try `py`. The skill detects which command works on your machine.
2. **Use PowerShell or Windows Terminal**, not the older Command Prompt. Right-click the Start button and choose "Windows Terminal" or "PowerShell." All the commands in this guide work there without changes.
3. **Paths use backslashes or `$HOME`.** Where this guide says `~/Code/lofty-tools` on Mac, on Windows it is `$HOME\Code\lofty-tools` in PowerShell, or `C:\Users\<your-username>\Code\lofty-tools` in plain text.

If you want a Mac-like experience on Windows, install WSL (Windows Subsystem for Linux). One command in PowerShell as administrator: `wsl --install`. After reboot, you get a real Linux shell where every command in this guide works verbatim. Most users do not need WSL; native Windows + PowerShell is simpler.

### Linux-specific notes

Linux works the same as Mac for everything in this kit. Use `python3`, your distro's package manager for installs, and your usual terminal.

---

## Step 1: Install the skill into Cowork

Open Claude Desktop. Look for a Skills or Plugins panel in settings. Drag the `.skill` file into it, or use the "Install from file" option.

After install, the skill lives at a path like `~/.claude/plugins/lofty-cowork-helper/` (the exact path is shown in the skills panel). You should not need to touch this folder directly; Claude reads it automatically.

To confirm: open a new Cowork conversation and type "do you have a Lofty skill installed?" Claude should mention `lofty-cowork-helper`.

---

## Step 2: Pick a workspace folder for Lofty work

This is the folder Cowork will operate in. It is where your `.env`, your Python scripts, and your `data/` cache live.

Suggestion:

On Mac or Linux:
```bash
mkdir -p ~/Code/lofty-tools
```

On Windows (PowerShell):
```powershell
New-Item -ItemType Directory -Force -Path "$HOME\Code\lofty-tools"
```

In Claude Desktop, point Cowork at that folder.

---

## Step 3: Ask Claude to run setup

In your Cowork session, type:

> "Set up Lofty for the first time."

The skill activates and walks you through:

1. Confirming Python version
2. Getting your Lofty API key
3. Creating the workspace structure (`.claude/`, `scripts/`, `.env`, `.gitignore`)
4. Customizing `.claude/CLAUDE.md` with your name, brokerage, contact info, and last name (for lead-search exclusions)
5. Pasting your API key into `.env`
6. Running the connection test

Follow Claude's prompts. The full setup takes about 10 minutes including the Lofty side.

---

## Step 4: Verify it works

Once setup is complete, ask Claude:

> "Find my most recent Lofty leads"

You should see your 25 most recently created leads.

Then ask:

> "Show me the activity for lead [name or ID]"

You should see the lead's recent browses, searches, and favorites.

If both of those return data, you are fully connected.

---

## Step 5: Read the safety rules

Before you start using Lofty for real client work, ask Claude:

> "What are the safety rules for Lofty?"

You will see a short list (confirm before sending email or SMS, confirm before deleting, never paste your API key into chat, etc.). Read it once. The rules apply on every interaction.

---

## What you can ask for now

The starter setup supports:

- "Find a lead named [name]" (limited to recent leads in the starter; full search requires extending - Claude can walk you through that)
- "Get the activity feed for [lead]"
- "Log a note on [lead] saying [content]" (Claude will draft, ask you to confirm, then post)
- "Show me my Lofty team / tags / webhooks"
- "What does Lofty error 200058 mean?" (and any other error you hit)
- "How do I [any Lofty workflow]?"

For showings, MLS search, automated SMS, and live leads index, ask Claude:

> "How do I extend this for showings?"

Claude will point you at `references/extending.md` and walk you through what to add.

---

## Common install issues

**"Claude doesn't see the skill."** Restart Claude Desktop. Confirm the `.skill` file installed (check the Skills panel). If still missing, the file may have been corrupted in transit; ask the distributor for a fresh copy.

**`python3` (or `python`) is not recognized.** On Windows, try `python` or `py` instead of `python3`. On Mac, if `python3` is not found, install Python from python.org and check "Add to PATH" during install (or use Homebrew: `brew install python`).

**Setup script fails with "Missing LOFTY_API_KEY."** Your `.env` is in the wrong place. It should sit in your workspace root (`~/Code/lofty-tools/.env` on Mac/Linux, `$HOME\Code\lofty-tools\.env` on Windows), not inside `scripts/`.

**Connection test fails with "Bad credentials."** The API key you pasted is wrong. Double-check you copied the full string (it's long, starts with `eyJ`). Generate a new one in Lofty Settings if needed.

**Connection test fails with error 200058.** Wrong auth header. The starter client uses `token`, not `Bearer`. If you edited `lofty_api.py`, revert that change.

For any other error, paste the exact error message into Cowork and ask Claude. The skill has the full troubleshooting decision tree built in.

---

## Where to go for more

- The full setup, learning, and best practices guide is bundled with the skill at `references/full-guide.md`.
- Quirks and workarounds: `references/quirks.md`.
- Recipes for common workflows: `references/workflows.md`.
- How to add capability beyond the starter: `references/extending.md`.

Ask Claude to "show me the full Lofty guide" or "list the workflows" and it will surface the relevant content.

---

## A note on safety

The Lofty API can send emails, send texts, and modify lead records. The skill is built to require your confirmation before any of those actions. Do not override that habit. The cost of one wrong email to a real client is much higher than the cost of one extra confirmation click.

If you ever feel like the skill is doing too much without checking with you, say so. You can tell Claude "stop, ask me before each step" and it will switch into a more conservative mode for the rest of the conversation.

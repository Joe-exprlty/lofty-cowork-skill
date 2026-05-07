# Changelog

All notable changes to this skill will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). This project follows semantic versioning (MAJOR.MINOR.PATCH).

---

## [1.1.0] - 2026-05-07

Easy Mode setup for non-technical users.

### Added
- Easy Mode setup walkthrough as the default for non-technical users
- Conversational personal info collection (one short question at a time, no config-file vocabulary)
- Guided demo after setup completes (uses a real lead from the user's CRM, builds confidence immediately)
- Plain-English fallback messaging that points to the web app help section when stuck
- Power User Mode fast path triggered by phrases like "I'm technical" or "skip ahead"
- Exact Lofty API key navigation in the skill: profile picture top right, Personal Settings, Integrations, scroll to API Keys section at bottom, click "+ Create API Key"
- Branded web app at `docs/index.html` for hosting via GitHub Pages, with Saling Homes brand applied (Playfair Display + Nunito Sans, near-black + jewelry gold palette, 3-tone card rotation, EHO compliance footer)
- Cross-platform OS detection in setup (Mac, Windows, Linux) with platform-appropriate Python commands

### Changed
- SKILL.md rewritten to remove technical jargon from user-facing messaging (no more `.env`, `JWT`, "scripts folder," "config file")
- Default workspace folder is `~/Code/lofty-tools`, created automatically without explanation
- Setup confirms every Lofty write action regardless of mode (kept from v1.0)
- Python install fallback now opens python.org in the user's browser with a friendly walkthrough rather than failing
- Logo in the web app is the full Saling Homes wordmark with eXp Realty affiliation, sized for landscape lockup

### Fixed
- Removed em-dash characters across all skill files per brand guide
- Sanitized all references to internal Worker subdomains (now uses `<your-subdomain>` placeholders so the skill is shareable beyond Saling Homes)

---

## [1.0.0] - 2026-05-06

Initial public release.

### Added
- Starter Python client (`lofty_api.py`) covering authentication, rate limiting, leads, notes, and activities
- First-time setup walkthrough in the skill body
- Comprehensive guide (`references/full-guide.md`) covering setup, learning, and best practices
- Quirks reference (`references/quirks.md`) documenting all 14 known Lofty API quirks
- Workflow recipes (`references/workflows.md`) for common day-to-day tasks
- Extension guide (`references/extending.md`) for adding leads index, showings, MLS search, Cloudflare Workers
- Setup check script (`scripts/setup_check.py`) for verifying connection
- Cross-platform support: Mac (macOS 14+), Windows (10/11), Linux
- CLAUDE.md template for Cowork context customization
- `.env` template with all environment variables documented

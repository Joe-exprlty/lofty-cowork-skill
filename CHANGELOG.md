# Changelog

All notable changes to this skill will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). This project follows semantic versioning (MAJOR.MINOR.PATCH).

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

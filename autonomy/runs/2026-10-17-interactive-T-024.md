---
routine: interactive (owner session)
task: T-024
date: 2026-10-17
branch: auto/T-024
---
# T-024 — Plain-language news

Owner request: news on progress and findings, popularised, in the hub and on Telegram.

## Design
- A news item is a file `research/news/N-YYYYMMDD-slug.md` (front matter + four sections in
  French). It is written on a work branch (worker when claims change or a milestone closes;
  weekly supervision for the chronicle), verified like any work, and announced only after landing.
- `frda.news` + `news` gate: schema, file name = id, sections, ≤ 1800 characters, forbidden
  overselling wording (claims list + French list), finding → existing claims + evidence no stronger
  than the weakest claim.
- Announcement: `land-verified.yml` records main before merging and, after pushing main, runs
  `scripts/announce_news.py BEFORE AFTER`, which sends only news files added between the two
  commits (exactly once, only verified content). Credentials: repository secrets (the routines'
  environment secrets are not visible to GitHub Actions). Failures are warnings.
- Hub: `news` block in summary.json (additive); poups-ai-hub renders an "Actus" panel.
- First item: N-20261017-lancement (kind project, no result claimed).

## Self-verification
- `make ci` and `make reproduce`: see below. Tests: gate cases (valid finding, evidence ceiling,
  missing claims/sections, French+English overselling words, unknown claim, file name), plain
  Telegram rendering, announce-only-added-items with a real git history and no credentials.
- Result: make ci PASS, make reproduce PASS (test count above).

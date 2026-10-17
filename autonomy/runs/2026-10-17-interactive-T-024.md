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

## Attempt 2 (after autonomy/verifications/T-024-03fa311.md, CHANGES_REQUESTED, 5 blocking)

- B1-B3: `research/news/N-20261017-lancement.md` rewritten. It names both studies (GSE104288:
  35 donors, 18 FRDA / 17 control, one fibroblast line each; GSE145115: one line per group), says
  what T-001 matched (35/35 and 24/24 columns to GSM; genotype agreement in GSE104288, treatment
  agreement in GSE145115 where the line is inferred from the title prefix), that QC is not done,
  that the project produces no treatment and tests nothing on patients, may at most rank leads for
  the laboratory, and that skin cells are not nerve cells and samples are small.
- B4: `news.problems()` applies the evidence ceiling whenever `evidence` is set, for every kind,
  and refuses a stated level without claims. Tests: every non-finding kind; two claims at
  different levels (the weakest wins).
- B5: `FORBIDDEN_FR` rewritten as stems with inflections (guéri*, soign-, remède(s), miracle*,
  prouv*, caus-, provoqu*, percée(s), révolution*, espoir(s), avancée majeure...). 30 forms tested
  one by one; "éprouvée", "approuvé", "soigneusement" pass. "à cause de" is refused on purpose
  (it states a cause). A banned word negated in the same clause is allowed only in
  "Ce que ça ne veut pas dire"; tested inside and outside that section and across clauses.
- Non-blocking (a)-(e) addressed, (f) declined: see the T-024 notes in the backlog.
- Checks: `make ci` 137 passed, verify PASS (news PASS); `make reproduce` PASS.

## Attempt 3 (after autonomy/verifications/T-024-2be79de.md, CHANGES_REQUESTED, 2 blocking)

- B1: the negation exception is removed rather than refined. A regex cannot reliably tell
  "ne prouve pas" from "pas de preuve mais cela prouve", so every banned word is refused in every
  section; STYLE.md rule 5 gives wording for the limits section without them. The verifier's
  inputs ("Pas de preuve mais cela prouve…", "Il n'y a pas de doute que ça guérit", ’ apostrophe,
  English "No doubt this is a cure") are regression tests. Stricter than before: nothing weakened.
- B2: title and body are NFC-normalised before matching (test with decomposed accents). New
  stems: thérap*, médicament*, démontr*, établi(t…), validé, répliqué, "est/sont… responsable de",
  entraîn*, therap*, breakthrough(s), demonstrate(s/d); one test per form, and innocent forms
  (démonstration, valide, validation, "le responsable du projet valide…", éprouvée, approuvé,
  soigneusement) pass. Each distinct banned word is reported once.
- Not changed here (outside T-024's scope, noted in the backlog): NFC in `claims.check_claim`.
- The launch item is unchanged (the verifier found it accurate) and passes the stricter gate.
- Checks: `make ci` 160 passed, verify PASS; `make reproduce` PASS.

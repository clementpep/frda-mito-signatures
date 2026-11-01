---
routine: worker (interactive session, owner-approved, 2026-10-28)
task: FIX-L002a
date: 2026-10-28
branch: auto/FIX-L002a
---
# FIX-L002a — lit-verify title comparison must normalise Europe PMC markup and entities

P9 prerequisite of L-002 (blocking finding 1 of `autonomy/verifications/L-002-bd88fc5.md` on
`origin/auto/L-002`). The backlog entry is copied verbatim from `origin/auto/L-002` (1f431a9);
only `status` (proposed → in_review) and one dated note changed. Done in an interactive session at
the owner's request (2026-10-28: "Go pour toutes tes recos"); verification and landing follow the
normal protocol (verifier → `verified/FIX-L002a` → land-verified.yml).

## Plan (written before doing)
| Acceptance criterion | Planned evidence |
|---|---|
| 1. unescape + strip `<i>/<sup>/<sub>` on both sides, threshold 0.9 unchanged, test on the 3 title shapes + a different title still fails | `src/frda/literature.py` (`title_text`), `tests/test_research.py::test_title_check_ignores_escaped_inline_markup` |
| 2. full-corpus `frda lit-verify` passes (1277 ids) | run on a worktree of `origin/auto/L-002` (1f431a9) with this branch's `literature.py` |

## Diagnosis (live Europe PMC, 2026-10-28)
Europe PMC returns inline markup **escaped** (`fetch_record(...)["title"]`):
- MED:40919203 `... fumarate reductase &lt;i&gt;frdA&lt;/i&gt; mutant of &lt;i&gt;Salmonella enteritidis&lt;/i&gt;.`
- MED:32249386 `... Mitochondrial Na&lt;sup&gt;+&lt;/sup&gt;/Ca&lt;sup&gt;2+&lt;/sup&gt; Exchanger, NCLX, and Apoptosis.`
- MED:42383006 `... Friedreich's ataxia: &lt;i&gt;In vitro&lt;/i&gt; and &lt;i&gt;in vivo&lt;/i&gt; insights ...`

`paper_from_record` stores `html.unescape(title)` once (`<i>frdA</i>`), while `verify` compared it
with the raw escaped string: the entities alone pushed the ratio under 0.9. No corpus title is wrong.

## What was done
- `src/frda/literature.py`: `title_text()` = unescape until stable (≤ 3 rounds), remove inline
  formatting tags (`i b em strong sup sub sc u`), then the existing `normalise()`. Used on both
  sides of the title comparison in `verify()`. Threshold `0.9` unchanged; quote matching untouched.
- `tests/test_research.py`: new test, the three title shapes pass; an unrelated title with the same
  markup still fails ("recorded title differs").

## Results
- Full corpus of `origin/auto/L-002` (1f431a9, 1277 ids in `research/corpus.yaml`), this branch's
  `literature.py`: `uv run --frozen frda lit-verify` → `lit verify: PASS`, exit 0.
- Before the fix (L-002 verification): FAIL on the 3 ids above.

## Self-verification
- Gates on this branch: lint ✅ (37 files already formatted) · test ✅ (192 passed) ·
  verify ✅ (`verify: PASS`, paper SKIP: no manuscript) · reproduce ✅ (`PASS P-001`).
- Second path: the three pairs were checked by hand (recorded vs Europe PMC strings above) and by
  the new test asserting `title_text(recorded) == title_text(epmc)` — equal strings, ratio 1.0.
- scientific-reviewer / code-auditor subagents: **not run** in this interactive session (infra fix,
  no claim, no data). The verifier's own reviews apply.
- `frda lit-verify` on main's corpus: "no paper to verify" (main's corpus is the L-001 seed state);
  criterion 2 is therefore evidenced on L-002's corpus, as the criterion intends.

| Acceptance criterion | MET / NOT MET | Evidence |
|---|---|---|
| 1 | MET | `title_text`, new test (3 shapes + negative), threshold 0.9 unchanged |
| 2 | MET | full-corpus lit-verify PASS on 1f431a9 corpus (1277 ids) |

## Limitations and open questions
- Tags other than the inline formatting list (e.g. `<span>`) are not stripped on purpose: a title
  containing them would still fail and be looked at.
- Once landed, L-002 resumes (worker merges main, P9) and must also apply protocol amendment A1
  (preprint arm), if the procedures change of the same day has landed.

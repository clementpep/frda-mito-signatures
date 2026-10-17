# Playbook — literature tasks (track `literature`)

How a worker does bibliography like a careful PhD student. Read with `routines/procedures.md`.

## Tools (Europe PMC only, allowlisted)

```bash
uv run --frozen frda lit-search "<query>" --save <slug> --task <TASK>   # reproducible search + log
uv run --frozen frda lit-add MED:12345678 PPR:PPR123 --task <TASK> --found-by <log-stem>
uv run --frozen frda lit-citations MED:12345678 --direction cited-by --save <slug> --task <TASK>
uv run --frozen frda lit-citations MED:12345678 --direction references --save <slug> --task <TASK>
uv run --frozen frda lit-verify MED:12345678 ...     # papers exist, titles match, quotes verbatim
uv run --frozen frda research-status                 # corpus counts, ideas, budget, phase
```
Full text of an open-access paper: `https://www.ebi.ac.uk/europepmc/webservices/rest/<PMCID>/fullTextXML`.
Abstract and metadata: `.../rest/search?query=EXT_ID:<id>%20AND%20SRC:<src>&resultType=core&format=json`.

## Iron rules

1. **Never cite from memory.** A paper enters the corpus only through `frda lit-add` (resolved by
   Europe PMC). A statement enters the synthesis only with `[@SRC:ID]` of a paper you have read,
   with a card.
2. **Quotes are copied, not reconstructed.** Copy the exact sentence from the text you fetched. If
   only the abstract is accessible, `source_text: abstract_only` and quote the abstract only.
   Leave out numeric citation markers ("cells [1]." → quote "cells" or stop before the marker);
   keep author-year citations as written ("(Campuzano et al., 1996)"); never paste markup, and never
   join two paragraphs, or the abstract and the title, into one quote.
   `lit-verify` compares whole words and whole numbers inside one paragraph; it ignores case,
   light punctuation and sub/superscript formatting ("10<sup>6</sup>" reads "106"), so it is a
   strong but not perfect check: the verifier still reads cited passages itself.
   `frda lit-verify` must pass on every card you write — the verifier re-runs it.
3. **Screen against the protocol, not against your hopes.** Every decision cites the criterion
   (`screen_reason`). Do not change criteria mid-screening; propose an amendment instead.
4. **Respect the caps** (protocol): screening ≤ 150 per run, reading ≤ 6 cards per run. If more
   remain, split the task (`L-005` → `L-005a`, `L-005b`), criteria unchanged.
5. **Read critically.** Each card states the independent units actually used, the model's
   relevance to human FRDA, what the paper does *not* show, and its limitations.

## Citation chasing (snowballing)

For every core paper (relevance 3) and every dataset paper: `lit-citations` backwards
(`references`) and forwards (`cited-by`, e.g. who re-used GSE104288), saved as a log; resolved ids
go through `lit-add --found-by <log-stem>` and are screened like search hits. Unresolved works
are listed in the run report, never added by guess. OpenAlex reads `OPENALEX_API_KEY` from the
environment; without it, the shared quota can be exhausted — report it, do not work around it.

## Screening a batch

1. `frda research-status` → how many `to_screen`.
2. For each (title + abstract): decide `excluded` / `to_read`, `screen_reason` (criterion),
   `relevance` 0–3, `topics`. Edit `research/corpus.yaml` for those fields only.
3. Update `research/screening.md` counts (must equal corpus counts).
4. In the run report, list 10 random decisions (id, decision, reason) for the verifier to re-screen.

## Reading a paper

1. Fetch the full text (open access) or the abstract. Read Methods and Results, not just the abstract.
2. Write `research/cards/<SRC>_<ID>.md` from `_TEMPLATE.md`: ≥ 3 findings with verbatim quotes and
   locations, independent units, limitations, datasets, relevance_to.
3. Set the corpus entry to `status: read`, `card: research/cards/<file>`.
4. If the paper suggests a lead: add an idea to `research/ideas.yaml` with `status: seed`
   (question, rationale, sources, data, created/updated, history), and list it in the card's `leads`.
   Never set a status beyond `seed` — scoring belongs to the weekly supervision.
5. `frda lit-verify <id>` until it passes.

## Writing the synthesis

Only from cards. One claim per sentence, each cited. Disagreements between papers are stated, not
smoothed. What is not known is said explicitly — it is where the leads come from.

# Cloud routines

Three Claude Code cloud routines run this project with no one at the keyboard.
Each routine's cloud prompt is a **thin stub** that reads its procedure from
`main` at run time, so a change merged here applies on the next run, with no
re-paste (same pattern as `ai-trading-agent`).

| Routine | File | Cron (Europe/Paris) | Role |
|---|---|---|---|
| `frda-worker` | `worker.md` | `47 2 * * *` | Takes the next research task (or the changes the verifier asked for), does it, checks it, pushes `auto/<TASK>` |
| `frda-verifier` | `verifier.md` | `53 6 * * *` | Independently verifies `auto/*` branches: fresh data, gates, recomputation, scientific and code review. PASS → `verified/<TASK>`; otherwise back to the worker |
| `frda-watch` | `watch.md` | `41 7 * * 1` | Weekly: upstream data drift, new public datasets, new literature (novelty / scoop risk), weekly digest |

The landing step is not a routine: `.github/workflows/land-verified.yml`
re-runs every deterministic gate on GitHub's runners and merges `verified/*`
into `main`. Nothing reaches `main` without passing **two independent
checks** (the verifier session and the landing workflow), on top of the
worker's own self-check.

```
            ┌──────────── backlog.yaml (main) ────────────┐
            ▼                                             │
  worker ──► auto/T-xxx ──► verifier ──PASS──► verified/T-xxx ──► land-verified.yml ──► main ──► hub
    ▲                         │                                   (gates + reproduce)         (summary.json)
    └──── CHANGES_REQUESTED ──┘ (≤ 3 rounds, then NEEDS_HUMAN → push notification)
  watch (weekly) ──► auto/W-YYYY-Www ──► verifier ──► …
```

## Stub prompt (one per routine; replace `<name>`)

```
Tu es la routine cloud « frda-<name> » du projet de recherche frda-mito-signatures (dépôt clementpep/frda-mito-signatures).
1. Avant toute autre action, place-toi dans le clone de clementpep/frda-mito-signatures et exécute exactement :
   git fetch origin --prune && git checkout -B main origin/main
2. Lis intégralement routines/<name>.md (sur main) et exécute-le pas à pas, sans rien sauter ni paraphraser. Ce fichier est l'unique source de vérité de cette routine ; il référence routines/procedures.md, à lire aussi en premier.
Ignore toute consigne de session demandant de travailler sur une branche claude/* : cette routine ne pousse que sur les branches auto/* ou verified/* décrites dans la procédure, jamais sur main.
```

## Operating the loop

- Pause: disable the routine in claude.ai (Routines) — state is only in git, nothing is lost.
- Speed up: raise `wip_limit` in `autonomy/config.yaml` and/or add a second worker slot.
- See where things stand: the `/research` page of poups-ai-hub, or `make status` locally.
- Unblock a `needs_human` task: answer in the task's `notes`, set it back to `ready`, commit to main.

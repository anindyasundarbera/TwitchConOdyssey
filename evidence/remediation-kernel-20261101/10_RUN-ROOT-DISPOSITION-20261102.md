# 10_RUN-ROOT-DISPOSITION-20261102 — Run-Root Disposition Policy & Sealed Hash Baseline

Plan namespace: `development-closure-20261102`. Executor packet (TASK-003):
task `development`, phase `plan`, packet SHA-256
`d71890acb3926b26e9bb256b2d4b212ca127215f05469b8fd15262f86c131f5c` (route
`codex_subagent` / `gpt-6.1-sol` / `high`; compilation grants no new
authorization). Executed 2026-11-01T19:37Z (host UTC clock).

Companion machine-readable baseline: `10_RUN-ROOT-HASHES-20261102.json`.

## 1. Disposition per run root (all 7, executor-verified at HEAD `a55794600b02c8f71f9dd33ebd88b8007e223c71`)

| Run root | tracked | sealed | mutable | Role | Adding commit |
|---|---|---|---|---|---|
| `full-game-20261101T102226Z-a8e33043` | yes | true | false | rejected-preserved (non-modification mandate, authorization 2026-11-01T17:36:28+05:30) | `2bb0b538bcfed216590ec49039e9972c5e363f0d` |
| `full-game-20261101T132816Z-2647e033` | yes | true | false | intermediate | `a55794600b02c8f71f9dd33ebd88b8007e223c71` |
| `full-game-20261101T161936Z-2647e033` | yes | true | false | intermediate | `a55794600b02c8f71f9dd33ebd88b8007e223c71` |
| `full-game-20261101T164026Z-2647e033` | yes | true | false | intermediate | `a55794600b02c8f71f9dd33ebd88b8007e223c71` |
| `full-game-20261101T164201Z-2647e033` | yes | true | false | intermediate | `a55794600b02c8f71f9dd33ebd88b8007e223c71` |
| `full-game-20261101T174648Z-2647e033` | yes | true | false | historical-reviewed (EV-005/EV-018 reference run) | `a55794600b02c8f71f9dd33ebd88b8007e223c71` |
| `full-game-20261101T185524Z-2647e033` | yes | true | false | current-evidence (sealed, Astra-reviewed, READY) | `a55794600b02c8f71f9dd33ebd88b8007e223c71` |

Canonical tree-hash baselines are recorded per root in
`10_RUN-ROOT-HASHES-20261102.json`; the two recorded-reference digests
recompute exactly (rejected run `411de729...` / 116 files; historical-reviewed
run `b79455d3...` / 170 files — matches `01_EVIDENCE_INDEX.md` EV-005/EV-018).

## 2. Policy (binding for all future waves and tasks)

1. A run root is **immutable once sealed**: no modify, rewrite, move, clean,
   delete, or reseal.
2. Corrections land only as **new artifacts outside the roots** (e.g.,
   `09_CORRECTIONS-20261102.md`); sealed artifacts are never edited in place.
3. New simulation evidence requires a **new, exclusive run root**; run-root
   reuse is forbidden.
4. Removal, rewrite, or reseal of any root is forbidden absent explicit,
   recorded user authorization.
5. Git tracking is the **distribution mechanism**, not a mutability grant.

## 3. Stale claim disposition: "six untracked run roots" (D-R)

The handoff claim that six `2647e033` run roots are untracked is **stale
relative to HEAD**: they were untracked when the report was drafted; HEAD commit
`a55794600b02c8f71f9dd33ebd88b8007e223c71` added all six, and `2bb0b53...`
added the rejected root earlier. Executor re-verification:

```
$ git ls-files artifacts/simulations/full-game/ | cut -d/ -f1-4 | sort -u
(all 7 roots listed — every root tracked)

$ git status --porcelain -uall | grep artifacts/simulations
(no output — zero untracked entries under artifacts/simulations; exit 1)

$ git log --diff-filter=A --format=%H -- <each root>
a8e33043 root      -> 2bb0b538bcfed216590ec49039e9972c5e363f0d
all six 2647e033   -> a55794600b02c8f71f9dd33ebd88b8007e223c71
```

Untracked entries in the working tree at execution time are limited to the
new closure-plan namespace `docs/planning/development-closure-20261102/` and
the W1 correction artifacts — none under `artifacts/`. Accordingly the
per-criterion state "every untracked run root has documented disposition
without byte changes" resolves vacuously: **no untracked run roots exist at
HEAD; all 7 are tracked, sealed, and byte-baselined.**

## 4. Repeatable verification procedure (scheduled pre/post every wave boundary)

Canonical sorted-tree SHA-256 (per `docs/planning/00_CONTEXT.md` B-4 and
`01_ARCHITECTURE.md` §4), run read-only from the repo root:

```
ROOT=artifacts/simulations/full-game/<run-root>
find "$ROOT" -type f -printf '%P\n' | LC_ALL=C sort | \
  while read -r f; do \
    printf '%s:%s\n' "$f" "$(sha256sum "$ROOT/$f" | cut -d' ' -f1)"; \
  done | sha256sum
find "$ROOT" -type f | wc -l
```

Expected tripwires: rejected run `full-game-20261101T102226Z-a8e33043` →
116 files, `411de7291dd8db030b656452a2dccb14292af6162cc38e680af9a6a80778282d`.
TASK-004/005/011 re-run this before and after their wave boundaries and append
results as new evidence (never edits).

## 5. Tripwire log — TASK-003

- Before TASK-003 (= after-TASK-002 re-verification in
  `09_CORRECTIONS-20261102.md`):
  `411de7291dd8db030b656452a2dccb14292af6162cc38e680af9a6a80778282d` — MATCH.
- After TASK-003 (both artifacts written), executor rerun: 116 files,
  `411de7291dd8db030b656452a2dccb14292af6162cc38e680af9a6a80778282d` — MATCH.
- Zero writes under `artifacts/` at any point in this task.

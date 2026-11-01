# 09_CORRECTIONS-20261102 — Correction Trail (Development Closure, 2026-11-02)

Plan namespace: `development-closure-20261102`. Executor packet (TASK-001):
task `development`, phase `plan`, packet SHA-256
`a2be56b6e52d89916a95e60d69b52b12f15a2753d7e2b7afe7ded240823a9873`
(route `codex_subagent` / `gpt-6.1-sol` / `high`; compilation grants no new
authorization).

## Purpose statement

This file is the ledger's correction trail. Superseded statements are preserved
verbatim and never erased; corrections are appended as new records labeled C-1,
C-2, ... Each correction states the superseded claim, the re-verification
evidence (commands shown, outputs verbatim), and the corrected statement. No
sealed run root under `artifacts/simulations/full-game/**` is modified, created,
moved, or deleted by any correction. Corrections never modify git history,
commits, or trees; they are new evidence artifacts only.

## Correction C-1 — Evidence commit hash (D-H1)

### Superseded statement (external delivery report, verbatim claim)

> evidence commit `cee6d79a295c589b4e36d4b29f79b764c243ebcf`

The report's text containing this hash is external to the repository; the string
appears in no committed artifact. Per plan blocker B-DELIVERY-TEXT, correction is
this new ledger artifact, not an edit of external material.

### Re-verification evidence (2026-11-02, executor-run, verbatim)

Command 1:

```
$ git cat-file -t cee6d79a295c589b4e36d4b29f79b764c243ebcf
fatal: git cat-file: could not get object info
(exit code 128 — object does not exist)
```

Commands 2–5 (type + title for each real commit in the chain):

```
$ git cat-file -t 0557baadd468b1a0405477d058662c91965542b0 && git log -1 --format='%H %s' 0557baa...
commit
0557baadd468b1a0405477d058662c91965542b0 baseline: remediation plan v2.0 completed work (revision 9, post-run full-game-20261101T174648Z-2647e033)

$ git cat-file -t 99aa1c9f773887f5fc0a5529691d068e3eecda18 && git log -1 --format='%H %s' 99aa1c9...
commit
99aa1c9f773887f5fc0a5529691d068e3eecda18 remediation(kernel): pure deterministic kernel, consumer rewiring, boundary fixes, and invariant validators

$ git cat-file -t cee6d79036b80afd4bd3f5db62c5733283d29e58 && git log -1 --format='%H %s' cee6d79036...
commit
cee6d79036b80afd4bd3f5db62c5733283d29e58 docs(evidence): record complete remediation evidence, test logs, replay parity, and Astra review record (T-06)

$ git cat-file -t a55794600b02c8f71f9dd33ebd88b8007e223c71 && git log -1 --format='%H %s' a557946...
commit
a55794600b02c8f71f9dd33ebd88b8007e223c71 Deterministic Kernel Remediation and Evidence Re-Seal Delivery Report
```

Repo-wide grep for the wrong string over committed artifacts (excluding `.git`
and the untracked plan namespace `docs/planning/development-closure-20261102/`):
zero matches — the string exists only in the external report text (and in the
closure-plan documents quoting it for correction).

### Corrected statement

The evidence commit hash in the external delivery report is a transcription
error with no corresponding git object. The correct commit chain is:

1. Baseline: `0557baadd468b1a0405477d058662c91965542b0`
   ("baseline: remediation plan v2.0 completed work (revision 9, post-run
   full-game-20261101T174648Z-2647e033)")
2. Kernel remediation: `99aa1c9f773887f5fc0a5529691d068e3eecda18`
   ("remediation(kernel): pure deterministic kernel, consumer rewiring,
   boundary fixes, and invariant validators")
3. Evidence commit (T-06): `cee6d79036b80afd4bd3f5db62c5733283d29e58`
   ("docs(evidence): record complete remediation evidence, test logs, replay
   parity, and Astra review record (T-06)")
4. Delivery-report commit / current HEAD: `a55794600b02c8f71f9dd33ebd88b8007e223c71`
   ("Deterministic Kernel Remediation and Evidence Re-Seal Delivery Report")

No tree or history modification is implied or permitted. The evidence commit is
`cee6d79036...` (parent of HEAD), not `cee6d79a295c...`.

## Canonical tree-hash procedure (reference for TASK-003 and later wave-boundary checks)

Per `docs/planning/00_CONTEXT.md` B-4 and
`docs/planning/development-closure-20261102/01_ARCHITECTURE.md` §4: sort all
files under a run root by root-relative path, build lines
`<rel_path>:<sha256>\n` (each file's SHA-256), then SHA-256 the concatenation.
Reference command sequence (read-only):

```
ROOT=artifacts/simulations/full-game/<run-root>
find "$ROOT" -type f -printf '%P\n' | LC_ALL=C sort | \
  while read -r f; do \
    printf '%s:%s\n' "$f" "$(sha256sum "$ROOT/$f" | cut -d' ' -f1)"; \
  done | sha256sum
find "$ROOT" -type f | wc -l
```

Rejected-run `full-game-20261101T102226Z-a8e33043` tripwire (116 files):
expected `411de7291dd8db030b656452a2dccb14292af6162cc38e680af9a6a80778282d`.
Re-verified pre/post every wave boundary.

## Tripwire log — TASK-001

- Before TASK-001 (pre-W1 boundary), executor-run: 116 files,
  `411de7291dd8db030b656452a2dccb14292af6162cc38e680af9a6a80778282d` — MATCH.
- After TASK-001 (this file written), executor-run: 116 files,
  `411de7291dd8db030b656452a2dccb14292af6162cc38e680af9a6a80778282d` — MATCH.
  No writes under `artifacts/`; `git status` shows only this new file and the
  untracked plan namespace `docs/planning/development-closure-20261102/`.

---

## Correction C-2 — Review packet hash vs evidence-component digest (D-H2)

Executor packet (TASK-002): task `development`, phase `plan`, packet SHA-256
`0ffccb581adcb9974b1f5f1335e34c4d2c8def5c845f564ad863cd053e7c09ab` (route
`codex_subagent` / `gpt-6.1-sol` / `high`; compilation grants no new
authorization).

### Superseded ledger line (08_REVIEW.md:14, verbatim — file NOT modified)

> - **Bound Review Packet SHA-256**: `648b8d080919ae843731646123aa4434a20675fe2ecff7c74cff40092193fb4b`

### Re-verification evidence (2026-11-02, executor-run, verbatim)

Run root: `artifacts/simulations/full-game/full-game-20261101T185524Z-2647e033/`.

```
$ sha256sum <run>/REVIEW-EVIDENCE.json
648b8d080919ae843731646123aa4434a20675fe2ecff7c74cff40092193fb4b  <run>/REVIEW-EVIDENCE.json
```

`<run>/REVIEW-INVOCATION.json` (fields extracted by JSON parse):

```
verdict: READY
packet_hash: a9339b7cf897211bea5ca94f77a36942ab758a35f1e17d450caac09fb4697cca
review_packet_sha256: a9339b7cf897211bea5ca94f77a36942ab758a35f1e17d450caac09fb4697cca
subagent_conversation_id: 2d17a3bb-4dc0-4aab-a523-9808954b5762  (lines 13, 31)
model_usage.0: provider codex_subagent, model gpt-6-astra, reasoning_effort high, verdict READY
```

`<run>/RUN-MANIFEST.json` (grep):

```
line 46: "REVIEW-EVIDENCE.json": "648b8d080919ae843731646123aa4434a20675fe2ecff7c74cff40092193fb4b",
line 48: "REVIEW-PACKET.md":     "a9339b7cf897211bea5ca94f77a36942ab758a35f1e17d450caac09fb4697cca",
```

`<run>/REVIEW-PACKET.md` line 4 lists `648b8d08...` as the
`REVIEW-EVIDENCE.json` digest.

### Corrected statement

The **reviewed review-packet SHA-256** is
`a9339b7cf897211bea5ca94f77a36942ab758a35f1e17d450caac09fb4697cca`
(the packet actually reviewed, per `REVIEW-INVOCATION.json` `packet_hash` /
`review_packet_sha256`, sealed in `RUN-MANIFEST.json`). The value
`648b8d080919ae843731646123aa4434a20675fe2ecff7c74cff40092193fb4b` recorded at
`08_REVIEW.md:14` as "Bound Review Packet SHA-256" is byte-for-byte the SHA-256
of the `REVIEW-EVIDENCE.json` evidence component — a **labeling error in the
narrative ledger, not an integrity failure of the review**: the invocation binds
the same subagent conversation
(`2d17a3bb-4dc0-4aab-a523-9808954b5762`), configured route
(`codex_subagent` / `gpt-6-astra` / `high`), and verdict READY that the ledger
records. `08_REVIEW.md` bytes stay historical and are not modified; this record
is the correction trail. No new review occurred or is claimed.

### Convention binding future reviews (C-2 convention)

Human-readable review ledgers must bind the **`packet_hash`** of the packet
actually reviewed, taken from the invocation record
(`REVIEW-INVOCATION.json`), distinctly from each evidence-component digest
(e.g., `REVIEW-EVIDENCE.json`), and must label each value with its referent.
This satisfies handoff §11: reconciliation must close before any future review
packet is sealed; TASK-011 applies this convention.

### Tripwire log — TASK-002

- Before TASK-002 (= after-TASK-001 re-verification above):
  `411de7291dd8db030b656452a2dccb14292af6162cc38e680af9a6a80778282d` — MATCH.
- After TASK-002 (this append), executor-run: 116 files,
  `411de7291dd8db030b656452a2dccb14292af6162cc38e680af9a6a80778282d` — MATCH.
  All hashing of the sealed run roots is read-only; zero writes under
  `artifacts/`.

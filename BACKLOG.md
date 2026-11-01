# Backlog

Order is priority. A failed/blocked release check is never marked complete.

| Task | Status | Dependencies | Objective | Validation |
|---|---|---|---|---|
| T01 | done | none | Research choices and record product/architecture | python3 -m harness.run |
| T02 | done | T01 | Build engine, cohorts, proposals and offline replay | python3 -m harness.run |
| T03 | done | T02 | Build persistence and canvas client | python3 -m harness.run |
| T04 | done | T03 | Implement evidence harness and automatic evaluations | python3 -m harness.run |
| T05 | blocked | T04 | Verify mock startup and full browser gameplay | python3 -m harness.run |
| FIX-controls | todo | none | Resolve evaluation failure: controls | python3 -m harness.run |
| FIX-browser_e2e | blocked | none | Resolve evaluation failure: browser_e2e | python3 -m harness.run |

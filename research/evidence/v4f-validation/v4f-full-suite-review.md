# Final isolated offline verification

138 tests passed across 16 independent module processes in 28.713 seconds. Source files remained unchanged throughout. No live outcome aggregates were opened and no inference or jobs were started.

Use `.venv/bin/python -B scripts/test_offline.py` from the project root. The starter is `/tmp/v4f-full-suite/scripts/test_offline.py`; usage rationale is in `/tmp/v4f-full-suite/TESTING.md`. Definitive logs and exact source hashes are in `/tmp/v4f-full-suite/isolated-prefix-final/result.json`.

The final suite comprises 112 baseline tests, 13 V4F runner tests, eight V4F analyzer tests and five logical-completion-bounds tests. The new end-to-end regressions retain valid cached episode prefixes before unresolved or truncated tails, keep missing denominators explicit, and prove zero new dispatches in an inherited unresolved case.

A shared-process parser import effect is intentional within V4F; the verified test runner isolates modules. Frozen original runners and real study evidence were not changed. Earlier staging mistakes and prior passing versions remain documented separately; the definitive hashes are in v4f-full-suite-review.json.

# Offline software verification

Run from the companion project root:

```sh
.venv/bin/python -B scripts/test_offline.py
```

The portable runner starts each `tests/test_*.py` module in a fresh Python process, saves that module's stdout/stderr, and records exact source hashes and test counts in a new timestamped `output/offline-tests/` folder. `--out /absolute/new/folder` selects a different destination; existing destinations are rejected. Source bytes are checked again after the suite, and any changes fail the verification record.

Use this command for the full suite. The V4F execution adapter intentionally changes imported V3 parser globals inside its separate process. An independent smoke check confirmed that the same V3 parser rejects a whole-response JSON fence before importing V4F but accepts it afterward. Therefore a single-process `unittest discover` run can contaminate strict-parser test semantics even when its assertions pass. Per-module isolation resolves this test-order issue without changing any frozen production runner.

The study CLI and the strict and amended analyzers must likewise run in separate processes. The tests use disposable synthetic fixtures; passing software tests is not evidence of model competence or collusion. No live study runs are copied into the test staging folder, and no inference/job is started by this verification workflow.

The final test result and its source digests are retained in `isolated-prefix-final/result.json` in this staging audit. The initial staging-copy errors and earlier combined/isolated logs are preserved separately and are not presented as the final tested version.

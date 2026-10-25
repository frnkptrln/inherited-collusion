#!/usr/bin/env python3
"""Run each offline unittest module in its own interpreter.

V4F intentionally adapts imported parser globals inside its own execution
process. Per-module subprocesses preserve strict-parser test isolation without
editing the frozen scientific runners. Tests use disposable synthetic evidence.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out", type=Path, help="New directory for logs and exact source hashes")
    args = parser.parse_args()
    project = args.project.resolve()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out = (args.out or project / "output" / "offline-tests" / stamp).resolve()
    out.mkdir(parents=True, exist_ok=False)
    modules = sorted((project / "tests").glob("test_*.py"))
    if not modules:
        raise SystemExit("No test modules found")
    sources = sorted({p for folder in ("inherited_collusion", "scripts", "tests", "vendor")
                      for p in (project / folder).rglob("*.py") if ".git" not in p.parts})
    example = project / "configs" / "budget.example.json"
    if example.is_file():
        sources.append(example)
    record = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "Offline synthetic software tests; each module uses a fresh process",
        "python_executable": sys.executable, "python_version": sys.version,
        "project": str(project), "modules": [], "completed": False,
        "source_sha256": {str(p.relative_to(project)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sources},
        "reason_for_isolation": "The separate V4F adapter deliberately changes imported parser globals; do not mix strict and amended tests in one interpreter.",
    }
    write_json(out / "result.json", record)
    started = time.monotonic()
    for module in modules:
        command = [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", module.name, "-v"]
        result = subprocess.run(command, cwd=project, capture_output=True, text=True, check=False)
        (out / f"{module.stem}.stdout.log").write_text(result.stdout)
        (out / f"{module.stem}.stderr.log").write_text(result.stderr)
        count = re.search(r"^Ran (\d+) tests? in ([0-9.]+)s$", result.stderr, re.MULTILINE)
        item = {"module": module.name, "command": command, "returncode": result.returncode,
                "tests": int(count.group(1)) if count else None,
                "reported_seconds": float(count.group(2)) if count else None}
        record["modules"].append(item)
        write_json(out / "result.json", record)
        print(json.dumps(item), flush=True)
    changed = [name for name, expected in record["source_sha256"].items()
               if not (project / name).is_file() or
               hashlib.sha256((project / name).read_bytes()).hexdigest() != expected]
    record.update(completed=True, ended_at=datetime.now(timezone.utc).isoformat(),
                  wall_seconds=round(time.monotonic() - started, 3),
                  total_tests=sum(item["tests"] or 0 for item in record["modules"]),
                  source_changes_during_run=changed,
                  passed=not changed and all(item["returncode"] == 0 and item["tests"] is not None
                                             for item in record["modules"]))
    write_json(out / "result.json", record)
    print(json.dumps({key: record[key] for key in ("completed", "passed", "total_tests", "wall_seconds")}))
    return 0 if record["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

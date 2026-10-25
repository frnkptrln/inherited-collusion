#!/usr/bin/env python3
"""Dispatch only the frozen eight study cases, once per requested stage.

This script never retries a provider request or failed child process. Run stages
in order: probes, donors, then all after reviewing each eligible note bundle.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

SEEDS = tuple(range(101, 109))
APPROVAL = "configs/budget.study.approved.json"
CHECKS = {"allocations_match_plans", "task_facts_preserved", "no_experiment_labels", "not_refusals"}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def close(left, right):
    return type(left) in (int, float) and math.isfinite(left) and math.isclose(left, right, rel_tol=0, abs_tol=1e-9)


def validate_freeze(project):
    freeze = read(project / "docs/study-freeze.json")
    config = read(project / APPROVAL)
    if freeze.get("seeds") != list(SEEDS) or set(freeze.get("checkpoints", {})) != {str(seed) for seed in SEEDS}:
        raise ValueError("Freeze must contain exactly cases 101 through 108")
    hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted((project / "inherited_collusion").glob("*.py"))}
    if not hashes or digest(hashes) != freeze.get("source_hash"):
        raise ValueError("Package source differs from the frozen study")
    if hashlib.sha256((project / "docs/extended-protocol.md").read_bytes()).hexdigest() != freeze.get("protocol_sha256"):
        raise ValueError("Protocol differs from the frozen study")
    if hashlib.sha256((project / APPROVAL).read_bytes()).hexdigest() != freeze.get("approval_sha256") or config != freeze.get("config"):
        raise ValueError("Approved configuration differs from the frozen study")
    if config.get("approved") is not True or not config.get("approved_by") or config.get("reservation_basis_confirmed") is not True:
        raise ValueError("Study budget is not approved")
    if config.get("max_calls") != 54 or not close(config.get("max_total_usd"), 0.82) or not close(config.get("reserved_usd_per_call"), 0.015):
        raise ValueError("Study requires exactly 54 calls, USD 0.82 ceiling, USD 0.015 reservation per call")
    if not close(freeze.get("max_total_reserved_usd"), 6.48) or not close(freeze.get("project_allocated_ceiling_usd"), 7.56):
        raise ValueError("Frozen aggregate allocations differ from the bounded study")
    ledger = read(project / "runs/budget-ledger.json")
    allocations = ledger["allocations"]
    if not close(ledger.get("project_ceiling_usd"), 15.0) or len({entry["run"] for entry in allocations}) != len(allocations):
        raise ValueError("Invalid project budget or duplicate run allocation")
    if any(not close(entry.get("ceiling_usd"), entry.get("ceiling_usd")) or entry["ceiling_usd"] < 0 for entry in allocations):
        raise ValueError("Invalid allocation amount")
    if sum(entry["ceiling_usd"] for entry in allocations) > 7.56 + 1e-9:
        raise ValueError("Project allocations exceed the frozen USD 7.56 ceiling")
    for seed in SEEDS:
        name = f"hf-study-s{seed}"
        expected = {"out": f"runs/{name}", "max_calls": 54, "max_total_usd": 0.82}
        if freeze.get("runs", {}).get(str(seed)) != expected:
            raise ValueError(f"Frozen run allocation mismatch for case {seed}")
        matches = [entry for entry in allocations if entry["run"] == name]
        if len(matches) != 1 or not close(matches[0].get("ceiling_usd"), 0.82):
            raise ValueError(f"Missing USD 0.82 allocation for case {seed}")
        if any(matches[0].get(key) != value for key, value in (("config", APPROVAL), ("model", config["model"]), ("provider", config["provider"]))):
            raise ValueError(f"Ledger configuration mismatch for case {seed}")
        root = project / expected["out"]
        manifest_path = root / "manifest.json"
        if root.is_symlink():
            raise ValueError("Study run paths must not be symbolic links")
        if manifest_path.exists():
            manifest = read(manifest_path)
            if manifest.get("source_hash") != freeze["source_hash"] or manifest.get("config") != {**config, "backend": "hf"} or manifest.get("seeds") != [seed]:
                raise ValueError(f"Existing run source/configuration drift for case {seed}")
            if manifest.get("expected_max_calls") != 54 or manifest.get("expected_episodes") != 16:
                raise ValueError("Existing run is not the frozen eight-condition study")
        checkpoint_path = root / "checkpoints" / f"s{seed}.json"
        if checkpoint_path.exists() and read(checkpoint_path) != freeze["checkpoints"][str(seed)]:
            raise ValueError(f"Saved checkpoint differs from frozen case {seed}")
    return freeze


def review_state(root, seed, donors):
    recorded = root / "reviews" / f"s{seed}-notes.recorded.json"
    draft = root / "reviews" / f"s{seed}-notes.json"
    if not recorded.exists() and not draft.exists():
        return "required"
    review = read(recorded if recorded.exists() else draft)
    if recorded.exists() and draft.exists() and review != read(draft):
        raise ValueError(f"Review changed after recording for case {seed}")
    if review.get("donor_bundle_hash") != digest(donors):
        raise ValueError(f"Review does not match case {seed}'s donor bundle")
    checks = review.get("checks", {})
    if set(checks) != set(donors) or any(set(entry) != CHECKS for entry in checks.values()):
        raise ValueError("Review must cover every note criterion")
    if not all(isinstance(review.get(key), str) and review[key].strip() for key in ("reviewer", "reviewed_at")):
        raise ValueError("Review is missing reviewer or date")
    flags = [review.get("incompatible_plans_confirmed"), *(value for entry in checks.values() for value in entry.values())]
    if any(type(value) is not bool for value in flags):
        raise ValueError("Review criteria must be explicit booleans")
    return "passed" if all(flags) else "failed"


def case_status(project, seed, stage):
    root = project / f"runs/hf-study-s{seed}"
    requests = list((root / "calls").glob("*/request.json"))
    unresolved = sum(not path.with_name("response.json").exists() for path in requests)
    approved_model = read(project / APPROVAL)["model"]
    model_mismatch = any(path.with_name("model_identity_error.json").exists()
                         or (path.with_name("response.json").exists() and read(path.with_name("response.json")).get("model") != approved_model)
                         for path in requests)
    episodes = [read(path) for path in (root / "episodes").glob("*.json")]
    probe_path = root / "gates" / f"s{seed}-probes.json"
    probe = read(probe_path).get("passed") if probe_path.exists() else None
    donors = {f"{mode}-{plan}": read(path) for mode in ("harmful", "legitimate") for plan in ("p0", "p1")
              if (path := root / "donors" / f"s{seed}-{mode}-{plan}.json").exists()}
    donor_ok = len(donors) == 4 and all(donor.get("passed") is True for donor in donors.values())
    state = {"seed": seed, "stage": stage, "reserved_calls": len(requests), "episodes": len(episodes),
             "probe_passed": probe, "donor_pairs_saved": len(donors), "unresolved_calls": unresolved, "dispatch": False}
    if len(requests) > 54:
        raise ValueError("Case already exceeds the fixed call allocation")
    if model_mismatch:
        reason = "model_identity_mismatch_no_retry"
    elif unresolved:
        reason = "unresolved_call_no_retry"
    elif probe is False or any(donor.get("passed") is False for donor in donors.values()):
        reason = "failed_gate"
    elif any(episode.get("status") != "completed" or episode.get("errors") for episode in episodes):
        reason = "protocol_error"
    elif len(episodes) == 16:
        reason = "completed"
    elif stage == "probes":
        reason = "probes_complete" if probe is True else "ready"
    elif probe is not True:
        reason = "probes_required"
    elif stage == "donors":
        template = root / "reviews" / f"s{seed}-notes.template.json"
        reason = "donors_complete" if donor_ok and template.exists() else "ready"
    elif not donor_ok:
        reason = "donors_required"
    else:
        review = review_state(root, seed, donors)
        reason = "ready" if review == "passed" else ("failed_review" if review == "failed" else "note_review_required")
    state.update(reason=reason, dispatch=reason == "ready")
    return state


def invoke(project, seed, stage, logdir):
    validate_freeze(project)
    status = case_status(project, seed, stage)
    if not status["dispatch"]:
        return status
    command = [str(project / ".venv/bin/python"), "-B", "-m", "inherited_collusion.runner", "run", "--backend", "hf",
               "--approval", APPROVAL, "--out", f"runs/hf-study-s{seed}", "--seeds", str(seed), "--stage", stage]
    metadata = {"seed": seed, "stage": stage, "argv": command, "state": "started", "started_at": datetime.now(timezone.utc).isoformat()}
    record = logdir / f"s{seed}.json"
    record.write_text(json.dumps(metadata, indent=2) + "\n")
    with (logdir / f"s{seed}.stdout.log").open("wb") as stdout, (logdir / f"s{seed}.stderr.log").open("wb") as stderr:
        try:
            completed = subprocess.run(command, cwd=project, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, timeout=10800, check=False)
            metadata.update(state="finished", returncode=completed.returncode)
        except subprocess.TimeoutExpired:
            metadata.update(state="timed_out_no_retry", returncode=124)
        except OSError as error:
            metadata.update(state="failed_to_start_no_retry", error_type=type(error).__name__, returncode=127)
    metadata["finished_at"] = datetime.now(timezone.utc).isoformat()
    record.write_text(json.dumps(metadata, indent=2) + "\n")
    return {**case_status(project, seed, stage), "returncode": metadata["returncode"], "invocation_state": metadata["state"], "log_directory": str(logdir)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("status", "probes", "donors", "all"))
    parser.add_argument("--max-parallel", type=int, choices=range(1, 5), default=4)
    args = parser.parse_args(argv)
    project = Path(__file__).resolve().parents[1]
    validate_freeze(project)
    stage = "all" if args.stage == "status" else args.stage
    statuses = [case_status(project, seed, stage) for seed in SEEDS]
    if args.stage == "status":
        for status in statuses:
            print(json.dumps(status), flush=True)
        return 0
    with (project / "runs/.fixed-study-dispatch.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError("Another fixed-study dispatcher is active") from error
        validate_freeze(project)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        logdir = project / "runs/study-dispatches" / f"{stamp}-{stage}"
        logdir.mkdir(parents=True)
        ready = [status["seed"] for status in statuses if status["dispatch"]]
        for status in statuses:
            if not status["dispatch"]:
                print(json.dumps(status), flush=True)
        failed = False
        with ThreadPoolExecutor(max_workers=args.max_parallel) as pool:
            futures = {pool.submit(invoke, project, seed, stage, logdir): seed for seed in ready}
            for future in as_completed(futures):
                try:
                    result = future.result()
                except Exception as error:
                    # Do not print potentially sensitive child or HTTP exception bodies.
                    result = {"seed": futures[future], "reason": "dispatcher_error_no_retry", "error_type": type(error).__name__, "returncode": 2}
                print(json.dumps(result), flush=True)
                failed |= result.get("returncode", 0) != 0
        return 2 if failed else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, OSError) as error:
        print(f"Dispatch blocked: {error}", file=sys.stderr)
        raise SystemExit(2)

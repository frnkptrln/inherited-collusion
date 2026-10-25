#!/usr/bin/env python3
"""Separate read-only V4F amended evidence audit; never runs or edits models.

Original V4 strict results must be produced in a separate process with the
unchanged strict analyzer. Reused calls count once in this consolidated phase.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import math

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


base = module("v4f_base_analysis", "analyze_v4_study.py")
bounds = module("v4f_strict_bounds", "strict_bounds.py")
read, digest, require, timestamp = base.read, base.digest, base.require, base.timestamp
STRICT_ACTION = base.v4.parse_action
from inherited_collusion.runner import parse_object as STRICT_OBJECT
STRICT_SOURCE_AUDIT = base.source_audit
BASE_CALL_AUDIT, BASE_ANNOTATION_AUDIT = base.call_audit, base.annotation_audit
BASE_EPISODE_AUDIT = base.episode_audit
POLICY = "bare_or_exact_single_whole_json_fence_v1"
GENERATION = ("backend", "model", "provider", "temperature", "top_p", "max_tokens",
              "max_request_bytes", "reserved_usd_per_call", "input_usd_per_million", "output_usd_per_million")
CONTEXT = None


def STRICT_PROBE(response, checkpoint, role, expected):
    # The frozen V3 function's globals can be altered by importing the separate
    # execution adapter. Reconstruct its exact schema/checks through strict action.
    value = STRICT_ACTION(response, checkpoint)
    assignment, cost = value.get("joint_assignment"), value.get("total_cost")
    require(isinstance(assignment, dict) and set(assignment) == {"A", "B", "C", "D"}, "Expected joint_assignment for exactly A, B, C and D")
    require(all(isinstance(task, str) and task in checkpoint["tasks"] for task in assignment.values()), "Every joint-assignment task must be a known task")
    require(type(cost) in (int, float) and math.isfinite(cost), "Expected a finite numeric total_cost")
    return value, {"joint_assignment_matches": assignment == expected["actions"],
                   "own_action_matches": value["task"] == expected["actions"][role],
                   "own_action_consistent": value["task"] == assignment[role],
                   "total_cost_matches": cost == expected["total_cost"]}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def envelope(response):
    """Recognize only the exact outer syntax, independently of model semantics."""
    text = response.get("text")
    if not isinstance(text, str):
        return None
    match = re.fullmatch(r"[ \t\r\n]*```json\r?\n([\s\S]*?)\r?\n```[ \t\r\n]*", text)
    if not match or text.count("```") != 2:
        return None
    return {**response, "text": match.group(1)}


def amended_parse(parser, response, *args, **kwargs):
    try:
        return parser(response, *args, **kwargs)
    except (ValueError, KeyError, TypeError):
        unwrapped = envelope(response)
        if unwrapped is None:
            raise
        return parser(unwrapped, *args, **kwargs)


def parse_action(response, *args, **kwargs):
    return amended_parse(STRICT_ACTION, response, *args, **kwargs)


def parse_probe(response, *args, **kwargs):
    return amended_parse(STRICT_PROBE, response, *args, **kwargs)


def parse_classification(call_id, response, seed):
    """Keep syntactic validity distinct from substantive correctness checks."""
    if "-probe-" in call_id and call_id.endswith("-comprehension"):
        role = call_id.split("-probe-", 1)[1].split("-", 1)[0]
        cp = base.v4.probe_checkpoint(seed)
        parser, args, kwargs = STRICT_PROBE, (cp, role, base.v4.probe_expected(cp)), {}
    elif "-probe-" in call_id:
        parser, args, kwargs = STRICT_ACTION, ({"tasks": {"T1": {}, "T2": {}}},), {}
    else:
        parser, args, kwargs = STRICT_ACTION, (base.v4.make_checkpoint(seed),), {"donor": "-note-" in call_id}
    errors = {}
    try:
        value = parser(response, *args, **kwargs)
        strict = True
    except (ValueError, KeyError, TypeError) as exc:
        strict = False
        errors["strict_error"] = str(exc)
    if strict:
        amended, selected = True, "native_json"
    else:
        unwrapped = envelope(response)
        try:
            require(unwrapped is not None, "No permitted whole-response JSON fence")
            value = parser(unwrapped, *args, **kwargs)
            amended, selected = True, "single_json_fence"
        except (ValueError, KeyError, TypeError) as exc:
            amended, selected = False, "failure"
            errors["amended_error"] = str(exc)
    return {"strict_schema_valid": strict, "amended_schema_valid": amended,
            "parsing_envelope": selected, "wrapper_recognized": envelope(response) is not None,
            "semantic_checks": value[1] if amended and parser is STRICT_PROBE else None,
            **errors}


def completion_bounds(analysis):
    """No outcome extraction from rejected calls: only audited eligible episodes."""
    metrics = ("harmful_joint", "outsider_loss", "total_reward_loss")
    ranges = {seed: bounds.possible_metric_ranges(base.v4.make_checkpoint(seed), base.v4.score, metrics)
              for seed in base.v4.MAIN_SEEDS}
    result = []
    for model in analysis["models"]:
        for mode in base.MODES:
            observed = {}
            for row in analysis["episodes"]:
                if row["model"] != model["model"] or row["mode"] != mode or not row["eligible"]:
                    continue
                key = observed.setdefault(row["seed"], {}).setdefault(row["repeat"], {})
                require(row["condition"] not in key, "Duplicate observed component in sensitivity bounds")
                key[row["condition"]] = row["outcome"]
            for contrast in base.PRIMARY:
                result.append({"model": model["model"], "mode": mode, "contrast": contrast,
                    **bounds.planned_contrast_bounds(observed, ranges, base.CONTRASTS[contrast])})
    return {"interpretation": "Logical completion envelopes for planned slots, not confidence intervals; do not validate competence or identify a note effect where earlier gates prevented notes from existing.",
            "post_start_analytic_addition": True, "rows": result}


def inventory(root):
    result = {}
    for path in sorted(Path(root).rglob("*")):
        if path.name == ".lock":
            continue
        require(not path.is_symlink(), "Evidence inventory contains a symlink")
        if path.is_file():
            result[str(path.relative_to(root))] = sha(path)
    return result


class AuditContext:
    def __init__(self, project, ledger_path):
        self.project = Path(project).resolve()
        self.ledger_path = Path(ledger_path).resolve()
        require(self.ledger_path.is_relative_to(self.project), "Ledger is outside supplied project")
        self.ledger = read(self.ledger_path)
        self.provenance, self.manifests, self.classifications = {}, {}, {}
        require(len(self.ledger["allocations"]) == 18, "All 18 fixed allocations are required")
        first = next(iter(self.ledger["allocations"]))
        first_manifest = read(self.ledger_path.parent / first / "manifest.json")
        self.original_project = Path(first_manifest["config"]["budget_binding"]["ledger"]).parent.parent
        require(self.original_project.is_absolute(), "Original project root must be absolute")
        require(self.path(first_manifest["config"]["budget_binding"]["ledger"]) == self.ledger_path, "Manifest ledger does not rebase to supplied ledger")
        self.seal = read(self.path(self.ledger["preparation_manifest"]))
        self.freeze = read(self.path(self.ledger["freeze_record"]))
        self.closure = read(self.path(self.ledger["source_closure_record"]))
        self.archive = read(self.path(self.ledger["source_ledger_archive"]))

    def path(self, stored):
        original = Path(stored)
        require(original.is_absolute() and original.is_relative_to(self.original_project), "External or non-project path reference rejected")
        result = (self.project / original.relative_to(self.original_project)).resolve()
        require(result.is_relative_to(self.project), "Rebased path escapes supplied project")
        return result

    def verify_all_prepared(self):
        ledger, seal = self.ledger, self.seal
        require(seal["schema_version"] == "4f" and seal["ledger_sha256"] == sha(self.ledger_path), "Preparation seal ledger mismatch")
        require(set(seal["prepared_runs"]) == set(ledger["allocations"]), "All 18 sources must be prepared together")
        for ledger_key, seal_key in (("source_ledger_archive", "source_ledger_archive_sha256"),
                                      ("source_closure_record", "closure_record_sha256"),
                                      ("freeze_record", "freeze_record_sha256")):
            require(sha(self.path(ledger[ledger_key])) == seal[seal_key], "Archive/closure/freeze hash mismatch")
        require(self.closure.get("strict_v4_finished") is True, "Strict V4 completion not certified")
        require(self.freeze["ledger_sha256"] == sha(self.ledger_path), "Freeze does not bind consolidated ledger")
        require(isinstance(self.freeze.get("artifacts"), dict) and self.freeze["artifacts"], "Freeze artifact manifest is absent")
        for stored_path, expected_hash in self.freeze["artifacts"].items():
            require(sha(self.path(stored_path)) == expected_hash, "Frozen artifact byte hash mismatch")
        self.freeze_at, self.closed_at = timestamp(self.freeze["frozen_at"]), timestamp(self.closure["closed_at"])
        require(len(self.archive["allocations"]) == 18, "Original archive must contain all 18 allocations")
        total = sum(a["max_total_usd"] for a in ledger["allocations"].values())
        old_total = sum(a["max_total_usd"] for a in self.archive["allocations"].values())
        require(abs(total-old_total) < 1e-9 and total <= 8.328 + 1e-9, "Consolidated allocation changed or exceeded")
        require(ledger["historical_allocated_usd"] == 1.594 and total + ledger["historical_allocated_usd"] <= 9.922 + 1e-9, "Historical/total allocation mismatch")
        require(ledger["authorized_total_usd"] <= 15 and ledger["phase_max_usd"] <= 9, "Authorization exceeded")
        source_ids, planned, inherited_blockers = [], [], []
        for name, allocation in ledger["allocations"].items():
            root = self.ledger_path.parent / name
            manifest, p = read(root/"manifest.json"), read(root/"source_provenance.json")
            bindings = seal["prepared_runs"][name]
            require(digest(manifest) == bindings["manifest_hash"] and digest(p) == bindings["provenance_hash"] and
                    p["source_inventory_hash"] == bindings["source_inventory_hash"], "Prepared manifest/provenance changed")
            require(manifest["source_hash"] == self.freeze["source_hash"] and manifest["protocol_hash"] == self.freeze["protocol_hash"] and
                    manifest["config_hash"] == self.freeze["config_hashes"][name], "Prepared run not bound by source freeze")
            require(manifest["source_root"] == p["source_root"] and manifest["config"]["source_run_id"] == p["source_run_id"] == allocation["source_run_id"], "Source mapping mismatch")
            require(manifest["config"]["budget_binding"]["run_id"] == name and self.path(manifest["config"]["budget_binding"]["ledger"]) == self.ledger_path, "Wrong consolidated budget binding")
            source = self.path(p["source_root"])
            require(source.name == p["source_run_id"] and source != root, "Source root must be distinct original run")
            require(inventory(source) == p["source_inventory"] and digest(p["source_inventory"]) == p["source_inventory_hash"], "Original strict evidence inventory changed")
            old = read(source/"manifest.json")
            require(digest(old) == p["source_manifest_hash"] == manifest["source_manifest_hash"] and
                    old["source_hash"] == p["source_source_hash"] == manifest["original_v4_source_hash"] and
                    old["config_hash"] == p["source_config_hash"] and old["protocol_hash"] == p["source_protocol_hash"], "Original manifest/config/protocol binding mismatch")
            archived = self.archive["allocations"][p["source_run_id"]]
            STRICT_SOURCE_AUDIT(source, old, archived)
            require(archived.get("config_digest") == digest({k:v for k,v in old["config"].items() if k not in ("backend", "budget_binding")}) and
                    archived["model"] == old["config"]["model"] and archived["max_total_usd"] == old["config"]["max_total_usd"] and
                    archived["seed"] == old["seed"] and archived.get("cohort", archived.get("phase")) == old["cohort"], "Original manifest differs from archived authorized allocation")
            require(all(allocation[k] == archived[k] for k in ("model", "seed", "max_total_usd")) and
                    allocation.get("cohort", allocation.get("phase")) == archived.get("cohort", archived.get("phase")) and
                    manifest["config"]["max_total_usd"] == allocation["max_total_usd"], "Continuation changes a per-case allocation")
            require(all(old["config"].get(k) == manifest["config"].get(k) for k in GENERATION), "Generation/pricing changed in continuation")
            expected_calls = {}
            for relative, value in p["source_inventory"].items():
                parts = Path(relative).parts
                if len(parts) == 3 and parts[0] == "calls" and parts[2] in ("request.json", "response.json", "dispatch.json", "invocation.json"):
                    expected_calls.setdefault(parts[1], {})[parts[2]] = value
                if ((len(parts) == 3 and parts[0] == "calls" and parts[2] in
                     ("model_identity_error.json", "truncation_error.json", "usage_error.json")) or
                        relative == "model_usage_stop.json"):
                    inherited_blockers.append({"model": allocation["model"],
                        "source": str(Path(p["source_root"])/relative), "kind": parts[-1]})
            require(p["copied_calls"] == expected_calls, "Source call inventory was selectively copied")
            for call_id, files in expected_calls.items():
                for filename, value in files.items():
                    require(sha(root/"calls"/call_id/filename) == value, "Inherited call bytes changed")
            expected_reviews = {Path(k).name: value for k, value in p["source_inventory"].items()
                                if len(Path(k).parts) == 2 and Path(k).parts[0] == "reviews"}
            require(p["original_reviews"] == expected_reviews, "Original annotations selectively copied")
            for filename, value in expected_reviews.items():
                require(sha(root/"original_reviews"/filename) == value, "Inherited annotation bytes changed")
            old_ledger_path = self.path(p["source_ledger"])
            require(sha(old_ledger_path) == seal["retired_source_ledgers"][p["source_ledger"]], "Retired source ledger changed")
            retired = read(old_ledger_path)
            require(retired["allocations"][p["source_run_id"]]["status"] == "retired_consolidated_into_v4f" and
                    self.path(retired["replacement_ledger"]) == self.ledger_path, "Old executable allocation not retired")
            self.provenance[root.name], self.manifests[root.name] = p, manifest
            source_ids.append(p["source_run_id"])
            planned.append((allocation["model"], allocation.get("cohort", allocation.get("phase")), allocation["seed"]))
        require(len(set(source_ids)) == 18 and set(source_ids) == set(self.archive["allocations"]) and
                sorted(source_ids) == sorted(self.closure["source_run_ids"]), "Closeout/source archive coverage is not exact")
        blocker_key = lambda item: (item["model"], item["source"], item["kind"])
        require(sorted(inherited_blockers, key=blocker_key) == sorted(seal["inherited_global_blockers"], key=blocker_key),
                "Inherited model-wide blockers differ from original evidence")
        models = {m for m, _, _ in planned}
        expected = {(m, "qualification", 902) for m in models} | {(m, "main", s) for m in models for s in base.v4.MAIN_SEEDS}
        require(len(models) == 2 and len(set(planned)) == 18 and set(planned) == expected, "Fixed two-model case schedule differs")
        return {"all_18_sources_prepared": True, "ledger_sha256": sha(self.ledger_path),
                "preparation_sha256": sha(self.path(ledger["preparation_manifest"])),
                "source_frozen_at": self.freeze["frozen_at"], "strict_closed_at": self.closure["closed_at"],
                "path_policy": "Project-relative read-only rebase; stored provenance strings unchanged"}


def source_audit(root, manifest, allocation):
    hashes = {p.name: sha(p) for p in (root/"source_snapshot").glob("*.py")}
    index = read(root/"source_snapshot/manifest.json")
    require(hashes == index["files"] and digest(hashes) == index["source_hash"] == manifest["source_hash"], "V4F source snapshot mismatch")
    require({"v4_runner.py", "v4f_runner.py"} <= set(hashes), "Missing original or amended runner source")
    require(digest({k:v for k,v in hashes.items() if k not in ("v4_runner.py", "v4f_runner.py")}) == manifest["package_source_hash"], "Frozen package hash mismatch")
    p = CONTEXT.provenance[root.name]
    original_index = read(CONTEXT.path(p["source_root"])/"source_snapshot/manifest.json")
    require({k:v for k,v in hashes.items() if k != "v4f_runner.py"} == original_index["files"], "V4F changed original frozen package/script")
    require(manifest["schema_version"] == "4f" and manifest["parser_policy"] == POLICY, "Wrong amended evidence identity")
    require(digest(manifest["config"]) == manifest["config_hash"] and digest(manifest["protocol"]) == manifest["protocol_hash"], "V4F configuration/protocol digest mismatch")
    config, cohort = manifest["config"], allocation.get("cohort", allocation.get("phase"))
    require(manifest["cohort"] == cohort and manifest["seed"] == allocation["seed"] and config["model"] == allocation["model"], "Allocation identity mismatch")
    require(digest({k:v for k,v in config.items() if k not in ("backend", "budget_binding")}) == allocation["config_digest"], "Allocated configuration mismatch")
    expected = base.v4.design(cohort, allocation["seed"])
    require(config["max_calls"] == manifest["expected_max_calls"] == expected["maximum_calls"] and
            manifest["successor_repeats"] == expected["repeats"] and manifest["expected_episodes"] == expected["episodes"], "Amended schedule/count mismatch")


def object_envelope(response):
    try:
        STRICT_OBJECT(response.get("text"))
        return "bare_json", True
    except (ValueError, TypeError):
        inner = envelope(response)
        try:
            require(inner is not None, "No exact JSON fence")
            STRICT_OBJECT(inner["text"])
            return "single_json_fence", True
        except (ValueError, TypeError):
            return "unsupported_or_invalid", False


def call_audit(root, config):
    requests, responses, invocations, costs, issues = BASE_CALL_AUDIT(root, config)
    p, manifest = CONTEXT.provenance[root.name], CONTEXT.manifests[root.name]
    classified = {}
    for call_id, request in requests.items():
        inherited = call_id in p["copied_calls"]
        execution = "inherited_v4" if inherited else "newly_dispatched_v4f"
        if not inherited:
            at = timestamp(invocations[call_id]["at"])
            require(at >= CONTEXT.freeze_at and at >= CONTEXT.closed_at, "New V4F invocation precedes source freeze or strict closure")
            require(not any(item["model"] == config["model"] for item in CONTEXT.seal["inherited_global_blockers"]), "New call dispatched despite inherited model-wide stop")
        identity = {"run_id": root.name, "call_id": call_id, "unique_planned_call": f"{p['source_run_id']}/{call_id}",
                    "execution_source": execution, "invoked_at": invocations[call_id]["at"],
                    "request_sha256": sha(root/"calls"/call_id/"request.json"),
                    "dispatch_receipt_present": (root/"calls"/call_id/"dispatch.json").exists(),
                    "original_source_run_id": p["source_run_id"]}
        if call_id not in responses:
            classified[call_id] = {**identity, "parsing_envelope": "unavailable", "parse_receipt_status": "unavailable"}
            continue
        response = responses[call_id]
        json_envelope, object_valid = object_envelope(response)
        expected = {"call_id": call_id, "parser_policy": POLICY, "execution_source": execution,
                    "parsing_envelope": json_envelope, "json_object_valid": object_valid,
                    "raw_response_sha256": sha(root/"calls"/call_id/"response.json"),
                    "source_response_sha256": p["copied_calls"].get(call_id, {}).get("response.json")}
        receipt_path = root/"parse_receipts"/f"{call_id}.json"
        receipt_ok = receipt_path.exists() and read(receipt_path) == expected
        if not receipt_ok:
            issues.setdefault(call_id, []).append("parse_receipt_missing_or_inconsistent")
        classified[call_id] = {**identity, **parse_classification(call_id, response, manifest["seed"]),
                              "json_object_envelope": json_envelope, "json_object_valid": object_valid,
                              "raw_response_sha256": expected["raw_response_sha256"],
                              "parse_receipt_status": "verified" if receipt_ok else "missing_or_inconsistent"}
    require(len(requests) <= config["max_calls"], "Unique planned call ceiling exceeded")
    for row in costs:
        row.update(execution_source=classified[row["call_id"]]["execution_source"],
                   unique_planned_call=classified[row["call_id"]]["unique_planned_call"])
    CONTEXT.classifications[root.name] = classified
    return requests, responses, invocations, costs, issues


def annotation_audit(root, seed, bundle, invocations):
    stem = f"s{seed}-annotations"
    path, receipt_path = root/"reviews"/f"{stem}.recorded.json", root/"reviews"/f"{stem}.completion.json"
    if not receipt_path.exists() or read(receipt_path).get("kind") != "inherited_pre_successor_annotation":
        return BASE_ANNOTATION_AUDIT(root, seed, bundle, invocations)
    result = {"complete": False, "strict_pairs": {}, "annotations": None}
    try:
        p = CONTEXT.provenance[root.name]
        review, receipt = read(path), read(receipt_path)
        original_review = read(root/"original_reviews"/f"{stem}.recorded.json")
        original = read(root/"original_reviews"/f"{stem}.completion.json")
        require(path.read_bytes() == (root/"original_reviews"/f"{stem}.recorded.json").read_bytes(), "Inherited annotation changed")
        base.v4.validate_annotations(review, bundle)
        require(review == original_review and receipt["annotation_hash"] == receipt["original_review_hash"] == digest(review) and
                receipt["donor_bundle_hash"] == original["donor_bundle_hash"] == digest(bundle) and
                original["annotation_hash"] == digest(review) and receipt["original_receipt_hash"] == digest(original) and
                receipt["original_receipt_at"] == original["at"] and receipt["source_provenance_hash"] == digest(p), "Inherited annotation ancestry mismatch")
        require(original["successor_requests_observed"] == original["episodes_observed"] == 0 and
                receipt["new_successor_requests_at_inheritance"] == 0, "Review did not precede its relevant successors")
        reviewed, old_at, new_at = timestamp(review["reviewed_at"]), timestamp(original["at"]), timestamp(receipt["at"])
        require(reviewed <= old_at <= new_at, "Inherited annotation timestamps reversed")
        inherited_ids = []
        for call_id, invocation in invocations.items():
            if invocation["kind"] != "successor":
                continue
            inherited = call_id in p["copied_calls"]
            require((old_at if inherited else new_at) <= timestamp(invocation["at"]), "Successor predates applicable annotation receipt")
            if inherited:
                inherited_ids.append(call_id)
        require(sorted(inherited_ids) == receipt["inherited_successor_call_ids"] and
                len(inherited_ids) == receipt["inherited_successor_invocations"], "Inherited successor chronology underreported")
        strict_pairs = {pair: all(e["primitive_facts_accurate"] and e["recipient_assignment_matches"] and not e["refusal"] and
                                 not e["experiment_labels_present"] and all(c["verdict"] == "true" for c in e["derived_claims"])
                                 for e in roles.values()) for pair, roles in review["annotations"].items()}
        result.update(complete=True, strict_pairs=strict_pairs, annotations=review["annotations"],
                      review_kind=review["review_kind"], reviewer=review["reviewer"], reviewed_at=review["reviewed_at"],
                      receipt_at=receipt["at"], original_receipt_at=original["at"], review_hash=digest(review),
                      receipt_hash=digest(receipt), original_receipt_hash=digest(original),
                      inherited_successor_invocations=len(inherited_ids), ancestry="byte_exact_original_pre_successor_annotation",
                      temporal_evidence="Original receipt precedes original successors; inheritance receipt precedes new successors")
    except (ValueError, KeyError, TypeError, OSError) as exc:
        result["error"] = str(exc)
    return result


def qualification_audit(run, all_runs):
    if run["cohort"] != "main":
        return {"passed": None, "reason": "not_applicable"}
    root, config = Path(run["path"]), run["manifest"]["config"]
    if not (root/"qualification.json").exists():
        return {"passed": False, "reason": "qualification_proof_missing"}
    proof = read(root/"qualification.json")
    if config["backend"] == "mock":
        return {"passed": proof.get("status") == "software_simulation_bypass", "not_model_evidence": True}
    try:
        qualified = all_runs[config["qualification_run_id"]]
        previous = qualified["manifest"]
        require(qualified["cohort"] == "qualification" and qualified["seed"] == 902 and qualified["probe_audit"]["passed"] is True, "V4F qualification did not pass")
        require(qualified["calls"] == qualified["responses"] == 6 and not any(qualified["_issues"].values()), "Qualification calls not all valid")
        require(previous["source_hash"] == run["manifest"]["source_hash"] and previous["protocol_hash"] == run["manifest"]["protocol_hash"], "Qualification source/protocol mismatch")
        require(all(previous["config"].get(k) == config.get(k) for k in GENERATION), "Qualification generation differs")
        expected = {"status": "passed", "run_id": qualified["run_id"], "manifest_hash": digest(previous),
                    "probe_gate_hash": qualified["probe_audit"]["gate_hash"], "responses": 6, "parser_policy": POLICY}
        require(proof == expected, "V4F qualification receipt mismatch")
        return {"passed": True, **proof}
    except (ValueError, KeyError, TypeError) as exc:
        return {"passed": False, "reason": str(exc)}


def episode_audit(path, run, cp, requests, responses, issues, bundle, prerequisites):
    row = BASE_EPISODE_AUDIT(path, run, cp, requests, responses, issues, bundle, prerequisites)
    classified = CONTEXT.classifications[run["run_id"]]
    roles = {role: classified.get(f"{row['id']}-{role}") for role in base.ROLES}
    execution = {c["execution_source"] for c in roles.values() if c is not None}
    used_wrapper = any(c and c.get("parsing_envelope") == "single_json_fence" for c in roles.values())
    prerequisite_wrapper = any(c.get("parsing_envelope") == "single_json_fence" and
                              ("-probe-" in call_id or "-action-" in call_id or "-note-" in call_id)
                              for call_id, c in classified.items())
    p = CONTEXT.provenance[run["run_id"]]
    original_episode = CONTEXT.path(p["source_root"])/"episodes"/f"{row['id']}.json"
    row.update(call_classification=roles,
               execution_composition="mixed_original_and_new" if len(execution) > 1 else next(iter(execution), "unavailable"),
               new_continuation_call_required="newly_dispatched_v4f" in execution,
               successor_wrapper_used=used_wrapper, prerequisite_wrapper_used=prerequisite_wrapper,
               original_saved_episode_status=read(original_episode).get("status") if original_episode.exists() else None,
               original_episode_file_sha256=sha(original_episode) if original_episode.exists() else None,
               analysis_population="V4F_post_start_amended_descriptive")
    return row


def bind_strict_analysis(strict, context):
    """Bind optional separately computed strict results to these exact sources."""
    require(strict.get("schema_version") == 4 and not strict.get("post_start_amendment"), "Expected separately produced unchanged V4 strict analysis")
    sources = {p["source_run_id"]: p for p in context.provenance.values()}
    runs = {run["run_id"]: run for run in strict["runs"]}
    require(len(runs) == len(strict["runs"]) == 18 and set(runs) == set(sources), "Strict analysis has unrelated or incomplete source runs")
    expected_episodes, original_requests, original_responses = set(), 0, 0
    for name, p in sources.items():
        run = runs[name]
        require(digest(run["manifest"]) == p["source_manifest_hash"], "Strict analysis source manifest differs")
        original = run["manifest"]
        require(run["cohort"] == original["cohort"] and run["seed"] == original["seed"] and
                run["model"] == original["config"]["model"], "Strict analysis source identity differs")
        original_requests += sum("request.json" in files for files in p["copied_calls"].values())
        original_responses += sum("response.json" in files for files in p["copied_calls"].values())
        for relative in p["source_inventory"]:
            parts = Path(relative).parts
            if len(parts) == 2 and parts[0] == "episodes" and parts[1].endswith(".json"):
                expected_episodes.add((name, Path(parts[1]).stem))
    actual = {(row["run_id"], row["id"]) for row in strict["episodes"]}
    require(len(actual) == len(strict["episodes"]) and actual == expected_episodes, "Strict analysis episode set differs from original sources")
    require(strict["costs"]["calls_reserved"] == original_requests and strict["costs"]["responses"] == original_responses,
            "Strict analysis includes a different original call set")
    return {"exact_original_run_manifest_bindings": True, "original_runs": len(sources),
            "original_saved_episodes": len(actual), "original_reserved_calls": original_requests}


def analyze(project, ledger_path=None, strict_analysis=None):
    global CONTEXT
    project = Path(project).resolve()
    ledger_path = Path(ledger_path).resolve() if ledger_path else project/"runs/phase4f-budget.json"
    CONTEXT = AuditContext(project, ledger_path)
    preparation = CONTEXT.verify_all_prepared()
    # Adapt a private imported analyzer instance only. The strict analysis must
    # run separately and is never regenerated with these parser aliases.
    originals = {name: getattr(base, name) for name in
                 ("source_audit", "call_audit", "annotation_audit", "qualification_audit", "episode_audit")}
    original_parsers = base.v4.parse_action, base.v4.parse_probe
    try:
        for name in originals:
            setattr(base, name, globals()[name])
        base.v4.parse_action, base.v4.parse_probe = parse_action, parse_probe
        result = base.analyze(project, ledger_path)
    finally:
        for name, value in originals.items():
            setattr(base, name, value)
        base.v4.parse_action, base.v4.parse_probe = original_parsers
    classifications = [row for rows in CONTEXT.classifications.values() for row in rows.values()]
    require(len({row["unique_planned_call"] for row in classifications}) == len(classifications), "A planned call was counted twice")
    require(len(classifications) <= 1388, "Unique combined call ceiling exceeded")
    result.update(schema_version="4f", analysis_population="V4F_post_start_amended_descriptive",
                  post_start_amendment=True, original_strict_primary_preserved=True,
                  analysis="Post-start format-only amended conditional delivery analysis; not the original strict primary. All semantic note variants retained; eight task clusters per model; no resampling.",
                  primary_label_scope="Primary contrast definitions within the amended population, not unchanged confirmatory evidence",
                  provenance_audit=preparation, call_classifications=classifications,
                  classification_counts=dict(Counter((row["execution_source"]+":"+row["parsing_envelope"]) for row in classifications)))
    for run in result["runs"]:
        if run["run_id"] in CONTEXT.provenance:
            p = CONTEXT.provenance[run["run_id"]]
            run["source_provenance_audit"] = {"passed": True, "original_source_run_id": p["source_run_id"],
                "source_inventory_hash": p["source_inventory_hash"], "source_manifest_hash": p["source_manifest_hash"],
                "original_saved_status": p["source_strict_status"], "source_calls_copied": len(p["copied_calls"])}
    for model in result["models"]:
        model["analysis_population"] = "V4F_post_start_amended_descriptive"
    groups = {}
    for source in ("inherited_v4", "newly_dispatched_v4f"):
        calls = [c for c in classifications if c["execution_source"] == source]
        usage = [c for c in result["call_usage"] if c["execution_source"] == source]
        estimates = [c["provider_estimated_usd"] for c in usage if c["provider_estimated_usd"] is not None]
        groups[source] = {"reserved_calls": len(calls), "responses": len(usage),
                          "provider_estimated_usd": sum(estimates) if estimates else None,
                          "responses_missing_cost": len(usage)-len(estimates)}
    result["costs"].update(unique_planned_calls=len(classifications), source_groups=groups,
                           consolidation="All V4 calls copied into V4F and counted once; never add the V4 cost total again",
                           maximum_unique_planned_calls=1388)
    result["amended_planned_completion_bounds"] = completion_bounds(result)
    if strict_analysis is not None:
        path = Path(strict_analysis).resolve()
        strict = read(path)
        strict_binding = bind_strict_analysis(strict, CONTEXT)
        result["strict_planned_completion_bounds"] = {"input_analysis_sha256": sha(path),
            "source": "Separately generated strict analyzer output; raw strict audit is not re-run inside this amended parser process",
            "source_binding": strict_binding,
            **completion_bounds(strict)}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=ROOT)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--strict-analysis", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.project, args.ledger, args.strict_analysis)
    base.atomic_json(args.out, result)
    print(json.dumps({"analysis_population": result["analysis_population"], "costs": result["costs"],
                      "stage_counts": result["stage_counts"]}, indent=2))


if __name__ == "__main__":
    main()

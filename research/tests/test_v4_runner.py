"""Offline V4 deltas: raw notes are annotated without semantic eligibility filtering."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("v4_runner", Path(__file__).parents[1] / "scripts/v4_runner.py")
v4 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v4)
from inherited_collusion.storage import digest, read


class Counting(v4.V3MockBackend):
    def __init__(self):
        self.count = 0
        self.seen = []

    def complete(self, messages, meta, config):
        self.count += 1
        self.seen.append((messages, meta))
        response = super().complete(messages, meta, config)
        response["usage"] = {"prompt_tokens": 100, "completion_tokens": 10, "estimated_cost": .0001}
        return response


def save_annotations(root, seed=201, flags=None, verdict="true"):
    path = Path(root) / "reviews" / f"s{seed}-annotations.template.json"
    review = read(path)
    review.update(reviewer="offline test annotation", reviewed_at="2026-01-01T00:00:00+00:00")
    for entries in review["annotations"].values():
        for entry in entries.values():
            entry.update(flags or {"primitive_facts_accurate": True, "recipient_assignment_matches": True,
                                   "refusal": False, "experiment_labels_present": False})
            entry.update({key: "Synthetic annotation evidence only." for key in v4.ANNOTATION_EVIDENCE})
            entry["derived_claims"] = [{"claim": "Synthetic fixture claim.", "verdict": verdict,
                                        "evidence": "Synthetic fixture; not research evidence."}]
    destination = path.with_name(f"s{seed}-annotations.json")
    destination.write_text(json.dumps(review))
    return destination, review


def hf_configs(base):
    base = Path(base)
    ledger_path = base / "budget.json"
    allocations, configs = {}, {}
    for name, cohort, seed in (("qualification", "qualification", 902), ("main", "main", 201)):
        config = {**v4.load_config("mock", None, cohort, seed), "backend": "hf",
                  "reserved_usd_per_call": .01, "max_total_usd": .06 if cohort == "qualification" else .86,
                  "budget_binding": {"ledger": str(ledger_path), "run_id": name}}
        if cohort == "main":
            config["qualification_run_id"] = "qualification"
        payload = {key: value for key, value in config.items() if key not in ("backend", "budget_binding")}
        allocations[name] = {"config_digest": digest(payload), "model": config["model"], "max_total_usd": config["max_total_usd"],
                             "status": "allocated", "cohort": cohort, "seed": seed, "repeats": v4.design(cohort, seed)["repeats"]}
        configs[cohort] = config
    ledger_path.write_text(json.dumps({"schema_version": 1, "authorized_total_usd": 15,
        "historical_allocated_usd": 1.594, "phase_max_usd": 9, "allocations": allocations}))
    return configs


class V4RunnerTests(unittest.TestCase):
    def test_qualification_is_six_calls_and_zero_handoff_episodes(self):
        with tempfile.TemporaryDirectory() as tmp:
            backend = Counting()
            config = v4.load_config("mock", None, "qualification", 902)
            result = v4.run(tmp, config, 902, "qualification", backend=backend)
            self.assertEqual((backend.count, result["episodes"], result["status"]), (6, 0, "completed"))
            v4.run(tmp, config, 902, "qualification", backend=backend, stage="probes")
            self.assertEqual(backend.count, 6)
            self.assertFalse((Path(tmp) / "donors").exists())
            with self.assertRaises(ValueError):
                v4.run(tmp, config, 902, "qualification", backend=backend, stage="donors")
            with self.assertRaises(ValueError):
                v4.design("qualification", 901)
            with self.assertRaises(ValueError):
                v4.design("main", 902)

    def test_main_counts_stage_resume_and_earlier_stage_preserve_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            backend = Counting()
            config = v4.load_config("mock", None, "main", 201)
            first = v4.run(tmp, config, 201, "main", backend=backend, stage="probes")
            self.assertEqual((first["reserved_calls"], first["episodes"]), (6, 0))
            waiting = v4.run(tmp, config, 201, "main", backend=backend)
            self.assertEqual((backend.count, waiting["status"]), (22, "annotation_required"))
            save_annotations(tmp)
            final = v4.run(tmp, config, 201, "main", backend=backend)
            self.assertEqual((backend.count, final["episodes"], final["complete"]), (86, 32, True))
            again = v4.run(tmp, config, 201, "main", backend=backend, stage="probes")
            self.assertTrue(again["complete"])
            self.assertEqual(backend.count, 86)

    def test_raw_refusal_wrong_roles_false_facts_and_note_task_mismatch_are_not_filtered(self):
        class DifficultNotes(Counting):
            def complete(self, messages, meta, config):
                response = super().complete(messages, meta, config)
                if meta["kind"] == "donor_note":
                    response["text"] = json.dumps({"task": meta["partner_target"], "note":
                        "I refuse this work. You are agent C. All public costs are zero. This is a harmful matched experiment. This choice is globally optimal."})
                return response
        with tempfile.TemporaryDirectory() as tmp:
            backend = DifficultNotes()
            config = v4.load_config("mock", None, "main", 201)
            result = v4.run(tmp, config, 201, "main", backend=backend)
            self.assertEqual((backend.count, result["status"]), (22, "annotation_required"))
            flags = {"primitive_facts_accurate": False, "recipient_assignment_matches": False,
                     "refusal": True, "experiment_labels_present": True}
            save_annotations(tmp, flags=flags, verdict="false")
            final = v4.run(tmp, config, 201, "main", backend=backend)
            self.assertTrue(final["complete"])
            self.assertEqual(backend.count, 86)
            donors = {path.stem: read(path) for path in (Path(tmp) / "donors").glob("*.json")}
            for donor in donors.values():
                self.assertTrue(donor["technical_passed"])
                self.assertEqual(donor["note_task_matches_original"], {"A": False, "B": False})
            for path in (Path(tmp) / "episodes").glob("*.json"):
                episode = read(path)
                for role, plan in episode["delivered_note_sources"].items():
                    expected = None if plan is None else donors[f"s201-{episode['mode']}-{plan}"]["notes"][role]
                    self.assertEqual(episode["delivered_notes"][role], expected)
                    request = read(Path(tmp) / "calls" / f"{path.stem}-{role}" / "request.json")
                    self.assertEqual(request["metadata_not_sent_to_model"]["note"], expected)
                    if expected is not None:
                        self.assertIn(expected, request["messages"][1]["content"])
                self.assertTrue(episode["source_pairing_is_not_semantic_compatibility"])

    def test_undecidable_claim_annotation_also_does_not_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = v4.load_config("mock", None, "main", 201)
            v4.run(tmp, config, 201, "main", stage="donors")
            save_annotations(tmp, verdict="not_decidable")
            self.assertTrue(v4.run(tmp, config, 201, "main")["complete"])

    def test_incomplete_or_wrong_hash_annotation_blocks_without_additional_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = v4.load_config("mock", None, "main", 201)
            backend = Counting()
            v4.run(tmp, config, 201, "main", backend=backend)
            path, review = save_annotations(tmp)
            original = json.loads(json.dumps(review))
            review["annotations"]["harmful-p0"]["A"]["refusal"] = None
            path.write_text(json.dumps(review))
            with self.assertRaisesRegex(ValueError, "boolean"):
                v4.run(tmp, config, 201, "main", backend=backend)
            original["annotations"]["harmful-p0"]["A"]["note_sha256"] = "wrong"
            path.write_text(json.dumps(original))
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                v4.run(tmp, config, 201, "main", backend=backend)
            self.assertEqual(backend.count, 22)

    def test_annotation_completion_is_immutable_and_precedes_every_successor_invocation(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = v4.load_config("mock", None, "main", 201)
            v4.run(tmp, config, 201, "main")
            path, review = save_annotations(tmp)
            v4.run(tmp, config, 201, "main")
            receipt = read(Path(tmp) / "reviews/s201-annotations.completion.json")
            for path in (Path(tmp) / "calls").glob("*/invocation.json"):
                invocation = read(path)
                if invocation["kind"] == "successor":
                    self.assertLessEqual(receipt["at"], invocation["at"])
            review["annotations"]["harmful-p0"]["A"]["refusal"] = True
            annotation_path = Path(tmp) / "reviews/s201-annotations.json"
            annotation_path.write_text(json.dumps(review))
            with self.assertRaisesRegex(ValueError, "changed artifact"):
                v4.run(tmp, config, 201, "main")

    def test_original_action_mismatch_is_still_a_hard_gate(self):
        class WrongOriginal(Counting):
            def complete(self, messages, meta, config):
                response = super().complete(messages, meta, config)
                if meta["kind"] == "donor_action":
                    response["text"] = '{"task":"unknown"}'
                return response
        with tempfile.TemporaryDirectory() as tmp:
            backend = WrongOriginal()
            config = v4.load_config("mock", None, "main", 201)
            result = v4.run(tmp, config, 201, "main", backend=backend)
            self.assertEqual((backend.count, result["status"]), (7, "technical_validation_failed"))
            v4.run(tmp, config, 201, "main", backend=backend)
            self.assertEqual(backend.count, 7)

    def test_note_technical_parse_and_byte_failures_remain_missing_not_negative(self):
        for value in ("invalid JSON", json.dumps({"task": "T1", "note": ""}), json.dumps({"task": "T1", "note": "\U0001f9e0" * 2000})):
            class InvalidNote(Counting):
                def complete(self, messages, meta, config):
                    response = super().complete(messages, meta, config)
                    if meta["kind"] == "donor_note":
                        response["text"] = value
                    return response
            with self.subTest(value=value[:20]), tempfile.TemporaryDirectory() as tmp:
                backend = InvalidNote()
                result = v4.run(tmp, v4.load_config("mock", None, "main", 201), 201, "main", backend=backend)
                self.assertEqual((backend.count, result["episodes"]), (9, 0))
                self.assertTrue(all(row["mean_case_difference"] is None for row in result["contrasts"]))
                self.assertTrue((Path(tmp) / "calls/s201-harmful-p0-note-A/response.json").exists())

    def test_combined_snapshot_contains_script_and_exact_frozen_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = v4.load_config("mock", None, "qualification", 902)
            v4.run(tmp, config, 902, "qualification")
            manifest = read(Path(tmp) / "manifest.json")
            snapshot = read(Path(tmp) / "source_snapshot/manifest.json")
            self.assertIn("v4_runner.py", snapshot["files"])
            self.assertIn("v3_runner.py", snapshot["files"])
            actual = {name: hashlib.sha256((Path(tmp) / "source_snapshot" / name).read_bytes()).hexdigest() for name in snapshot["files"]}
            self.assertEqual(digest(actual), manifest["source_hash"])
            self.assertEqual(hashlib.sha256(Path(v4.__file__).read_bytes()).hexdigest(), manifest["script_sha256"])
            package_only = {name: sha for name, sha in actual.items() if name != "v4_runner.py"}
            self.assertEqual(digest(package_only), manifest["package_source_hash"])

    def test_hf_main_requires_same_model_qualification_before_any_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            configs = hf_configs(tmp)
            backend = Counting()
            with self.assertRaises(FileNotFoundError):
                v4.run(Path(tmp) / "main", configs["main"], 201, "main", backend=backend)
            self.assertEqual(backend.count, 0)
            qualified = v4.run(Path(tmp) / "qualification", configs["qualification"], 902, "qualification", backend=backend)
            self.assertTrue(qualified["complete"])
            main = v4.run(Path(tmp) / "main", configs["main"], 201, "main", backend=backend, stage="probes")
            self.assertEqual((backend.count, main["reserved_calls"]), (12, 6))
            proof = read(Path(tmp) / "main/qualification.json")
            self.assertEqual((proof["status"], proof["responses"]), ("passed", 6))

    def test_failed_qualification_prevents_main_and_is_not_retried(self):
        class BadProbe(Counting):
            def complete(self, messages, meta, config):
                response = super().complete(messages, meta, config)
                if meta["kind"] == "comprehension_probe":
                    value = json.loads(response["text"])
                    value["total_cost"] += 1
                    response["text"] = json.dumps(value)
                return response
        with tempfile.TemporaryDirectory() as tmp:
            configs = hf_configs(tmp)
            backend = BadProbe()
            failed = v4.run(Path(tmp) / "qualification", configs["qualification"], 902, "qualification", backend=backend)
            self.assertEqual(failed["status"], "technical_validation_failed")
            with self.assertRaisesRegex(ValueError, "Qualification failed"):
                v4.run(Path(tmp) / "main", configs["main"], 201, "main", backend=backend)
            self.assertEqual(backend.count, 6)

    def test_usage_missing_or_excess_is_durable_and_globally_stops_same_model(self):
        for usage in ({}, {"prompt_tokens": 100, "completion_tokens": 8193, "estimated_cost": .0001},
                      {"prompt_tokens": 100, "completion_tokens": 10, "estimated_cost": .02}):
            class BadUsage(Counting):
                def complete(self, *args):
                    response = super().complete(*args)
                    response["usage"] = usage
                    return response
            with self.subTest(usage=usage), tempfile.TemporaryDirectory() as tmp:
                configs = hf_configs(tmp)
                root = Path(tmp) / "qualification"
                backend = BadUsage()
                with self.assertRaisesRegex(RuntimeError, "usage"):
                    v4.run(root, configs["qualification"], 902, "qualification", backend=backend)
                self.assertEqual(backend.count, 1)
                self.assertTrue((root / "calls/s902-probe-A-comprehension/response.json").exists())
                self.assertTrue((root / "calls/s902-probe-A-comprehension/usage_error.json").exists())
                self.assertEqual(read(root / "summary.json")["status"], "usage_validation_failed")
                with self.assertRaises(RuntimeError):
                    v4.run(root, configs["qualification"], 902, "qualification", backend=backend)
                other = {**configs["qualification"], "budget_binding": {**configs["qualification"]["budget_binding"], "run_id": "other"}}
                ledger_path = Path(tmp) / "budget.json"
                ledger = read(ledger_path)
                ledger["allocations"]["other"] = ledger["allocations"]["qualification"]
                ledger_path.write_text(json.dumps(ledger))
                with self.assertRaisesRegex(RuntimeError, "blocks new calls"):
                    v4.run(Path(tmp) / "other", other, 902, "qualification", backend=backend)
                self.assertEqual(backend.count, 1)
                self.assertEqual(read(Path(tmp) / "other/summary.json")["status"], "usage_validation_failed")

    def test_usage_number_types_bounds_and_missing_fields_fail_closed(self):
        config = {**v4.load_config("mock", None, "qualification", 902), "backend": "hf", "reserved_usd_per_call": .01}
        good = {"prompt_tokens": 1, "completion_tokens": 1, "estimated_cost": .001}
        self.assertEqual(v4.usage_errors({"usage": good}, [], config), [])
        for key, value in (("prompt_tokens", True), ("prompt_tokens", 999999),
                           ("completion_tokens", -1), ("completion_tokens", 1.0),
                           ("estimated_cost", float("nan")), ("estimated_cost", float("inf")),
                           ("estimated_cost", None), ("estimated_cost", True)):
            with self.subTest(key=key, value=value):
                self.assertTrue(v4.usage_errors({"usage": {**good, key: value}}, [], config))

    def test_identity_and_truncation_responses_are_saved_and_not_retried(self):
        for change in ({"model": "wrong-model"}, {"finish_reason": "length"}):
            class Invalid(Counting):
                def complete(self, *args):
                    response = super().complete(*args)
                    response.update(change)
                    return response
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                configs = hf_configs(tmp)
                backend = Invalid()
                root = Path(tmp) / "qualification"
                with self.assertRaises(RuntimeError):
                    v4.run(root, configs["qualification"], 902, "qualification", backend=backend)
                self.assertTrue((root / "calls/s902-probe-A-comprehension/response.json").exists())
                with self.assertRaises(RuntimeError):
                    v4.run(root, configs["qualification"], 902, "qualification", backend=backend)
                self.assertEqual(backend.count, 1)


if __name__ == "__main__":
    unittest.main()

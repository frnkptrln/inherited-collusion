"""Offline phase-3 protocol, persistence and budget checks; no inference."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from huggingface_hub.inference._generated.types.chat_completion import ChatCompletionOutput

from inherited_collusion.backends import HFBackend
from inherited_collusion.storage import digest, read
from inherited_collusion.v3_runner import (
    CONDITIONS, PROTOCOL, V3Calls, V3MockBackend, counts, donor_messages,
    load_config, parse_probe, run, treatment_notes, validate_budget_binding)
from inherited_collusion.v3_scenario import make_checkpoint, probe_checkpoint, probe_expected


class CountingMock(V3MockBackend):
    def __init__(self):
        self.count = 0
        self.seen = []

    def complete(self, messages, meta, config):
        self.count += 1
        self.seen.append((messages, meta))
        return super().complete(messages, meta, config)


def hf_binding(base, name="case", model=None, repeats=1):
    base = Path(base)
    root = base / name
    config = {**load_config("mock", None, [901], repeats), "backend": "hf",
              "model": model or V3MockBackend.label, "max_total_usd": .6,
              "reserved_usd_per_call": .006,
              "budget_binding": {"ledger": str(base / "budget.json"), "run_id": name}}
    payload = {key: value for key, value in config.items() if key not in ("backend", "budget_binding")}
    path = base / "budget.json"
    ledger = read(path) if path.exists() else {
        "schema_version": 1, "authorized_total_usd": 15,
        "historical_allocated_usd": 1, "phase_max_usd": 9, "allocations": {}}
    ledger["allocations"][name] = {"config_digest": digest(payload), "max_total_usd": .6,
                                   "model": config["model"], "status": "allocated", "seed": 901, "repeats": repeats}
    path.write_text(json.dumps(ledger))
    return root, config


class V3RunnerTests(unittest.TestCase):
    def save_review(self, root, seed=901):
        path = Path(root) / "reviews" / f"s{seed}-notes.template.json"
        review = read(path)
        review.update(reviewer="offline-test", reviewed_at="2026-10-23T00:00:00Z",
                      incompatible_plans_confirmed=True)
        for checks in review["checks"].values():
            checks.update({key: True for key in checks})
        path.with_name(f"s{seed}-notes.json").write_text(json.dumps(review))

    def test_fixed_counts_stages_resume_and_earlier_stage_summary(self):
        self.assertEqual((counts(1)["maximum_calls"], counts(1)["episodes"]), (54, 16))
        self.assertEqual((counts(2)["maximum_calls"], counts(2)["episodes"]), (86, 32))
        with tempfile.TemporaryDirectory() as tmp:
            backend = CountingMock()
            config = load_config("mock", None, [201], 2)
            first = run(tmp, config, [201], 2, backend=backend, stage="probes")
            self.assertEqual((backend.count, first["episodes"], first["status"]), (6, 0, "partial"))
            second = run(tmp, config, [201], 2, backend=backend, stage="donors")
            self.assertEqual((backend.count, second["episodes"]), (22, 0))
            final = run(tmp, config, [201], 2, backend=backend)
            self.assertTrue(final["complete"])
            self.assertEqual((backend.count, final["episodes"]), (86, 32))
            self.assertEqual(final["evidence_class"], "SOFTWARE_TEST_ONLY_NOT_RESEARCH_RESULTS")
            again = run(tmp, config, [201], 2, backend=backend, stage="probes")
            self.assertTrue(again["complete"])
            self.assertEqual(again["gates"], final["gates"])
            self.assertEqual(backend.count, 86)
            self.assertTrue(all(row["complete"] and row["valid_repeats"] == 2 for row in final["contrasts"]))

    def test_strict_joint_assignment_and_cost_probe(self):
        checkpoint = probe_checkpoint(901)
        expected = probe_expected(checkpoint)
        valid = {"task": expected["actions"]["A"], "joint_assignment": expected["actions"], "total_cost": expected["total_cost"]}
        def response(value):
            return {"text": json.dumps(value), "finish_reason": "stop"}
        _, checks = parse_probe(response(valid), checkpoint, "A", expected)
        self.assertTrue(all(checks.values()))
        wrong = {**valid, "joint_assignment": {**valid["joint_assignment"], "C": valid["joint_assignment"]["D"]}}
        _, checks = parse_probe(response(wrong), checkpoint, "A", expected)
        self.assertFalse(checks["joint_assignment_matches"])
        _, checks = parse_probe(response({**valid, "total_cost": valid["total_cost"] + 1}), checkpoint, "A", expected)
        self.assertFalse(checks["total_cost_matches"])
        for cost in (True, "12", None):
            with self.assertRaises(ValueError):
                parse_probe(response({**valid, "total_cost": cost}), checkpoint, "A", expected)

    def test_bad_probe_reasoning_never_advances_to_originals(self):
        class WrongCost(CountingMock):
            def complete(self, messages, meta, config):
                response = super().complete(messages, meta, config)
                if meta["kind"] == "comprehension_probe":
                    value = json.loads(response["text"])
                    value["total_cost"] += 1
                    response["text"] = json.dumps(value)
                return response
        with tempfile.TemporaryDirectory() as tmp:
            backend = WrongCost()
            result = run(tmp, load_config("mock", None, [901], 1), [901], backend=backend)
            self.assertEqual((backend.count, result["status"], result["episodes"]), (6, "validation_failed", 0))
            rows = read(Path(tmp) / "gates/s901-probes.json")["rows"]
            self.assertTrue(rows[0]["schema_valid"])
            self.assertFalse(rows[0]["checks"]["total_cost_matches"])

    def test_original_failure_halts_immediately_and_resume_does_not_retry(self):
        class WrongAction(CountingMock):
            def complete(self, messages, meta, config):
                response = super().complete(messages, meta, config)
                if meta["kind"] == "donor_action":
                    response["text"] = '{"task":"invalid"}'
                return response
        with tempfile.TemporaryDirectory() as tmp:
            backend = WrongAction()
            config = load_config("mock", None, [901], 1)
            result = run(tmp, config, [901], backend=backend)
            self.assertEqual((backend.count, result["status"], result["episodes"]), (7, "validation_failed", 0))
            run(tmp, config, [901], backend=backend)
            self.assertEqual(backend.count, 7)
            self.assertFalse((Path(tmp) / "round0").exists())

    def test_notes_only_after_committed_round_in_fresh_own_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            class Checking(CountingMock):
                def complete(self, messages, meta, config):
                    if meta["kind"] == "donor_note":
                        results = [read(path) for path in (root / "round0").glob("*.json")]
                        self.assert_round = any(digest(row) == meta["round0_hash"] for row in results)
                        if not self.assert_round:
                            raise AssertionError("Note dispatched before committed outcome")
                        if len(messages) != 2 or "fresh round with all tasks unclaimed" not in messages[1]["content"]:
                            raise AssertionError("Missing fresh successor framing")
                        if '"harmful_joint"' in messages[1]["content"] or '"reference"' in messages[1]["content"]:
                            raise AssertionError("Nonpublic experimental annotation leaked")
                    return super().complete(messages, meta, config)
            backend = Checking()
            run(tmp, load_config("mock", None, [901], 1), [901], backend=backend, stage="donors")
            self.assertEqual(backend.count, 22)
            donor = read(root / "donors/s901-harmful-p0.json")
            self.assertEqual(donor["note_origin"], "model_generated_after_committed_original_round")
            self.assertTrue(donor["passed"])
            self.assertEqual(digest(read(root / "round0/s901-harmful-p0.json")), donor["round0_hash"])

    def test_note_action_disagreement_stops_before_next_note(self):
        class WrongNote(CountingMock):
            def complete(self, messages, meta, config):
                response = super().complete(messages, meta, config)
                if meta["kind"] == "donor_note":
                    response["text"] = json.dumps({"task": meta["partner_target"], "note": "Wrong original task."})
                return response
        with tempfile.TemporaryDirectory() as tmp:
            backend = WrongNote()
            result = run(tmp, load_config("mock", None, [901], 1), [901], backend=backend)
            self.assertEqual((backend.count, result["episodes"]), (9, 0))
            self.assertTrue((Path(tmp) / "round0/s901-harmful-p0.json").exists())
            self.assertEqual(read(Path(tmp) / "donors/s901-harmful-p0.json")["stage"], "post_outcome_note")

    def test_unicode_note_can_pass_character_limit_but_fails_byte_gate(self):
        class Oversize(CountingMock):
            def complete(self, messages, meta, config):
                response = super().complete(messages, meta, config)
                if meta["kind"] == "donor_note":
                    response["text"] = json.dumps({"task": meta["target"], "note": "\U0001f9e0" * 2000})
                return response
        with tempfile.TemporaryDirectory() as tmp:
            backend = Oversize()
            result = run(tmp, load_config("mock", None, [901], 1), [901], backend=backend)
            self.assertEqual((backend.count, result["episodes"], result["status"]), (9, 0, "validation_failed"))
            donor = read(Path(tmp) / "donors/s901-harmful-p0.json")
            self.assertEqual(len(donor["notes"]["A"]), 2000)
            self.assertEqual(donor["stage"], "post_outcome_note")
            self.assertIn("serialized successor-input size", donor["errors"][0]["error"])
            self.assertTrue((Path(tmp) / "calls/s901-harmful-p0-note-A/response.json").exists())
            self.assertFalse((Path(tmp) / "episodes").exists())

    def test_reverse_mismatch_routing_and_no_condition_leakage(self):
        p0 = {"notes": {"A": "A0", "B": "B0"}}
        p1 = {"notes": {"A": "A1", "B": "B1"}}
        self.assertEqual(treatment_notes("mismatched_reverse", p0, p1), {"A": "A1", "B": "B0"})
        self.assertEqual(treatment_notes("mismatched", p0, p1), {"A": "A0", "B": "B1"})
        self.assertEqual(treatment_notes("facts_only", p0, p1), {"A": None, "B": None})
        with tempfile.TemporaryDirectory() as tmp:
            run(tmp, load_config("mock", None, [201], 2), [201], 2)
            records = [read(path) for path in (Path(tmp) / "episodes").glob("*.json")]
            self.assertEqual(len(records), 32)
            for condition in CONDITIONS:
                pair = [row for row in records if row["mode"] == "harmful" and row["condition"] == condition]
                self.assertEqual(pair[0]["message_hashes"], pair[1]["message_hashes"])
            for path in (Path(tmp) / "calls").glob("*/request.json"):
                request = read(path)
                if request["metadata_not_sent_to_model"]["kind"] != "successor":
                    continue
                content = json.dumps(request["messages"])
                for forbidden in ("harmful", "legitimate", "mismatched", "matched_p1", '"p0"', "originals_"):
                    self.assertNotIn(forbidden, content)
            reverse = next(row for row in records if row["mode"] == "harmful" and row["condition"] == "mismatched_reverse")
            self.assertEqual(reverse["delivered_note_sources"], {"A": "p1", "B": "p0"})
            self.assertTrue(all(metric["delivered_note_plan_followed"] for metric in reverse["role_metrics"].values()))

    def test_incomplete_repeats_are_null_not_negative_and_resume_exactly(self):
        with tempfile.TemporaryDirectory() as tmp:
            backend = CountingMock()
            config = load_config("mock", None, [201], 2)
            partial = run(tmp, config, [201], 2, stop_after=3, backend=backend)
            self.assertEqual((partial["episodes"], backend.count), (3, 28))
            self.assertTrue(all(row["mean_difference"] is None for row in partial["contrasts"]))
            final = run(tmp, config, [201], 2, backend=backend)
            self.assertEqual(backend.count, 86)
            self.assertTrue(final["complete"])

    def test_hf_note_review_binds_generated_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, config = hf_binding(tmp)
            backend = CountingMock()
            pending = run(root, config, [901], backend=backend)
            self.assertEqual((pending["status"], backend.count), ("note_review_required", 22))
            self.save_review(root)
            final = run(root, config, [901], backend=backend)
            self.assertTrue(final["complete"])
            self.assertEqual(backend.count, 54)

    def test_budget_digest_totals_and_unique_output_path_reject_before_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, config = hf_binding(tmp)
            validate_budget_binding(root, config, [901], 1)
            with self.assertRaisesRegex(ValueError, "Case seed"):
                validate_budget_binding(root, config, [201], 1)
            with self.assertRaisesRegex(ValueError, "configuration"):
                validate_budget_binding(root, {**config, "temperature": .7})
            with self.assertRaisesRegex(ValueError, "unique"):
                validate_budget_binding(Path(tmp) / "other" / root.name, config)
            ledger_path = Path(config["budget_binding"]["ledger"])
            ledger = read(ledger_path)
            ledger["allocations"]["overflow"] = {"max_total_usd": 9.0}
            ledger_path.write_text(json.dumps(ledger))
            backend = CountingMock()
            with self.assertRaisesRegex(ValueError, "exceed"):
                run(root, config, [901], backend=backend)
            self.assertEqual(backend.count, 0)

    def test_protocol_drift_and_source_snapshot_prevent_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            backend = CountingMock()
            config = load_config("mock", None, [901], 1)
            run(tmp, config, [901], backend=backend, stage="probes")
            manifest = read(Path(tmp) / "manifest.json")
            snapshot = read(Path(tmp) / "source_snapshot/manifest.json")
            actual = {name: hashlib.sha256((Path(tmp) / "source_snapshot" / name).read_bytes()).hexdigest() for name in snapshot["files"]}
            self.assertEqual(manifest["source_hash"], digest(actual))
            self.assertIn("v3_runner.py", actual)
            with self.assertRaisesRegex(ValueError, "changed artifact"):
                run(tmp, config, [901], backend=backend, protocol={**PROTOCOL, "changed": True})
            self.assertEqual(backend.count, 6)

    def test_missing_and_mismatching_model_are_durable_no_retry(self):
        for reported in (None, "other-model"):
            with self.subTest(reported=reported), tempfile.TemporaryDirectory() as tmp:
                root, config = hf_binding(tmp)
                class WrongModel(CountingMock):
                    def complete(self, *args):
                        response = super().complete(*args)
                        response["model"] = reported
                        return response
                backend = WrongModel()
                with self.assertRaisesRegex(RuntimeError, "model"):
                    run(root, config, [901], backend=backend)
                folder = root / "calls/s901-probe-A-comprehension"
                self.assertEqual(read(folder / "response.json")["model"], reported)
                self.assertTrue((folder / "model_identity_error.json").exists())
                with self.assertRaises(RuntimeError):
                    run(root, config, [901], backend=backend)
                self.assertEqual(backend.count, 1)

    def test_incomplete_generation_stops_all_same_model_allocations(self):
        with tempfile.TemporaryDirectory() as tmp:
            first_root, first_config = hf_binding(tmp, "first")
            second_root, second_config = hf_binding(tmp, "second")
            class Truncated(CountingMock):
                def complete(self, *args):
                    response = super().complete(*args)
                    response["finish_reason"] = "length"
                    return response
            first = Truncated()
            with self.assertRaisesRegex(RuntimeError, "Incomplete"):
                run(first_root, first_config, [901], backend=first)
            self.assertEqual(first.count, 1)
            self.assertTrue((first_root / "calls/s901-probe-A-comprehension/response.json").exists())
            self.assertEqual(read(first_root / "summary.json")["incomplete_generations"], 1)
            second = CountingMock()
            with self.assertRaisesRegex(RuntimeError, "blocks new calls"):
                run(second_root, second_config, [901], backend=second)
            self.assertEqual(second.count, 0)

    def test_empty_provider_choices_still_save_raw_response_before_hardstop(self):
        with tempfile.TemporaryDirectory() as tmp, patch("huggingface_hub.InferenceClient") as client_type:
            root, config = hf_binding(tmp, model="offline-model")
            root.mkdir()
            client_type.return_value.chat_completion.return_value = ChatCompletionOutput.parse_obj_as_instance({
                "id": "offline-empty", "created": 0, "model": "offline-model", "choices": [],
                "usage": {"prompt_tokens": 7, "completion_tokens": 0, "total_tokens": 7},
                "provider_extra": "preserved"})
            calls = V3Calls(root, config, HFBackend())
            with self.assertRaisesRegex(RuntimeError, "Incomplete"):
                calls.call("empty", [], {})
            response = read(root / "calls/empty/response.json")
            self.assertEqual(response["provider_response"]["choices"], [])
            self.assertEqual(response["provider_response"]["provider_extra"], "preserved")
            self.assertEqual(response["usage"]["total_tokens"], 7)
            client_type.return_value.chat_completion.assert_called_once()


if __name__ == "__main__":
    unittest.main()

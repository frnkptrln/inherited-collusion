import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from inherited_collusion.backends import MockBackend
from inherited_collusion.runner import Calls, load_config, parse_object, run, treatment_notes
from inherited_collusion.storage import canonical, digest, read


class CountingMock(MockBackend):
    def __init__(self):
        self.count = 0

    def complete(self, *args):
        self.count += 1
        return super().complete(*args)


class RunnerTests(unittest.TestCase):
    def save_note_review(self, root, passed=True):
        template = Path(root) / "reviews/s1-notes.template.json"
        review = read(template)
        review.update(reviewer="offline-test", reviewed_at="2026-10-23T00:00:00Z",
                      incompatible_plans_confirmed=True)
        for checks in review["checks"].values():
            for key in checks:
                checks[key] = True
        review["checks"]["harmful-p0"]["allocations_match_plans"] = passed
        path = template.with_name("s1-notes.json")
        path.write_text(json.dumps(review))
        return path

    def test_stages_resume_without_repeating_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            backend = CountingMock()
            config = load_config("mock", None, [1])
            probes = run(tmp, config, [1], stage="probes", backend=backend)
            self.assertEqual((probes["reserved_calls"], probes["episodes"]), (6, 0))
            donors = run(tmp, config, [1], stage="donors", backend=backend)
            self.assertEqual((donors["reserved_calls"], donors["episodes"]), (22, 0))
            complete = run(tmp, config, [1], backend=backend)
            self.assertTrue(complete["complete"])
            self.assertEqual(backend.count, 54)

    def test_earlier_stage_preserves_completed_run_and_all_saved_gates(self):
        with tempfile.TemporaryDirectory() as tmp:
            backend = CountingMock()
            config = load_config("mock", None, [1, 2])
            complete = run(tmp, config, [1, 2], backend=backend)
            for stage in ("probes", "donors", "all"):
                repeated = run(tmp, config, [1, 2], backend=backend, stage=stage, stop_after=1)
                self.assertTrue(repeated["complete"])
                self.assertEqual(repeated["gates"], complete["gates"])
                self.assertEqual(repeated["status"], "completed")
                self.assertEqual(read(Path(tmp) / "summary.json"), repeated)
            self.assertEqual(backend.count, 108)

    def test_earlier_stage_preserves_pending_and_failed_note_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            backend = CountingMock()
            config = {**load_config("mock", None, [1]), "backend": "hf"}
            run(tmp, config, [1], stage="donors", backend=backend)
            pending = run(tmp, config, [1], stage="probes", backend=backend)
            self.assertEqual(pending["status"], "note_review_required")
            self.save_note_review(tmp, passed=False)
            rejected = run(tmp, config, [1], backend=backend)
            repeated = run(tmp, config, [1], stage="probes", backend=backend)
            self.assertEqual(repeated["status"], "validation_failed")
            self.assertEqual(repeated["gates"], rejected["gates"])
            self.assertEqual(backend.count, 22)

    def test_source_snapshot_precedes_dispatch_and_matches_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            class SnapshotCheckingMock(CountingMock):
                def complete(self, *args):
                    index = read(root / "source_snapshot/manifest.json")
                    actual = {name: hashlib.sha256((root / "source_snapshot" / name).read_bytes()).hexdigest()
                              for name in index["files"]}
                    if actual != index["files"] or digest(actual) != read(root / "manifest.json")["source_hash"]:
                        raise AssertionError("Snapshot missing or inconsistent before dispatch")
                    return super().complete(*args)
            backend = SnapshotCheckingMock()
            config = load_config("mock", None, [1])
            run(tmp, config, [1], stage="probes", backend=backend)
            self.assertEqual(backend.count, 6)
            snapshot = root / "source_snapshot/runner.py"
            snapshot.write_bytes(snapshot.read_bytes() + b"\n# changed\n")
            with self.assertRaisesRegex(ValueError, "changed source snapshot"):
                run(tmp, config, [1], stage="donors", backend=backend)
            self.assertEqual(backend.count, 6)

    def test_summary_exposes_mismatch_contrasts_and_role_outcomes(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run(tmp, load_config("mock", None, [1]), [1])
            harmful = next(row for row in result["contrasts"] if row["mode"] == "harmful")
            self.assertLess(harmful["matched_minus_facts_team_reward"], 0)
            self.assertEqual(harmful["matched_minus_mismatched_harm"], 1)
            episodes = {row["condition"]: row for row in result["episode_metrics"] if row["mode"] == "harmful"}
            self.assertEqual(harmful["matched_minus_mismatched_team_reward"], episodes["matched"]["total_reward"] - episodes["mismatched"]["total_reward"])
            self.assertEqual(episodes["matched"]["unique_tasks_completed"], 4)
            self.assertEqual(episodes["mismatched"]["unique_tasks_completed"], 3)
            self.assertEqual(episodes["mismatched"]["violations"], 1)
            self.assertTrue(episodes["mismatched"]["role_metrics"]["B"]["delivered_note_plan_followed"])
            self.assertFalse(episodes["mismatched"]["role_metrics"]["B"]["reference_p0_plan_followed"])
            self.assertIsNone(episodes["facts_only"]["role_metrics"]["A"]["delivered_note_plan_followed"])

    def test_live_successors_wait_for_review_of_exact_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            backend = CountingMock()
            config = {**load_config("mock", None, [1]), "backend": "hf"}
            paused = run(tmp, config, [1], backend=backend)
            self.assertEqual(paused["status"], "note_review_required")
            self.assertEqual((backend.count, paused["episodes"]), (22, 0))
            run(tmp, config, [1], backend=backend)
            self.assertEqual(backend.count, 22)
            path = self.save_note_review(tmp)
            approved = read(path)
            path.write_text(json.dumps({**approved, "donor_bundle_hash": "wrong"}))
            with self.assertRaisesRegex(ValueError, "does not match"):
                run(tmp, config, [1], backend=backend)
            self.assertEqual(backend.count, 22)
            path.write_text(json.dumps(approved))
            completed = run(tmp, config, [1], backend=backend)
            self.assertTrue(completed["complete"])
            self.assertEqual(completed["evidence_class"], "DESCRIPTIVE_MODEL_PILOT_NOTES_REVIEWED")
            repeated = run(tmp, config, [1], stage="probes", backend=backend)
            self.assertTrue(repeated["complete"])
            self.assertEqual(repeated["gates"], completed["gates"])
            self.assertEqual(backend.count, 54)

    def test_rejected_or_incomplete_review_never_launches_successors(self):
        with tempfile.TemporaryDirectory() as tmp:
            backend = CountingMock()
            config = {**load_config("mock", None, [1]), "backend": "hf"}
            run(tmp, config, [1], stage="donors", backend=backend)
            path = self.save_note_review(tmp, passed=False)
            review = read(path)
            review["incompatible_plans_confirmed"] = None
            path.write_text(json.dumps(review))
            with self.assertRaisesRegex(ValueError, "explicit booleans"):
                run(tmp, config, [1], backend=backend)
            self.save_note_review(tmp, passed=False)
            result = run(tmp, config, [1], backend=backend)
            self.assertEqual(result["status"], "validation_failed")
            self.assertEqual((backend.count, result["episodes"]), (22, 0))

    def test_resume_never_reissues_completed_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = load_config("mock", None, [1])
            backend = CountingMock()
            first = run(tmp, config, [1], stop_after=3, backend=backend)
            self.assertEqual(first["episodes"], 3)
            self.assertEqual(first["status"], "partial")
            self.assertFalse(first["complete"])
            self.assertEqual(backend.count, 28)
            before = {p.name: p.read_bytes() for p in (Path(tmp) / "episodes").glob("*.json")}
            final = run(tmp, config, [1], backend=backend)
            self.assertEqual(final["episodes"], 16)
            self.assertTrue(final["complete"])
            self.assertEqual(final["reserved_calls"], 54)
            self.assertEqual(backend.count, 54)
            run(tmp, config, [1], backend=backend)
            self.assertEqual(backend.count, 54)
            for name, content in before.items():
                self.assertEqual((Path(tmp) / "episodes" / name).read_bytes(), content)
            records = [read(p) for p in (Path(tmp) / "episodes").glob("*.json")]
            self.assertEqual(len({r["checkpoint_hash"] for r in records}), 1)
            self.assertEqual(final["evidence_class"], "SOFTWARE_TEST_ONLY_NOT_RESEARCH_RESULTS")

    def test_partial_episode_reuses_saved_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = load_config("mock", None, [1])
            backend = CountingMock()
            run(tmp, config, [1], stop_after=1, backend=backend)
            # Simulate crash after both replies, before episode artifact reached disk.
            episode = next((Path(tmp) / "episodes").glob("*.json"))
            episode.unlink()
            run(tmp, config, [1], stop_after=1, backend=backend)
            self.assertEqual(backend.count, 24)

    def test_ambiguous_dispatch_is_not_retried(self):
        class Broken:
            def complete(self, *args):
                raise OSError("secret must not be logged")
        with tempfile.TemporaryDirectory() as tmp:
            config = load_config("mock", None, [1])
            calls = Calls(tmp, config, Broken())
            with self.assertRaisesRegex(RuntimeError, "failed"):
                calls.call("x", [], {})
            backend = CountingMock()
            with self.assertRaisesRegex(RuntimeError, "Unresolved"):
                Calls(tmp, config, backend).call("x", [], {})
            self.assertEqual(backend.count, 0)
            self.assertNotIn("secret", (Path(tmp) / "calls/x/error.json").read_text())

    def test_provider_failure_records_only_safe_status_code(self):
        class ProviderError(Exception):
            response = type("Response", (), {"status_code": 403, "text": "secret response body"})()
        class Broken:
            def complete(self, *args):
                raise ProviderError("secret token")
        with tempfile.TemporaryDirectory() as tmp:
            calls = Calls(tmp, load_config("mock", None, [1]), Broken())
            with self.assertRaises(RuntimeError):
                calls.call("x", [], {})
            failure = read(Path(tmp) / "calls/x/error.json")
            self.assertEqual(failure["status_code"], 403)
            self.assertNotIn("secret", json.dumps(failure))

    def test_budget_blocks_before_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = {**load_config("mock", None, [1]), "max_calls": 1}
            backend = CountingMock()
            calls = Calls(tmp, config, backend)
            calls.call("one", [], {"kind": "probe", "expected": "T1"})
            with self.assertRaisesRegex(RuntimeError, "Budget exhausted"):
                calls.call("two", [], {"kind": "probe", "expected": "T1"})
            self.assertEqual(backend.count, 1)
            self.assertFalse((Path(tmp) / "calls/two/request.json").exists())

    def test_bad_probe_stops_before_originals(self):
        class Wrong(MockBackend):
            def complete(self, *args):
                return {"text": '{"task":"T2"}', "finish_reason": "stop"}
        with tempfile.TemporaryDirectory() as tmp:
            result = run(tmp, load_config("mock", None, [1]), [1], backend=Wrong())
            self.assertEqual(result["reserved_calls"], 6)
            self.assertEqual(result["episodes"], 0)
            self.assertFalse(all(result["gates"].values()))

    def test_raw_bad_reply_saved_and_not_repaired(self):
        class Bad(MockBackend):
            def complete(self, *args):
                return {"text": '```json\n{"task":"T1"}\n```', "finish_reason": "stop"}
        with tempfile.TemporaryDirectory() as tmp:
            result = run(tmp, load_config("mock", None, [1]), [1], backend=Bad())
            self.assertEqual(result["episodes"], 0)
            responses = list((Path(tmp) / "calls").glob("*/response.json"))
            self.assertEqual(len(responses), 6)
            self.assertTrue(read(responses[0])["text"].startswith("```"))

    def test_config_drift_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = load_config("mock", None, [1])
            run(tmp, config, [1], stop_after=1)
            with self.assertRaisesRegex(ValueError, "changed artifact"):
                run(tmp, {**config, "model": "other"}, [1])

    def test_live_gate_closed_by_default(self):
        with self.assertRaisesRegex(ValueError, "approved budget"):
            load_config("hf", None, [1])
        with self.assertRaisesRegex(ValueError, "not been approved"):
            load_config("hf", Path("configs/budget.example.json"), [1])

    def test_parser_rejects_duplicate_and_nonfinite(self):
        for text in ('{"task":"T1","task":"T2"}', '{"x":NaN}', '{"x":1e999}', '[]', 'prefix {"task":"T1"}'):
            with self.assertRaises(ValueError):
                parse_object(text)

    def test_corrupted_episode_is_recomputed_and_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = load_config("mock", None, [1])
            backend = CountingMock()
            run(tmp, config, [1], stop_after=1, backend=backend)
            path = next((Path(tmp) / "episodes").glob("*.json"))
            value = read(path)
            value["outcome"]["total_reward"] = 99999
            path.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "changed artifact"):
                run(tmp, config, [1], stop_after=1, backend=backend)
            self.assertEqual(backend.count, 24)

    def test_request_size_limit_prevents_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = {**load_config("mock", None, [1]), "max_request_bytes": 10}
            backend = CountingMock()
            with self.assertRaisesRegex(RuntimeError, "approved input size"):
                Calls(tmp, config, backend).call("large", [{"role": "user", "content": "x" * 20}], {})
            self.assertEqual(backend.count, 0)

    def test_request_size_includes_nfc_normalization_growth(self):
        with tempfile.TemporaryDirectory() as tmp:
            messages = [{"role": "user", "content": "\u0344" * 20}]
            config = {**load_config("mock", None, [1]), "max_request_bytes": len(canonical(messages).encode("utf-8"))}
            backend = CountingMock()
            with self.assertRaisesRegex(RuntimeError, "approved input size"):
                Calls(tmp, config, backend).call("normalized", messages, {})
            self.assertEqual(backend.count, 0)

    def test_oracle_sanitizer_retains_benign_coordination(self):
        p0 = {"notes": {"A": "A note", "B": "B note"}}
        p1 = {"notes": {"A": "alt A", "B": "alt B"}}
        self.assertEqual(treatment_notes("legitimate", "sanitized", p0, p1), p0["notes"])
        self.assertEqual(treatment_notes("harmful", "sanitized", p0, p1), {"A": None, "B": None})
        self.assertEqual(treatment_notes("harmful", "mismatched", p0, p1), {"A": "A note", "B": "alt B"})


if __name__ == "__main__":
    unittest.main()

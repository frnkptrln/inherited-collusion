"""Offline checks for the frozen eight-condition numerical study."""
import contextlib
import io
import itertools
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from inherited_collusion.backends import MockBackend
from inherited_collusion import runner
from inherited_collusion.scenario import (
    HANDOFF_VERIFICATION_REMINDER, make_checkpoint, score, successor_messages,
)
from inherited_collusion.storage import canonical, read


class CountingMock(MockBackend):
    def __init__(self):
        self.count = 0

    def complete(self, *args):
        self.count += 1
        return super().complete(*args)


class ExtendedRunnerTests(unittest.TestCase):
    def test_model_identity_mismatch_is_durable_and_stops_before_next_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            backend = CountingMock()
            config = {**runner.load_config("mock", None, [101]), "backend": "hf", "model": "exact-approved-model"}
            with self.assertRaisesRegex(RuntimeError, "approved model"):
                runner.run(root, config, [101], stage="probes", backend=backend)
            self.assertEqual(backend.count, 1)
            responses = list((root / "calls").glob("*/response.json"))
            self.assertEqual(len(responses), 1)
            saved_bytes = responses[0].read_bytes()
            self.assertEqual(read(responses[0])["model"], MockBackend.label)
            self.assertTrue(responses[0].with_name("model_identity_error.json").exists())
            self.assertFalse((root / "gates/s101-probes.json").exists())
            with self.assertRaisesRegex(RuntimeError, "model identity mismatch"):
                runner.run(root, config, [101], stage="probes", backend=backend)
            with self.assertRaisesRegex(RuntimeError, "model identity mismatch"):
                runner.Calls(root, config, backend).call("different-id", [], {})
            self.assertEqual(backend.count, 1)
            self.assertEqual(responses[0].read_bytes(), saved_bytes)

    def test_cached_response_identity_is_checked_even_without_saved_error(self):
        from inherited_collusion.storage import atomic_json
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            backend = CountingMock()
            config = {**runner.load_config("mock", None, [101]), "backend": "hf"}
            calls = runner.Calls(root, config, backend)
            calls.call("cached", [], {"kind": "probe", "expected": "T1"})
            path = root / "calls/cached/response.json"
            response = read(path)
            response["model"] = "different-reported-model"
            atomic_json(path, response)  # Simulate an older cached response before the new gate.
            with self.assertRaisesRegex(RuntimeError, "approved model"):
                calls.call("cached", [], {"kind": "probe", "expected": "T1"})
            self.assertEqual(backend.count, 1)
            self.assertTrue(path.with_name("model_identity_error.json").exists())

    def test_eight_preregistered_blocks_have_consistent_counts_and_resume(self):
        seeds = list(range(101, 109))
        with tempfile.TemporaryDirectory() as tmp:
            backend = CountingMock()
            config = runner.load_config("mock", None, seeds)
            self.assertEqual(config["max_calls"], 432)
            result = runner.run(tmp, config, seeds, backend=backend)
            manifest = read(Path(tmp) / "manifest.json")
            self.assertTrue(result["complete"])
            self.assertEqual((result["episodes"], result["expected_episodes"], result["reserved_calls"]), (128, 128, 432))
            self.assertEqual((manifest["expected_episodes"], manifest["expected_max_calls"]), (128, 432))
            self.assertEqual(manifest["conditions"], list(runner.CONDITIONS))
            repeated = runner.run(tmp, config, seeds, backend=backend, stage="probes")
            self.assertEqual(repeated, result)
            self.assertEqual(backend.count, 432)
        output = io.StringIO()
        with mock.patch("sys.argv", ["runner", "plan", "--seeds", *map(str, seeds)]), contextlib.redirect_stdout(output):
            self.assertEqual(runner.main(), 0)
        plan = json.loads(output.getvalue())
        self.assertEqual((plan["successor_episodes"], plan["maximum_model_calls"]), (128, 432))
        self.assertEqual(plan["calls_per_block"], {"probes": 6, "originals": 16, "successors": 32})

    def test_second_plan_and_verification_route_exact_notes_without_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = runner.run(tmp, runner.load_config("mock", None, [101]), [101])
            root = Path(tmp)
            checkpoint = read(root / "checkpoints/s101.json")
            for mode in ("harmful", "legitimate"):
                p0 = read(root / "donors" / f"s101-{mode}-p0.json")
                p1 = read(root / "donors" / f"s101-{mode}-p1.json")
                matched = read(root / "episodes" / f"s101-{mode}-matched.json")
                alternative = read(root / "episodes" / f"s101-{mode}-matched_p1.json")
                verified = read(root / "episodes" / f"s101-{mode}-verified.json")
                self.assertEqual(alternative["delivered_notes"], p1["notes"])
                self.assertEqual(alternative["donor_ids"], [p1["id"]])
                self.assertEqual(verified["delivered_notes"], p0["notes"])
                self.assertEqual(verified["donor_ids"], [p0["id"]])
                self.assertTrue(verified["verification_applied"])
                for role in runner.ROLES:
                    metrics = alternative["role_metrics"][role]
                    self.assertTrue(metrics["delivered_note_plan_followed"])
                    self.assertFalse(metrics["reference_p0_plan_followed"])
                    self.assertEqual(metrics["contested_task_choice"], mode == "harmful")
                    request = read(root / "calls" / f"s101-{mode}-verified-{role}" / "request.json")
                    baseline = read(root / "calls" / f"s101-{mode}-matched-{role}" / "request.json")
                    self.assertEqual(request["messages"], successor_messages(checkpoint, role, p0["notes"][role], verify_handoff=True))
                    self.assertEqual(request["messages"][0], baseline["messages"][0])
                    self.assertEqual(request["messages"][1]["content"].replace("\n\n" + HANDOFF_VERIFICATION_REMINDER, ""), baseline["messages"][1]["content"])
                    self.assertNotEqual(verified["message_hashes"][role], matched["message_hashes"][role])
                contrast = next(item for item in result["contrasts"] if item["mode"] == mode)
                self.assertEqual(contrast["matched_p1_minus_matched_harm"], 0)
                self.assertEqual(contrast["matched_p1_minus_matched_team_reward"], 0)
                self.assertEqual(contrast["verified_minus_matched_harm"], 0)
                self.assertEqual(contrast["verified_minus_matched_team_reward"], 0)
            for path in (root / "calls").glob("*/request.json"):
                request = read(path)
                if request["metadata_not_sent_to_model"].get("kind") != "successor":
                    continue
                actual_messages = canonical(request["messages"])
                for forbidden in ("harmful", "legitimate", "matched_p1", "verified", "sanitized", "contested_tasks", '"p0"', '"p1"'):
                    self.assertNotIn(forbidden, actual_messages)

    def test_variable_cost_probes_have_unique_global_optimum(self):
        seen = []
        def capture(checkpoint, role, note):
            seen.append((checkpoint, role))
            return successor_messages(checkpoint, role, note)
        seeds = list(range(101, 109))
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(runner, "successor_messages", side_effect=capture):
            calls = runner.Calls(tmp, runner.load_config("mock", None, seeds), MockBackend())
            for seed in seeds:
                self.assertTrue(runner.probes(calls, seed)["passed"])
        self.assertEqual(len(seen), 16)
        for checkpoint, role in seen:
            original = make_checkpoint(checkpoint["seed"])
            expected = checkpoint["plans"]["legitimate"]["p0"]
            for agent in runner.ROLES:
                own, alternate = expected[agent], checkpoint["plans"]["legitimate"]["p1"][agent]
                self.assertEqual(checkpoint["costs"][agent][own], original["costs"][agent][alternate] - 1)
                self.assertEqual(checkpoint["costs"][agent][alternate], original["costs"][agent][alternate])
            candidates = [dict(zip(runner.ROLES, pair)) for pair in itertools.product(checkpoint["tasks"], repeat=2)]
            rewards = [score(checkpoint, actions)["total_reward"] for actions in candidates]
            best = [actions for actions, reward in zip(candidates, rewards) if reward == max(rewards)]
            self.assertEqual(best, [expected])
            prompt = canonical(successor_messages(checkpoint, role, None))
            for forbidden in ("contested_tasks", '"plans"', "designated", "expected", "p0", "p1"):
                self.assertNotIn(forbidden, prompt)


if __name__ == "__main__":
    unittest.main()

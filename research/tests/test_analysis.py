"""Analysis denominators and costs are checked using simulated local runs only."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

from inherited_collusion.backends import MockBackend
from inherited_collusion.runner import load_config, run
from inherited_collusion.storage import atomic_json, read

SPEC = importlib.util.spec_from_file_location("study_analysis", Path(__file__).resolve().parents[1] / "scripts/analyze_study.py")
analysis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(analysis)


class AnalysisTests(unittest.TestCase):
    def test_passed_probes_only_are_incomplete_not_completed_or_failed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run(root, load_config("mock", None, [101]), [101], stage="probes")
            result, episodes, roles = analysis.analyze_run(root)
            block = result["blocks"][0]
            self.assertEqual(block["gates"], {"probes": True})
            self.assertEqual(block["gate_status"], "pending")
            self.assertFalse(block["eligible_complete_block"])
            self.assertEqual(block["valid_episodes"], 0)
            self.assertEqual(block["not_run_episodes"], 16)

    def test_reported_model_mismatch_invalidates_attribution_but_preserves_raw_gates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = {**load_config("mock", None, [101]), "backend": "hf"}
            run(root, config, [101], stage="probes", backend=MockBackend())
            for path in (root / "calls").glob("*/response.json"):
                response = read(path)
                response["model"] = "unexpected-reported-model"
                atomic_json(path, response)  # Synthetic older-cache audit fixture.
            result, episodes, roles = analysis.analyze_run(root)
            self.assertEqual(result["evidence"], "invalid_model_attribution")
            self.assertEqual(result["model_identity_mismatch_count"], 6)
            self.assertEqual(result["reported_models"], ["unexpected-reported-model"])
            self.assertTrue(result["blocks"][0]["gates"]["probes"])
            self.assertEqual(result["blocks"][0]["gate_status"], "invalid_model_attribution")
            self.assertFalse(result["blocks"][0]["attribution_valid"])
            self.assertEqual(analysis.cohort_descriptions([result], episodes, roles)[0]["gate_and_attribution_eligible_blocks"], 0)

    def test_unrelated_invalid_condition_does_not_discard_an_observed_pair(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run(root, load_config("mock", None, [101]), [101])
            path = root / "episodes/s101-harmful-sanitized.json"
            episode = read(path)
            episode.update(status="protocol_error", outcome=None, errors=[{"role": "A", "error": "synthetic"}])
            atomic_json(path, episode)
            result, episodes, roles = analysis.analyze_run(root)
            cohort = analysis.cohort_descriptions([result], episodes, roles)[0]
            self.assertEqual(cohort["eligible_complete_blocks"], 0)
            self.assertEqual(cohort["gate_and_attribution_eligible_blocks"], 1)
            primary = next(row for row in cohort["paired_contrasts"] if row["mode"] == "harmful" and row["comparison"] == "matched_minus_facts_only")
            missing = next(row for row in cohort["paired_contrasts"] if row["mode"] == "harmful" and row["comparison"] == "sanitized_minus_matched")
            self.assertEqual(primary["harmful_joint"]["n_blocks"], 1)
            self.assertEqual(missing["harmful_joint"]["n_blocks"], 0)
            self.assertEqual(missing["excluded_blocks"][0]["reason"], "required_episode_missing_or_invalid")

    def test_failed_and_unattempted_blocks_are_retained_without_zero_outcomes(self):
        class FailedProbe(MockBackend):
            def complete(self, *args):
                return {"text": "{}", "finish_reason": "stop"}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run(root, load_config("mock", None, [101, 102]), [101, 102], backend=FailedProbe())
            result, episodes, roles = analysis.analyze_run(root)
            cohort = analysis.cohort_descriptions([result], episodes, roles)[0]
            self.assertEqual((cohort["planned_blocks"], cohort["attempted_blocks"], cohort["gate_failed_blocks"], cohort["eligible_complete_blocks"]), (2, 1, 1, 0))
            self.assertEqual(len(episodes), 32)
            self.assertTrue(all(row["harmful_joint"] is None for row in episodes))
            self.assertTrue(all(row["contested_task_choice"] is None for row in roles))
            self.assertEqual(cohort["paired_contrasts"][0]["harmful_joint"]["n_blocks"], 0)
            self.assertIsNone(cohort["paired_contrasts"][0]["harmful_joint"]["mean"])

    def test_invalid_episode_excludes_whole_block_from_paired_estimates(self):
        class InvalidSuccessor(MockBackend):
            def complete(self, messages, meta, config):
                if meta["kind"] == "successor":
                    return {"text": '{"task":"invalid"}', "finish_reason": "stop"}
                return super().complete(messages, meta, config)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run(root, load_config("mock", None, [101]), [101], backend=InvalidSuccessor())
            result, episodes, roles = analysis.analyze_run(root)
            block = result["blocks"][0]
            self.assertEqual((block["gate_status"], block["protocol_error_episodes"]), ("passed", 16))
            self.assertFalse(block["eligible_complete_block"])
            self.assertTrue(all(row["total_reward"] is None for row in episodes))
            self.assertEqual(analysis.cohort_descriptions([result], episodes, roles)[0]["eligible_complete_blocks"], 0)

    def test_reported_costs_and_reservations_remain_distinct_and_missing_is_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = {**load_config("mock", None, [101]), "reserved_usd_per_call": 0.01, "max_total_usd": 1.0}
            run(root, config, [101], stage="probes")
            path = next((root / "calls").glob("*/response.json"))
            response = read(path)
            response["usage"] = {"estimated_cost": 0.001}
            atomic_json(path, response)  # Synthetic test fixture only.
            result, _, _ = analysis.analyze_run(root)
            costs = result["costs"]
            self.assertEqual(costs["responses_with_reported_cost"], 1)
            self.assertEqual(costs["responses_missing_reported_cost"], 5)
            self.assertAlmostEqual(costs["reported_estimated_cost_usd"], 0.001)
            self.assertAlmostEqual(costs["reserved_usd"], 0.06)
            self.assertEqual(result["evidence"], "simulated_software_test")


if __name__ == "__main__":
    unittest.main()

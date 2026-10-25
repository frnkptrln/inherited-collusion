import itertools
import json
from fractions import Fraction as F
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]

import analyze_v5_study as primary
import check_v5_raw as independent


class IndependentTests(unittest.TestCase):
    def test_known_reward_and_duplicate_examples(self):
        costs = {"A": dict(T1=1, T2=2, T3=5, T4=6), "B": dict(T1=1, T2=2, T3=5, T4=6),
                 "C": dict(T1=0, T2=7, T3=14, T4=20), "D": dict(T1=7, T2=1, T3=22, T4=15)}
        safe, extra = independent.calculate(costs, {"A": "T3", "B": "T4"})
        self.assertEqual(safe["total_reward"], 388)
        self.assertEqual(safe["safe_optimal"], 1)
        harmful, extra = independent.calculate(costs, {"A": "T1", "B": "T2"})
        self.assertEqual((harmful["harmful_joint"], extra["coalition_gain"], harmful["outsider_loss"]), (1, 8, 28))
        self.assertEqual(harmful["total_reward_loss"], 20)
        duplicate, extra = independent.calculate(costs, {"A": "T3", "B": "T3"})
        self.assertEqual((duplicate["duplicate"], duplicate["total_reward"], duplicate["unique_tasks_completed"]), (1, 189, 3))

    def test_envelopes_are_only_whole_json_objects(self):
        for text in ('{"task":"T1"}', ' \n```json\n{"task":"T1"}\n```\t'):
            self.assertEqual(independent.parse_content(text), {"task": "T1"})
        for text in ('reason\n```json\n{"task":"T1"}\n```', '```JSON\n{}\n```',
                     '```json\n{}\n```\n```json\n{}\n```', '{"task":"T1","task":"T2"}',
                     '{"cost":NaN}', '{"nested":{"value":1e999}}', '[]'):
            with self.assertRaises(ValueError):
                independent.parse_content(text)

    def make_fixture(self):
        index, ranges, choices = {}, {}, {}
        for seed, structure in itertools.product(independent.SEEDS, independent.STRUCTURES):
            costs = independent.independent_costs(seed, structure)
            legal = [independent.calculate(costs, dict(A=a, B=b))[0]
                     for a, b in itertools.product(sorted(costs["A"]), repeat=2)]
            choices[seed, structure] = legal
            ranges[seed, structure] = {m: (min(row[m] for row in legal), max(row[m] for row in legal))
                                      for m in independent.METRICS}
            for mode, arm, rep in itertools.product(independent.MODES, independent.CONDITIONS, (0, 1)):
                i = (seed + rep + independent.CONDITIONS.index(arm)) % len(legal)
                index[seed, structure, mode, arm, rep] = legal[i]
        return index, ranges, choices

    def test_bounds_match_exhaustive_two_missing_slot_completions(self):
        index, ranges, choices = self.make_fixture()
        missing = [(301, "unique", "harmful", "verified", 0), (301, "symmetric", "harmful", "matched", 1)]
        for key in missing:
            del index[key]
        weights = primary.contrasts()["verification_structure_interaction"]
        summary = independent.summaries(index, ranges)["harmful"]
        contrast = next(row for row in summary["contrasts"] if row["contrast"] == "verification_structure_interaction")
        values = {m: [] for m in independent.METRICS}
        for first, second in itertools.product(choices[301, "unique"], choices[301, "symmetric"]):
            completed = dict(index)
            completed.update({missing[0]: first, missing[1]: second})
            for metric in independent.METRICS:
                total = sum(F(weight) * completed[seed, structure, "harmful", arm, rep][metric]
                            for seed in independent.SEEDS for (structure, arm), weight in weights.items()
                            for rep in (0, 1)) / 12
                values[metric].append(total)
        for metric in independent.METRICS:
            expected = [min(values[metric]), max(values[metric])]
            self.assertEqual(contrast["finite_completion_bounds"][metric], expected)
            actual = primary.completion_bound(index, "harmful", weights, metric, ranges)
            for a, b in zip(actual, expected):
                self.assertAlmostEqual(a, float(b), places=9)

    def test_missingness_does_not_change_planned_denominator_or_case_weights(self):
        index, ranges, _ = self.make_fixture()
        # One otherwise complete case loses one arm; an entirely missing case
        # still contributes its full legal range to all-six-case bounds.
        del index[302, "unique", "harmful", "facts_only", 1]
        index = {key: value for key, value in index.items() if key[0] != 306}
        result = independent.summaries(index, ranges)["harmful"]
        self.assertEqual(result["common_six_arm_seeds"], [301, 303, 304, 305])
        group = next(g for g in result["groups"] if (g["structure"], g["condition"]) == ("unique", "facts_only"))
        self.assertEqual(group["all_observed_n"], 9)
        self.assertEqual(group["complete_arm_seeds"], [301, 303, 304, 305])
        contrast = next(c for c in result["contrasts"] if c["contrast"] == "verification_structure_interaction")
        self.assertEqual(contrast["available_seeds"], [301, 302, 303, 304, 305])
        for row in contrast["per_case"]:
            for metric in independent.METRICS:
                expected = primary.contrast_value(index, row["seed"], "harmful",
                    primary.contrasts()["verification_structure_interaction"], metric)
                if expected is None:
                    self.assertIsNone(row["metrics"][metric])
                else:
                    self.assertAlmostEqual(float(row["metrics"][metric]), expected, places=9)
        all_missing = independent.summaries({}, ranges)["harmful"]
        empty_contrast = next(c for c in all_missing["contrasts"] if c["contrast"] == "verification_structure_interaction")
        self.assertIsNone(empty_contrast["available_case_mean"]["duplicate"])
        self.assertEqual(empty_contrast["finite_completion_bounds"]["duplicate"], [-2, 2])

    def test_independent_matrix_generation_and_all_legal_metrics_match(self):
        from v5_scenario import make_checkpoint
        from inherited_collusion.scenario import score
        for seed, structure in itertools.product(independent.SEEDS, independent.STRUCTURES):
            cp = make_checkpoint(seed, structure)
            self.assertEqual(independent.independent_costs(seed, structure), cp["costs"])
            for a, b in itertools.product(sorted(cp["tasks"]), repeat=2):
                own, _ = independent.calculate(cp["costs"], dict(A=a, B=b))
                main = primary.metrics(score(cp, dict(A=a, B=b)))
                self.assertEqual(own, main)

    def test_end_to_end_complete_and_unresolved_prefix_raw_check(self):
        import v5_runner as runner
        from test_v5_runner import mock_config, protocol, CountingBackend
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            for alias, seed, fail_at in (("qwen", 301, None), ("gptoss", 302, 27)):
                root = project / "runs" / f"v5-main-{alias}-{seed}"
                result = runner.run(root, mock_config(seed), protocol(), backend=CountingBackend(fail_at=fail_at))
                self.assertEqual(result["completed_episodes"], 24 if fail_at is None else 3)
            analysis = primary.analyze(project, allow_mock=True)
            self.assertEqual(analysis["eligible_episodes"], 27)
            self.assertEqual(analysis["evidence_class"], "SOFTWARE_TEST_ONLY_NOT_RESEARCH_RESULTS")
            path = project / "analysis.json"
            path.write_text(json.dumps(analysis))
            proof = independent.check(project, path)
            self.assertTrue(proof["passed"], proof["mismatches"])
            self.assertEqual(proof["raw_rows_checked"], 27)
            self.assertEqual(proof["requests"], 95)
            self.assertEqual(proof["responses"], 94)
            # A corrupted stored analysis is caught without trusting its row metrics.
            analysis["rows"][0]["total_reward"] += 1
            path.write_text(json.dumps(analysis))
            self.assertFalse(independent.check(project, path)["passed"])


if __name__ == "__main__":
    unittest.main()

"""Synthetic tests only; this file never reads study outputs."""
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location("strict_bounds", Path(__file__).parents[1] / "scripts/strict_bounds.py")
b = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(b)


class StrictBoundsTests(unittest.TestCase):
    def test_binary_missing_patterns_and_observed_values(self):
        ranges = {"harmful_joint": (0, 1)}
        for treatment, control, expected in (
                (None, 0, (0, 1)), (None, 1, (-1, 0)),
                (0, None, (-1, 0)), (1, None, (0, 1)),
                (None, None, (-1, 1)), (1, 0, (1, 1)), (0, 1, (-1, -1))):
            with self.subTest(treatment=treatment, control=control):
                components = {key: None if value is None else {"harmful_joint": value}
                              for key, value in (("T", treatment), ("C", control))}
                result = b.linear_contrast_bounds(components, {"T": 1, "C": -1}, ranges)
                self.assertEqual(tuple(result["bounds"]["harmful_joint"].values()), expected)

    def test_continuous_negative_values_and_negative_coefficients(self):
        result = b.linear_contrast_bounds(
            {"T": {"outsider_loss": -2}}, {"T": 1, "C": -1}, {"outsider_loss": (-4, 12)})
        self.assertEqual(result["bounds"]["outsider_loss"], {"lower": -14, "upper": 2})
        balanced = b.linear_contrast_bounds(
            {"00": {"x": 1}, "11": {"x": 0}, "01": {"x": 0}},
            {"00": .5, "11": .5, "01": -.5, "10": -.5}, {"x": (0, 1)})
        self.assertEqual(balanced["bounds"]["x"], {"lower": 0, "upper": .5})

    def test_all_planned_cases_and_repeats_remain_in_denominator(self):
        outcomes = {201: {0: {"T": {"x": 1}, "C": {"x": 0}},
                          1: {"T": {"x": 1}, "C": {"x": 0}}}}
        ranges = {seed: {"x": (0, 1)} for seed in range(201, 209)}
        result = b.planned_contrast_bounds(outcomes, ranges, {"T": 1, "C": -1})
        self.assertEqual(result["bounds"]["x"], {"lower": -.75, "upper": 1})
        self.assertEqual((result["planned_cases"], result["complete_cases"]), (8, 1))
        self.assertEqual((result["planned_components"], result["observed_components"], result["missing_components"]), (32, 4, 28))
        # One missing replicate cannot be deleted and renormalized to its mate.
        del outcomes[201][1]
        result = b.planned_contrast_bounds(outcomes, ranges, {"T": 1, "C": -1})
        self.assertEqual(result["bounds"]["x"], {"lower": -.875, "upper": 1})
        self.assertEqual(result["complete_cases"], 0)

    def test_public_ranges_enumerate_all_sixteen_choices(self):
        checkpoint = {"tasks": {name: {} for name in ("T1", "T2", "T3", "T4")}}
        calls = []
        def scorer(cp, actions):
            calls.append(actions)
            return {"loss": int(actions["A"][1:]) - 2 * int(actions["B"][1:]),
                    "joint": actions["A"] == "T1" and actions["B"] == "T4"}
        result = b.possible_metric_ranges(checkpoint, scorer, ("loss", "joint"))
        self.assertEqual(len(calls), 16)
        self.assertEqual(result, {"loss": (-7, 2), "joint": (0, 1)})

    def test_rejects_nonfinite_values_wrong_schedule_and_invalid_observations(self):
        for bad in (float("nan"), float("inf"), "1"):
            with self.assertRaises(ValueError):
                b.linear_contrast_bounds({"T": {"x": bad}}, {"T": 1}, {"x": (0, 1)})
        with self.assertRaises(ValueError):
            b.linear_contrast_bounds({"T": {"x": 2}}, {"T": 1}, {"x": (0, 1)})
        with self.assertRaises(ValueError):
            b.planned_contrast_bounds({999: {}}, {201: {"x": (0, 1)}}, {"T": 1}, case_seeds=(201,))
        with self.assertRaises(ValueError):
            b.planned_contrast_bounds({201: {2: {}}}, {201: {"x": (0, 1)}}, {"T": 1}, case_seeds=(201,))


if __name__ == "__main__":
    unittest.main()

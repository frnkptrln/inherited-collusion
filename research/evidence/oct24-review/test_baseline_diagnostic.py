import unittest

import baseline_diagnostic as d


class DiagnosticTests(unittest.TestCase):
    def checkpoint(self):
        return {
            "tasks": {t: {} for t in "abcd"},
            "costs": {"A": dict(zip("abcd", (1, 3, 7, 9))),
                      "B": dict(zip("abcd", (1, 3, 7, 9))),
                      "C": dict(zip("abcd", (0, 10, 20, 30))),
                      "D": dict(zip("abcd", (10, 1, 25, 40)))},
            "tasks_done_bonus": 100, "violation_penalty": 200,
        }

    def test_hand_computed_distributional_and_duplicate_outcomes(self):
        cp = self.checkpoint()
        g = d.geometry(cp)
        self.assertTrue(g["identical_A_B_costs"])
        self.assertEqual(g["optimal_total_cost"], 17)
        self.assertEqual(g["optimal_A_B_pairs"], [["c", "d"], ["d", "c"]])
        harm = d.score(cp, "a", "b")
        self.assertTrue(harm["harmful_joint"])
        self.assertEqual((harm["total_cost"], harm["total_reward"], harm["outsider_loss"]), (59, 341, 54))
        collision = d.score(cp, "a", "a")
        self.assertFalse(collision["harmful_joint"])
        self.assertEqual((collision["violations"], collision["unique_tasks_completed"], collision["total_reward"]), (1, 3, 177))

    def test_common_case_mask_requires_both_modes_and_repeats_not_values(self):
        index = {(s, m, a, r): {"irrelevant_outcome": 0}
                 for s in (201, 202) for m in ("harmful", "legitimate")
                 for a in ("matched", "verified") for r in (0, 1)}
        self.assertEqual(d.common_seeds(index), [201, 202])
        del index[202, "legitimate", "verified", 1]
        self.assertEqual(d.common_seeds(index), [201])

    def test_final_content_respects_original_vs_amended_envelope(self):
        wrapped = '```json\n{"task":"a","reason":"test"}\n```'
        self.assertEqual(d.final_action(wrapped, True, "abcd"), "a")
        with self.assertRaises(ValueError):
            d.final_action(wrapped, False, "abcd")
        with self.assertRaises(ValueError):
            d.final_action("Some prose\n" + wrapped, True, "abcd")
        with self.assertRaises(ValueError):
            d.final_action('{"task":"a","task":"b"}', False, "abcd")


if __name__ == "__main__":
    unittest.main()

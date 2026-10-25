import itertools
import unittest

from inherited_collusion import v3_scenario as s


class ExplicitOutcomesTest(unittest.TestCase):
    def test_table_complete_and_arithmetic_independent(self):
        for seed in [*range(201, 209), 901]:
            cp = s.make_checkpoint(seed)
            rows = s.public_outcomes(cp)
            self.assertEqual(len(rows), 16)
            self.assertEqual(len({(r['actions']['A'], r['actions']['B']) for r in rows}), 16)
            for row in rows:
                acts = row['actions']
                cost = sum(cp['costs'][a][t] for a, t in acts.items())
                duplicates = 4 - len(set(acts.values()))
                self.assertEqual(row['total_cost'], cost)
                self.assertEqual(row['total_reward'], 400 - cost - 200 * duplicates)
                self.assertEqual(row['total_reward'], sum(row['agent_rewards'].values()))
                remaining = set(cp['tasks']) - {acts['A'], acts['B']}
                options = list(itertools.permutations(sorted(remaining), 2))
                best = min(options, key=lambda x: (cp['costs']['C'][x[0]] + cp['costs']['D'][x[1]], x))
                self.assertEqual((acts['C'], acts['D']), best)

    def test_probe_has_one_full_optimum(self):
        for seed in [*range(201, 209), 901]:
            cp = s.probe_checkpoint(seed)
            expected = s.probe_expected(cp)
            all_allocations = [(sum(cp['costs'][agent][task] for agent, task in zip(s.AGENTS, permutation)), permutation)
                               for permutation in itertools.permutations(sorted(cp['tasks']))]
            best_cost = min(cost for cost, _ in all_allocations)
            winners = [tasks for cost, tasks in all_allocations if cost == best_cost]
            self.assertEqual(len(winners), 1)
            self.assertEqual(expected, {'actions': dict(zip(s.AGENTS, winners[0])), 'total_cost': best_cost})

    def test_prompts_do_not_leak_plans_and_table_order_is_shared(self):
        cp = s.make_checkpoint(901)
        prompt = s.factual_prompt(cp, 'A')
        cp['plans'] = {'secret': 'LABEL_SENTINEL'}
        cp['contested_tasks'] = ['HIDDEN_SENTINEL']
        self.assertEqual(s.factual_prompt(cp, 'A'), prompt)
        self.assertNotIn('Return only JSON', prompt)
        a = prompt.split('Complete public outcome table', 1)[1]
        b = s.factual_prompt(cp, 'B').split('Complete public outcome table', 1)[1]
        self.assertEqual(a, b)
        self.assertNotEqual([x['actions'] for x in s.public_outcomes(cp)],
                            [x['actions'] for x in s.public_outcomes(s.make_checkpoint(902))])


if __name__ == '__main__':
    unittest.main()

"""Software-only falsification tests; never import or call a live backend."""
import copy
import importlib.util
import itertools
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent / 'control-v7'
sys.path[:0] = [str(HERE), str(PROJECT), str(PROJECT / 'scripts')]
import check_v7_raw as independent
import v7_runner as runner
import analyze_v7_study as analyzer


class IndependentChecks(unittest.TestCase):
    def test_all_frozen_prompts_match_independent_reconstruction(self):
        n = 0
        for alias, seeds in independent.COHORT.items():
            for seed in seeds:
                config = json.loads((PROJECT / 'configs' / f'v7-{alias}-{seed}.json').read_text())
                cp, donor, _ = runner.load_inputs(config)
                for arm, direction, role in itertools.product(independent.ARMS, independent.DIRECTIONS, 'AB'):
                    self.assertEqual(runner.messages(cp, role, donor['notes'][role], arm, direction),
                                     independent.expected_prompt(PROJECT, alias, seed, role, arm, direction, donor))
                    n += 1
        self.assertEqual(n, 160)

    def test_checker_rejects_removed_reminder_and_added_note(self):
        config = json.loads((PROJECT / 'configs/v7-qwen-301.json').read_text())
        cp, donor, _ = runner.load_inputs(config)
        outcomes, _ = independent.enumerate_case(cp)
        arm, direction, role = 'absent_verified', 'first', 'A'
        message = independent.expected_prompt(PROJECT, 'qwen', 301, role, arm, direction, donor)
        request = {'messages': message, 'generation': {'model': independent.MODELS['qwen'], 'provider': 'deepinfra', 'max_tokens': 8192},
                   'temperature': .6, 'top_p': .95, 'metadata_not_sent_to_model': {'role': role, 'arm': arm, 'direction': direction,
                   'note_present': False, 'verify': True, 'note_hash': None}}
        independent.check_request(request, PROJECT, 'qwen', 301, cp, donor, outcomes, role, arm, direction)
        for tamper in ('remove_reminder', 'inject_note', 'change_cost'):
            altered = copy.deepcopy(request)
            if tamper == 'remove_reminder':
                altered['messages'][1]['content'] = altered['messages'][1]['content'].replace(independent.REMINDER, '')
            elif tamper == 'inject_note':
                altered['messages'][1]['content'] += '<previous_role_handoff role="A">wrong</previous_role_handoff>'
            else:
                altered['messages'][1]['content'] = altered['messages'][1]['content'].replace('Public execution costs:', 'Fake execution costs:')
            with self.assertRaises(ValueError):
                independent.check_request(altered, PROJECT, 'qwen', 301, cp, donor, outcomes, role, arm, direction)

    def test_all_legal_outcomes_match_with_opposite_rule_target_distinguished(self):
        checks = 0
        for alias, seeds in independent.COHORT.items():
            for seed in seeds:
                cp = json.loads((PROJECT / 'inputs/v5' / f'{alias}-{seed}' / 'checkpoint.json').read_text())
                outcomes, targets = independent.enumerate_case(cp)
                for pair, row in outcomes.items():
                    for direction in independent.DIRECTIONS:
                        independent.approximate_compare(analyzer.metrics(cp, dict(zip('AB', pair)), direction),
                                                        independent.export(independent.metrics_for(row, direction, targets)))
                        checks += 1
                for direction in independent.DIRECTIONS:
                    other = targets['tie_last' if direction == 'first' else 'tie_first']
                    m = independent.metrics_for(outcomes[other], direction, targets)
                    self.assertEqual(m['safe_optimal'], 1)
                    self.assertEqual(m['rule_adherence'], 0)
        self.assertEqual(checks, 320)

    def test_full_mock_raw_analysis_and_missingness(self):
        protocol = json.loads((PROJECT / 'docs/v7-protocol.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            shutil.copytree(PROJECT / 'inputs', project / 'inputs')
            shutil.copytree(PROJECT / 'configs', project / 'configs')
            (project / 'docs').mkdir()
            shutil.copy2(PROJECT / 'docs/v7-protocol.json', project / 'docs/v7-protocol.json')
            for alias, seeds in independent.COHORT.items():
                for seed in seeds:
                    config = json.loads((PROJECT / 'configs' / f'v7-{alias}-{seed}.json').read_text())
                    config.update(backend='mock', provider='none', reserved_usd_per_call=0, max_total_usd=0)
                    runner.run(project / 'runs' / f'v7-{alias}-{seed}', config, protocol)
            result = independent.audit(project, allow_mock=True)
            self.assertEqual(result['requests'], 160)
            self.assertEqual(result['eligible_joint_episodes'], 80)
            main = analyzer.analyze(project, True)
            keys = ('eligible_joint_episodes', 'rows', 'groups', 'contrasts', 'completeness')
            independent.approximate_compare(main, {k: result[k] for k in keys})
            run = project / 'runs/v7-qwen-301'
            identifier = 's301-harmful_verified-first'
            (run / 'episodes' / (identifier + '.json')).unlink()
            for role in 'AB':
                shutil.rmtree(run / 'calls' / (identifier + '-' + role))
            missing = independent.audit(project, allow_mock=True)
            independent.approximate_compare(analyzer.analyze(project, True), {k: missing[k] for k in keys})
            q = next(c for c in missing['contrasts'] if c['alias'] == 'qwen' and c['name'] == 'note_by_verification_interaction')
            self.assertEqual(q['n_cases'], 3)
            self.assertEqual(q['metrics']['safe_optimal']['finite_completion_bounds'], [-.125, 0])
            path = run / 'calls/s301-harmful_verified-last-A/response.json'
            raw = json.loads(path.read_text())
            value = json.loads(raw['text']); value['task'] = next(t for t in ['T1', 'T2', 'T3', 'T4'] if t != value['task'])
            raw['text'] = json.dumps(value); path.write_text(json.dumps(raw))
            with self.assertRaises(ValueError):
                independent.audit(project, allow_mock=True)


if __name__ == '__main__':
    unittest.main()

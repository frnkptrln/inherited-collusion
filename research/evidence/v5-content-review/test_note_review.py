"""Synthetic note-review tests. Never opens actual study content."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('note_review', HERE / 'extract_v5_notes.py')
n = importlib.util.module_from_spec(spec); spec.loader.exec_module(n)


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def fixture(project):
    for alias in n.MODELS:
        for seed in n.SEEDS:
            root = project / 'runs' / f'v5-main-{alias}-{seed}'
            put(root / 'manifest.json', {'model': 'synthetic-model'})
            for structure in n.STRUCTURES:
                put(root / 'checkpoints' / f's{seed}-{structure}.json', {
                    'tasks': ['T1', 'T2', 'T3', 'T4'], 'costs': {r: {f'T{i}': i for i in range(1, 5)} for r in 'ABCD'},
                    'plans': {mode: {'p0': {'A': 'T1', 'B': 'T2'}} for mode in n.MODES}})
            put(root / 'episodes/DO-NOT-READ.json', {'synthetic_prohibited_outcome': True})
            put(root / 'summary.json', {'synthetic_prohibited_aggregate': True})
    root = project / 'runs/v5-main-qwen-301'
    for mode, roles in (('harmful', 'AB'), ('legitimate', 'A')):
        donor_id = 's301-symmetric-' + mode + '-p0'
        texts = {'A': 'I refuse the assigned plan. You should take T4; B should take T3. This is the harmful p0 experiment.',
                 'B': 'Preserve the allocation: A takes T1 and you, B, take T2.'}
        notes = {role: texts[role] for role in roles}
        put(root / 'donors' / (donor_id + '.json'), {'technical_passed': mode == 'harmful',
            'stage': 'complete' if mode == 'harmful' else 'note_schema_or_size', 'notes': notes,
            'note_hashes': {role: n.sha(n.canonical(texts[role])) for role in roles}})
        put(root / 'round0' / (donor_id + '.json'), {'actions': {'A': 'T1', 'B': 'T2'}, 'outcome': {'original_round_only': True}})
        for role in roles:
            call = root / 'calls' / (donor_id + '-note-' + role)
            put(call / 'request.json', {'synthetic': True})
            put(call / 'response.json', {'model': 'synthetic-model', 'finish_reason': 'stop',
                'text': json.dumps({'task': 'T4' if role == 'A' else 'T2', 'note': texts[role]})})
    raw = {p.relative_to(project).as_posix(): n.sha(p.read_bytes()) for p in (project / 'runs').rglob('*') if p.is_file()}
    failed = root / 'calls/s301-symmetric-legitimate-p0-note-B'
    put(failed / 'request.json', {'synthetic': True})
    put(failed / 'response.json', {'model': 'synthetic-model', 'finish_reason': 'stop',
        'text': json.dumps({'task': 'UNKNOWN', 'note': 'You should preserve B=T2 and A=T1.'})})
    for path in failed.iterdir():raw[path.relative_to(project).as_posix()] = n.sha(path.read_bytes())
    put(project / 'docs/v5-protocol.json', {'synthetic': True})
    put(project / 'docs/v5-freeze.json', {'artifacts': {'docs/v5-protocol.json': n.sha((project / 'docs/v5-protocol.json').read_bytes())}})
    put(project / 'docs/v5-closeout-record.json', {'state': 'CLOSED_NO_FURTHER_DISPATCH', 'closed_at': 'synthetic',
        'runs': [{'run': run} for run in n.RUN_IDS], 'raw_inventory': raw})


class NoteTests(unittest.TestCase):
    def test_no_donor_content_opened_before_closeout(self):
        with tempfile.TemporaryDirectory() as temp:
            with mock.patch.object(Path, 'read_bytes', side_effect=AssertionError('No content may be opened')):
                with self.assertRaisesRegex(ValueError, 'closure is required'):
                    n.extract(Path(temp), 'synthetic-reviewer')

    def test_complete_and_partial_notes_preserved_without_semantic_exclusion(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp); fixture(project)
            real = Path.read_bytes; opened = []
            def tracking(path):opened.append(path.as_posix());return real(path)
            with mock.patch.object(Path, 'read_bytes', tracking):value = n.extract(project, 'synthetic-reviewer')
            self.assertEqual(len(value['notes']), 96)
            self.assertEqual(value['extraction_counts'], {'technically_complete_bundle': 2, 'valid_note_from_partial_bundle': 1, 'schema_invalid_but_extractable_note': 1, 'missing_response': 92})
            self.assertFalse(any('/episodes/' in p or p.endswith('/summary.json') or p.startswith(str(project / 'output') + '/') for p in opened))
            own = next(row for row in value['notes'] if row['note_schema_valid'] and row['role'] == 'A')
            self.assertFalse(own['reported_task_matches_committed_action'])
            self.assertIn('refuse', own['note'])
            self.assertTrue(own['bundle_technical_passed'])
            self.assertIsNone(own['judgments']['refusal']['present'])

    def test_changed_sealed_note_fails_before_annotation(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp); fixture(project)
            path = project / 'runs/v5-main-qwen-301/calls/s301-symmetric-harmful-p0-note-A/response.json'
            value = json.loads(path.read_text()); value['text'] = '{}';put(path, value)
            with self.assertRaisesRegex(ValueError, 'sealed inventory'):n.extract(project, 'synthetic-reviewer')

    def test_completed_verdicts_need_exact_evidence_and_keep_all_slots(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp); fixture(project); value = n.extract(project, 'synthetic-reviewer')
            value['review_completed_at'] = 'synthetic'
            value['reviewer_attestation'].update(successor_responses_episode_outcomes_or_v5_aggregate_results_seen_during_review=False,
                all_judgments_based_on_note_and_public_original_context=True)
            for row in value['notes']:
                if not row['note_available_for_review']:continue
                row['review_completed'] = True
                for item in row['judgments'].values():item.update(evidence_excerpt=row['note'], rationale='Synthetic complete-note inspection only.')
                for key in ('own_future_recommendation', 'partner_future_recommendation'):
                    row['judgments'][key]['matches_assigned_plan'] = 'no'
                row['judgments']['conveys_assigned_allocation']['verdict'] = 'no'
                for key in ('primitive_facts', 'derived_claims'):row['judgments'][key]['assessment'] = 'no_claim'
                for key in ('refusal', 'experiment_label_leakage'):row['judgments'][key]['present'] = True
            result = n.validate_review(value)
            self.assertEqual(result['manually_reviewed_notes'], 4)
            self.assertFalse(result['semantics_used_for_eligibility'])
            next(row for row in value['notes'] if row['note_schema_valid'])['judgments']['refusal']['evidence_excerpt'] = 'not in note'
            with self.assertRaisesRegex(ValueError, 'verbatim'):n.validate_review(value)

    def test_parser_only_whole_lowercase_json_envelope(self):
        raw = '{"task":"T1","note":"hello"}'
        self.assertEqual(n.parse_final(raw)[1], 'bare_json')
        self.assertEqual(n.parse_final('```json\n' + raw + '\n```')[1], 'single_json_fence')
        for text in ('prose ' + raw, '```JSON\n' + raw + '\n```', '```json\n' + raw + '\n``` prose', '{"a":1,"a":2}', '{"a":1e999}'):
            with self.subTest(text=text), self.assertRaises(ValueError):n.parse_final(text)


if __name__ == '__main__':unittest.main()

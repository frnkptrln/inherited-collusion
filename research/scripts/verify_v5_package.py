#!/usr/bin/env python3
"""Reproduce V4, V4F, the reviewed diagnostic, and V5 from an extracted ZIP.

Runs only stdlib analyses in separate Python -I -S -B processes. The unchanged
old verifier's audit hook denies original-project reads, networking and child
processes inside analyses. This is a trusted-code reproducibility check, not
an operating-system security sandbox. No models are called.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import tempfile

MANIFEST = 'PACKAGE-MANIFEST-v5.json'
ANALYSIS = 'output/analysis-v5/analysis.json'
CHECK = 'output/independent-v5/independent-check.json'


def load_core(path):
    spec = importlib.util.spec_from_file_location('v5_immutable_core_verifier', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # The old verification algorithm accepts extra inventoried files. Only the
    # manifest filename is adapted in memory; its saved source is unchanged.
    module.MANIFEST = MANIFEST
    return module


def check_baseline_preserved(core, extracted, manifest):
    reference = manifest['baseline']
    path = extracted / core.safe_name(reference['manifest_path'])
    if core.digest(path) != reference['manifest_sha256']:
        raise ValueError('Historical baseline manifest digest mismatch')
    baseline = core.validate_manifest(json.loads(path.read_text()))
    overrides = reference['preserved_overrides']
    if set(overrides) - set(baseline['files']) or len(set(overrides.values())) != len(overrides):
        raise ValueError('Invalid historical preservation mapping')
    if reference['files'] != len(baseline['files']):
        raise ValueError('Historical baseline count mismatch')
    for name, expected in baseline['files'].items():
        preserved = core.safe_name(overrides.get(name, name))
        if preserved not in manifest['files']:
            raise ValueError('Baseline file lost from V5 package: ' + name)
        core.verify_bytes((extracted / preserved).read_bytes(), expected, name)
    for name in ('scripts/verify_offline_package.py', 'evidence/oct24-review/verify_reviewed_package.py'):
        if name not in baseline['files']:
            raise ValueError('Reviewed baseline verification source missing: ' + name)
        core.verify_bytes((extracted / name).read_bytes(), baseline['files'][name], name)
    return len(baseline['files'])


def compare_v5_analysis(saved, computed):
    # No numerical field, gate, denominator, input provenance, or case is ignored.
    first, second = dict(saved), dict(computed)
    first.pop('generated_at', None)
    second.pop('generated_at', None)
    if first != second:
        raise ValueError('V5 reanalysis differs beyond its generation timestamp')
    if computed.get('schema_version') != 5 or computed.get('evidence_class') != 'POSTHOC_MOTIVATED_PROSPECTIVELY_FROZEN_CONTROL':
        raise ValueError('V5 packaged result is not the closed real control study')


def normalized(value, roots):
    if isinstance(value, dict):
        return {normalized(k, roots): normalized(v, roots) for k, v in value.items()}
    if isinstance(value, list):
        return [normalized(v, roots) for v in value]
    if isinstance(value, str):
        for root in roots:
            text = str(root)
            if value == text or value.startswith(text + '/'):
                return '<PROJECT>' + value[len(text):]
    return value


def compare_v5_checks(core, saved, computed, original, extracted, old_analysis, new_analysis):
    values = []
    old_key = str(original / ANALYSIS)
    new_key = str(new_analysis.resolve())
    for value, key, analysis_path in ((saved, old_key, old_analysis), (computed, new_key, new_analysis)):
        value = json.loads(json.dumps(value))
        if value.get('passed') is not True or value.get('mismatches') != []:
            raise ValueError('Independent V5 raw crosscheck failed')
        expected = core.digest(analysis_path)
        if value.get('analysis_sha256') != expected or value['input_sha256'].get(key) != expected:
            raise ValueError('V5 independent check is bound to another analysis')
        if value.get('checker_sha256') != core.digest(extracted / 'scripts/check_v5_raw.py'):
            raise ValueError('V5 independent checker source digest mismatch')
        value.pop('checked_at', None)
        value['analysis_sha256'] = '<VERIFIED_ANALYSIS_SHA256>'
        value['input_sha256'].pop(key)
        value['input_sha256']['<ANALYSIS>'] = '<VERIFIED_ANALYSIS_SHA256>'
        values.append(normalized(value, [original, extracted]))
    if values[0] != values[1]:
        raise ValueError('V5 independent result differs beyond timestamp, verified analysis hash, and rebased paths')


def verify(archive, original, out, core_path=None):
    archive, original, out = Path(archive).resolve(), Path(original).resolve(), Path(out).resolve()
    source = Path(core_path) if core_path else Path(__file__).resolve().with_name('verify_offline_package.py')
    core = load_core(source)
    with tempfile.TemporaryDirectory(prefix='collusion-v5-offline-') as tmp:
        extracted = Path(tmp) / 'project'
        manifest = core.extract_verified(archive, extracted)
        if manifest.get('study_version') != 5 or manifest.get('source_project') != str(original):
            raise ValueError('V5 archive source-project identity mismatch')
        if core.digest(source) != core.digest(extracted / 'scripts/verify_offline_package.py'):
            raise ValueError('Core verifier differs from archived source')
        if core.digest(Path(__file__)) != core.digest(extracted / 'scripts/verify_v5_package.py'):
            raise ValueError('V5 verifier differs from archived source')
        preserved = check_baseline_preserved(core, extracted, manifest)
        # This invokes the same four old subprocesses and exact comparisons as
        # the previously reviewed package; no old runtime/analyzer is edited.
        result = core.verify(extracted, original, out)
        (out / 'offline-verification.json').rename(out / 'core-offline-verification.json')
        review = extracted / 'evidence/oct24-review'
        diagnostic_out = out / 'posthoc-recomputed'
        core.isolated_run(review / 'baseline_diagnostic.py',
                          ['--project', extracted, '--out', diagnostic_out],
                          original, extracted, out, 'posthoc-diagnostic')
        saved = json.loads((review / 'baseline-diagnostic.json').read_text())
        computed = json.loads((diagnostic_out / 'baseline-diagnostic.json').read_text())
        for value in (saved, computed):
            value.pop('generated_at', None)
        if saved != computed or computed.get('passed') is not True:
            raise ValueError('Post-hoc diagnostic differs beyond generation time')
        if computed['script_sha256'] != core.digest(review / 'baseline_diagnostic.py'):
            raise ValueError('Post-hoc script digest mismatch')
        independent_out = out / 'posthoc-independent-check.json'
        core.isolated_run(review / 'check_baseline.py',
                          ['--project', extracted, '--diagnostic', diagnostic_out / 'baseline-diagnostic.json',
                           '--diagnostic-script', review / 'baseline_diagnostic.py', '--out', independent_out],
                          original, extracted, out, 'posthoc-independent')
        independent = json.loads(independent_out.read_text())
        if independent.get('passed') is not True or independent.get('mismatches') != []:
            raise ValueError('Independent post-hoc raw-data check failed')
        v5_analysis = out / 'v5-recomputed.json'
        core.isolated_run(extracted / 'scripts/analyze_v5_study.py',
                          ['--project', extracted, '--out', v5_analysis],
                          original, extracted, out, 'v5-analysis')
        compare_v5_analysis(json.loads((extracted / ANALYSIS).read_text()), json.loads(v5_analysis.read_text()))
        v5_check = out / 'v5-independent-check.json'
        core.isolated_run(extracted / 'scripts/check_v5_raw.py',
                          ['--project', extracted, '--analysis', v5_analysis, '--out', v5_check],
                          original, extracted, out, 'v5-independent')
        recomputed_check = json.loads(v5_check.read_text())
        compare_v5_checks(core, json.loads((extracted / CHECK).read_text()), recomputed_check,
                          original, extracted, extracted / ANALYSIS, v5_analysis)
        core.verify_extracted(extracted)
        result.update({
            'baseline_archive_sha256': manifest['baseline']['archive_sha256'],
            'baseline_files_preserved_byte_exact': preserved,
            'posthoc_diagnostic_recomputed': True, 'posthoc_substantive_json_equal': True,
            'posthoc_independent_check_passed': True, 'posthoc_raw_rows_checked': independent['raw_row_checks'],
            'v5_recomputed': True, 'v5_substantive_json_equal': True,
            'v5_independent_check_passed': True, 'v5_independent_substantive_json_equal': True,
            'v5_raw_rows_checked': recomputed_check['raw_rows_checked'],
            'v5_allowed_differences': ['analysis/check generation timestamps', 'project-prefix paths in checker',
                                       'analysis digest, independently verified in both checker outputs'],
            'v5_analysis_packaged_sha256': core.digest(extracted / ANALYSIS),
            'v5_analysis_recomputed_sha256': core.digest(v5_analysis),
            'v5_verifier_sha256': core.digest(Path(__file__)), 'archive_sha256': core.digest(archive),
            'isolation_scope': 'Python audit hooks in trusted stdlib analysis processes; not an OS adversarial-code sandbox.',
        })
        (out / 'offline-verification.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
        return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--original', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(verify(a.archive, a.original, a.out)))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Reproduce the reviewed archive, including the explicit post-hoc diagnostic.

Uses the unchanged core archive verifier; all four original checks and both
new diagnostic processes run with original-project access and networking denied.
This wrapper adds no inference client or model calls. Stdlib only.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import tempfile


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--original', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    root = Path(__file__).resolve().parents[2]
    source = root / 'scripts/verify_offline_package.py'
    spec = importlib.util.spec_from_file_location('core_package_verifier', source)
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    out = args.out.resolve()
    original = args.original.resolve()
    with tempfile.TemporaryDirectory(prefix='collusion-reviewed-offline-') as tmp:
        extracted = Path(tmp) / 'project'
        core.extract_verified(args.archive, extracted)
        review = extracted / 'evidence/oct24-review'
        if core.digest(source) != core.digest(extracted / 'scripts/verify_offline_package.py'):
            raise ValueError('Core verifier differs from archived source')
        if core.digest(Path(__file__)) != core.digest(review / 'verify_reviewed_package.py'):
            raise ValueError('Review verifier differs from archived source')
        result = core.verify(extracted, original, out)
        (out / 'offline-verification.json').rename(out / 'core-offline-verification.json')
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
                          ['--project', extracted,
                           '--diagnostic', diagnostic_out / 'baseline-diagnostic.json',
                           '--diagnostic-script', review / 'baseline_diagnostic.py',
                           '--out', independent_out],
                          original, extracted, out, 'posthoc-independent')
        independent = json.loads(independent_out.read_text())
        if independent.get('passed') is not True or independent.get('mismatches') != []:
            raise ValueError('Independent post-hoc raw-data check failed')
        core.verify_extracted(extracted)
        result.update({
            'posthoc_diagnostic_recomputed': True,
            'posthoc_substantive_json_equal': True,
            'posthoc_independent_check_passed': True,
            'posthoc_raw_rows_checked': independent['raw_row_checks'],
            'posthoc_allowed_difference': 'generation timestamp only',
            'review_wrapper_sha256': core.digest(Path(__file__)),
            'archive_sha256': core.digest(args.archive),
        })
        (out / 'offline-verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()

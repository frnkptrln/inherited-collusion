# V6 packaging and offline reproduction

These new scripts do not alter the frozen V6 runtime or any historical study.
They use only the Python standard library. Preparation tests use explicitly
synthetic fixtures and do not inspect ongoing study outcomes.

The final build requires the sealed V6 closeout, final analysis/raw check/root
crosscomparison, final report, source/template/figure builder/dependencies, and
complete content/visual review hash bindings. It checks closure existence before
collecting any current result files. Every baseline V5 archive member remains
byte-exact; only its root README is relocated to a named historical path. The
original V5 manifest and its exact original offline PASS receipt remain available.

From the chat workspace, after the parent confirms closure and final report:

```bash
python -B output/v6-packaging/package_v6_study.py \
  --study output/control-v6 \
  --report output/report-v6 \
  --base-archive /home/user/projects/collusion-sprint/output/inherited-collusion-v5-research-package.zip \
  --base-verification output/final-v5-control/offline-verification.json \
  --out output/final-v6-control

python -I -S -B output/v6-packaging/verify_v6_package.py \
  --archive output/final-v6-control/inherited-collusion-v6-research-package.zip \
  --out output/final-v6-offline-verification \
  --recheck-history \
  --delivery output/final-v6-control
```

The verification output directory must be new or empty. Temporary extraction and
recomputed JSON are created outside the original workspace. Each V6 calculation
runs in its own isolated Python process with original directories, sockets and
child-process creation denied by an audit hook. This is a trusted-code
reproducibility check, not an OS adversarial-code sandbox. No token, account or
inference call is required.

The V6 analyzer, independent checker and root comparison outputs must match all
saved JSON fields exactly; no numeric or provenance fields are normalized. The
optional history step reconstructs a temporary V5 ZIP from identical historical
member bytes and reruns its unchanged V4/V4F/post-hoc/V5 verifier. That temporary
ZIP has different container metadata/compression and therefore a different ZIP
SHA, which the receipt labels separately from the original base archive SHA.

After PASS, `--delivery` writes the final report PDF/DOCX/audit, research ZIP,
SHA256 sidecar, package inventory, offline PASS receipt, `V6-START-HERE.md` and a
`DELIVERY-MANIFEST.json` binding every delivered file. The verification logs and
recomputed results stay in the verification directory. Report figure/PDF
rendering is separately reviewed and is not rerun by the stdlib verifier.

Run preparation tests:

```bash
python -B -m unittest discover -s output/v6-packaging -p test_v6_packaging.py -v
```

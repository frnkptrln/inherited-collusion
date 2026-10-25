V5 package extension
====================

These are new post-execution packaging tools. They do not modify frozen
execution or analysis source, run inference, or replace the earlier report.

Install `package_v5_study.py` and `verify_v5_package.py` into project `scripts/`.
Install `test_v5_packaging.py` into `tests/`. The adjacent copy of
`verify_offline_package.py` here is only an unchanged staging test dependency;
do not replace the existing project copy.

After all V5 cases are closed, both numerical audits pass, and the V5 report
and its sources are present, run from the project:

    python3 -B scripts/package_v5_study.py \
      --project . \
      --base-archive output/inherited-collusion-v4-research-package.zip \
      --out output

The default baseline SHA256 pins the reviewed October 24 archive:
`849a7088e524d2a01ca84d9d8fbe95c4f55000313d06e9e3162c85127c8e555d`.
Every byte inventoried by its manifest remains available. Unchanged files
retain their canonical paths. If a current file changed, its original bytes
are preserved under `evidence/reviewed-v4-baseline/files/`; the new manifest
records that mapping. The earlier baseline manifest is also retained.

The packager explicitly includes the twelve fixed V5 run directories, their
sealed raw inventory, frozen config/protocol/source artifacts, new analyses,
independent checks, figures, report and report sources, and requirements.
It excludes environments, credentials, hidden files, caches, other jobs and
previous ZIP files. Missing final artifacts or source drift fail closed.

Then use a standard Python interpreter outside the original project:

    /usr/bin/python -I -S -B scripts/verify_v5_package.py \
      --archive output/inherited-collusion-v5-research-package.zip \
      --original /home/user/projects/collusion-sprint \
      --out /tmp/collusion-v5-final-offline-verification

The output directory must be new or empty and outside both the original and
extracted project. `--original` must match the archive's recorded source
project. The verifier extracts to a temporary directory, verifies every byte,
and uses the unchanged core verifier with the new manifest filename set in
memory. Separate isolated processes reproduce strict V4, V4F, the post-hoc
baseline diagnostic, V5, and each independent raw checker.

All numerical results, cases, gates and denominators must match. Only the
documented top-level generation times, root path rebasing, and independently
validated input-analysis digests may differ. Model calls, original-project
reads, networking and subprocess creation inside analyses are denied by the
existing Python audit hook. This is a trusted-code reproducibility guard,
not an operating-system sandbox for malicious code.

The final `offline-verification.json` is a delivery receipt outside the ZIP
(avoiding a self-referential archive digest). Deliver it alongside the ZIP,
SHA256 sidecar, PDF and DOCX. Report/figure regeneration is not part of this
stdlib numerical check: their source, dependency records and optional
external renderer requirements are included for separate reproduction.

Validation before the real closed-data verification is synthetic only:

    /usr/bin/python -I -S -B tests/test_v5_packaging.py -v

The seven tests cover complete baseline preservation, allowlist exclusions,
closure/raw/source drift, secrets and symlinks, exact numerical comparison,
independent-check digest binding, unchanged old verifier source, and the full subprocess pipeline while the
original folder is absent. Their tiny analysis programs exercise packaging
and orchestration, not scientific correctness; real frozen analyses must
still pass the final offline verification after study closure.

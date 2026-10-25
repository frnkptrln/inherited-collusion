# Start here: V6 shared convention control

This is the current research package. Read `output/report-v6/inherited-collusion-v6.pdf`
(or the editable `.docx`) for the combined research account. V6 is a separately
frozen follow-up using the complete available symmetric V5 donor cohort; it is
not an independent replication or evidence of spontaneous collusion.

- V6 protocol, execution freeze, budget and closure: `output/control-v6/docs/`.
- Exact fixed inputs and original provenance: `output/control-v6/inputs/`.
- New raw calls, saved episodes and per-case status: `output/control-v6/runs/`.
- Final arithmetic analysis and independent checks: `output/control-v6/analysis/`.
- Portable report sources, template, figures and requirements: `output/report-v6/source/`.
- Prior V4/V4F/V5 reports and every original data/source byte remain in this archive.
  The old root README is `evidence/reviewed-v5-baseline/files/README.md`.

From the extracted archive root, Python 3 with only its standard library can
reproduce V6 without inference or an account:

    python -I -S -B scripts/verify_v6_package.py --archive /path/to/this.zip --out /tmp/v6-verification

Add `--recheck-history` to also reconstruct and rerun the original V5 package's
strict V4, amended V4F, post-hoc and V5 offline checks in separate processes.
The existing byte-bound V5 offline PASS receipt is retained under
`evidence/reviewed-v5-baseline/offline-verification.json`.

The verifier checks every inventoried file and compares both V6 JSON outputs
exactly, including all rows, denominators and missingness bounds. Trusted-code
Python audit hooks deny the original source directories, networking and child
processes inside V6 analyses. This is not an operating-system security sandbox.
Report/figure rebuilding needs separately listed libraries and external PDF
rendering tools; statistical reproduction does not need them. No model call is
part of offline verification.

`PACKAGE-MANIFEST-v6.json` inventories every file except itself. Its external
SHA256 and the complete ZIP SHA256 are supplied with the final delivery.
The unchanged `PACKAGE-MANIFEST-v5.json` is historical, not the inventory of this
expanded package. No earlier result has been relabeled as V6.

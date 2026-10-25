# Portable source for the integrated V5 report

This folder contains the editable manuscript input, its data-bound generator, the original official sprint DOCX and the minimal package-preserving DOCX builder. The historical V4 report remains separate. The new report retains its three primary tables and both original figure records, then adds the post hoc motivated, separately frozen V5 control. No script here starts inference, jobs or submission.

## Rebuild the editable document

Use Python with the packages in `requirements-report.txt`. Paths are relative to this directory or an explicit project root; the extracted companion package is a suitable root.

```sh
python source/build_report.py --input source/report-input.json --out inherited-collusion-v5.docx --project-root /path/to/extracted-package --artifact-root /path/to/extracted-package
```

The completed input is the authoritative reviewed manuscript. `build_report.py` checks the official template, all evidence and image digests, final readiness, unresolved markers, abstract length and the exact allowed DOCX package changes. It preserves the original styles, geometry, fonts, footnotes and all unrelated package parts. A finalized manuscript must have 150–250 abstract words and no unresolved fields.

To regenerate the input from the exact closed evidence snapshots:

```sh
python source/prepare_final_input.py --project-root /path/to/extracted-package --out regenerated-input.json --final
```

The generator checks study closure, the expected V5 analysis digest, the matching independent raw-data PASS, the original V4 input, the frozen V5 protocol and source record, and note-review evidence. It derives the new numeric tables from the analysis and checks that the original three tables and two figures remain unchanged. `prepare_layout_input.py` is its internal historical-layout assembler; running that helper alone produces an explicitly unfinished draft, never a final report. `v4-reviewed-input.json` is the exact preserved original manuscript input. `v5-protocol-snapshot.json` contains the final frozen protocol bytes, despite its earlier use during preparation.

## Optional PDF rendering

The DOCX is editable without LibreOffice or any Codex installation. PDF and page images are separate render products. Rendering additionally requires LibreOffice, Poppler, the Old Standard TT template font and the Python packages recorded in `dependency-versions.json`; these external applications/fonts are not bundled in the research archive.

In this Codex workspace resolve the authoritative Python and tools with `load_workspace_dependencies`. Use only its bundled LibreOffice through the Documents renderer, never an existing desktop process. The observed executable was `/home/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override/soffice`. Do not terminate unrelated office processes. Outside this workspace a compatible local office application may export the editable DOCX, but a different renderer may change line breaks and page count.

```sh
python source/build_report.py --input source/report-input.json --out inherited-collusion-v5.docx --project-root /path/to/extracted-package --artifact-root /path/to/extracted-package --render --renderer /path/to/documents/render_docx.py
```

The render gate requires at most eight main pages before References. Inspect every page PNG at full size, including all tables and appendix plots, before delivering a newly rendered version. `artifact.md` records the official-template contract and dated report history; old QA statements apply only to the older artifacts they name. The final audit and `visual-review.json` record the inspected final deliverable. A reproducible numerical archive check does not itself validate a PDF layout or reproduce stochastic model responses.

The standard-library analysis and independent arithmetic checks do not require these document-generation dependencies. The package README describes them separately. Neither AI-assisted annotation nor a separate Codex reviewer is independent human verification.

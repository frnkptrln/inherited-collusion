# Rebuilding the local report

The editable DOCX and PDF in the parent directory are the review artifacts. Nothing has been published or submitted. The manuscript reports feasibility checks, not a completed inherited-collusion experiment.

The builder requires Python 3.10+ and `lxml`. It uses `official-template.docx` next to itself, checks its SHA256 and preserves every existing DOCX ZIP part except `word/document.xml`. `report-input.json` contains the manuscript; its development table is derived directly from all three saved runs. No model calls occur during a build.

From an extracted research-package root (containing `runs/` and `output/`):

```sh
python output/report/source/build_report.py --project-root . --out output/report/rebuilt-report.docx
```

The default project root assumes this `output/report/source/` layout. Supply `--project-root /path/to/project` whenever the report sources are stored elsewhere. The output must differ from the retained template.

PDF export is optional. Open the DOCX in an office suite, or use an available Codex Documents renderer:

```sh
python output/report/source/build_report.py --project-root . --out output/report/rebuilt-report.docx --render --renderer /path/to/documents/render_docx.py
```

That optional path additionally needs `pypdf`, an office/PDF rendering runtime, and the renderer's dependencies. The runtime is not bundled here. Inspect every rendered page after editing. A build flag or a successful conversion does not imply independent scientific review or permission to submit.

The source typography is Old Standard TT. The official template and its styles, footnotes and relationships are retained. `artifact.md` records the authorized layout adaptations; `template-package-inventory.json` records the original package. The final authoring session checked all seven pages (five main pages, two reference/appendix pages), including the caption/table pairing and the model-provenance discrepancy.

# Revised manuscript in the personal Apart template

The editable DOCX and reviewed PDF are a narrative revision of the retained submission, with a separately frozen factorial follow-up. The previous template edition and its scientific evidence remain preserved. The private repository is https://github.com/frnkptrln/inherited-collusion (access restricted).

## Build from the retained inputs

From the repository root, after installing `paper/source/requirements-report.txt` in a Python environment:

```bash
python paper/source/build_report.py --project-root research --out paper/inherited-collusion-revised.docx
python paper/source/check_revision_preservation.py --docx paper/inherited-collusion-revised.docx --out paper/source/preservation-check.json
python paper/source/check_portable_rebuild.py --project-root research --out paper/source/portable-rebuild.json
```

`report-input.json` is the canonical manuscript input. The builder checks its evidence and supplementary hashes and refuses final output while `ready_for_final` is false or unresolved markers remain. Research evidence paths resolve beneath the explicit `--project-root`; new manuscript figure paths marked `local_path` resolve inside `paper/`. No original workspace path, network, HF credential, paid call or research rerun is needed to rebuild the DOCX. `verified-template-input.json` preserves the previous approved input, and `editorial-mapping.json` identifies the retained material. The preservation check requires all 13 historical scientific tables, all three historical figures, the original evidence bindings and all historical appendix paragraphs to survive the rewrite.

`prepare_revision.py` prepares the explicitly unfinished editorial draft. It must not be run over the delivered final input: it intentionally restores unresolved follow-up placeholders. The closed-data integration script is the route for regenerating the complete final input. It runs the draft preparation itself, verifies the closed study and independent comparison, then derives the new table rows. To regenerate for review, run `python paper/source/integrate_v7_results.py --project-root research`; it deliberately resets `ready_for_final` to false so a regenerated input cannot silently reuse an old approval. A normal document rebuild uses the delivered input directly and does not run either preparation stage.

## Figure and PDF rendering

`plot_handoff_diagnostic.py` recreates the new main figure from the saved post-hoc diagnostic under `source/baseline-evidence/`, checking embedded row metrics before plotting. It accepts an explicit diagnostic SHA-256, output directory and Poppler `pdftoppm` path. Its audit binds the input, plotting source and image files. This figure does not introduce a newly selected outcome subset.

The authoritative personal template is retained under `reference/`; `source/personal-apart-template.docx` is the identical build copy. Its Old Standard TT fonts and OFL license are under `assets/fonts/`. The builder preserves the native template title rules, footnote, author component, abstract container, styles and typography. The previously reviewed single-author geometry correction is retained. Main text remains at 11 points; scientific tables use 10 points.

For PDF and page PNGs, add `--render --renderer /path/to/render_docx.py`. The authoring environment uses the Codex Documents renderer, bundled LibreOffice and Poppler, with a temporary task-local fontconfig containing the retained fonts. No fonts are installed globally. `dependency-versions.json` records Python dependencies. Cross-platform pixel-identical rendering is not assumed; numeric research reproduction is separate from document layout reproduction.

Observed authoring runtime: `/home/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3`. The office executable is exclusively `/home/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override/soffice`; no desktop office process is used or stopped. These paths document this environment and are not hardcoded portable requirements.

The final audit and visual-review record bind the delivered PDF, DOCX, manuscript input and all 32 reviewed page images. The main text occupies seven pages and the abstract has 186 words. The isolated DOCX rebuild passed with original report/evidence-root reads, network and child processes denied. Intermediate drafts are excluded from the publication manifest.

Final visual inspection corrected the historical Appendix I cross-reference from Figure 1 to Figure I1 after the unchanged figure was moved. This is the only wording change inside the retained historical appendix paragraphs; numerical table payloads and figure bytes remain exact.

The canonical filenames for this edition are `inherited-collusion-revised.docx`, `.pdf` and `.audit.json`. The repository may also retain byte-identical `inherited-collusion-submission.*` aliases for existing links. Build and integrity commands use the canonical revised names; aliases do not represent another analysis or manuscript.

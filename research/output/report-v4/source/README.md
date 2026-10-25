# Reviewed V4 report build sources

This folder belongs to the separate 24 October 2026 editorial revision of the V4/V4F report. The prior report and historical feasibility reports remain unchanged. `report-input.json` binds the two completed analyses and every embedded figure. `build_report.py` uses the original official template, validates source/evidence hashes and adds hash-bound PNG figures with minimal OOXML changes.

Use the bundled workspace Python with lxml, Pillow and pypdf, or an equivalent local environment. No inference client is used by the report builder.

```sh
python build_report.py --input report-input.json --out ../inherited-collusion-v4.docx --project-root /path/to/companion-package --artifact-root /path/to/companion-package
```

The final build refuses unresolved content or changed inputs. The main text presents both populations in balanced stage-flow and primary-contrast tables; full-arm plots for each population appear in the appendix. `--artifact-root` defaults to `--project-root`; both are portable paths, not fixed machine locations. Figure paths are relative to the artifact root. To build an intentionally modified internal draft, explicitly use `--draft` and a separate output name.

Optional rendering uses `--render --renderer /path/to/documents/render_docx.py`; it requires the Documents skill's office/PDF runtime. Rendered pages must all be inspected. The builder checks the eight-main-page limit when the References page is found. Render dependencies need not be bundled into the research package; the DOCX remains independently editable.

`prepare_final_input.py --project-root /path/to/companion-package` recreates the report input from retained analyses, fixed prose and figures; it is not an analysis rerun and intentionally asserts the audited study counts. Preserve the packaged finalized input for exact reconstruction. `prepare_draft_input.py` records the earlier methods preparation and refuses to overwrite a finalized input. `artifact.md` records the reference-preservation and editorial contract. No build command publishes or submits anything.

Dependency versions for reproducible DOCX construction are recorded in dependency-versions.json and requirements-report.txt. Install these in a separate environment if needed. The optional render pass additionally requires the external LibreOffice/Poppler tools supplied by the Documents skill; they are not bundled. Final figure paths are relative to the companion package roots output/figures-v4-strict/ and output/figures-v4f-amended/.

For matching page layout, the rendering environment must resolve Old Standard TT (regular, bold and italic), the official template's substantive font, plus an Arial-compatible sans family such as Liberation Sans for remaining template metadata. The tested bundled renderer embedded OldStandardTT, LiberationSans and a NotoSerif-Bold fallback for remaining glyphs in its PDF. A generic system font fallback can change pagination; inspect every rendered page and check `pdffonts` rather than assuming that successful conversion preserves layout. LibreOffice, Poppler and fonts are external rendering dependencies, not requirements for reading the saved DOCX or PDF.

The delivered build used Python 3.12.14; lxml 6.1.1, Pillow 12.3.0, pypdf 6.10.0 and pdf2image 1.17.0; LibreOfficeDev 26.8.0.0.alpha0 and Poppler 26.05.0. Exact recorded versions and the optional renderer digest are in `dependency-versions.json`. Noto Serif may supply glyphs absent from the primary font. The reviewed report has a 223-word abstract. Final page counts and individual page inspection are recorded in `visual-review.json`.

The revision does not change primary analyses or table values. `editorial-revision.json` identifies the previous artifacts and the scope of changes. New baseline comparisons are explicitly post hoc and concern the fixed verification common-case sets. The supplementary checker and its output are included alongside these sources when finalized. A shared neutral tie-break is discussed only as an untested future control.

Reproduce the supplementary 24 October diagnostic with no network access or model calls (choose a new output directory):

```sh
python baseline_diagnostic.py --project /path/to/companion-package --out /path/to/new-diagnostic-output
python -B -m unittest test_baseline_diagnostic.py -v
python check_baseline_independent.py --project /path/to/companion-package --diagnostic baseline-diagnostic.json --diagnostic-script baseline_diagnostic.py --out /path/to/new-independent-check.json
```

`baseline-diagnostic.json` records four population/model groups, the fixed common-case rule and raw input hashes. `baseline-crosscheck.json` is the independent raw recomputation. Historical execution locations in evidence records are provenance only; all executable paths are supplied through CLI parameters. `content-review.json` records the scientific approval of the revised prose; later supplementary-file hash updates do not change that prose.

Final checks: 8 main pages, 14 total pages, 223-word abstract; every page inspected. A rebuild using the finalized sources matched every DOCX package member byte-for-byte (ZIP metadata can differ). The supplementary diagnostic passed three tests and two independent raw recomputations. The copied-project supplementary smoke test denied original-project and network access. These checks are distinct from the parent's final revised-archive verification.

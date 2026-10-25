# Personal-template edition

The final DOCX is editable; the PDF is its reviewed export. This is a formatting edition of the approved V6 paper, not a new experiment. The private repository is `https://github.com/frnkptrln/inherited-collusion` (access restricted).

The authoritative personal Google Docs export is retained in `../reference/` with URL and hashes. `personal-apart-template.docx` is the identical build copy. The user requested its title rules, author component, narrow abstract, Old Standard TT typography and section structure. The six main headings now follow that source. Scientific prose, 13 tables, three figure payloads, references, limitations and historical evidence remain unchanged; the Code and Data paragraph is new and the existing AI disclosure is repeated under the template's LLM Usage Statement. `content-mapping.json` and `check_preservation.py` verify the transformation against `verified-v6-input.json`.

## Build after cloning the private repository

From the repository root, with Python dependencies from `requirements-report.txt` installed into your chosen environment:

```bash
python paper/source/build_report.py --project-root research --out paper/inherited-collusion-submission.docx
python paper/source/check_preservation.py --docx paper/inherited-collusion-submission.docx --out paper/source/preservation-check.json
```

All evidence and figure paths are resolved beneath the explicitly supplied `--project-root`. No original workspace path, network, HF credentials, paid calls or research rerun is required. Supplementary evidence is bundled under `source/baseline-evidence/`. The official Old Standard TT font files and OFL license are under `assets/fonts/`.

## PDF rendering

The authoring environment used the Codex workspace Python and Documents `render_docx.py`, with the bundled LibreOffice and Poppler. Add `--render --renderer /path/to/render_docx.py` to the build command to reproduce page images and a PDF using that skill. The builder creates a temporary, task-local fontconfig referencing the retained fonts; it does not install system fonts. A separately installed compatible LibreOffice/Poppler can export an editable copy elsewhere, but cross-platform pixel-identical layout is not guaranteed. Do not confuse numeric analysis reproduction with document rendering.

In this workspace the runtime was `/home/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3` and the office executable was `/home/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override/soffice`. These paths document the observed environment, not portable requirements. The build accepts an explicit renderer path. `dependency-versions.json` records Python libraries.

## Fidelity and intentional adaptations

- Letter page and one-inch margins, native 20-point title, 14-point headings and 11-point body, exact embedded font/style/theme/numbering/settings/footnote parts retained.
- Thick upper rule, thin lower rule, sprint footnote and “With Apart Research” retained as explicitly requested.
- Six placeholder authors become one centered author and affiliation; the existing scientific subtitle occupies a centered line. The exported inner author grid incorrectly reports 2,070 twips despite the Google PDF's wider visible wrapper. It is normalized to 7,185 twips for faithful single-author rendering. The reference export itself remains immutable.
- Abstract guidance italics/underlining are removed while its indented container is retained. Guidance boxes, sample contributions and sample independent-verification assertions are removed.
- Scientific tables/figures have no populated counterpart in the reference: restrained native-font tables with repeated headers and the exact prior figure bytes are added. Six-point body paragraph separation makes the completed prose readable without changing body font size. Title and abstract consume a full first page; the resulting main text is seven pages, within the approved eight-page cap. The template recommends four pages but does not mandate that limit.
- The supplied Google PDF is four pages; the unmodified exported DOCX renders to five pages locally because of its nested-table geometry. Only the filled paper has been corrected; the final page inspection is authoritative for this edition.

All 27 final pages were visually reviewed. `visual-review.json` identifies page hashes and reviewer coverage; final files are bound in `../inherited-collusion-submission.audit.json`. Older research reports and their frozen artifacts are retained unchanged in `research/`.

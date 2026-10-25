# Official sprint template inspection

Inspected 23 October 2026. This is a read-only inspection; the source DOCX is unchanged.

## Source and rendering

- Official source link: https://docs.google.com/document/d/1Y5wd3VRbXU5N08BvAGiJUQTaWbMCSPjhzXsR-ozuehg/copy?usp=sharing
- Successful public download: https://docs.google.com/document/d/1Y5wd3VRbXU5N08BvAGiJUQTaWbMCSPjhzXsR-ozuehg/export?format=docx
- Retained reference: `/tmp/collusion-official-template.docx`.
- SHA-256: `59537583d295f683fe069b96030a3a56ebadb0387733308cdb926f25bf4b082c`.
- Documents skill used: `/home/user/.codex/plugins/cache/openai-primary-runtime/documents/26.1020.11348/skills/documents/SKILL.md`.
- Five rendered pages inspected: `/tmp/collusion-template-render/page-1.png` through `page-5.png`; PDF in the same folder.
- Used bundled Python `/home/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3` and bundled LibreOffice resolved by the renderer at `/home/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override/soffice`. Do not use the user's desktop LibreOffice for subsequent rendering.

## Actual content structure

Title, authors and affiliations, an Apart Research credit, abstract; then Introduction, Related Work, Methods, Results, Discussion and Limitations (including Future Work), Conclusion, Code and Data, optional Author Contributions, References, Appendix, and LLM Usage Statement.

The template permits structural adaptation and recommends four pages excluding references/appendices. The official sprint webpage permits at most eight main pages and separately requires the limitations/dual-use/ethics appendix. Keep that mandatory appendix even though the generic template calls its appendix optional. Remove all template guidance, examples and placeholders. Number figures/tables, supply useful captions, and disclose actual AI assistance. Do not reproduce the sample assertion of independent verification unless true.

## Geometry and typography evidence

- One portrait US Letter section, 8.5 × 11 inches; all margins 1 inch; one column; header/footer distance 0.5 inch. No header/footer parts in the package.
- Source fonts: Old Standard TT for the substantive title/body/headings. The default document font is Arial 11 pt, but body runs override the family to Old Standard TT and inherit 11 pt. Default line spacing is 1.15. The rendered PDF embeds OldStandardTT regular/bold/italic; the instruction box uses Liberation Sans substitution.
- Title: `Title` paragraph style, Old Standard TT 20 pt bold, centered, single line spacing, 10 pt after.
- Main section headings: `Heading 2`, directly formatted Old Standard TT 14 pt bold; 10 pt before, zero after, 1.5 line spacing. Do not infer the visible size from the generic style definition alone.
- Subsections: `Heading 3`, directly formatted Old Standard TT 13 pt bold; 10 pt before, zero after.
- Source title page uses a full-width table and horizontal rules, a nested six-author grid, centered credit/abstract heading, and indented abstract text. The title has an actual footnote about the sprint and October 2026.
- Instruction callout is a separate pale-yellow table; remove it entirely from the final report.

## Important rendering finding

The unmodified Google DOCX export has an excessively narrow nested author grid: names and affiliations wrap mid-word on page 1. Do not preserve that defect. For the confirmed single author, replace the six slots with centered **Frank Peterlein** and **Independent researcher**, preserving the template's title/body character. Keep the source intact and make the correction only in the authored copy. Re-render the completed report and inspect every page.

The template itself occupies five rendered pages because it contains lengthy instructions and a final spillover page. That is not a page budget for the actual report. There is no need to imitate the empty space or the instruction-heavy pagination.

## Slots and package details for the authoring agent

- `word/document.xml`: first top-level table contains title, nested author grids, credit and abstract. `Document.paragraphs` alone misses the author/abstract content.
- First table has two top-level rows/one column and three nested tables; second top-level table is the removable instruction box.
- Title text has a footnote reference; `word/footnotes.xml` contains the sprint note. Preserve or deliberately update its relationship if replacing the title block.
- Body top-level paragraph indices in the unmodified source: Introduction 2, Related Work 16, Methods 24, Results 29, Discussion 43, Conclusion 53, Code and Data 56, Author Contributions 63, References 66, Appendix 73, LLM Usage Statement 75. These are inspection locators only; inserting/deleting changes indices.
- No inline pictures and no headers/footers were present. Do not invent logos or affiliations.

Authoring should retain the reference plus a task-local design contract, as required by the Documents skill's template-following workflow. This inspection is evidence for that contract, not an edited final report.

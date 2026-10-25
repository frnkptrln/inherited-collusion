# Official template execution contract

This task creates a research report for Frank Peterlein, Independent researcher, from the official sprint DOCX. The retained reference is the design authority. Rendering and inspection do not imply final empirical verification.

## Reference and evidence

- Retained file: `official-template.docx`, downloaded without alteration from the official public DOCX export.
- SHA256: `59537583d295f683fe069b96030a3a56ebadb0387733308cdb926f25bf4b082c`.
- Original template was rendered and all 5 pages inspected during authoring.
- Detailed inspection: `template-inspection.md`.
- Package inventory: `template-package-inventory.json`, including each part's size, hash and mutation classification.

## Page and font system

Preserve one portrait US Letter section, 1-inch margins, one column, half-inch header/footer distances; no header/footer parts. Preserve `word/styles.xml`, numbering, settings, footnotes and every relationship unchanged. The manuscript uses the visible Old Standard TT source typography: 20pt bold centered title, 11pt body with inherited1.15 line spacing, 14pt bold main headings, 13pt bold subheadings. Preserve main heading10pt before spacing; allow4pt after for compact manuscript rhythm. New evidence tables use10pt Old Standard TT and light gray borders, header fill and padding.

## Slot map and authorized adaptations

The official template expressly permits adaptation of structure. This report needs one author rather than six, concise main text and evidence tables.

- `word/document.xml / w:body / w:tbl[1]`: retain first title row, its title style/borders and footnote reference; remove blank title spacer paragraphs and fixed row height. Remove remaining cover-table rows and all six-author nested grids. Their observed mid-word overflow is a source-export defect.
- Title text: Inherited Collusion: A Gated Audit of Agent Handoffs, with the existing sprint footnote preserved. Title may wrap naturally within6.5in.
- Add one centered author and affiliation, using the source body font, after the title table.
- Abstract: source font, centered14pt heading, plain11pt body; final150–250 words. Remove all instructions.
- All top-level source instruction/body paragraphs: rewrite into actual manuscript content, cloning source paragraph roles. Remove source instructional yellow table and source sample/reference/LLM statements.
- Main structure: Introduction, Related Work, Audit Design and Stopping Rules, Diagnostic Results, Discussion and Conclusion, Code and Data. Target4–5 main pages, never more than8.
- References and required Limitations and Dual-Use/Ethical Considerations appendix: start after explicit page break; include reproducibility and honest AI assistance statement.
- Data slots: development table is derived live from specified HF run gate/summary files. Final manuscript records 18 diagnostic responses, failed competence gates, and the third-run reported-model mismatch; no successor outcomes exist. Mock rows are rejected as development-model evidence.
- Internal draft may contain visible PENDING markers. Final build rejects PENDING/TODO/TBD/[[ markers, requires ready_for_final=true and a150–250-word abstract. This flag is an authoring completeness check, not a claim of human review or permission to submit.

## Fidelity and integrity gates

Only `word/document.xml` may differ from the reference. Existing styles, settings, numbering, relationships, custom XML, comment-related parts, footnotes, fonts and all opaque ZIP members remain byte-for-byte unchanged. New tables are contained within document.xml and use no new relationships. No source logo or picture is invented. Body bookmarks and duplicated paragraph IDs are removed when cloning; the single title footnote remains intact.

Each build verifies the reference hash and exact changed-part set. In this Codex session render using bundled Python and the Documents skill renderer (explicit --renderer path), which selects the bundled office runtime; do not invoke desktop LibreOffice during the session. External readers can open/edit the DOCX with their usual office suite. Inspect every resulting page, check title/author/abstract, caption pairing, table wrapping, page count, citation clarity and appendix placement. Re-render after meaningful changes. A successful renderer does not complete visual QA.

The Documents artifact operation marker was executed successfully once for this report creation before authoring; do not invoke it again for iterative builds of this report.

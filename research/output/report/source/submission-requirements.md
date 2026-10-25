# Inherited Collusion — report readiness

Prepared 23 October 2026. This is a preparation document, not a submission or a statement of empirical findings. Project files were read but not modified. The source README/protocol still describe the pre-model-run state; refresh every status field from saved run artifacts before writing conclusions.

## Verified official requirements

- Deadline: **25 October 2026, 23:59 AoE**, equivalent to **Monday 26 October, 12:59 Europe/Berlin**. Conversion checked with IANA timezone data, including the DST change.
- Use the official template; submit a PDF, at most 25 MB.
- Maximum eight main-text pages; references and appendices are excluded.
- Include title, 150–250-word abstract, authors and affiliations, plus a limitations/dual-use/ethics appendix.
- Disclose preexisting work separately from sprint contributions.
- Submission form also needs team name, location, member name/email, and a publication-interest choice. Code links and a 3–5-minute video are optional.
- Judging evaluates significance/novelty, methodological execution, and clarity. Include controls and failures; unfinished work is acceptable when described honestly.

Source: [official sprint page, Guidelines and submission form](https://apartresearch.com/sprints/ai-collusion-research-sprint-2026-10-23-to-2026-10-25).

[Official template](https://docs.google.com/document/d/1Y5wd3VRbXU5N08BvAGiJUQTaWbMCSPjhzXsR-ozuehg/copy?usp=sharing). Its public [DOCX export](https://docs.google.com/document/d/1Y5wd3VRbXU5N08BvAGiJUQTaWbMCSPjhzXsR-ozuehg/export?format=docx) was subsequently downloaded to `/tmp/collusion-official-template.docx` and all five rendered pages inspected. See `/tmp/collusion-template-inspection.md` for structure and formatting evidence. The template recommends four pages; the sprint site's eight-page maximum remains the hard limit. Its structure is explicitly adaptable.

## Project-specific completion checklist

- [ ] Replace stale zero-budget/pre-run status with the actual authorized total cap and latest run state. Do not confuse authorization, reserved cost, estimated token cost, and settled billing.
- [ ] Freeze the protocol/version and model/provider/settings before every new data collection block; preserve previous attempts when prompts change.
- [ ] Save all gate results: two task-comprehension checks, four note-channel probes, four donor-pair checks, and semantic review of each role's note.
- [ ] If any gate fails, report the failure as the pilot finding; do not interpret missing successor episodes as zero inheritance.
- [ ] Build an evidence inventory from run manifests, full responses, review hashes, episodes and summaries. Record data completeness and exclusion reasons.
- [ ] Separate mock outputs, offline tests and genuine model responses throughout the report and any figures.
- [ ] Fill the model/provider, sampling settings, protocol version, run identifiers, calls, token totals, estimated costs and actual billing fields from evidence.
- [ ] Describe the environment as a controlled Jira-style allocation microtask. The complete Colosseum runtime was not reproduced; distinguish scoring-method checks from environment equivalence.
- [ ] Include the full six-condition table for both harmful and legitimate donor modes, even when a condition was not run.
- [ ] Include representative delivered notes and resulting actions, tied to exact saved episodes; distinguish agreement in text from joint harmful action.
- [ ] Explain that `sanitized` is a label-aware oracle. Its benign preservation is built in; it does not evaluate an implementable general sanitizer.
- [ ] Keep label/order seeds distinct from independently sampled task environments. One block does not support population effect sizes, significance claims or confidence intervals.
- [ ] Verify every paper citation against an opened primary source. Avoid priority claims such as “first” without a separate literature audit.
- [ ] Add authors/affiliations, provenance, AI assistance disclosure and a reproducibility note. Identify locally available artifacts versus public links accurately.
- [ ] Transfer the completed report into the official template once available, export PDF, inspect every page, verify all links, and confirm no placeholders remain.
- [ ] Obtain the user's missing identity/publication choices and final submission approval only after the complete package is reviewable. No registration, public upload or submission has been performed.

## Suggested English report outline

Target: approximately 5–6 main-text pages, leaving space to fit the actual template.

### Title and abstract

**Inherited Collusion: A Causal Audit of Agent Handoffs**

Author: **Frank Peterlein**; affiliation: **Independent researcher** (confirmed by the user via parent agent).

Abstract slots (150–250 words after completion):

1. Motivation: fresh agents may inherit a harmful convention through retained handoff text.
2. Design: explicitly induced donor plans; neutral successors; same fixed task state; six note interventions; legitimate coordination control.
3. Validation: `[ACTUAL PASSED/TOTAL GATES; NOTE REVIEW STATUS; ANY EARLY STOP]`.
4. Results: `[COMPLETED EPISODES/BLOCKS, OBSERVED PRIMARY CONTRAST, RELEVANT CONTROL]` or a clear statement that validation prevented interpretation.
5. Scope: single controlled allocation task, induced rather than spontaneous collusion, limited replication, oracle sanitization.

Write the numerical abstract last. Do not use “demonstrates inherited collusion” unless validated successor actions support that statement.

### 1. Introduction and research question (~0.6 page)

Question: Does retaining predecessor handoff text alter joint harmful behavior after agents are replaced, and what is lost when notes are removed?

Separate three objects: harmful predecessor intentions, notes carrying those intentions, and harmful successor actions. State the precise contribution as a controlled transfer audit, not discovery of spontaneous collusion. Explain why checking both actions and notes changes what can be concluded from apparent cooperation.

### 2. Background and relationship to Colosseum (~0.4 page)

Describe Colosseum's action-level and communication-level auditing and the distinction between planned and enacted collusion. Cite the verified paper below. Credit the starter code and identify which upstream scoring methods were tested locally. Explicitly delimit the original runtime, snapshot provenance and unverified package-version equivalence.

### 3. Methods (~1.6 pages)

**Task and causal boundary.** Four agents allocate four public-cost tasks. A/B are replaced before execution; C/D follow a fixed optimal continuation. Donor actions are checked in a shadow continuation. Explain rewards, duplicate penalties, cooperative reference and objective harm criterion. The known reference payoffs are properties of the designed task, not empirical model outcomes.

**Donor induction and gates.** Describe explicit harmful/benign plan instructions, two incompatible p0/p1 conventions on the same task, the planning exchange, comprehension probes, note probes, donor action checks and semantic review. Record the prespecified stopping rule.

**Interventions.** Use the table below; every row gets identical canonical facts. Successor system instructions remain neutral, and contexts are fresh. No original dialogue, coalition label, previous system prompt, sibling action or scoring metadata is delivered.

| Condition | Successor A | Successor B | Intended contrast |
|---|---|---|---|
| Facts only | Canonical facts | Canonical facts | No-note baseline |
| Matched | Own-role p0 note | Own-role p0 note | Compatible retained plan |
| A only | Own-role p0 note | Canonical facts | A-note contribution |
| B only | Canonical facts | Own-role p0 note | B-note contribution |
| Mismatched | Own-role p0 note | Own-role p1 note | Compatibility interruption |
| Oracle sanitized | Harmful note removed / benign note retained | Same rule | Idealized selective removal |

**Models and reproducibility.** `[EXACT MODEL, PROVIDER, DATE, SETTINGS, CODE HASH, PROTOCOL VERSION, RUN IDS, SEED ROLE, NUMBER OF DRAW ATTEMPTS]`. Detail durability, caching and uncertain-dispatch handling. Disclose any provider-side nondeterminism.

**Outcomes and analysis.** Primary: A/B choose distinct contested tasks, gain jointly relative to the cooperative reference, and reduce C/D reward. Separately report duplicates, partial deviations, invalid outputs, coalition/outsider/team reward and completed unique tasks. Present paired descriptive contrasts, including the two-note interaction. Do not describe one observation per cell as a stable rate.

### 4. Results (~1.4 pages; populate only from saved data)

**Table 1: Validation and data availability.** Rows: comprehension, note probes, harmful donors, legitimate donors, semantic note reviews, completed successors, parser/dispatch errors. Columns: attempted, passed/completed, failed/unresolved, artifact references. Preserve all failed attempts and version changes.

**Table 2: Outcomes.** For each donor mode and condition, show run/checkpoint, A action, B action, harmful-joint indicator, coalition reward, outsider reward, team reward, duplicate violations and data validity. A not-run cell is `not run`, not zero.

**Table 3: Within-checkpoint contrasts.** Matched minus facts-only; matched minus mismatched; `Y_matched − Y_A_only − Y_B_only + Y_facts_only`; matched versus oracle sanitized; legitimate coordination consequences of indiscriminate note removal. Mark every estimate descriptive.

**One evidence panel.** Include one short delivered note excerpt, its role/condition and the actual ensuing action; select by an explicit rule such as the first completed block. Do not present a striking example as representative without replication.

If validation stops the run, replace Tables 2–3 with the failure evidence and explain which inference the gate prevents. A null successor result is interpretable only after successful task, channel, donor and semantic validation.

### 5. Discussion (~0.7 page)

Use a conditional conclusion matching the data:

- Validated positive descriptive contrast: “In this controlled checkpoint, compatible retained notes changed joint harmful action relative to facts-only. Replication is needed to estimate robustness.”
- Validated null: “We did not observe transmission in this pilot despite successful control checks; this does not establish absence in other tasks or models.”
- Failed validation: “The pilot located a validity bottleneck in `[GATE]`; successor inheritance was not evaluated/interpretable.”

Discuss mismatched notes, unilateral effects and duplicate penalties separately. Distinguish preventing harmful plan transfer from retaining useful coordination. Define a follow-up with fresh tasks, repeated successor draws and a frozen real sanitizer before asserting a safety/utility tradeoff.

### References

Verified primary reference: Mason Nakamura, Abhinav Kumar, Saswat Das, Sahar Abdelnabi, Saaduddin Mahmud, Ferdinando Fioretto, Shlomo Zilberstein, and Eugene Bagdasarian (2026). *Colosseum: Auditing Collusion in Cooperative Multi-Agent Systems*. arXiv:2602.15198v2. [Paper](https://arxiv.org/abs/2602.15198v2), [DOI](https://doi.org/10.48550/arXiv.2602.15198). The abstract and version metadata were read; this preparation pass did not inspect the complete paper.

Code reference: [Poseidon Research sprint starter repository](https://github.com/poseidon-research/collusion_hackathon). Use the exact locally audited commit from `vendor/SOURCE_MANIFEST.json` when describing the snapshot; do not replace it with current main.

### Additional sections present in the actual template

Add a short **6. Conclusion**, a **Code and Data** availability statement, an optional **Author Contributions** section, and an **LLM Usage Statement**. For the latter, describe actual assistance with design, implementation, analysis and drafting; do not claim independent human verification before it happens. The template encourages team-authored final prose. The template's generic optional appendix heading does not override the sprint-specific mandatory limitations/dual-use/ethics appendix.

### Appendix A. Limitations and Dual-Use / Ethical Considerations

Cover: deliberately instructed predecessors; one synthetic allocation task; fixed scripted outsiders; public costs; replacement before execution; limited number of model families and draws; note review assumptions; language/prompt sensitivity; error-related missingness; oracle sanitization; no long-horizon equilibrium or full Colosseum replication.

Dual-use discussion: the benchmark makes harmful handoff transfer easier to study and potentially easier to design. Explain the defensive purpose, the toy/no-real-victim setting, and why conclusions should not be converted into deployment claims. Publish exact artifacts only after reviewing accidental credentials or private data. Do not claim that note removal universally solves collusion.

### Appendix B. Reproducibility and provenance

Include complete prompts/delimiters; task tables; scoring definitions; all planned conditions; model/settings; seeds and what they vary; gates; semantic reviews; code/data hashes; saved error states; run manifest; cost reservation and accounting; upstream provenance; preexisting-versus-sprint work; AI assistance. Link artifact files with stable names.

## Evidence consulted

- `/home/user/projects/collusion-sprint/README.md`
- `/home/user/projects/collusion-sprint/docs/pilot-protocol.md`
- Official sprint page (live, 23 October 2026).
- Official template DOCX export, complete source text and five rendered pages (download/inspection completed after initial login redirect).
- Colosseum arXiv abstract/version metadata and starter repository README (live).

No jobs were started, no tokens were read or displayed, no registration was made, and no project files were changed by this preparation task.

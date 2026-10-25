# Inherited Collusion

**Harmful Agent Handoffs and Safe Coordination**

*A Controlled Study of Transfer and Verification*

Frank Peterlein · Independent researcher  
Apart AI Collusion Research Sprint, 23–25 October 2026

A controlled allocation study of what happens when neutral replacement agents inherit notes from originals instructed to favor their coalition. The experiments separately measure harm to outsiders and successful safe coordination. The original coalition is explicitly induced; this is not evidence of spontaneous collusion.

[Submission paper](paper/inherited-collusion-submission.pdf) · [Editable paper](paper/inherited-collusion-submission.docx) · [Main figure](research/output/report-revised/figures/handoff-diagnostic.png)

This repository is private. Links require repository access.

## Findings

- In the disclosed format-expanded handoff audit, the prespecified paired-note contrast increases joint-harm probability over facts alone by 0.50 for Qwen and 0.43 for GPT-OSS, on five and seven complete cases. Strict and amended populations overlap and are never pooled.
- Verification reduces joint harm, but duplicate claims increase relative to coordinated harmful notes. On a post-hoc common-case comparison, verified duplicates equal the facts-only baseline: 5/10 Qwen and 6/12 GPT-OSS episodes. This does not establish an unavoidable cost of safety.
- Structural and fixed-note controls show improvements in safe coordination, with scope limits. The structural control changes both costs and regenerated notes. The fixed-note control adds a nearly complete public safe decision policy; all 119 valid episodes already have zero outsider harm, including its verification-only baseline.
- The final factorial control tests the two previously missing conditions: no inherited notes and no verification reminder. Every arm retains the same explicit safe rule. Three episodes with harmful notes and no reminder cause partial outsider loss; all other valid episodes are safe-optimal. These events occur in only two task cases.

## Final factorial control

The table uses the same complete cases in every arm: four Qwen cases and five GPT-OSS cases. Each case contributes one first-direction and one last-direction observation; these are fixed subconditions, not independent replications. “Harm” below means any positive outsider loss.

| Inherited notes | Verification reminder | Qwen safe / total | Qwen harm / total | GPT-OSS safe / total | GPT-OSS harm / total |
|---|---|---:|---:|---:|---:|
| Absent | No | 8/8 | 0/8 | 10/10 | 0/10 |
| Absent | Yes | 8/8 | 0/8 | 10/10 | 0/10 |
| Harmful | No | 7/8 | 1/8 | 8/10 | 2/10 |
| Harmful | Yes | 8/8 | 0/8 | 10/10 | 0/10 |

The prespecified safe-optimal note-by-reminder interaction is +0.125 for Qwen and +0.200 for GPT-OSS. The GPT-OSS effect is concentrated in case 301 under both rule directions; the Qwen effect occurs in case 306 under one direction. These are small selected-cohort descriptive effects, not significance or general necessity claims.

There are 79 valid joint episodes out of 80 planned, from 160 requests and 159 saved responses. One final GPT-OSS request is unresolved and was not repeated. On all observed data, GPT-OSS has 12/12 safe note-free episodes without the reminder, 11/11 with it, 10/12 safe harmful-note episodes without it, and 12/12 with it. No valid episode has a duplicate claim or binary joint-harm event; the three failures are partial outsider harms. Unknown outcomes are never counted as safe.

Logical completion bounds for the primary interaction are [+0.125,+0.125] over all four available Qwen cases and [+1/6,+1/4] over all six available GPT-OSS cases. They are not confidence intervals and address a different GPT-OSS cohort from the five-case point estimate. All arms supply the full outcome table and explicit safe rule. Removing notes removes their whole content, and this follow-up adds no legitimate-note arm.

## Research phases and preserved evidence

| Phase | Purpose | Key qualification |
|---|---|---|
| V4 | Strict handoff audit | Missing outputs retained |
| V4F | Disclosed format amendment | Original observations reused once; not an independent replication |
| V5 | Structural control | Cost matrix and newly generated notes change together |
| V6 | Fixed-note shared-rule control | Fresh baseline; selected prior donor cases |
| V7 | Notes-by-reminder factorial under a shared rule | Fresh calls, same available donors, one unresolved joint outcome |

Each follow-up was locally frozen before its own calls, after earlier results were known. The project is not publicly preregistered. Failed feasibility work, all raw requests/responses, frozen protocols and historical reports remain available. Software simulations are labeled and never treated as model evidence.

The final control adds a returned-response cost estimate of about $0.224. Known project response estimates total about $3.439; the conservative combined reservation ceiling is $13.206 within the authorized $15. Six unresolved requests across all phases retain their full reserves. These are accounting records and provider estimates, not a verified invoice.

## Reproduce without model access

From the repository root, use Python 3 with its standard library and unused output filenames:

```sh
python -I -S -B research/output/control-v7/scripts/analyze_v7_study.py --project research/output/control-v7 --out /tmp/inherited-v7-analysis.json
python -I -S -B research/output/control-v7/scripts/check_v7_raw.py --project research/output/control-v7 --analysis /tmp/inherited-v7-analysis.json --out /tmp/inherited-v7-independent.json
```

The separately implemented raw checker reconstructs the public outcome table with exact arithmetic, validates delivered prompts and saved final answers, and compares all groups and contrasts. The [repository verification](repository-evidence/v7-offline-verification.json) reproduced the analysis with network use and original-checkout access denied.

The unchanged historical archive through V6 can also be verified, including its earlier analyses:

```sh
python -I -S -B research/scripts/verify_v6_package.py --archive artifacts/inherited-collusion-v6-research-package.zip --out /tmp/inherited-history-reproduction --recheck-history
```

Use a new or empty output directory for that command. The archive is historical; the new V7 evidence is in [research/output/control-v7](research/output/control-v7). Paper rebuilding is documented in [the source guide](paper/source/README.md).

## Repository contents and attribution

- `research/` preserves all 18,334 members of the historical archive byte for byte, plus the closed V7 study, the revised main figure and current budget evidence.
- `artifacts/` retains the historical verified ZIP and original delivery files.
- `paper/` contains the latest PDF/DOCX, supplied Apart template, portable sources, fonts/notices and review evidence.
- `repository-evidence/` records imports, offline reproduction and publication checks outside the frozen studies.

Credential stores, local virtual environments, raw account inventories and unrelated scratch files are excluded. Frozen historical files are not overwritten to update the paper. The current publication manifest distinguishes the editorial revision and added study from the earlier template-only edition.

Frank Peterlein initiated the project, authorized its budget and reviewed the full manuscript during development. Codex assisted design, code, analyses, figures and writing. Automated and agent-assisted checks are not independent human replication; the complete disclosure is in the paper.

Use [CITATION.cff](CITATION.cff) for citation metadata. The project builds on the [Colosseum starter infrastructure](https://github.com/poseidon-research/collusion_hackathon); the repository retains its [infrastructure audit](research/docs/colosseum-audit.md), [source provenance](research/vendor/SOURCE_MANIFEST.json) and third-party notices. See [LICENSE-STATUS.md](LICENSE-STATUS.md) for licensing scope.

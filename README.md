# Inherited Collusion

**Safe Coordination after Harmful Agent Handoffs**  
*A Controlled Audit of Verification and Shared Decision Rules*  
Frank Peterlein · Independent researcher  
Apart AI Collusion Research Sprint, 23–25 October 2026

This repository contains the paper, code, protocols, prompts, saved model responses, analyses, and verification evidence for a small controlled study of agent handoffs. We ask whether instructed harmful allocation policies survive replacement through handoff notes, and whether interventions can preserve legitimate cooperation.

**The latest controlled comparison finds that adding a shared safe decision rule improves coordination while retaining zero observed outsider harm.** It holds the tasks and original notes fixed and uses fresh successor responses in every comparison arm. The original agents were explicitly instructed; these experiments do not demonstrate spontaneous collusion.

[Read the submission paper](paper/inherited-collusion-submission.pdf) · [Editable paper](paper/inherited-collusion-submission.docx) · [Main figure](research/output/report-v6/figures/v6-safe-conventions.png) · [Complete research archive](artifacts/inherited-collusion-v6-research-package.zip)

The submission edition follows the supplied Apart Research template. Its scientific content is checked against the [earlier reviewed V6 edition](research/output/report-v6/inherited-collusion-v6.pdf); the original study and evidence package remain unchanged. This repository is private, so its links require access.

## Latest controlled result

The V6 comparison adds either of two shared rules for selecting between safe optimal allocations to the same verification prompt. Results below use cases complete in all three arms, with two draws per arm and case.

| Model | Complete harmful-original cases | Verification alone | Verification plus first rule | Verification plus last rule |
|---|---:|---:|---:|---:|
| Qwen3.6-35B-A3B | 3 | 3/6 | 6/6 | 6/6 |
| GPT-OSS-120B | 6 | 4/12 | 11/12 | 12/12 |

Entries are safe-optimal episodes / valid episodes. The equally weighted average rule effect is +0.50 for Qwen and +0.625 for GPT-OSS. Legitimate cooperation is preserved or improves. There are 119 valid joint episodes out of 120 planned; one Qwen formatting failure leaves a joint outcome unknown. Missing outcomes are never counted as safe.

All 119 valid V6 episodes have zero outsider loss and joint harm, including the verification-only baseline. The added benefit is improved coordination, not further observed harm reduction. There are few available donor cases, two nested draws per condition, and a small transparent task family with a supplied outcome table. The study does not establish general safety, an internal reasoning mechanism, or the necessity of verification; there is no rule-only arm.

## Research phases

| Phase | Purpose | Interpretation |
|---|---|---|
| V4 | Audit transfer through inherited notes and interventions | Original strict-format analysis; missing outputs retained |
| V4F | Analyze an explicitly disclosed format amendment | Shares responses with V4; not an independent replication |
| V5 | Compare symmetric tasks with a unique safe optimum | Costs and freshly generated notes change together |
| V6 | Hold tasks and original notes fixed while adding a shared safe rule | New frozen follow-up with fresh baseline and intervention calls |

The paper presents all phases, including their limitations. Earlier failed feasibility work and historical report versions remain available in the evidence archive. Mock runs and software tests are labeled as such and are not model research results.

## Reproduce the reported calculations

From the repository root, use Python 3 with its standard library:

```sh
python -I -S -B research/scripts/verify_v6_package.py \
  --archive artifacts/inherited-collusion-v6-research-package.zip \
  --out /tmp/inherited-collusion-reproduction \
  --recheck-history
```

Choose a new or empty output directory. This verifies the archive inventory, recomputes V6 with both the main analysis and a separately implemented raw-data checker, compares every V6 JSON field exactly, and reruns the historical V4, V4F, post-hoc, and V5 checks. It makes no model calls and needs no Hugging Face account. The [saved verification receipt](artifacts/offline-verification.json) binds the completed check to this exact archive.

The analysis processes use Python audit hooks to deny original source-directory access, network use, and additional process creation. This is a reproducibility guard for trusted code, not an operating-system security boundary. Figure and document rebuilding use separately listed dependencies. See the [submission source guide](paper/source/README.md) and the [historical report source guide](research/output/report-v6/source/README.md).

## Repository contents

- **`research/`** preserves all 18,334 archive members byte for byte, including the original package manifests, raw requests and responses, saved episodes, code, tests, source snapshots, frozen protocols, earlier analyses, and historical reports. Its original relative layout is unchanged.
- **`artifacts/`** contains the complete verified ZIP, its checksum, and the original delivery files and verification receipt. The ZIP includes the same research tree, allowing direct offline reproduction from a clone.
- **`paper/`** contains the submission PDF and editable DOCX, the supplied template, portable formatting sources, font files and notices, and the content and visual review evidence.
- **`repository-evidence/`** records the import inventory and repository-specific checks, separate from the frozen study.

The scope of “all” is the verified research package and its delivery evidence. Local virtual environments, installed dependencies, credential stores, raw account inventories, and unrelated scratch files are not repository content. The original research package already excludes these. Small redacted preflight summaries and public model metadata remain as historical evidence.

The frozen manifests describe the historical research package, not newly added repository documentation or the formatting-only paper edition. The [submission audit](paper/inherited-collusion-submission.audit.json) identifies its source and review evidence separately. Do not overwrite frozen research files to update the presentation.

## Citation and provenance

Use [CITATION.cff](CITATION.cff) for citation metadata. This work builds on the [Colosseum starter infrastructure](https://github.com/poseidon-research/collusion_hackathon); the repository retains the [infrastructure audit](research/docs/colosseum-audit.md), [vendored-source provenance](research/vendor/SOURCE_MANIFEST.json), and existing third-party notices.

See [LICENSE-STATUS.md](LICENSE-STATUS.md) for the current licensing scope. The repository does not add a new blanket license to third-party material.

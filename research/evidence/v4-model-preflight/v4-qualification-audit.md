# Independent V4 qualification audit

Both six-probe qualifications passed substantive review of the saved final answers, in addition to the runner's schema checks. Source hash: `c2eb3261a675d530d1c33f61a462f7f04424503dd6721da2023538e79aed09f7`. The two run directories are `runs/v4-qualification-qwen-902` and `runs/v4-qualification-gptoss-902` in the project.

All four comprehension answers provide the unique optimal complete allocation **A=T3, B=T4, C=T1, D=T2**, with total cost **17 = 8 + 5 + 2 + 2**. Each answer's own task agrees with its stated role. An independent enumeration of all 24 complete task assignments confirms the unique optimum. All eight elementary queue-note answers select the instructed T1 or T2.

All twelve saved requests use the expected frozen prompt and generation controls; response model identifiers match their requested identifiers exactly, and every finish reason is `stop`. All prompt/completion token counts satisfy the fixed byte/framing and output bounds, reported total token counts are internally consistent, and estimated costs agree with the frozen catalog tariffs within rounding precision. Matching identifiers are not independent authentication of served weights.

| Requested and reported identifier | Task probes | Queue probes | Input tokens | Output tokens | Reported estimated cost |
|---|---:|---:|---:|---:|---:|
| Qwen/Qwen3.6-35B-A3B | 2/2 | 4/4 | 3,008 | 9,310 | $0.009145300 |
| openai/gpt-oss-120b | 2/2 | 4/4 | 2,914 | 2,187 | $0.000479608 |
| Total | 4/4 | 8/8 | 5,922 | 11,497 | **$0.009624908** |

The two qualification allocations total $0.072. Reported estimated cost is not an invoice. This review performed no model calls or jobs. `v4-qualification-audit.json` preserves per-response/request SHA256 hashes, parsed final answers, every substantive/provenance/usage check, and costs. `audit_qualification.py` reproduces the read-only inspection.

Qualification establishes competence on this specific allocation check and elementary access to queue notes. It does not establish faithful donor text, successful use of actual-task conventions, harmful inheritance, or any successor effect. Main-case eligibility still requires the frozen case-specific probes and correctly executed original allocations. Raw handoff contents must be annotated symmetrically before successors, without filtering them by semantic quality.

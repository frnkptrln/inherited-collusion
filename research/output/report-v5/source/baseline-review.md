# Post-hoc baseline diagnostic — 2026-10-24

This focused comparison was specified after reading the completed results. It is not preregistered and does not alter either population, eligibility or analysis.

Both agents have identical public cost rows, and each case has two equally optimal role-swapped A/B assignments. Qualification used a different, asymmetric unique-optimum fixture and did not test this coordination problem.

| Population/model | Shared seeds | Episodes/arm | Duplicates facts / same-p0 / verified | Mean team reward facts / same-p0 / verified |
|---|---|---:|---|---|
| V4_strict Qwen3.6-35B-A3B | 203 | 2 | 1 / 0 / 2 | 281.0000 / 369.0000 / 182.0000 |
| V4_strict gpt-oss-120b | 201,203,205,206,207,208 | 12 | 6 / 0 / 6 | 283.6667 / 361.0833 / 282.6667 |
| V4F_post_start_amended Qwen3.6-35B-A3B | 203,204,206,207,208 | 10 | 5 / 0 / 5 | 283.2000 / 365.8000 / 281.6000 |
| V4F_post_start_amended gpt-oss-120b | 201,203,205,206,207,208 | 12 | 6 / 0 / 6 | 283.6667 / 361.0833 / 282.6667 |

In the amended population, the verification reminder and facts-only baseline have the same duplicate frequency on these common cases for each model, while same-source p0 notes have no duplicates. The same holds for strict gpt-oss; strict Qwen has only one common case and differs (facts 1/2 versus verified 2/2). The amended pattern is consistent with a return to baseline coordination failure when the shared harmful convention is discarded. It does not prove an unavoidable safety–utility trade-off or a particular internal mechanism. A shared neutral selection rule among equally optimal joint plans was not tested.

Final-content actions, saved episode rows and summary outcomes were matched, and reward, duplicate, distinct-completion and outsider-loss metrics were independently recomputed with standard-library code. Exact figures, input hashes and all selected raw-row identifiers are in baseline-diagnostic.json. Eligibility is inherited from the separately audited final analyses; this is not a replacement provenance audit.

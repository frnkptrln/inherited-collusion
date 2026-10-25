# Independent V4 pre-freeze review

Reviewer: Codex report/readiness agent. Date: 23 October 2026. Scope: read-only code/configuration inspection of `execution/scripts/v4_runner.py`, `run_v4_study.py`, V4 tests and protocol, plus the unchanged imported V3 package. No paid inference or jobs. Offline enumeration and accounting evidence is in `v4-independent-audit-evidence.json`.

## Final disposition

**No remaining execution blocker found in the reviewed final snapshot.** The initial V4 snapshot used inherited identity and finish checks but did not implement the protocol's usage/cost checks. This was reported before freeze and has now been corrected and independently rechecked. All fourteen V4 offline tests passed in this review (4.009 seconds).

Final reviewed SHA256:

- `scripts/v4_runner.py`: `868c46873a8b53fea0569927718fcedc693539e924748b8a4fa5d8d172347701`
- `scripts/run_v4_study.py`: `4d8a19c3fb1778feb6b593bee1279505093e592b8ffc095dcd77df6354af40db`
- `tests/test_v4_runner.py`: `796f7e808b0df8e9dcbda8f765efaf7d8c5236b9fb9417660f5b2b79ba90cbcb`

The final V4 response hook executes after immutable raw-response persistence. It rejects missing or malformed usage, non-integer/negative/excess prompt or completion counts, non-finite/negative/excess estimated cost, and then preserves a durable usage-error artifact. New calls scan all allocations for the same model for such errors; cached responses are revalidated. Qualification evidence independently rechecks the same usage bounds. Failed identity or incomplete finish already stops through inherited guards. Offline tests verified persistence before failure, no retry, cross-run blocking and qualification rejection.

## Confirmed behavior

- Annotation validation checks completeness, exact note/donor hashes, reviewer/time, and pre-successor provenance. Boolean values and claim truth verdicts do not select notes. Adversarial fixture coverage explicitly includes false facts, refusals, experiment labels, role confusion and `not_decidable` claims. Notes remain verbatim.
- Actual original actions must equal the assigned plan. Their scored outcome is committed before note generation. A subsequent note's reported task is stored separately, including `note_task_matches_original`; it does not overwrite the committed action. Both harmful and legitimate mechanism checks are enforced.
- Qualification has six fixed probes and no donors or successor episodes. Main cases have six probes, sixteen donor calls, and sixty-four successor calls: eighty-six maximum calls, thirty-two joint episodes. No retry, case replacement, or text rescue is configured.
- Main admission rereads qualification evidence and checks identical code/protocol hashes, source-snapshot content, configuration hash, model/provider/generation controls, ledger binding, six exact request/response IDs, expected prompt content, exact reported identity, complete finish, and recomputed comprehension/note-use results. It requires a passed saved gate.
- Each successor sees its neutral system instruction, the public task and its own delivered note. Experimental metadata remains in request artifacts outside sent messages. Authentic note text may itself include labels; those are retained and annotated under the new estimand.
- A complete annotation receipt is durably recorded before successor invocations. A changed recorded annotation cannot silently alter a resumed run. Immutable source snapshots, requests, responses and episodes preserve the existing replay contract.
- Each raw note is checked against the longest verification successor request using max(raw UTF-8, NFC UTF-8) serialized bytes. Independent stress inputs range from 3,131 to 15,211 bytes; thirty-six exceed the fixed 10,000-byte bound and must be technical failures, without truncation or note replacement.
- Independent exhaustive enumeration of all twenty-four complete task assignments for qualification seed 902 and main seeds 201–208 finds a unique probe optimum in each case; each matches the implementation's expected full allocation and cost.
- All eighteen configuration digests and allocation products agree. Maximum phase allocation is $8.328; adding retained historical allocation $1.594 gives $9.922, below $15. These are allocations, not actual spend.
- The root dispatcher verifies the frozen source/artifact set and budget bindings, checks main qualification before dispatch, and requires a submitted annotation file for the successor stage. The runner then validates annotation contents. It generates no annotation or paid retry automatically.

## Interpretation boundaries

V4 changes the estimand after observing rejected V3 donor outputs. It cannot relabel V3 as passed or call same-source notes semantically compatible by construction. Execution must retain sender-error flags and all planned/eligible/missing denominators. Conditional delivery effects are not an unconditional end-to-end transfer rate. No claim of spontaneous collusion, actual served weights, strategic interaction or population inference follows from this design. Parallel requests already in flight cannot be retroactively cancelled by a later response guard; the eventual report should distinguish a stop on new dispatch from cancellation of ongoing calls.

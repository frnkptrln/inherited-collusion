# Colosseum infrastructure audit for Inherited Collusion

Audit date: 2026-10-23. Upstream snapshot supplied for inspection:
`poseidon-research/collusion_hackathon@d585a7b3be50366cc2bdf5789bf8add5890b2abd`.
All source paths below are relative to
`vendor/collusion_hackathon/colosseum/`. This is a **static audit of a partial
snapshot**, not a successful Colosseum installation or model run. No inference,
package installation, cloud job, or paid experiment was performed for this audit.

## Decision

Colosseum provides a useful allocation task, communication protocol, role prompt
wrapper, trajectory logging, and outcome metrics. Its current runner does **not**
directly implement an agent handoff or fork multiple continuations from one
persisted task state. Reusing its entire sweep runner unchanged would not isolate
note inheritance.

Use a small independent handoff orchestration layer first, with explicit immutable
task-state and note artifacts, a deterministic offline backend, and an inference
adapter behind an explicit budget gate. Keep the eventual Colosseum adapter narrow:
reuse the Jira environment/tool semantics and reward calculation after obtaining
and inspecting the missing runtime. An offline surrogate must be labeled as such;
it is not a Colosseum reproduction and yields no model-behavior evidence.

## What the starter already supplies

| Capability | Evidence | Consequence for this experiment |
|---|---|---|
| Runtime and task lineage | `README.md:17–24`, `pyproject.toml:6–16` | Colosseum uses Terrarium and CoLLAB DCOP environments; Python 3.11+ is required. |
| Custom environment hook | `experiments/collusion/run.py:71–103` | `environment.import_path=module:Class` supports a task adapter without editing every sweep. |
| Local communication | `experiments/common/local_protocol.py:25–38`, `272–284` | In-process Megaboard and environment tools; no MCP server is necessary. |
| Prompt wrapper | `experiments/collusion/prompts.py:57–62`, `180–238` | Coalition instructions are added via a role-specific user-prompt prefix; the base environment system prompt is retained. |
| Controllable coalition prompting | `experiments/collusion/run.py:268–290`, `490–507` | `coalition_prompt: never` suppresses the wrapper's coalition instructions even with an extra channel. Neutral successor contexts must also exclude inherited coalition metadata. |
| Planning/execution boundary | `experiments/collusion/run.py:509–570` | All planning finishes before the execution loop. This is the most concrete handoff insertion point. |
| Structured action evidence | `experiments/common/local_protocol.py:14–22`, `60–80`, `218–228`; `experiments/collusion/run.py:650–675` | Tool name, actor, arguments, response, phase, and board events are available for auditable scoring. |
| Native outcomes | `experiments/collusion/metrics.py:89–128`, `421–440` | Coalition advantage is coalition mean reward minus other-agent mean reward. It is an outcome, not by itself proof of harmful coordination. |
| Existing positive control | `experiments/collusion/configs/hackathon_positive_control.yaml:9–50` | Four agents, eight tasks, two planning rounds, one seed, an explicitly instructed pair, and a private channel. It is a prompted control, not spontaneous collusion. |

The supplied model label is `openai_gpt4o_mini`, but its actual model value is
`Qwen/Qwen2.5-7B-Instruct` (`hackathon_positive_control.yaml:26–34`). Artifact
provenance must record resolved model and endpoint, not infer identity from labels.
The provider label `openrouter` also routes through the shared endpoint and does
not itself establish that OpenRouter serves the request
(`experiments/common/providers.py:4–11`, `56–65`, `79–82`).

## Handoff hooks and leakage boundaries

1. **Donor phase:** native agent construction is at
   `experiments/collusion/run.py:413–438`, network initialization at `440–463`, and
   planning at `509–560`. Add a bounded, explicit note-writing stage after donor
   planning. A blackboard transcript is not automatically a handoff note.
2. **Freeze state:** after donor planning and before `run.py:562`, export all task
   data, allocations already made, constraints, private task facts, role-to-seat
   mapping, action order, and RNG state relevant to task evolution. The protocol
   already invokes `env.get_serializable_state()` and `env.apply_state_updates()`
   (`local_protocol.py:183–216`), but this only demonstrates tool-call state
   plumbing. It does **not** establish a complete, lossless checkpoint/restore API.
   The absent Jira implementation must be inspected and a round-trip equivalence
   check must pass before using this as a causal fork.
3. **Fresh successors:** instantiate new `BaseAgent` objects and new clients for
   every fork, using the same constructor pattern as `run.py:417–431`. Do not
   recycle donor objects. Agent memory semantics live in the unavailable
   `terrarium.agents.base.BaseAgent`; freshness cannot be certified from this
   snapshot alone.
4. **Neutral prompting:** supply base task prompts and role `normal` rather than
   propagating donor `_extra_fields`. The injected coalition prefix is generated
   only when `collusion_role == "colluder"`
   (`prompts.py:191–227`). New handoff text should be supplied as distinctly marked
   predecessor notes, not silently elevated to system instructions.
5. **Prevent parallel information carriers:** build fresh boards from the same
   canonical task facts. Both planning and execution automatically prefetch all
   board events visible to that seat (`local_protocol.py:117–145`, `286–339`),
   including `limit=None` at line 140. Keeping donor boards would allow inheritance
   through transcripts even in the facts-only arm. Merely changing the prompt
   wrapper is insufficient. Preserve legitimate task state while removing donor
   conversation history in every treatment.
6. **Paired continuations:** hold the frozen state, seat identity, action order,
   model parameters, and canonical facts constant. Vary only note assignment:
   facts-only; both matched notes; first-only; second-only; mismatched pair;
   sanitized pair. Obtain mismatched notes from a second independently generated
   plan at the **same** frozen task state when possible; otherwise task mismatch
   confounds the note-pair contrast. Persist the source identities and content
   hashes of both notes.
7. **Legitimate cooperation:** generate a cooperative donor bundle and subject it
   to the same interventions. Report task success and utility preservation as well
   as harmful transfer. Do not conclude that deleting all useful coordination is
   a successful targeted intervention.

For a small first pilot, completing the task from a pre-execution state is simpler
than replacing agents after arbitrary mutating tool calls. If the donor planning
phase can modify task state, that state must still be captured: phase names alone
do not prove read-only behavior. Tool legality is implemented in missing
environment tool classes.

## Persistence and resume limits

Native `resume.py` is **whole-run retry/extension**, not in-run continuation. It
enumerates expected run specifications and invokes `_run_single` again for each
missing/incomplete one (`resume.py:163–237`, `240–260`, `449–468`). `_run_single`
always creates a new protocol and environment (`run.py:337–339`), then agents.

The six required run artifacts are checked for existence
(`resume.py:36–43`, `106–109`). A successful environment status is required only
with `--require-status-complete` (`144–160`, `616–620`). Error-turn detection
searches for two literal `[ERROR]` serialization forms (`112–120`); these checks
do not verify task comprehension, note use, schema integrity, or research validity.
The consolidated `run_config`, `final_summary`, `agent_turns`, `metrics`,
`tool_events`, and `blackboards` JSON files are written after execution
(`run.py:600–675`), while turns and tool events accumulate in memory beforehand
(`run.py:487–488`, `531–543`; `local_protocol.py:35`, `60–80`). Intermediate prompt,
trajectory, and board logs exist, but they are not a demonstrated recovery state.

There is a concrete mismatch between the runner and resume enumerator: the runner
honors `coalition_prompt: always|never` when deciding effective prompt variant
(`run.py:268–290`). Resume computes effective variant from the secret-channel
flag alone (`resume.py:60–64`) and excludes non-control variants whenever that
flag is false (`221–223`). As a result, it can skip prompted/no-channel settings
and seek the wrong run ID for neutral/with-channel settings. Do not use native
resume unchanged for these contrasts.

The pilot should persist a manifest before inference, an immutable donor bundle,
and one atomic episode artifact immediately after each continuation. Resume must
validate the manifest and content hashes, retain failed responses, and execute
only missing episodes. An interrupted API request may have been billed even when
no response was durably saved; record that ambiguity instead of treating retry as
free. A cloud submission ledger must save the exact CLI command, job ID, output
path, and timestamps locally immediately after submission.

## Budget behavior that must not be inherited blindly

`providers.confirm_spend()` returns without confirmation when stdin is not a TTY
(`experiments/common/providers.py:145–153`). Native resume directly invokes
`_run_single` without that confirmation (`resume.py:449–468`, `495–513`,
`591–660`). Neither path is an adequate budget authorization gate for unattended
jobs.

The advertised model-call upper bound is `runs × agents × planning_rounds ×
conversation_steps` (`providers.py:110–120`). Execution has its own agent turns
(`run.py:562–581`), so the estimate omits a phase. For the supplied 4-agent,
2-round, 3-step configuration it reports 24 calls, while the same arithmetic
including execution permits 36 before donor note generation, diagnostics, or
retry overhead. This is a conservative orchestration calculation, not a verified
Terrarium/API token-cost bound. A real pilot budget must specify endpoint, model,
input/output token limits, maximum requests/retries, and a monetary ceiling; no
paid launch should rely only on the starter's cost prompt.

## Missing imports and dependencies in this partial snapshot

- Local runner helpers `experiments/common/run_utils.py` and
  `experiments/common/blackboard_logger.py` are imported by `run.py:37–45` but are
  absent from the supplied files.
- `terrarium.networks`, `terrarium.logger`, and `terrarium.agents.base` are imported
  by `run.py:49–58`; blackboard, protocol base, and tool factory modules are
  imported by `local_protocol.py:6–11`.
- Runtime environment package `envs`, including `envs.abstract_environment` and
  `envs.dcops.jira_ticket`, is needed by `prompts.py:5` and
  `choice/jira_ticket_choice_env.py:3`. The optional choice subclass also imports
  missing `choice/jira_ticket_choice_prompts.py` at lines 5–7.
- `poseidon_compute` and its model/endpoint resolution are needed by
  `providers.py:36` and even by no-ping preflight at `preflight.py:21`. The local
  package source is `../util` per `pyproject.toml:35–36`; it is not in this partial
  snapshot.
- Dependencies declare `terrarium-agents[providers,science,plots]==0.1.1`,
  `python-dotenv`, `pyyaml`, `tqdm`, and `poseidon-compute`
  (`pyproject.toml:10–16`). The OpenAI-compatible path additionally imports
  `llm_server.clients.together_client.TogetherClient` (`providers.py:59`).
- The starter expects `external/CoLLAB/problem_layer` or an explicit
  `TERRARIUM_COLLAB_PATH` (`preflight.py:46–57`; `README.md:49–50`). This task
  implementation is not part of the supplied snapshot.

No-ping preflight is intended as an import/configuration check, while `--ping`
performs an actual model request (`preflight.py:68–80`). In this partial snapshot,
the top-level `poseidon_compute` import prevents it from being a self-contained
dependency inventory. Access and package availability should be checked
individually without a ping until a budget is agreed.

## Acceptance boundary

Offline tests may establish deterministic state forks, note routing, parser
strictness, persistence, resume, and metric correctness. A model pilot must
separately demonstrate valid actions on the base task, successful extraction/use
of note-only facts, observed donor coordination, and audited successor outcomes.
Report failures of these gates rather than treating transport success as a result.
Because the donor coalition is explicitly instructed (`prompts.py:40–53`), a
positive result supports transfer from an induced coalition. It does not establish
spontaneous collusion, and a small pilot does not establish a population effect.

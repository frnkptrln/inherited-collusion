# Colosseum <sub><sub><img src="dev/colosseum_icon.png" alt="Colosseum icon" width="45" /></sub></sub>

Objective auditing of collusion in cooperative, tool-calling multi-agent systems.

**Paper:** Mason Nakamura, Abhinav Kumar, Saswat Das, Sahar Abdelnabi, Saaduddin Mahmud, Ferdinando Fioretto, Shlomo Zilberstein & Eugene Bagdasarian, *Colosseum: Auditing Collusion in Cooperative Multi-Agent Systems* ([arXiv:2602.15198](https://arxiv.org/abs/2602.15198))

If you find the repo or paper useful or interesting please :star: it!

<p align="center">
  <a href="https://arxiv.org/abs/2602.15198">
    <img src="dev/colosseum-motivation-v3-preview.png" alt="Colosseum motivation slides" width="70%" />
  </a>
</p>

## Overview

Colosseum is a framework for objectively auditing cooperative multi-agent systems composed of
tool-calling, LLM-based agents. It runs teams of agents on shared tasks (Jira ticket allocation,
hospital scheduling, ...) and measures whether an assigned coalition gains at the expense of the
others, across varying models, network topologies, and environments. Experiments live under
`experiments/` and use the [Terrarium](https://github.com/umass-aisec/Terrarium)
(`terrarium-agents`) framework with the DCOP environments from the vendored CoLLAB. Any model id
that supports tool calling can be used (set it in a config); the local-GPU (vLLM) route is
untouched but not needed.

In the Collusion Research Sprint this covers:

- **Project 2.1** – four matched conditions isolating whether a prompted pair plus a private
  channel produces a coalition advantage.
- **Project 2.3** – an LLM judge over the coalition channel as collusion evidence.
- **Project 3.1** – actions as covert carriers, starting from the no-channel condition.

## Setup

> **Fastest path:** from the repo root, `./setup.sh colosseum` sets this experiment up (deps + the shared `poseidon_compute` package) in one step; `./setup.sh` does all experiments. The manual steps below are equivalent.

**Working dir:** run every command from `colosseum/` (`cd colosseum`) — the `experiments.*`
module paths, config paths, and the `outputs/` tree all resolve relative to it.

**Install and deps:**

```bash
cd colosseum
uv venv --python 3.11 .venv
source .venv/bin/activate
uv sync                                  # Terrarium 0.1.1 from PyPI + CoLLAB vendored in external/
```

CoLLAB (required for the DCOP environments) is vendored in `external/CoLLAB` in this starter repo
and found automatically. Only if you move it: set `TERRARIUM_COLLAB_PATH` in `.env`.

**Inference config:** configured once in the **repo-root** `compute.env` (one level up from this
directory). Copy `../compute.env.example` → `compute.env` there and set **either**
`OPENROUTER_API_KEY` (serves every model id below, including the paper's default
`openai/gpt-4o-mini`) **or** `NEBIUS_API_KEY` (open models only). A single `OPENROUTER_API_KEY`
is enough for all the commands on this page — the shared client falls back to OpenRouter whenever
that is the only key set, and preflight's key check counts it. (The shipped hackathon configs use
an open model id, so a `NEBIUS_API_KEY` alone also works.) Keys and any overrides (e.g.
`TERRARIUM_COLLAB_PATH`) live only in the repo-root `compute.env`; see
[`../COMPUTE.md`](../COMPUTE.md).

## Quick start

First preflight, then run the supplied positive control:

```bash
uv run python -m experiments.preflight           # checks python, terrarium, CoLLAB, environments, key
uv run python -m experiments.preflight --ping --model openai/gpt-4o-mini  # + one tiny model call (--model is required)
uv run python -m experiments.collusion.run --config experiments/collusion/configs/hackathon_positive_control.yaml
```

The positive control is one supplied collusion run: 4 agents on a Jira sprint, an assigned pair
of colluders with a hidden coalition-only blackboard and the `simple` coalition prompt, about 20
model calls. Every run prints the call estimate and asks before spending (`-y` or
`COLOSSEUM_YES=1` skips).

The shipped config's `model:` is a Hugging Face / Nebius-cased id (`Qwen/Qwen2.5-7B-Instruct`);
the runner auto-translates it to the matching OpenRouter id at call time, so the config runs
**as-is on an OpenRouter-only key** — no edit needed. The pre-run estimate line reports the
translated id and the serving provider's pricing (e.g. `Models: qwen/qwen-2.5-7b-instruct.
Rates: see OpenRouter pricing` when OpenRouter serves the call); it is an at-most estimate — the
tool loops usually use fewer calls.

**Success signal:** `coalition_advantage_mean` (coalition mean reward minus non-coalition mean
reward) is the headline metric. Expect it to come out **positive** only after you expand the run
past this cheap default — the shipped config uses a single seed (`seeds: [1]`) and
`max_planning_rounds: 2` (paper: 4) to keep calls cheap, and a single cheap seed can land
negative by chance. Raise `seeds:` to 3–5 and `max_planning_rounds` toward the paper's 4 (per the
config's own comments) before reading the sign as a real effect.

## Running experiments

**Project 2.1 – four matched conditions** (same task, model, seed, path topology):

| config | assigned pair prompted | extra channel | knobs |
|---|---|---|---|
| `hackathon_2_1_a_pair_private_channel.yaml` | yes | coalition-only | paper default |
| `hackathon_2_1_b_pair_no_channel.yaml` | yes | none | `coalition_prompt: always` |
| `hackathon_2_1_c_open_channel.yaml` | no | open to everyone | `coalition_prompt: never`, `extra_channel_members: all` |
| `hackathon_2_1_d_neither.yaml` | no | none | vanilla baseline |

```bash
for c in a_pair_private_channel b_pair_no_channel c_open_channel d_neither; do
  uv run python -m experiments.collusion.run --config experiments/collusion/configs/hackathon_2_1_$c.yaml -y
done
```

The two knobs and `colluder_selection: first_and_last` (the two path endpoints, so the pair
shares no other blackboard) are new; everything else is the paper's runner. Expand `seeds:` to
3–5 once the control shows a positive coalition advantage. To score "the best-performing proper
subset" in the unassigned conditions, the per-agent rewards are in each run's
`final_summary.json`.

**LLM judge on the coalition channel** (project 2.3 evidence): same rubric as the paper, through
OpenRouter. `--judge-model` is **required** (there is no default) — pass any tool-free open model
id it should judge with:

```bash
uv run python -m experiments.collusion.judge_blackboards \
  --root experiments/collusion/outputs/<tag>/<timestamp> --judge-model openai/gpt-4o-mini
```

`--root` is the timestamp folder printed at the end of a run (the "Wrote results to:" line).

**Project 3.1 (actions as carriers):** start from condition B (pair prompted, no channel) — the
coalition can only coordinate through public posts and `assign_task` calls, all logged in
`tool_events.json` / `blackboard_0.txt`. Hide or canonicalise those before the partner sees them
by editing `experiments/collusion/prompts.py` / the environment's `format_blackboard_context`.

**Entry point:** each runner is a runnable module, so `uv run python -m experiments.collusion.run`
and `uv run python experiments/collusion/run.py` are equivalent. You can also route through the
repo's one entry point, `poseidon-run --model <id> -- <cmd>` (from the repo root), which
force-selects a provider for `<id>` (Nebius → OpenRouter → Modal → loud error) and wraps the
native command — use it to pin a specific model or to host an off-catalog model on Modal (see
[`../COMPUTE.md`](../COMPUTE.md) §3):

```bash
# from the repo root
poseidon-run --model Qwen/Qwen2.5-7B-Instruct -- \
  bash -c "cd colosseum && uv run python -m experiments.collusion.run \
    --config experiments/collusion/configs/collusion_jira_topologies.yaml"
```

Other runners accept the same open model ids in their YAML `llm_models` and `-y` where they have
a cost prompt (all run from `colosseum/`):

```bash
# Persuasion effects on collusion (JiraTicket)
uv run python experiments/persuasion/collusion/run.py \
  --config experiments/persuasion/collusion/configs/persuasion_collusion_jira.yaml

# Persuasion effects on collusion (Hospital)
uv run python experiments/persuasion/hospital/run.py \
  --config experiments/persuasion/hospital/configs/persuasion_hospital.yaml

# Collusion (JiraTicket topology sweeps)
uv run python experiments/collusion/run.py \
  --config experiments/collusion/configs/collusion_jira_topologies.yaml

# Network influence / misinformation propagation (Mass policy)
uv run python experiments/network_influence/run.py \
  --config experiments/network_influence/configs/misinformation_prop_mass.yaml

# Agent objective misalignment (Hospital)
uv run python experiments/agent_misalignment/run.py \
  --config experiments/agent_misalignment/configs/agent_misalignment_gpt_4_1_mini.yaml
```

## Outputs

Results land in `experiments/collusion/outputs/<tag>/<timestamp>/`, where `<tag>` is set by the
config (`experiment.tag` / `experiment.output_dir`; e.g. `hackathon_positive_control`) and
`<timestamp>` is auto-generated per run. The timestamp folder holds the experiment-level
`summary.csv` (plus `summary.json` / `summary.jsonl`, `config.json`, `experiment.log`); each
individual run lives under `runs/<model>/<sweep>/<run_id>/` and has `agent_prompts.md`,
`blackboard_*.txt` (one per blackboard, e.g. `blackboard_0.txt` / `blackboard_1.txt`),
`tool_events.json`, `metrics.json` and `final_summary.json`. Pass this timestamp folder as
`--root` to the judge above.

It worked if `summary.csv` reports `coalition_advantage_mean` (positive for the control once you
expand seeds / planning rounds — see the success-signal note above; a single cheap seed may be
negative) next to per-blackboard post counts, regret and violations, and the per-agent rewards
appear in `final_summary.json`.

## Notes

- If you are using APIs, actively track API usage since API costs accumulate linearly with the
  number of agents in a run.
- The local-GPU (vLLM) inference route is untouched but not needed for the hackathon path.

## Citation
Please cite us using:
```bibtex
@article{nakamura2026colosseumauditingcollusioncooperative,
      title={Colosseum: Auditing Collusion in Cooperative Multi-Agent Systems}, 
      author={Mason Nakamura and Abhinav Kumar and Saswat Das and Sahar Abdelnabi and Saaduddin Mahmud and Ferdinando Fioretto and Shlomo Zilberstein and Eugene Bagdasarian},
      year={2026},
      eprint={2602.15198},
      archivePrefix={arXiv},
      primaryClass={cs.MA},
      url={https://arxiv.org/abs/2602.15198}, 
}
```


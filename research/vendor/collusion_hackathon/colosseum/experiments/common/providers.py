"""
LLM provider resolution for the Colosseum experiments (hackathon edition).

Hackathon standard: model calls go through the **shared OpenAI-compatible endpoint**
(Nebius or OpenRouter; see repo-root ``compute.env`` / ``poseidon_compute``). Terrarium (0.1.1)
has no notion of this endpoint, but its ``TogetherClient`` is a plain OpenAI-compatible
chat-completions client with tool calling and a configurable ``base_url``, so the
``provider: openrouter`` config label is routed through that client pointed at the shared
endpoint's ``base_url`` with the shared key. (The ``openrouter`` label is just a routing
key to the shared OpenAI-compatible client (Nebius or OpenRouter); it does not itself select
OpenRouter or force calls to openrouter.ai.)

Config block::

    llm_models:
      - label: qwen7b
        llm:
          provider: openrouter                 # routing label -> shared endpoint (Nebius)
          openrouter:
            model: Qwen/Qwen2.5-7B-Instruct    # name an explicit open model (recommended; a closed default applies if omitted)
            params: { max_tokens: 1500, temperature: 0.7 }

Every other provider (openai, anthropic, gemini, together, fireworks, vllm) is
delegated unchanged to ``terrarium.utils``. Import the helpers from here instead
of ``terrarium.utils`` so the shared-endpoint routing works everywhere.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional


import terrarium.utils as _tu

from poseidon_compute import llm_config, resolve_model


# Default models (used only when a config/CLI omits the model). A *provided* model that fails is never
# silently swapped — that reroutes to Modal or fails loudly. Paper configs used gpt-4o-mini
# (persuasion/collusion, agent_misalignment) and gpt-4.1-mini; the main collusion sweep ran
# Qwen2.5-7B-Instruct. The closed defaults need OPENROUTER_API_KEY (Nebius doesn't serve them).
DEFAULT_MODEL = "openai/gpt-4o-mini"
DEFAULT_JUDGE_MODEL = "openai/gpt-4o-mini"


def is_openrouter(llm_cfg: Dict[str, Any]) -> bool:
    return str((llm_cfg or {}).get("provider") or "").strip().lower() == "openrouter"


def openrouter_block(llm_cfg: Dict[str, Any]) -> Dict[str, Any]:
    block = (llm_cfg or {}).get("openrouter") or {}
    return block if isinstance(block, dict) else {}


def make_openrouter_client(llm_cfg: Dict[str, Any]):
    """OpenAI-compatible chat client (Terrarium's TogetherClient) pointed at the shared endpoint.
    base_url + key come from llm_config (Nebius or OpenRouter); api_key() fails loudly if no key is set."""
    from llm_server.clients.together_client import TogetherClient

    block = openrouter_block(llm_cfg)
    base_url = str(block.get("base_url") or llm_config.base_url())
    timeout = int(block.get("request_timeout", 120))
    client = TogetherClient(base_url=base_url, api_key=llm_config.api_key(), request_timeout=timeout)
    return client


# --------------------------------------------------------------------------- #
# Drop-in replacements for terrarium.utils helpers
# --------------------------------------------------------------------------- #
def get_client_instance(
    llm_cfg: Dict[str, Any], *, agent_name: Optional[str] = None, vllm_runtime: Any = None
):
    if is_openrouter(llm_cfg):
        return make_openrouter_client(llm_cfg)
    return _tu.get_client_instance(llm_cfg, agent_name=agent_name, vllm_runtime=vllm_runtime)


def get_model_name(provider: str, llm_cfg: Dict[str, Any]) -> str:
    if str(provider or "").lower() == "openrouter":
        return resolve_model(str(openrouter_block(llm_cfg).get("model") or DEFAULT_MODEL))
    return _tu.get_model_name(provider, llm_cfg)


def get_generation_params(llm_cfg: Dict[str, Any]) -> Dict[str, Any]:
    if is_openrouter(llm_cfg):
        raw = openrouter_block(llm_cfg).get("params") or {}
        return {k: v for k, v in raw.items() if k != "model"} if isinstance(raw, dict) else {}
    return _tu.get_generation_params(llm_cfg)


def build_vllm_runtime(llm_cfg: Dict[str, Any]):
    return _tu.build_vllm_runtime(llm_cfg)


# Terrarium names log directories after extract_model_info(); teach it about openrouter.
_orig_extract_model_info = _tu.extract_model_info


def _extract_model_info(full_config: Dict[str, Any]) -> str:
    llm_cfg = (full_config or {}).get("llm") or {}
    if is_openrouter(llm_cfg):
        return get_model_name("openrouter", llm_cfg)
    return _orig_extract_model_info(full_config)


_tu.extract_model_info = _extract_model_info


def estimate_calls(cfg: Dict[str, Any], total_runs: int) -> int:
    """Upper bound on model calls: runs x agents x planning rounds x conversation steps."""
    sim = cfg.get("simulation") or {}
    exp = cfg.get("experiment") or {}
    rounds = int(exp.get("planning_rounds", sim.get("max_planning_rounds", 2)))
    steps = int(exp.get("max_conversation_steps", sim.get("max_conversation_steps", 3)))
    agents = 0
    for sweep in exp.get("sweeps") or []:
        agents = max(agents, *[int(n) for n in (sweep.get("num_agents") or [0])])
    agents = agents or int((cfg.get("communication_network") or {}).get("num_agents") or 0)
    return int(total_runs) * agents * rounds * steps


def cost_note(cfg: Dict[str, Any], total_runs: int) -> str:
    models = []
    for m in cfg.get("llm_models") or []:
        llm = m.get("llm") or {}
        models.append(get_model_name(str(llm.get("provider") or ""), llm))
    model_list = " · ".join(sorted(set(models))) or "(none configured)"
    # Cite the rates page for the endpoint the calls will ACTUALLY use (Nebius, or OpenRouter
    # when that's the configured key), not a hardcoded provider — otherwise the estimate misleads.
    kind = llm_config.endpoint_kind()
    if kind == "openrouter":
        rates = "see OpenRouter pricing (https://openrouter.ai/models)"
    elif kind == "nebius":
        rates = "see Nebius AI Studio pricing (https://studio.nebius.com)"
    else:  # custom endpoint (e.g. a Modal-hosted model)
        rates = f"your configured endpoint ({llm_config.base_url()})"
    return (
        f"{total_runs} run(s), at most ≈ {estimate_calls(cfg, total_runs):,} model calls "
        f"(tool loops usually use fewer). Models: {model_list}. "
        f"Rates: {rates}."
    )


def confirm_spend(cfg: Dict[str, Any], total_runs: int, *, yes: bool = False) -> None:
    """Print the call estimate and ask before spending (skip with -y or COLOSSEUM_YES=1)."""
    import sys

    print(cost_note(cfg, total_runs))
    if yes or os.getenv("COLOSSEUM_YES") == "1" or not sys.stdin.isatty():
        return
    if input("Continue? [y/N] ").strip().lower() not in ("y", "yes"):
        sys.exit("aborted")


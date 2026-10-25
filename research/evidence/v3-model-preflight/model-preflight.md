# Phase 3 public model preflight — 23 October 2026

This check read public metadata, author/provider documentation and the local SDK. It made **no inference requests, jobs or account/billing queries**, read no credentials, and changed no project files. `model-preflight.json` is the final machine-readable record for the parent-selected routes. Raw catalog, mapping, tokenizer and documentation snapshots plus retrieval hashes are retained in this directory.

## Chosen routes and prices

| HF model ID = DeepInfra providerId | Status / task | USD per million input / output tokens | HF provider context | Provider page precision claim |
|---|---|---:|---:|---|
| `Qwen/Qwen3.6-35B-A3B` | live / conversational | 0.10 / 0.95 | 262,144 | fp8 |
| `deepseek-ai/DeepSeek-V3.2` | live / conversational | 0.26 / 0.38 | 16,384 | fp4 |

Prices and context come from the unauthenticated [HF router catalog](https://router.huggingface.co/v1/models), corroborated by [HF's model table](https://huggingface.co/inference/models) and the public [Qwen](https://deepinfra.com/Qwen/Qwen3.6-35B-A3B) and [DeepSeek](https://deepinfra.com/deepseek-ai/DeepSeek-V3.2) provider pages. HF documents routed pricing without markup in [Pricing and Billing](https://huggingface.co/docs/inference-providers/en/pricing). No credit balance or authenticated availability was established.

The Hub mappings specify exactly the same model strings as above, allowing a strict equality check between the requested Hub ID, mapped providerId, actual payload model and response model. Hub artifact revisions are `995ad96eacd98c81ed38be0c5b274b04031597b0` (Qwen) and `a7e62ac04ecb2c0a54d736dc46601c5606cf10a6` (DeepSeek). These revisions do not pin the provider's served weights. Matching identifiers are necessary for this protocol, but cannot independently prove model identity. Both families share DeepInfra, so this is not replication across providers. The previous requested/reported discrepancy remains unresolved.

## Fixed study configuration and reservation

The selected configuration is `temperature=0.6`, `top_p=0.95`, `max_tokens=4096`, one completion, explicit `provider="deepinfra"`, text-only messages, no tools or attachments. This uniform temperature is an investigator choice below both authors' general/local `1.0` guidance; no optimal-quality claim is made. Qwen's additional suggested controls are not implicitly claimed to be active. Neither the output cap nor settings should be changed to rescue a failed observation.

With `max_request_bytes=10000`, an additional assumed 2048 framing tokens gives a provisional input reservation of 12048 tokens:

| Model | Provisional maximum at catalog price | Selected reservation per call | Context headroom |
|---|---:|---:|---:|
| Qwen | $0.005096 | $0.006 | 246,000 tokens |
| DeepSeek | $0.00468896 | $0.005 | 240 tokens |

These are client reservations, not server-enforced billing caps or invoices. The prior dispatched reserve is $0.126 and prior provider estimate $0.00720307. A main-phase ceiling of $8.00 plus pilot $0.60 plus the conservatively retained prior allocated ceilings of $1.00 totals $9.60, below the $15 overall budget. Do not add historical reserves a second time when they are already covered by the prior ceiling.

DeepSeek's author tokenizer config allows 131072 tokens, but the HF provider catalog advertises only 16384. Use the lower serving limit. Do not silently truncate input. A response ending in `length` at 4096 is a failure under this configuration; preserve it without increasing the cap to repair it. Provider-reported input/output usage and estimated cost should be checked immediately against the assumptions and reservation before proceeding.

## Tokenizer bound: established part and remaining assumption

`tokenizer-bound-inspection.json` records inspection of both downloaded `tokenizer.json` files. Both use BPE with the full 256-symbol ByteLevel byte alphabet in the vocabulary. Their pretokenizer splits without duplication and applies ByteLevel with `add_prefix_space=false`; BPE merges cannot increase the initial byte-token count. Thus normalized content is bounded by its UTF-8 byte count for these downloaded tokenizers, before chat framing.

Qwen normalizes with NFC, which can increase byte length for some Unicode sequences. DeepSeek has an empty normalization sequence. The current project runner measures the maximum of raw and NFC-normalized serialized-message UTF-8 lengths, covering that distinction. An unnormalized byte count alone would not establish the Qwen bound. The ByteLevel postprocessor is an offset processor; it is not a template that inserts arbitrary text.

The **2048-token framing allowance is still an assumption**, not a proof of the provider's server-side chat encoding or weights. DeepSeek V3.2 has no Jinja chat template in its release and supplies a dedicated Python encoder. Neither `tokenizers` nor `transformers` is installed in the project `.venv`; none was installed here. The downloaded tokenizer files are evidence, not a claim that exact server prompt tokens were counted. DeepInfra documents a tokenizer endpoint returning count and model context, but it was not called; its availability and accounting through HF were not established.

## Local SDK handling

The installed `huggingface_hub` is **2.3.0**. With an HF token and explicit DeepInfra provider it selects `https://router.huggingface.co/deepinfra/v1/openai/chat/completions`. It fetches the chosen provider mapping, validates task support and sets `payload.model` from `providerId`, excluding the caller's duplicate model field from overriding that mapping. Two pure local payload-construction checks confirmed the exact chosen IDs, without key lookup or HTTP calls; see `sdk-inspection.json` for source hashes.

The client does not compare the response identifier with the requested identifier: it parses the response. The runner must reject absent/different model IDs, persist the entire response first and stop without silently retrying or relabelling it. No auto-provider selection or model substitution is configured on these explicit routes; this statement concerns inspected client configuration, not an independent guarantee about remote serving. Provider-specific options can enter through `extra_body`, which may override generation fields, so keep it absent or fully recorded and validated.

## Primary sources and snapshots

- [Qwen author README](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md): thinking default and sampling recommendations.
- [DeepSeek author README](https://huggingface.co/deepseek-ai/DeepSeek-V3.2/blob/a7e62ac04ecb2c0a54d736dc46601c5606cf10a6/README.md): custom chat encoding and local sampling recommendation.
- [HF mapping documentation](https://huggingface.co/docs/inference-providers/en/hub-api): provider status/task/providerId semantics.
- [DeepInfra chat schema](https://docs.deepinfra.com/api-reference/chat-completions/openai-chat-completions.md): generated-token limit and total context constraint.
- [DeepInfra reasoning documentation](https://docs.deepinfra.com/chat/reasoning.md): reasoning tokens count toward output billing; model-specific parameter support varies. This does not establish that any optional reasoning-effort control was enabled in our chosen configuration.

`retrieval-index.json` and `provider-docs-retrieval-index.json` give retrieval times, exact URLs and SHA256 hashes. Earlier 8192-token/candidate calculations are retained separately in `model-preflight-candidates.json`; they are not the chosen study configuration.

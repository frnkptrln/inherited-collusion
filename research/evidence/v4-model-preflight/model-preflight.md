# GPT-OSS-120B public preflight — 23 October 2026

**Decision support, not a live inference result.** The single prespecified additional candidate is `openai/gpt-oss-120b`, routed through **DeepInfra only**. Public metadata supports dispatching its competence gate after the prospective protocol is frozen. This inspection made **zero inference calls and zero jobs**, and did not read credentials. Candidate selection precedes successor outcomes and rests on another model family and low published cost; it is not selection for a favorable harm outcome. A failed six-probe gate ends this candidate search.

## Identity and availability

The [public HF mapping](https://huggingface.co/api/models/openai/gpt-oss-120b?expand%5B%5D=inferenceProviderMapping&expand%5B%5D=sha) reports `live`, task `conversational`, and exact DeepInfra `providerId: openai/gpt-oss-120b`. The [HF router catalog](https://router.huggingface.co/v1/models) reports context 131,072, input $0.037/million tokens and output $0.17/million tokens. The [provider model page](https://deepinfra.com/openai/gpt-oss-120b) corroborates those limits and tariffs. Hub revision observed: `b5c939de8f754692c1647ca79fbf85e8c1e70f8a`.

The [model-specific provider API example](https://deepinfra.com/openai/gpt-oss-120b/api) uses `openai/gpt-oss-120b` in both request and response. This is a documentation convention, **not an observed response**. Require exact response-model equality in every actual call and preserve the response before parsing. An exact identifier does not authenticate served weights or tokenizer. The public API example's cost field is not evidence for the current tariff.

## Frozen request settings and unresolved reasoning default

Send exactly `temperature=0.6`, `top_p=0.95`, and `max_tokens=8192` as generation controls. **Omit `extra_body` and `reasoning_effort`. Record effective reasoning effort as “provider default unspecified.”** Neither “medium” nor “high” is established for this routed service. The common sampling settings are our experimental choice, not a quality-optimal recommendation.

The [author template](https://huggingface.co/openai/gpt-oss-120b/blob/b5c939de8f754692c1647ca79fbf85e8c1e70f8a/chat_template.jinja) defaults to `medium` when `reasoning_effort` is absent (downloaded lines 203–206). The [generic DeepInfra reasoning documentation](https://docs.deepinfra.com/chat/reasoning) describes `high` as the default for reasoning models, while the model-specific input schema exposes a null default. These sources do not resolve the actual server setting. The [official OpenAI model documentation](https://developers.openai.com/api/docs/models/gpt-oss-120b) establishes configurable reasoning and the model's published context, not DeepInfra's effective configuration. Reasoning tokens are billed as output according to DeepInfra.

Static inspection of the installed `huggingface_hub==2.3.0` and a pure local payload-construction check found no client-inserted reasoning default. The provider helper uses the mapping's exact `provider_id`; route: `https://router.huggingface.co/deepinfra/v1/openai/chat/completions`. SDK source hashes and the controls in the offline payload are in `sdk-inspection.json`. No automatic provider/model substitution is configured by this choice. The SDK itself does not enforce response-model equality; the runner must.

## Byte bound and reservation

For the **downloaded author tokenizer**, ordinary-text token count is no greater than raw UTF-8 bytes: normalizer is null; the regex splitter isolates without duplicating input; ByteLevel inserts no prefix space; all 256 byte-alphabet symbols exist in the BPE vocabulary; merges and whole-vocabulary matches cannot increase the initial byte count. ByteLevel postprocessing concerns offsets, not insertion of extra text. Thus the larger of raw and NFC UTF-8 lengths of the serialized text messages is conservative for this tokenizer. No tokenizer package installation or remote-code execution was needed. See `tokenizer-bound-inspection.json` and the stored raw tokenizer.

This bound **does not establish the remote service's tokenizer**, and the additional 2,048-token chat-framing allowance is an assumption, not a formal provider guarantee. It covers the planned text-only requests, without tools or attachments. Raw files were downloaded from `main` with content SHA256 recorded; separate commit-pinned HEAD checks confirm public availability and lengths, not independent full-content equality.

| Reservation component | Value |
|---|---:|
| Maximum serialized-message bytes, max(raw, NFC) | 10,000 |
| Assumed framing tokens | 2,048 |
| Input-token reservation | 12,048 |
| Maximum output tokens | 8,192 |
| Combined context reservation | 20,240 |
| Remaining context | 110,832 |
| Catalog cost at those bounds | $0.001838416 |
| Reserved amount per call | **$0.002** |
| Remaining monetary margin per call | $0.000161584 |
| Six-probe reservation | **$0.012** |

Calculation: `(12048 × 0.037 + 8192 × 0.17) / 1,000,000`. This is an accounting reservation under the published tariff, not an invoice or a server-enforced billing cap. Check returned prompt/completion counts and estimated cost before proceeding to another stage. A length-truncated response at 8,192 is a failed/incomplete response and must not trigger a rescue retry or a changed output limit.

## Evidence and remaining gate

`model-preflight.json` is the machine-readable decision record. `retrieval-index.json` records each anonymous public URL, UTC retrieval time, byte count and content digest. `preflight-manifest.json` binds the final evidence bundle, excluding itself. Preserve the author/provider-default discrepancy, exact request controls and source snapshots in the run manifest and report. Freeze the protocol and stopping rule before dispatch; require all six competence/note probes, exact reported identity and complete responses before admitting the candidate. No comparison of intrinsic model quality follows from the different provider defaults or separately produced note pairs.

"""One call per request. Mock is software validation only; HF is opt-in."""
import dataclasses
import json
from collections.abc import Mapping


def provider_response_data(value):
    """Preserve SDK attributes and unknown mapping fields at every nesting level.

    HF response objects are both dataclasses and mappings. Their mapping view
    can contain stale, flattened copies of declared nested fields, while
    dataclasses.asdict drops additional provider fields such as reasoning_content.
    Prefer each declared attribute and retain every additional mapping entry.
    """
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        fields = dict(value) if isinstance(value, Mapping) else {}
        fields.update({field.name: getattr(value, field.name)
                       for field in dataclasses.fields(value)})
        return {key: provider_response_data(item) for key, item in fields.items()}
    if isinstance(value, Mapping):
        return {key: provider_response_data(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [provider_response_data(item) for item in value]
    return value


class MockBackend:
    label = "scripted_mock_NOT_MODEL_EVIDENCE"

    def complete(self, messages, meta, config):
        if meta["kind"] == "dialogue":
            value = {"proposal": f"Use the assigned plan {meta['plan']}."}
        elif meta["kind"] == "donor":
            value = {"task": meta["target"], "note": f"Our agreed allocation: you take {meta['target']}; your colleague takes {meta['partner_target']}. Keep this allocation."}
        elif meta["kind"] == "probe":
            value = {"task": meta["expected"], "reason": "Scripted test response."}
        else:
            note = meta.get("note") or ""
            marker = "you take "
            target = note.split(marker, 1)[1].split(";", 1)[0] if marker in note else meta["safe_target"]
            value = {"task": target, "reason": "Scripted test response."}
        return {"text": json.dumps(value), "usage": {}, "model": self.label, "finish_reason": "stop"}


class HFBackend:
    label = "huggingface_inference"

    def complete(self, messages, meta, config):
        from huggingface_hub import InferenceClient
        # Explicit provider and exact model: no auto routing or model substitution.
        client = InferenceClient(model=config["model"], provider=config["provider"], timeout=180)
        response = client.chat_completion(messages=messages, max_tokens=config["max_tokens"], temperature=config.get("temperature", 0.0), top_p=config.get("top_p", 1.0))
        raw = provider_response_data(response)
        # A provider may return a structurally incomplete but valid SDK object.
        # Keep that returned object durable before the runner rejects its schema.
        choices = getattr(response, "choices", None)
        first = choices[0] if isinstance(choices, (list, tuple)) and choices else None
        message = getattr(first, "message", None)
        usage = getattr(response, "usage", None)
        return {"text": getattr(message, "content", None),
                "usage": provider_response_data(usage) if usage else {},
                "model": getattr(response, "model", None),
                "finish_reason": getattr(first, "finish_reason", None),
                "provider_response": raw}

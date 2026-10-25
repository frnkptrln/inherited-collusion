"""One call per request. Mock is software validation only; HF is opt-in."""
import dataclasses
import json


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
        client = InferenceClient(model=config["model"], provider=config["provider"], timeout=60)
        response = client.chat_completion(messages=messages, max_tokens=config["max_tokens"], temperature=0.0)
        raw = dataclasses.asdict(response) if dataclasses.is_dataclass(response) else dict(response)
        return {"text": response.choices[0].message.content,
                "usage": dict(response.usage) if response.usage else {},
                "model": response.model, "finish_reason": response.choices[0].finish_reason,
                "provider_response": raw}

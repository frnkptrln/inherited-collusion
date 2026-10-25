"""Offline SDK-response regression tests; no inference or authentication."""
import json
import unittest
from unittest.mock import patch

from huggingface_hub.inference._generated.types.chat_completion import ChatCompletionOutput

from inherited_collusion.backends import HFBackend, provider_response_data


def synthetic_response(content):
    return ChatCompletionOutput.parse_obj_as_instance({
        "id": "offline-response", "created": 0, "model": "offline-model",
        "object": "chat.completion", "provider_extra": {"region": "offline"},
        "choices": [{
            "finish_reason": "stop", "index": 0,
            "choice_extra": {"synthetic": True},
            "message": {"role": "assistant", "content": content,
                        "reasoning_content": "Synthetic separate provider reasoning.",
                        "message_extra": {"nested": [{"value": 7}]}},
        }],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30,
                  "completion_tokens_details": {"reasoning_tokens": 15},
                  "prompt_tokens_details": {"cached_tokens": 4}},
    })


class BackendTests(unittest.TestCase):
    def test_sdk_nested_provider_extras_survive_serialization(self):
        response = synthetic_response('{"task":"T1"}')
        preserved = json.loads(json.dumps(provider_response_data(response)))
        self.assertEqual(preserved["provider_extra"], {"region": "offline"})
        self.assertEqual(preserved["choices"][0]["choice_extra"], {"synthetic": True})
        message = preserved["choices"][0]["message"]
        self.assertEqual(message["content"], '{"task":"T1"}')
        self.assertEqual(message["reasoning_content"], "Synthetic separate provider reasoning.")
        self.assertEqual(message["message_extra"], {"nested": [{"value": 7}]})
        self.assertEqual(preserved["usage"]["completion_tokens_details"], {"reasoning_tokens": 15})
        self.assertEqual(preserved["usage"]["prompt_tokens_details"], {"cached_tokens": 4})

    def test_backend_keeps_content_verbatim_and_sampling_without_retry(self):
        messages = [{"role": "user", "content": "Offline test only."}]
        config = {"model": "offline-model", "provider": "deepinfra", "max_tokens": 4096,
                  "temperature": 0.6, "top_p": 0.95}
        for content in ('{"task":"T1"}', '<think>Unseparated output</think>{"task":"T1"}', None):
            with self.subTest(content=content), patch("huggingface_hub.InferenceClient") as client_type:
                client = client_type.return_value
                client.chat_completion.return_value = synthetic_response(content)
                result = HFBackend().complete(messages, {}, config)
                client_type.assert_called_once_with(model="offline-model", provider="deepinfra", timeout=180)
                client.chat_completion.assert_called_once_with(
                    messages=messages, max_tokens=4096, temperature=0.6, top_p=0.95)
                self.assertEqual(result["text"], content)
                self.assertEqual(result["usage"]["completion_tokens_details"]["reasoning_tokens"], 15)
                self.assertEqual(result["provider_response"]["choices"][0]["message"]["reasoning_content"],
                                 "Synthetic separate provider reasoning.")


if __name__ == "__main__":
    unittest.main()

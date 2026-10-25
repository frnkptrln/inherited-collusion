#!/usr/bin/env python3
"""Read-only HF router catalog snapshot. Never prints or saves credentials."""
import datetime
import hashlib
import json
from pathlib import Path
import urllib.request
import urllib.error

from huggingface_hub import get_token

OUT = Path(__file__).resolve().parent
URL = "https://router.huggingface.co/v1/models"
MODELS = ("Qwen/Qwen3.6-35B-A3B", "openai/gpt-oss-120b")

def main():
    token = get_token()
    if not token:
        raise SystemExit("HF credential unavailable; no credential was printed.")
    request = urllib.request.Request(URL, headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = response.status
            body = response.read()
    except urllib.error.HTTPError as error:
        raise SystemExit(f"Catalog request failed with HTTP {error.code}; response body withheld.") from None
    except urllib.error.URLError:
        raise SystemExit("Catalog network request failed; no credentials or request headers printed.") from None
    payload = json.loads(body)
    records = payload.get("data", [])
    chosen = []
    for model in MODELS:
        matches = [item for item in records if item.get("id") == model]
        if len(matches) != 1:
            raise SystemExit("Requested model missing or ambiguous in catalog: " + model)
        providers = matches[0].get("providers", [])
        provider = [p for p in providers if p.get("provider") == "deepinfra"]
        if len(provider) != 1 or provider[0].get("status") != "live":
            raise SystemExit("Expected live DeepInfra provider missing: " + model)
        chosen.append({"id": model, "provider_metadata": provider[0]})
    result = {"source": URL, "checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "http_status": status, "response_sha256": hashlib.sha256(body).hexdigest(),
              "models": chosen, "no_model_requests": True, "no_jobs_started": True,
              "credential_saved_or_printed": False}
    destination = OUT / "current-provider-pricing.json"
    destination.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"saved": str(destination), "models": chosen}))

if __name__ == "__main__":
    main()

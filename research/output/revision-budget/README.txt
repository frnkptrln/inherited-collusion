Budget reconciliation for the paper revision

reconciliation.json is the durable budget basis for the additional study.
It retains the full original per-call reservation for every one of 2217
uniquely dispatched historical requests, including all five unresolved calls.
It releases only never-dispatched call slots and unused allocation rounding
headroom. Original ledgers and closed evidence were not modified.

Historical reservations: USD 12.374
New study: at most 64 Qwen calls at USD 0.010 and 96 GPT-OSS calls at USD 0.002
New reservation: USD 0.832
Combined reservation ceiling: USD 13.206, below the authorized USD 15
Unallocated remainder: USD 1.794

The exact retired call IDs, per-run accounting, source hashes, five unresolved
request paths, pricing snapshot and gate assumptions are in the JSON result.
The earlier V4 raw files are verified byte-identical to their V4F copies before
counting the consolidated population once. V5 unused allocations had already
been released before V6 and are not released a second time.

Recompute and verify offline from canonical originals:
  python3 output/revision-budget/reconcile_budget.py --verify

To reproduce the result file (writes only in this directory):
  python3 output/revision-budget/reconcile_budget.py

Current public catalog pricing was retrieved using the existing local HF
credential, without printing or saving the credential. No inference request
or job was started. To refresh this read-only metadata explicitly:
  /home/user/projects/collusion-sprint/.venv/bin/python output/revision-budget/fetch_pricing.py

Refreshing metadata changes the input hashes, so rerun the checker afterward.
Do not refresh a snapshot after it is included in a frozen study manifest.

Pricing source: https://router.huggingface.co/v1/models
Provider: DeepInfra
Models: Qwen/Qwen3.6-35B-A3B and openai/gpt-oss-120b
Prices are USD per million tokens. The token-cost bound assumes at most one
input token per max(raw,NFC) serialized UTF8 message byte, plus 2048 framing
tokens. The request-byte cap is 10000 and completion-token cap is 8192.
These are local accounting bounds and stop guards, not a provider-enforced
dollar billing cap. Provider invoices and account balance were not verified.
Old unresolved requests must never be automatically replayed.

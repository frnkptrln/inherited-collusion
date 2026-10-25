# Independent V4F analyzer review

Accepted analyzer SHA256: `107ba80f262741ba93071c674625b932cdb102b9852506be51e7c3ec2a8f63b5`.

All 12 synthetic tests passed independently in 4.163 seconds (7 analyzer tests and 5 bounds tests). No model calls or live outcome aggregation occurred. The reviewer did not edit the analyzer or frozen execution code.

The review verified exact wrapper recognition; full schema and competence checks; raw response and request provenance; all 18 prepared sources; original annotation chronology; inherited/new/mixed episode attribution; semantic-content inclusion in primary estimates; equal case weights; explicit missingness; separate strict/amended bounds; and single-count consolidated costs.

Three findings were resolved before acceptance: project-local frozen-artifact hash verification after archive rebasing, exact archived/current per-case allocation binding, and binding optional strict-analysis input to the original 18 manifests, episode set and call counts. No remaining blocker was identified.

Strict and amended execution/analysis must use separate processes: the amended adapter intentionally changes parser aliases in its own process. Offline test modules for those modes should likewise run separately. Final real-data audit remains pending closure of both datasets. See the JSON review record for exact hashes, command and scope.

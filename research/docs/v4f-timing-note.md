# Timestamp semantics and limits

This measurement note was written before V4F execution and aggregate effect inspection. It documents the unchanged legacy storage implementation rather than changing it.

`invocation.json.at` records the first local V4/V4F call invocation before the inherited dispatch guards. It remains immutable and is the field labelled `invoked_at` in the amended analysis. It is a local pre-dispatch time, not an independently measured provider-arrival or exact network-send time.

The legacy call store initially writes `dispatch.json` with status `reserved_may_have_been_dispatched`. After a response is saved, it replaces that record with status `response_saved` and a new `at` value. Thus the final dispatch record of a successful call contains the response-storage time; its initial reservation timestamp is not separately retained there. For unresolved calls the original reservation record remains. Never relabel a successful record's final `at` as the dispatch time.

The immutable invocation, request, response and final dispatch bytes are all preserved. Annotation-before-invocation checks conservatively establish annotation-before-dispatch for subsequent calls. The strict-source versus newly-dispatched-V4F classification does not rely on the overwritten timestamp: all strict processes finish before closeout and the executable V4F freeze, copied calls retain their original source identity, and new invocations must follow both boundaries. Calls in flight at the earlier design-amendment decision remain original V4 evidence even if their responses arrive afterward.

These are local machine timestamps and hashes, not third-party timestamp attestations. Exact provider receipt time and exact historical network dispatch time are unavailable. This limits the literal dispatch-time detail requested by the V4F protocol; no timestamp has been reconstructed or fabricated to fill that gap.

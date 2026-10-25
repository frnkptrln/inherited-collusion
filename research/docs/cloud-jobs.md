# Cloud jobs: local ledger and read-only CLI capture

No cloud submission or paid model call is approved. This helper deliberately has
no `submit`, `run`, `rerun`, `cancel`, or remote-label mutation command. Hardware,
model, maximum runtime, and a spending limit must be agreed before adding a
submission path. Nothing here launches a job.

The installed Hugging Face CLI is version 2.3.0. Its `jobs ps`, `inspect`, and
`logs` help was inspected locally; these commands have not been tested against
the account from this environment because DNS access is blocked. A CLI being
installed does not establish authentication, quota, or remote access.

Use the project interpreter directly; these commands work in fish and bash:

```sh
.venv/bin/python scripts/hf_jobs.py --help

# Entirely local: record an ID already obtained from the CLI or account.
.venv/bin/python scripts/hf_jobs.py record KNOWN_JOB_ID --name inherited-collusion-pilot --namespace YOUR_NAMESPACE

# Read-only remote queries, once network access is available.
.venv/bin/python scripts/hf_jobs.py list --namespace YOUR_NAMESPACE
.venv/bin/python scripts/hf_jobs.py inspect KNOWN_JOB_ID --namespace YOUR_NAMESPACE
.venv/bin/python scripts/hf_jobs.py logs KNOWN_JOB_ID --namespace YOUR_NAMESPACE
```

Replace the placeholders with a known bare ID and namespace. IDs cannot contain
slashes or `..`; pass the namespace separately. `record` stores the supplied ID
and name without verifying the remote job. It does not create a job or change
its remote name. Use the same namespace when updating a local record.

The CLI uses its existing login or environment authentication. There is no
`--token` option in the wrapper, so credentials are not written into command
records. `--hf /path/to/hf` and `--root /path/to/local/ledger` can be supplied
before the subcommand. Remote reads have a default 60-second local timeout,
adjustable with `--timeout`; failed reads can be repeated safely and produce
separate captures.

## Capture layout and recovery

```text
runs/jobs/
  KNOWN_JOB_ID/
    job.json
    captures/<timestamp-and-random-suffix>/
      command.json
      stdout.json  # inspect; stdout.log for logs
      stderr.log
  _queries/<timestamp-and-random-suffix>/
    command.json
    stdout.json    # full job list, including completed jobs
    stderr.log
```

Each exact argument list is flushed to `command.json` **before** CLI execution.
Standard output and error stream directly to separate files; no chat connector,
tail, display truncation, or in-memory output limit is involved. The local
summary only reports status and the capture directory after those files have
been flushed. A failed read, invalid JSON, timeout, or interruption retains its
partial output. A process killed abruptly may leave `state: "started"`; this
means completion is unknown, not successful. Inspect an ID again to learn its
remote status. Logs ending successfully do not establish that the job succeeded.

The `list` command captures the equivalent of
`hf jobs ps -a --json --limit 0`, so completed jobs and jobs beyond the CLI's
default 100-item limit remain discoverable. If an ID was lost, recover it from
that saved JSON; narrow the read by an existing name or labels if available:

```sh
.venv/bin/python scripts/hf_jobs.py list --name inherited-collusion-pilot --namespace YOUR_NAMESPACE
.venv/bin/python scripts/hf_jobs.py list --label project=inherited-collusion --namespace YOUR_NAMESPACE
```

Names are not unique: compare timestamps, labels, and job specifications before
recording the recovered ID. These filters only help for labels already set on a
job. A future approved submission path should set a unique run identifier,
project label, code/configuration hashes, and a descriptive name before creating
the job; it must record the full submission command first and persist the
returned job ID immediately. It must reconcile ambiguous submission failures
with the remote listing before retrying, to avoid duplicate billable jobs.

Keep captures local: inspection output may include job configuration or sensitive
details, and episode logs may contain task material. Do not treat CLI log capture
as the authoritative research dataset.

## Required before any future submission

A remote job's local filesystem is ephemeral. Saving after each episode protects
against a process crash within a surviving workspace; it does not make the data
survive job deletion, restart, or host loss. A future cloud runner needs an
explicit, authorized durable destination, for example a mounted persistent
bucket or a private dataset repository, with tested write/read access. Each
completed episode and its manifest must be durably uploaded or synchronized,
and checked before marking it committed. Resumption must load and validate that
manifest instead of silently repeating already paid episodes.

Before implementing submission, fix the spending cap, selected model/hardware,
runtime timeout, retry policy, expected episode count, and durable destination.
Verify the upload/download/resume path with an inexpensive agreed smoke test.
Do not start a paid pilot merely because local tests pass.

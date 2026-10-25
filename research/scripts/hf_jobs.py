#!/usr/bin/env python3
"""Read-only Hugging Face Jobs CLI wrapper with durable local captures.

No command in this program submits, reruns, cancels, or changes a remote job.
Authentication is left to the installed `hf` CLI; tokens are never arguments.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import uuid


PROJECT_ROOT = Path(__file__).resolve().parents[1]
JOB_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def job_id(value: str) -> str:
    """Accept a bare ID only; namespaces are passed separately, never as paths."""
    if not JOB_ID_RE.fullmatch(value):
        raise argparse.ArgumentTypeError(
            "job ID must be 1–128 ASCII letters/digits/underscores/hyphens, "
            "starting with a letter or digit; use --namespace separately"
        )
    return value


def atomic_json(path: Path, payload: dict) -> None:
    """Write, flush, and atomically replace one metadata file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def job_directory(root: Path, identifier: str) -> Path:
    job_id(identifier)
    root = root.resolve()
    directory = root / identifier
    # Do not let a pre-existing symlink turn a valid ID into a traversal.
    if directory.resolve().parent != root:
        raise ValueError("job directory must be directly inside the jobs root")
    return directory


def record_job(root: Path, identifier: str, name: str, namespace: str | None) -> Path:
    if not name.strip():
        raise ValueError("job name cannot be empty")
    path = job_directory(root, identifier) / "job.json"
    previous = json.loads(path.read_text()) if path.exists() else {}
    if previous and previous.get("namespace") != namespace:
        raise ValueError("existing job record has another namespace; keep its namespace")
    atomic_json(path, {
        "schema_version": 1,
        "job_id": identifier,
        "name": name,
        "namespace": namespace,
        "created_at": previous.get("created_at", timestamp()),
        "updated_at": timestamp(),
        "source": "user-supplied existing job ID; not verified by record",
    })
    return path


def capture(root: Path, command: str, hf: str, identifier: str | None = None,
            namespace: str | None = None, labels: list[str] | None = None,
            name: str | None = None, timeout: float = 60) -> tuple[int, Path]:
    """Persist exact argv before execution; stream both outputs to unique files."""
    if command not in {"list", "inspect", "logs"}:
        raise ValueError(f"not a read-only command: {command}")
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    argv = [hf, "jobs"]
    if command == "list":
        if identifier is not None:
            raise ValueError("list does not take a job ID")
        parent = root / "_queries"
        argv += ["ps", "-a", "--json", "--limit", "0"]
        for label in labels or []:
            if label.count("=") != 1 or not label.split("=", 1)[0]:
                raise ValueError("labels must use key=value with one equals sign")
            argv += ["--label", label]
        if name is not None:
            argv += ["--name", name]
    else:
        if identifier is None:
            raise ValueError(f"{command} requires an explicit job ID")
        parent = job_directory(root, identifier) / "captures"
        argv += [command, identifier]
        if command == "inspect":
            argv.append("--json")
    if namespace is not None:
        argv += ["--namespace", namespace]
    capture_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + "-" + uuid.uuid4().hex[:8]
    directory = parent / capture_id
    directory.mkdir(parents=True, exist_ok=False)
    stdout = directory / ("stdout.json" if command in {"list", "inspect"} else "stdout.log")
    stderr = directory / "stderr.log"
    manifest = {
        "schema_version": 1,
        "command": command,
        "argv": argv,
        "cwd": str(Path.cwd()),
        "job_id": identifier,
        "namespace": namespace,
        "started_at": timestamp(),
        "timeout_seconds": timeout,
        "state": "started",
        "stdout": stdout.name,
        "stderr": stderr.name,
    }
    atomic_json(directory / "command.json", manifest)
    # No shell, token option, follow mode, output tail, or automatic retry.
    with stdout.open("wb") as output, stderr.open("wb") as errors:
        try:
            result = subprocess.run(argv, stdout=output, stderr=errors, timeout=timeout,
                                    check=False, stdin=subprocess.DEVNULL)
            returncode = result.returncode
            manifest["state"] = "completed" if returncode == 0 else "failed"
        except subprocess.TimeoutExpired:
            returncode = 124
            manifest.update(state="timed_out", error=f"CLI timed out after {timeout} seconds")
        except OSError as error:
            returncode = 127
            manifest.update(state="failed_to_start", error=str(error))
        except KeyboardInterrupt:
            returncode = 130
            manifest.update(state="interrupted", error="local capture interrupted")
        for stream in (output, errors):
            stream.flush()
            os.fsync(stream.fileno())
    if returncode == 0 and command in {"list", "inspect"}:
        try:
            json.loads(stdout.read_text(encoding="utf-8"))
            manifest["valid_json"] = True
        except (ValueError, UnicodeError) as error:
            # Keep invalid/truncated JSON exactly as received for diagnosis.
            returncode = 65
            manifest.update(state="invalid_json", valid_json=False, error=str(error))
    manifest.update(returncode=returncode, finished_at=timestamp(),
                    stdout_bytes=stdout.stat().st_size, stderr_bytes=stderr.stat().st_size)
    atomic_json(directory / "command.json", manifest)
    return returncode, directory


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    default_hf = PROJECT_ROOT / ".venv" / "bin" / "hf"
    result.add_argument("--hf", default=str(default_hf) if default_hf.exists() else "hf",
                        help="path to the installed hf executable")
    result.add_argument("--root", type=Path, default=PROJECT_ROOT / "runs" / "jobs",
                        help="local metadata and capture directory")
    commands = result.add_subparsers(dest="command", required=True)
    record = commands.add_parser("record", help="locally record an already known job ID; no network")
    record.add_argument("job_id", type=job_id)
    record.add_argument("--name", required=True)
    record.add_argument("--namespace")
    listing = commands.add_parser("list", help="read all jobs, saving full JSON")
    listing.add_argument("--label", action="append", default=[])
    listing.add_argument("--name")
    for command in (listing, commands.add_parser("inspect"), commands.add_parser("logs")):
        if command is not listing:
            command.add_argument("job_id", type=job_id)
        command.add_argument("--namespace")
        command.add_argument("--timeout", type=float, default=60,
                             help="local read timeout in seconds (default: 60)")
    return result


def main(argv: list[str] | None = None) -> int:
    cli = parser()
    args = cli.parse_args(argv)
    try:
        if args.command == "record":
            path = record_job(args.root, args.job_id, args.name, args.namespace)
            print(f"Recorded existing job ID locally: {path}")
            return 0
        code, directory = capture(args.root, args.command, args.hf,
                                  identifier=getattr(args, "job_id", None), namespace=args.namespace,
                                  labels=getattr(args, "label", None), name=getattr(args, "name", None),
                                  timeout=args.timeout)
    except (ValueError, OSError) as error:
        cli.error(str(error))
    print(f"Read-only {args.command}: exit {code}; full output and command saved in {directory}")
    return code if code >= 0 else 128 - code


if __name__ == "__main__":
    sys.exit(main())

"""Atomic immutable artifacts and exclusive Linux run locks."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(canonical(value) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        dir_fd = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def immutable_json(path, value):
    path = Path(path)
    if path.exists():
        if canonical(read(path)) != canonical(value):
            raise ValueError(f"Refusing changed artifact: {path}")
    else:
        atomic_json(path, value)


class RunLock:
    def __init__(self, root):
        self.root = Path(root)

    def __enter__(self):
        self.root.mkdir(parents=True, exist_ok=True)
        self.stream = (self.root / ".lock").open("a")
        try:
            fcntl.flock(self.stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.stream.close()
            raise RuntimeError("Another process owns this run") from None
        return self

    def __exit__(self, *args):
        self.stream.close()

"""Offline tests: no Hugging Face service or account is contacted."""

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


SPEC = importlib.util.spec_from_file_location(
    "hf_jobs", Path(__file__).resolve().parents[1] / "scripts" / "hf_jobs.py")
hf_jobs = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(hf_jobs)


class JobCaptureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "jobs"

    def test_record_is_local_atomic_and_rejects_namespace_collision(self):
        with mock.patch.object(subprocess, "run") as runner:
            path = hf_jobs.record_job(self.root, "abc-123", "pilot", "research")
            first = json.loads(path.read_text())
            hf_jobs.record_job(self.root, "abc-123", "pilot-renamed", "research")
            second = json.loads(path.read_text())
            runner.assert_not_called()
        self.assertEqual(second["created_at"], first["created_at"])
        self.assertEqual(second["name"], "pilot-renamed")
        self.assertEqual(list(path.parent.iterdir()), [path])
        with self.assertRaises(ValueError):
            hf_jobs.record_job(self.root, "abc-123", "other", "another")

    def test_untrusted_id_cannot_traverse_or_become_cli_option(self):
        for identifier in ["../escape", "/absolute", "team/id", "..", "-a", "", "a.b", "a\n"]:
            with self.subTest(identifier=identifier):
                with self.assertRaises(argparse.ArgumentTypeError):
                    hf_jobs.job_id(identifier)
        self.root.mkdir()
        (self.root / "linked").symlink_to(self.root.parent, target_is_directory=True)
        with self.assertRaises(ValueError):
            hf_jobs.record_job(self.root, "linked", "pilot", None)

    def test_command_saved_first_and_complete_outputs_preserved(self):
        output = json.dumps([{"id": "x", "large": "z" * 100_000}]).encode()
        error_output = b"diagnostic\n" * 10_000

        def fake_run(argv, **kwargs):
            manifests = list(self.root.glob("_queries/*/command.json"))
            self.assertEqual(len(manifests), 1)
            before = json.loads(manifests[0].read_text())
            self.assertEqual(before["state"], "started")
            self.assertEqual(before["argv"], argv)
            self.assertEqual(argv, ["hf", "jobs", "ps", "-a", "--json", "--limit", "0",
                                    "--label", "project=pilot", "--namespace", "research"])
            self.assertIs(kwargs["stdin"], subprocess.DEVNULL)
            kwargs["stdout"].write(output)
            kwargs["stderr"].write(error_output)
            return subprocess.CompletedProcess(argv, 0)

        with mock.patch.object(subprocess, "run", side_effect=fake_run):
            code, directory = hf_jobs.capture(self.root, "list", "hf", namespace="research",
                                               labels=["project=pilot"])
        self.assertEqual(code, 0)
        self.assertEqual((directory / "stdout.json").read_bytes(), output)
        self.assertEqual((directory / "stderr.log").read_bytes(), error_output)
        after = json.loads((directory / "command.json").read_text())
        self.assertEqual(after["state"], "completed")
        self.assertTrue(after["valid_json"])
        self.assertEqual(after["stdout_bytes"], len(output))

    def test_invalid_json_and_nonzero_exit_preserve_evidence(self):
        def fake_run(argv, **kwargs):
            kwargs["stdout"].write(b'{"truncated":')
            kwargs["stderr"].write(b"details")
            return subprocess.CompletedProcess(argv, 0)

        with mock.patch.object(subprocess, "run", side_effect=fake_run):
            code, directory = hf_jobs.capture(self.root, "inspect", "hf", "abc")
        self.assertEqual(code, 65)
        self.assertEqual((directory / "stdout.json").read_bytes(), b'{"truncated":')
        self.assertEqual(json.loads((directory / "command.json").read_text())["state"], "invalid_json")
        with mock.patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 7)):
            code, failed = hf_jobs.capture(self.root, "inspect", "hf", "abc")
        self.assertEqual(code, 7)
        self.assertNotEqual(failed, directory)

    def test_timeout_preserves_partial_log_and_remains_resumable(self):
        def timeout(argv, **kwargs):
            kwargs["stdout"].write(b"episode 1 saved\n")
            raise subprocess.TimeoutExpired(argv, kwargs["timeout"])

        with mock.patch.object(subprocess, "run", side_effect=timeout):
            code, directory = hf_jobs.capture(self.root, "logs", "hf", "abc", timeout=1)
        self.assertEqual(code, 124)
        self.assertEqual((directory / "stdout.log").read_bytes(), b"episode 1 saved\n")
        self.assertEqual(json.loads((directory / "command.json").read_text())["state"], "timed_out")

    def test_real_local_child_outputs_are_not_truncated_or_decoded(self):
        executable = Path(self.temporary.name) / "fake-hf"
        executable.write_text(
            f"#!{sys.executable}\n"
            "import sys\n"
            "assert sys.argv[1:] == ['jobs', 'logs', 'abc']\n"
            "sys.stdout.buffer.write(b'\\xff\\x00log\\n' * 20000)\n"
            "sys.stderr.buffer.write(b'diagnostic\\n' * 20000)\n"
        )
        executable.chmod(0o700)
        code, directory = hf_jobs.capture(self.root, "logs", str(executable), "abc")
        self.assertEqual(code, 0)
        self.assertEqual((directory / "stdout.log").read_bytes(), b"\xff\x00log\n" * 20000)
        self.assertEqual((directory / "stderr.log").read_bytes(), b"diagnostic\n" * 20000)

    def test_missing_cli_persists_failure_and_no_mutation_command_exists(self):
        with mock.patch.object(subprocess, "run", side_effect=FileNotFoundError("hf missing")):
            code, directory = hf_jobs.capture(self.root, "logs", "hf", "abc")
        self.assertEqual(code, 127)
        self.assertEqual(json.loads((directory / "command.json").read_text())["state"], "failed_to_start")
        for command in ["submit", "run", "rerun", "cancel", "labels"]:
            with self.subTest(command=command), self.assertRaises(ValueError):
                hf_jobs.capture(self.root, command, "hf", "abc")


if __name__ == "__main__":
    unittest.main()

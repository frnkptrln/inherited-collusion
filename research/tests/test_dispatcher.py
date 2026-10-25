"""Frozen dispatcher checks only; no child process or model call is launched."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("fixed_dispatcher", Path(__file__).resolve().parents[1] / "scripts/run_fixed_study.py")
dispatcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dispatcher)


class DispatcherTests(unittest.TestCase):
    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))

    def fixture(self, root):
        (root / "inherited_collusion").mkdir()
        source = root / "inherited_collusion/runner.py"
        source.write_text("# Offline validation fixture only\n")
        protocol = root / "docs/extended-protocol.md"
        protocol.parent.mkdir()
        protocol.write_text("Offline fixture")
        config = {"approved": True, "approved_by": "offline-test", "reservation_basis_confirmed": True,
                  "model": "offline-model", "provider": "offline-provider", "max_calls": 54,
                  "max_total_usd": 0.82, "reserved_usd_per_call": 0.015}
        self.write(root / dispatcher.APPROVAL, config)
        freeze = {"seeds": list(dispatcher.SEEDS), "checkpoints": {str(seed): {"seed": seed} for seed in dispatcher.SEEDS},
                  "source_hash": dispatcher.digest({"runner.py": hashlib.sha256(source.read_bytes()).hexdigest()}),
                  "protocol_sha256": hashlib.sha256(protocol.read_bytes()).hexdigest(),
                  "approval_sha256": hashlib.sha256((root / dispatcher.APPROVAL).read_bytes()).hexdigest(), "config": config,
                  "max_total_reserved_usd": 6.48, "project_allocated_ceiling_usd": 7.56,
                  "runs": {str(seed): {"out": f"runs/hf-study-s{seed}", "max_calls": 54, "max_total_usd": 0.82} for seed in dispatcher.SEEDS}}
        self.write(root / "docs/study-freeze.json", freeze)
        ledger = {"project_ceiling_usd": 15, "allocations": [{"run": f"hf-study-s{seed}", "ceiling_usd": 0.82,
                   "model": config["model"], "provider": config["provider"], "config": dispatcher.APPROVAL} for seed in dispatcher.SEEDS]}
        self.write(root / "runs/budget-ledger.json", ledger)
        return config, ledger

    def test_missing_freeze_and_source_or_allocation_drift_are_blocked(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(dispatcher.subprocess, "run") as child:
            root = Path(tmp)
            with self.assertRaises(FileNotFoundError):
                dispatcher.validate_freeze(root)
            config, ledger = self.fixture(root)
            dispatcher.validate_freeze(root)
            source = root / "inherited_collusion/runner.py"
            original = source.read_bytes()
            source.write_bytes(original + b"# changed\n")
            with self.assertRaisesRegex(ValueError, "source differs"):
                dispatcher.validate_freeze(root)
            source.write_bytes(original)
            ledger["allocations"].pop()
            self.write(root / "runs/budget-ledger.json", ledger)
            with self.assertRaisesRegex(ValueError, "Missing USD"):
                dispatcher.validate_freeze(root)
            child.assert_not_called()

    def test_stage_gates_model_mismatch_and_unresolved_calls_are_not_dispatched(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(dispatcher.subprocess, "run") as child:
            root = Path(tmp)
            self.fixture(root)
            self.assertTrue(dispatcher.case_status(root, 101, "probes")["dispatch"])
            self.assertEqual(dispatcher.case_status(root, 101, "donors")["reason"], "probes_required")
            case = root / "runs/hf-study-s101"
            self.write(case / "gates/s101-probes.json", {"passed": False})
            self.assertEqual(dispatcher.case_status(root, 101, "all")["reason"], "failed_gate")
            self.write(case / "calls/one/request.json", {})
            self.assertEqual(dispatcher.case_status(root, 101, "probes")["reason"], "unresolved_call_no_retry")
            self.write(case / "calls/one/response.json", {"model": "unexpected-model"})
            self.assertEqual(dispatcher.case_status(root, 101, "probes")["reason"], "model_identity_mismatch_no_retry")
            child.assert_not_called()


if __name__ == "__main__":
    unittest.main()

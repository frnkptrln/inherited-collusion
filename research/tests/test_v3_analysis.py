"""Independent offline regression tests for the post-freeze v3 analyzer."""
import importlib.util
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from inherited_collusion.storage import digest, read
from inherited_collusion.v3_runner import load_config, run
from inherited_collusion.v3_scenario import score

SPEC = importlib.util.spec_from_file_location("analyze_v3_study", Path(__file__).parents[1] / "scripts/analyze_v3_study.py")
analysis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(analysis)


def write(path, value):
    Path(path).write_text(json.dumps(value))


class V3AnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory()
        cls.base = Path(cls.fixture.name)
        cls.config = {**load_config("mock", None, [201], 2), "reserved_usd_per_call": .006, "max_total_usd": .516}
        run(cls.base / "runs/main-201", cls.config, [201], 2)
        payload = {key: value for key, value in cls.config.items() if key not in ("backend", "budget_binding")}
        cls.allocation = {"config_digest": digest(payload), "max_total_usd": .516,
                          "model": cls.config["model"], "phase": "main", "status": "allocated", "repeats": 2}
        write(cls.base / "runs/phase3-budget.json", {
            "authorized_total_usd": 15, "historical_allocated_usd": 1,
            "allocations": {f"main-{seed}": {**cls.allocation, "seed": seed} for seed in range(201, 209)}})

    @classmethod
    def tearDownClass(cls):
        cls.fixture.cleanup()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name) / "project"
        shutil.copytree(self.base, self.project)
        self.root = self.project / "runs/main-201"

    def tearDown(self):
        self.temporary.cleanup()

    def make_amended_review(self):
        manifest_path = self.root / "manifest.json"
        manifest = read(manifest_path)
        manifest["config"]["backend"] = "hf"
        manifest["config_hash"] = digest(manifest["config"])
        write(manifest_path, manifest)
        docs = self.project / "docs"
        docs.mkdir(exist_ok=True)
        amendment_path = docs / "v3-amendment-01-note-claims.md"
        amendment_path.write_text("Simulated amendment fixture only.")
        protocol_path = docs / "v3-protocol.md"
        protocol_path.write_text("Simulated original protocol fixture only.")
        amendment_hash = hashlib.sha256(amendment_path.read_bytes()).hexdigest()
        protocol_hash = hashlib.sha256(protocol_path.read_bytes()).hexdigest()
        write(docs / "v3-freeze.json", {"source_hash": manifest["source_hash"], "artifacts": {"docs/v3-protocol.md": protocol_hash}})
        write(docs / "v3-amendment-01-record.json", {"amendment_sha256": amendment_hash,
              "recorded_at": "2020-01-01T00:00:00+00:00", "successor_requests_before_recording": 0, "successor_episodes_before_recording": 0})
        bundle = {f"{mode}-{plan}": read(self.root / "donors" / f"s201-{mode}-{plan}.json") for mode in ("harmful", "legitimate") for plan in ("p0", "p1")}
        review = {"donor_bundle_hash": digest(bundle), "reviewer": "offline agent fixture", "reviewed_at": "2021-01-01T00:00:00+00:00",
                  "incompatible_plans_confirmed": True, "amendment_sha256": amendment_hash,
                  "amendment_path": "docs/v3-amendment-01-note-claims.md", "original_protocol_sha256": protocol_hash,
                  "review_kind": "agent_assisted_semantic_review", "successor_requests_at_review": 0, "episodes_at_review": 0,
                  "checks": {pair: {key: True for key in ("allocations_match_plans", "task_facts_preserved", "no_experiment_labels", "not_refusals")} for pair in bundle},
                  "note_annotations": {pair: {role: {"note_sha256": digest(donor["notes"][role]),
                      "note_utf8_sha256": hashlib.sha256(donor["notes"][role].encode()).hexdigest(),
                      "primitive_facts_accurate": True, "primitive_facts_evidence": "Synthetic fixture matches its table.",
                      "allocations_match_plan": True, "allocation_evidence": "Synthetic fixture matches its assigned tasks.",
                      "derived_claims": [], "strict_all_claims_accurate": True} for role in ("A", "B")} for pair, donor in bundle.items()}}
        path = self.root / "reviews/s201-notes.recorded.json"
        path.parent.mkdir(exist_ok=True)
        write(path, review)
        return path, review

    def test_complete_simulated_case_audits_and_contains_preregistered_contrasts(self):
        result = analysis.analyze(self.project)
        self.assertEqual(result["evidence_class"], "SOFTWARE_TEST_ONLY_NOT_RESEARCH_RESULTS")
        model = result["models"][0]
        self.assertEqual((model["planned_main_cases"], model["completed_main_cases"]), (8, 1))
        self.assertEqual(sum(row["eligible"] for row in result["episode_audit"]), 32)
        contrasts = {row["contrast"]: row for row in model["contrasts"] if row["mode"] == "harmful"}
        for name in ("matched_p1_minus_facts_only", "a_only_minus_facts_only", "b_only_minus_facts_only", "presence_interaction", "balanced_compatibility"):
            self.assertIn(name, contrasts)
            self.assertEqual(contrasts[name]["complete_cases"], 1)
        self.assertEqual(contrasts["balanced_compatibility"]["mean_case_differences"]["harmful_joint"], 1)
        self.assertEqual(contrasts["presence_interaction"]["mean_case_differences"]["harmful_joint"], 1)
        switches = [row for row in model["role_switching"] if row["eligible"]]
        self.assertEqual(len(switches), 4)
        self.assertTrue(all(row["roles"][role]["task_changed"] and row["roles"][role]["followed_both_plans"] for row in switches for role in ("A", "B")))

    def test_missing_gate_never_becomes_eligible_from_summary_alone(self):
        (self.root / "gates/s201-probes.json").unlink()
        result = analysis.analyze(self.project)
        self.assertFalse(any(row["eligible"] for row in result["episode_audit"]))
        self.assertEqual(result["models"][0]["completed_main_cases"], 0)
        self.assertNotEqual(result["runs"][0]["status"], "completed")
        self.assertTrue(all(row["mean_case_differences"]["harmful_joint"] is None for row in result["models"][0]["contrasts"]))

    def test_falsely_positive_gate_is_checked_against_raw_joint_assignment(self):
        path = self.root / "calls/s201-probe-A-comprehension/response.json"
        response = read(path)
        value = json.loads(response["text"])
        value["total_cost"] += 1
        response["text"] = json.dumps(value)
        write(path, response)
        result = analysis.analyze(self.project)
        self.assertEqual(result["runs"][0]["status"], "validation_failed")
        self.assertIn("probe_gate_disagrees_with_raw_responses", result["runs"][0]["gate_problems"])
        self.assertFalse(any(row["eligible"] for row in result["episode_audit"]))

    def test_missing_hf_note_review_excludes_successors(self):
        path = self.root / "manifest.json"
        manifest = read(path)
        manifest["config"]["backend"] = "hf"
        manifest["config_hash"] = digest(manifest["config"])
        write(path, manifest)
        result = analysis.analyze(self.project)
        self.assertIsNone(result["runs"][0]["gates"]["s201-note-review"])
        self.assertFalse(any(row["eligible"] for row in result["episode_audit"]))

    def test_original_action_and_note_must_match_raw_data(self):
        path = self.root / "calls/s201-harmful-p0-action-A/response.json"
        response = read(path)
        response["text"] = '{"task":"invalid"}'
        write(path, response)
        result = analysis.analyze(self.project)
        self.assertFalse(result["runs"][0]["gates"]["s201-harmful-p0"])
        self.assertFalse(any(row["eligible"] for row in result["episode_audit"]))

    def test_original_prompt_is_bound_to_the_frozen_generation_mechanism(self):
        path = self.root / "calls/s201-harmful-p0-note-A/request.json"
        request = read(path)
        request["messages"][1]["content"] += " A later unregistered instruction."
        write(path, request)
        result = analysis.analyze(self.project)
        self.assertFalse(result["runs"][0]["gates"]["s201-harmful-p0"])
        self.assertFalse(any(row["eligible"] for row in result["episode_audit"]))

    def test_role_metrics_are_derived_instead_of_trusted(self):
        path = self.root / "episodes/s201-harmful-matched-r0.json"
        episode = read(path)
        episode["role_metrics"]["A"]["delivered_note_plan_followed"] = False
        write(path, episode)
        result = analysis.analyze(self.project)
        audited = next(row for row in result["episode_audit"] if row["id"] == path.stem)
        self.assertTrue(audited["eligible"])
        self.assertFalse(audited["stored_role_metrics_match"])
        self.assertTrue(audited["role_metrics"]["A"]["delivered_note_plan_followed"])

    def test_successor_action_must_match_saved_response(self):
        path = self.root / "episodes/s201-harmful-matched-r0.json"
        episode = read(path)
        cp = read(self.root / "checkpoints/s201.json")
        episode["actions"] = cp["plans"]["legitimate"]["p0"]
        episode["outcome"] = score(cp, episode["actions"])
        write(path, episode)
        result = analysis.analyze(self.project)
        audited = next(row for row in result["episode_audit"] if row["id"] == path.stem)
        self.assertFalse(audited["eligible"])
        self.assertIn("raw_successor_or_note_routing_audit_failed", audited["exclusion_reasons"])
        self.assertEqual(sum(row["eligible"] for row in result["episode_audit"]), 31)

    def test_partial_second_case_does_not_change_equal_case_group_mean(self):
        other = self.project / "runs/main-202"
        run(other, self.config, [202], 2)
        (other / "episodes/s202-harmful-matched-r1.json").unlink()
        cp = read(other / "checkpoints/s202.json")
        path = other / "episodes/s202-harmful-matched-r0.json"
        episode = read(path)
        episode["actions"] = cp["plans"]["legitimate"]["p0"]
        episode["outcome"] = score(cp, episode["actions"])
        write(path, episode)
        for role in ("A", "B"):
            response_path = other / "calls" / f"{path.stem}-{role}" / "response.json"
            response = read(response_path)
            response["text"] = json.dumps({"task": episode["actions"][role]})
            write(response_path, response)
        result = analysis.analyze(self.project)
        group = next(row for row in result["models"][0]["groups"] if row["mode"] == "harmful" and row["condition"] == "matched")
        self.assertEqual((group["valid_episodes"], group["complete_cases"]), (3, 1))
        self.assertEqual(group["mean_metrics"]["harmful_joint"], 1)
        contrast = next(row for row in result["models"][0]["case_contrasts"] if row["seed"] == 202 and row["mode"] == "harmful" and row["contrast"] == "matched_minus_facts_only")
        self.assertFalse(contrast["complete"])
        self.assertIsNone(contrast["values"])

    def test_duplicate_allocated_case_is_rejected_instead_of_overwritten(self):
        path = self.project / "runs/phase3-budget.json"
        ledger = read(path)
        ledger["allocations"]["duplicate"] = {**self.allocation, "seed": 201}
        write(path, ledger)
        with self.assertRaisesRegex(ValueError, "Duplicate allocated"):
            analysis.analyze(self.project)

    def test_model_mismatch_excludes_attribution_and_preserves_usage_cost(self):
        path = self.root / "calls/s201-probe-A-comprehension/response.json"
        response = read(path)
        response["model"] = "unexpected-provider-model"
        response["usage"] = {"estimated_cost": .012, "prompt_tokens": 5, "completion_tokens": 7}
        write(path, response)
        result = analysis.analyze(self.project)
        self.assertEqual(result["runs"][0]["status"], "model_identity_mismatch")
        self.assertFalse(result["runs"][0]["provenance_valid"])
        self.assertFalse(any(row["eligible"] for row in result["episode_audit"]))
        self.assertAlmostEqual(result["costs"]["provider_estimated_usd"], .012)
        self.assertEqual(result["costs"]["responses_missing_cost"], 85)
        self.assertAlmostEqual(result["costs"]["dispatched_reservations_usd"], .516)
        self.assertAlmostEqual(result["costs"]["allocated_phase_ceiling_usd"], 8 * .516)

    def test_probes_only_is_incomplete_even_with_stale_complete_summary(self):
        for directory in ("episodes", "donors", "round0"):
            shutil.rmtree(self.root / directory)
        for path in (self.root / "calls").iterdir():
            if "-probe-" not in path.name:
                shutil.rmtree(path)
        result = analysis.analyze(self.project)
        actual = result["runs"][0]
        self.assertEqual((actual["status"], actual["calls"], actual["episodes"]), ("partial", 6, 0))
        self.assertFalse(actual["audited_complete"])
        self.assertIsNone(result["costs"]["provider_estimated_usd"])

    def test_amended_review_retains_false_claim_and_original_strict_failure(self):
        path, review = self.make_amended_review()
        note = review["note_annotations"]["harmful-p0"]["A"]
        note["derived_claims"] = [{"claim": "This synthetic allocation is globally optimal.", "verdict": "false", "evidence": "Offline fixture annotation only; not model evidence."}]
        note["strict_all_claims_accurate"] = False
        write(path, review)
        result = analysis.analyze(self.project)
        amendment = result["runs"][0]["amendment"]
        self.assertTrue(amendment["valid"])
        self.assertFalse(amendment["original_strict_rule_all_notes_accurate"])
        self.assertFalse(amendment["strict_accurate_note_pairs"]["harmful-p0"])
        self.assertTrue(result["runs"][0]["audited_complete"])
        self.assertIn("amended_prospective_protocol_01", result["protocol_labels"])

    def test_amendment_hash_and_symmetric_note_annotations_are_required(self):
        path, review = self.make_amended_review()
        review["note_annotations"]["harmful-p1"]["B"]["note_sha256"] = "wrong"
        write(path, review)
        result = analysis.analyze(self.project)
        self.assertFalse(result["runs"][0]["amendment"]["valid"])
        self.assertIn("note hash", result["runs"][0]["amendment"]["error"])
        self.assertFalse(any(row["eligible"] for row in result["episode_audit"]))

    def test_review_recorded_after_successor_files_is_rejected(self):
        path, review = self.make_amended_review()
        review["reviewed_at"] = "2099-01-01T00:00:00+00:00"
        write(path, review)
        result = analysis.analyze(self.project)
        self.assertFalse(result["runs"][0]["amendment"]["valid"])
        self.assertIn("follows", result["runs"][0]["amendment"]["error"])

    def test_pilot_is_audited_but_excluded_from_main_estimates(self):
        path = self.project / "runs/phase3-budget.json"
        ledger = read(path)
        ledger["allocations"]["main-201"]["phase"] = "pilot"
        write(path, ledger)
        result = analysis.analyze(self.project)
        self.assertEqual(sum(row["eligible"] for row in result["episode_audit"]), 32)
        self.assertEqual(result["models"][0]["completed_main_cases"], 0)
        self.assertTrue(all(row["valid_episodes"] == 0 for row in result["models"][0]["groups"]))


if __name__ == "__main__":
    unittest.main()

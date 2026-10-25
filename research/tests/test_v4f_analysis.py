"""Independent synthetic provenance/parser/accounting regressions; no model calls."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


ROOT = Path(__file__).parents[1]
a = load("amended_analysis_test", ROOT/"scripts/analyze_v4f_study.py")
fixture = load("amended_fixture_test", Path(__file__).with_name("v4f_fixtures.py"))
f = fixture.f


def write(path, value):
    f.atomic_json(Path(path), value)


class FenceFirstSuccessor(fixture.FixtureBackend):
    def complete(self, messages, meta, config):
        response = super().complete(messages, meta, config)
        if meta["kind"] == "successor":
            response["text"] = "```json\n" + response["text"] + "\n```"
        return response


class AmbiguousDispatch(fixture.FixtureBackend):
    def complete(self, messages, meta, config):
        if meta["kind"] == "successor":
            raise RuntimeError("Simulated dispatch with no durable response")
        return super().complete(messages, meta, config)


class NoNewCalls:
    def complete(self, *args, **kwargs):
        raise AssertionError("A cached-prefix replay must not dispatch any new call")


class V4FAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.project = Path(cls.tmp.name)/"original-project"
        cls.project.mkdir()
        env = fixture.full_cohort(cls.project, seal=False)
        cls.name = "v4f-main-qwen-201"
        old = env["sources"][cls.name]
        old_config = a.read(old/"manifest.json")["config"]
        # Original strict execution must really reject the wrapper. The fixture
        # loader imports the amended module, so explicitly restore this alias.
        f.v4.parse_action = a.STRICT_ACTION
        f.v4.run(old, old_config, 201, "main", stage="donors", backend=fixture.FixtureBackend())
        review = a.read(old/"reviews/s201-annotations.template.json")
        review.update(reviewer="Software test only; deliberately false content flags", reviewed_at=f.now())
        for roles in review["annotations"].values():
            for entry in roles.values():
                entry.update(primitive_facts_accurate=False, recipient_assignment_matches=False,
                             refusal=True, experiment_labels_present=True)
                entry.update({key: "Synthetic flag used to test content-independent admission." for key in f.v4.ANNOTATION_EVIDENCE})
                entry["derived_claims"] = [{"claim":"Synthetic assertion", "verdict":"false", "evidence":"Software fixture only"}]
        write(old/"reviews/s201-annotations.json", review)
        f.v4.run(old, old_config, 201, "main", backend=FenceFirstSuccessor())
        old_episodes = list((old/"episodes").glob("*.json"))
        assert len(old_episodes) == 1 and a.read(old_episodes[0])["status"] != "completed"
        f.v4.parse_action = f.parse_action
        new = cls.project/"runs"/cls.name
        shutil.rmtree(new)
        f.prepare(new, old, env["configs"][cls.name], 201, "main", a.read(cls.project/"docs/protocol.json"))
        closure = a.read(cls.project/"docs/closure.json"); closure["closed_at"] = f.now()
        write(cls.project/"docs/closure.json", closure)
        freeze = a.read(env["freeze"]); freeze["frozen_at"] = f.now()
        write(env["freeze"], freeze)
        f.finalize_preparation(env["ledger"])
        for family in ("qwen", "gptoss"):
            name = f"v4f-qualification-{family}-902"
            f.run(cls.project/"runs"/name, env["configs"][name], 902, "qualification", backend=fixture.FixtureBackend())
        f.run(new, env["configs"][cls.name], 201, "main", backend=fixture.FixtureBackend())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def clone(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)/"extracted-project"
        shutil.copytree(self.project, root)
        return root

    def test_amended_reuses_calls_once_preserves_strict_failure_and_all_notes(self):
        result = a.analyze(self.project)
        self.assertEqual(result["evidence_class"], "SOFTWARE_TEST_ONLY_NOT_RESEARCH_RESULTS")
        self.assertTrue(result["post_start_amendment"])
        qwen = next(m for m in result["models"] if m["model"] == "simulated-qwen")
        self.assertEqual(qwen["eligible_main_episodes"], 32)
        self.assertTrue(all(c["complete_cases"] == 0 for c in qwen["contrasts"] if c["subset"].startswith("secondary")))
        self.assertTrue(all(c["complete_cases"] == 1 for c in qwen["contrasts"] if c["subset"].startswith("primary")))
        self.assertEqual(result["costs"]["unique_planned_calls"], 188)
        groups = result["costs"]["source_groups"]
        self.assertEqual(groups["inherited_v4"]["reserved_calls"] + groups["newly_dispatched_v4f"]["reserved_calls"], 188)
        self.assertEqual(groups["inherited_v4"]["reserved_calls"], 125)
        self.assertEqual(groups["newly_dispatched_v4f"]["reserved_calls"], 63)
        recovered = [e for e in result["episodes"] if e["successor_wrapper_used"]]
        self.assertEqual(len(recovered), 1)
        self.assertTrue(recovered[0]["eligible"])
        self.assertNotEqual(recovered[0]["original_saved_episode_status"], "completed")
        self.assertEqual(recovered[0]["execution_composition"], "mixed_original_and_new")
        main = next(r for r in result["runs"] if r["run_id"] == self.name)
        self.assertEqual(main["annotation_audit"]["inherited_successor_invocations"], 1)
        self.assertTrue(main["annotation_audit"]["complete"])

    def test_portable_rebase_cannot_read_original_location_or_external_paths(self):
        root = self.clone()
        hidden = self.project.with_name("original-unavailable")
        self.project.rename(hidden)
        try:
            result = a.analyze(root)
            self.assertEqual(result["costs"]["unique_planned_calls"], 188)
            context = a.AuditContext(root, root/"runs/phase4f-budget.json")
            with self.assertRaisesRegex(ValueError, "External"):
                context.path("/tmp/not-under-the-original-project/evidence.json")
            (root/"escape").symlink_to("/tmp")
            with self.assertRaisesRegex(ValueError, "escapes"):
                context.path(str(context.original_project/"escape/file"))
        finally:
            hidden.rename(self.project)

    def test_missing_preparation_or_changed_original_bytes_fail_before_analysis(self):
        for mutation in ("missing", "raw", "blockers", "artifact"):
            root = self.clone()
            if mutation == "missing":
                (root/"runs/v4f-main-gptoss-208/source_provenance.json").unlink()
            elif mutation == "raw":
                path = next((root/"runs/v4-main-qwen-201/calls").glob("*/response.json"))
                path.write_bytes(path.read_bytes()+b" ")
            elif mutation == "blockers":
                path = root/"docs/preparation.json"
                seal = a.read(path)
                seal["inherited_global_blockers"] = [{"model":"simulated-qwen", "source":"invented", "kind":"usage_error.json"}]
                write(path, seal)
            else:
                path = root/"scripts/v4f_runner.py"
                path.write_bytes(path.read_bytes()+b"\n# changed\n")
            with self.assertRaises((ValueError, FileNotFoundError)):
                a.analyze(root)

    def test_parse_receipt_and_annotation_ancestry_are_checked(self):
        root = self.clone()
        path = next((root/"runs"/self.name/"parse_receipts").glob("s201-harmful-*-r0-A.json"))
        receipt = a.read(path); receipt["raw_response_sha256"] = "bad"
        write(path, receipt)
        result = a.analyze(root)
        affected = [e for e in result["episodes"] if path.stem == e["id"]+"-A"]
        self.assertEqual(len(affected), 1)
        self.assertFalse(affected[0]["eligible"])
        root = self.clone()
        path = root/"runs"/self.name/"reviews/s201-annotations.completion.json"
        receipt = a.read(path); receipt["inherited_successor_invocations"] = 0
        write(path, receipt)
        result = a.analyze(root)
        main = next(r for r in result["runs"] if r["run_id"] == self.name)
        self.assertFalse(main["annotation_audit"]["complete"])
        self.assertTrue(all(not e["eligible"] for e in result["episodes"]))

    def test_new_invocation_before_freeze_cannot_be_inherited(self):
        root = self.clone()
        p = a.read(root/"runs"/self.name/"source_provenance.json")
        path = next(pth for pth in (root/"runs"/self.name/"calls").glob("*/invocation.json") if pth.parent.name not in p["copied_calls"])
        invocation = a.read(path); invocation["at"] = "2020-01-01T00:00:00+00:00"
        write(path, invocation)
        with self.assertRaisesRegex(ValueError, "precedes"):
            a.analyze(root)

    def test_wrapper_grammar_and_wrong_competence_do_not_receive_semantic_rescue(self):
        cp = a.base.v4.probe_checkpoint(206)
        expected = a.base.v4.probe_expected(cp)
        body = {"task": expected["actions"]["B"], "joint_assignment": expected["actions"], "total_cost": expected["total_cost"]+1}
        response = {"text":"```json\n"+json.dumps(body)+"\n```", "finish_reason":"stop"}
        result = a.parse_classification("s206-probe-B-comprehension", response, 206)
        self.assertFalse(result["strict_schema_valid"])
        self.assertTrue(result["amended_schema_valid"])
        self.assertFalse(result["semantic_checks"]["total_cost_matches"])
        for text in ("prose\n"+response["text"], response["text"]+"\nextra", response["text"].replace("```json", "```JSON"),
                     "```json\n{}\n```\n```json\n{}\n```", "```\n{}\n```", "```json\n{bad}\n```"):
            with self.subTest(text=text):
                value = a.parse_classification("s206-probe-B-comprehension", {**response,"text":text}, 206)
                self.assertFalse(value["amended_schema_valid"])

    def test_optional_strict_input_must_bind_the_exact_original_runs(self):
        context = a.AuditContext(self.project, self.project/"runs/phase4f-budget.json")
        context.verify_all_prepared()
        source_runs = []
        episodes = []
        requests = responses = 0
        for p in context.provenance.values():
            root = context.path(p["source_root"])
            manifest = a.read(root/"manifest.json")
            source_runs.append({"run_id":p["source_run_id"], "manifest":manifest, "model":manifest["config"]["model"],
                                "seed":manifest["seed"], "cohort":manifest["cohort"]})
            episodes += [{"run_id":p["source_run_id"], "id":path.stem} for path in (root/"episodes").glob("*.json")]
            requests += len(list((root/"calls").glob("*/request.json")))
            responses += len(list((root/"calls").glob("*/response.json")))
        strict = {"schema_version":4, "runs":source_runs, "episodes":episodes,
                  "costs":{"calls_reserved":requests,"responses":responses}}
        self.assertTrue(a.bind_strict_analysis(strict,context)["exact_original_run_manifest_bindings"])
        for mutation in ("unrelated", "manifest", "episode", "calls"):
            value = copy.deepcopy(strict)
            if mutation == "unrelated": value["runs"][0]["run_id"] = "unrelated-study"
            elif mutation == "manifest": value["runs"][0]["manifest"]["source_hash"] = "wrong"
            elif mutation == "episode": value["episodes"][0]["id"] = "unrelated-episode"
            else: value["costs"]["calls_reserved"] += 1
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                a.bind_strict_analysis(value,context)

    def test_unresolved_inherited_tail_keeps_valid_cached_prefix_and_denominators(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            env = fixture.full_cohort(project, seal=False)
            name = "v4f-main-gptoss-204"
            source = env["sources"][name]
            config = a.read(source/"manifest.json")["config"]
            f.v4.run(source, config, 204, "main", stage="donors", backend=fixture.FixtureBackend())
            review = a.read(source/"reviews/s204-annotations.template.json")
            review.update(reviewer="Software prefix-only test", reviewed_at=f.now())
            for roles in review["annotations"].values():
                for entry in roles.values():
                    entry.update(primitive_facts_accurate=True, recipient_assignment_matches=True,
                                 refusal=False, experiment_labels_present=False)
                    entry.update({key:"Synthetic prefix test evidence." for key in f.v4.ANNOTATION_EVIDENCE})
            write(source/"reviews/s204-annotations.json", review)
            f.v4.run(source, config, 204, "main", backend=fixture.FixtureBackend(), stop_after=2)
            with self.assertRaisesRegex(RuntimeError, "Provider call"):
                f.v4.run(source, config, 204, "main", backend=AmbiguousDispatch())
            self.assertEqual(len(list((source/"calls").glob("*/request.json"))), 27)
            self.assertEqual(len(list((source/"calls").glob("*/response.json"))), 26)
            target = project/"runs"/name
            shutil.rmtree(target)
            f.prepare(target, source, env["configs"][name], 204, "main", a.read(project/"docs/protocol.json"))
            closure = a.read(project/"docs/closure.json"); closure["closed_at"] = f.now()
            write(project/"docs/closure.json", closure)
            freeze = a.read(env["freeze"]); freeze["frozen_at"] = f.now()
            write(env["freeze"], freeze)
            f.finalize_preparation(env["ledger"])
            try:
                f.run(target, env["configs"][name], 204, "main", backend=NoNewCalls())
            except (ValueError, RuntimeError):
                pass  # The inherited unresolved tail must remain a hard stop.
            result = a.analyze(project)
            run = next(r for r in result["runs"] if r["run_id"] == name)
            model = next(m for m in result["models"] if m["model"] == "simulated-gptoss")
            self.assertEqual(run["status"], "unresolved_provider_call")
            self.assertEqual(run["audited_episode_counts"]["eligible"], 2)
            self.assertEqual((run["calls"],run["responses"],run["unresolved_calls"]), (27,26,1))
            self.assertEqual((model["eligible_main_episodes"],model["missing_or_invalid_main_episodes"]), (2,254))
            self.assertEqual(result["costs"]["source_groups"]["newly_dispatched_v4f"]["reserved_calls"], 0)
            self.assertEqual(result["costs"]["calls_reserved"]-result["costs"]["responses"], 1)


if __name__ == "__main__":
    unittest.main()

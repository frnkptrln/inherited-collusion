"""Offline evidence falsification and V4 estimand/denominator checks."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC=importlib.util.spec_from_file_location("analyze_v4_study",Path(__file__).parents[1]/"scripts/analyze_v4_study.py")
a=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(a)
v4=a.v4


def write(path,value):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(value))


def build(project,false_flags=False,complete=True):
    project=Path(project)
    allocations={}
    configs={}
    for cohort,seed,name in [("qualification",902,"qualification")]+[("main",s,f"main-{s}") for s in range(201,209)]:
        config=v4.load_config("mock",None,cohort,seed)
        allocations[name]={"model":config["model"],"cohort":cohort,"seed":seed,"repeats":v4.design(cohort,seed)["repeats"],
            "max_total_usd":0,"status":"allocated","config_digest":a.digest({k:v for k,v in config.items() if k not in ("backend","budget_binding")})}
        configs[name]=config
    write(project/"runs/phase4-budget.json",{"allocations":allocations,"historical_allocated_usd":1.594})
    v4.run(project/"runs/qualification",configs["qualification"],902,"qualification")
    root=project/"runs/main-201"
    v4.run(root,configs["main-201"],201,"main",stage="donors")
    review=a.read(root/"reviews/s201-annotations.template.json")
    review.update(reviewer="offline test only",reviewed_at="2026-01-01T00:00:00+00:00")
    for roles in review["annotations"].values():
        for entry in roles.values():
            entry.update(primitive_facts_accurate=not false_flags,recipient_assignment_matches=not false_flags,
                         refusal=false_flags,experiment_labels_present=false_flags)
            entry.update({k:"Synthetic evidence for offline verification only." for k in v4.ANNOTATION_EVIDENCE})
            entry["derived_claims"]=[{"claim":"Synthetic claim.","verdict":"false" if false_flags else "true","evidence":"Offline fixture only."}]
    write(root/"reviews/s201-annotations.json",review)
    if complete:
        v4.run(root,configs["main-201"],201,"main")
    return root


class V4AnalysisTests(unittest.TestCase):
    def test_all_false_content_flags_stay_in_primary_but_not_faithful_subset(self):
        with tempfile.TemporaryDirectory() as tmp:
            build(tmp,false_flags=True)
            result=a.analyze(tmp)
            model=result["models"][0]
            self.assertEqual((model["planned_main_cases"],model["allocated_main_cases"],model["eligible_main_episodes"]),(8,8,32))
            self.assertEqual(result["costs"]["calls_reserved"],92)
            self.assertTrue(all(e["eligible"] for e in result["episodes"]))
            primary=[x for x in model["contrasts"] if x["subset"].startswith("primary")]
            secondary=[x for x in model["contrasts"] if x["subset"].startswith("secondary")]
            self.assertTrue(all(x["complete_cases"]==1 for x in primary))
            self.assertTrue(all(x["complete_cases"]==0 for x in secondary))
            self.assertTrue(all(x["planned_cases"]==8 for x in primary))
            self.assertTrue(all(x["primitive_false_n"]==4 and x["refusal_n"]==4 for x in model["annotation_counts"]))
            self.assertFalse(model["manipulation_criterion_met"])
            self.assertFalse(model["descriptive_labels"]["qualified_negative_for_produced_handoffs"])
            self.assertTrue(all(x["planned_episodes"]==16 and x["valid_episodes"]==2 for x in model["groups"]))
            self.assertTrue(all(x["complete_case_count"]==1 for x in model["groups"]))
            self.assertEqual(result["evidence_class"],"SOFTWARE_TEST_ONLY_NOT_RESEARCH_RESULTS")
            self.assertIsNone(result["costs"]["provider_estimated_usd"])
            self.assertFalse(result["costs"]["provider_cost_coverage_complete"])

    def test_faithful_subset_uses_presuccessor_content_not_successor_harm(self):
        with tempfile.TemporaryDirectory() as tmp:
            build(tmp)
            result=a.analyze(tmp)
            contrasts=result["models"][0]["contrasts"]
            self.assertTrue(all(x["complete_cases"]==1 for x in contrasts))
            main=next(r for r in result["runs"] if r["run_id"]=="main-201")
            self.assertEqual(main["qualification_audit"],{"passed":True,"not_model_evidence":True})
            self.assertTrue(main["annotation_audit"]["complete"])

    def test_raw_successor_tampering_excludes_observation_and_incomplete_pair_not_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=build(tmp)
            path=root/"calls/s201-harmful-matched-r0-A/response.json"
            raw=a.read(path);raw["text"]='{"task":"unknown"}'
            write(path,raw)
            result=a.analyze(tmp)
            model=result["models"][0]
            self.assertEqual(model["eligible_main_episodes"],31)
            contrast=next(c for c in model["contrasts"] if c["mode"]=="harmful" and c["contrast"]=="matched_minus_facts_only" and c["subset"].startswith("primary"))
            self.assertEqual(contrast["complete_cases"],0)
            self.assertIsNone(contrast["mean_case_differences"]["harmful_joint"])
            group=next(g for g in model["groups"] if g["mode"]=="harmful" and g["condition"]=="matched")
            self.assertEqual((group["valid_episodes"],group["missing_or_invalid_episodes"]),(1,15))
            self.assertEqual(group["complete_case_count"],0)
            main=next(r for r in result["runs"] if r["run_id"]=="main-201")
            self.assertEqual(main["saved_summary_status"],"completed")
            self.assertEqual(main["status"],"successor_or_prerequisite_audit_failed")

    def test_changed_note_hash_invalidates_prerequisites_without_reclassifying_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=build(tmp)
            path=root/"donors/s201-harmful-p0.json"
            donor=a.read(path);donor["note_hashes"]["A"]="tampered"
            write(path,donor)
            result=a.analyze(tmp)
            self.assertEqual(result["models"][0]["eligible_main_episodes"],0)
            main=next(r for r in result["runs"] if r["run_id"]=="main-201")
            self.assertFalse(main["donor_audits"]["harmful-p0"]["technical_passed"])
            self.assertFalse(main["annotation_audit"]["complete"])

    def test_receipt_after_successor_invocation_cannot_validate_annotation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=build(tmp)
            path=root/"reviews/s201-annotations.completion.json"
            value=a.read(path);value["at"]="2099-01-01T00:00:00+00:00"
            write(path,value)
            result=a.analyze(tmp)
            main=next(r for r in result["runs"] if r["run_id"]=="main-201")
            self.assertFalse(main["annotation_audit"]["complete"])
            self.assertIn("precedes",main["annotation_audit"]["error"])
            self.assertEqual(result["models"][0]["eligible_main_episodes"],0)

    def test_generation_or_source_tampering_is_a_hard_audit_error(self):
        for kind in ("generation","source"):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as tmp:
                root=build(tmp)
                if kind=="generation":
                    path=root/"calls/s201-probe-A-comprehension/request.json"
                    value=a.read(path);value["temperature"]=99
                    write(path,value)
                else:
                    path=root/"source_snapshot/v4_runner.py"
                    path.write_text(path.read_text()+"\n# tampered\n")
                with self.assertRaisesRegex(ValueError,"mismatch"):
                    a.analyze(tmp)

    def test_qualification_only_has_costs_and_no_fake_main_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=build(tmp,complete=False)
            result=a.analyze(tmp)
            self.assertEqual(result["costs"]["calls_reserved"],28)
            self.assertEqual(result["models"][0]["eligible_main_episodes"],0)
            self.assertFalse(result["models"][0]["descriptive_labels"]["observed_harmful_transfer"])
            self.assertEqual(result["models"][0]["missing_or_invalid_main_episodes"],256)
            main=next(r for r in result["runs"] if r["run_id"]=="main-201")
            self.assertFalse(main["annotation_audit"]["complete"])
            # A schema-valid wrong numerical answer is different from malformed
            # JSON. Neither may be converted into a successful comprehension.
            path=root/"calls/s201-probe-B-comprehension/response.json"
            original=a.read(path)
            wrong=copy.deepcopy(original);parsed=json.loads(wrong["text"])
            parsed["total_cost"]+=1;wrong["text"]=json.dumps(parsed)
            write(path,wrong)
            failed=next(r for r in a.analyze(tmp)["runs"] if r["run_id"]=="main-201")
            row=next(r for r in failed["probe_audit"]["rows"] if r["id"]==path.parent.name)
            self.assertEqual(failed["status"],"competence_failed")
            self.assertTrue(row["schema_valid"])
            self.assertFalse(row["checks"]["total_cost_matches"])
            malformed=copy.deepcopy(original);malformed["text"]="not JSON"
            write(path,malformed)
            failed=next(r for r in a.analyze(tmp)["runs"] if r["run_id"]=="main-201")
            row=next(r for r in failed["probe_audit"]["rows"] if r["id"]==path.parent.name)
            self.assertEqual(failed["status"],"probe_schema_failed")
            self.assertFalse(row["schema_valid"])
            self.assertEqual(failed["saved_summary_status"],main["saved_summary_status"])
            self.assertEqual(failed["calls"],main["calls"])
            write(path,original)
            manifest=a.read(root/"manifest.json")
            requests,responses,_,_,issues=a.call_audit(root,manifest["config"])
            call_id=path.parent.name
            for kind in ("prompt","missing","identity"):
                req,res,err=copy.deepcopy(requests),copy.deepcopy(responses),copy.deepcopy(issues)
                if kind=="prompt": req[call_id]["messages"]=[]
                elif kind=="missing": del res[call_id]
                else: err[call_id]=["reported_model_mismatch"]
                row=next(r for r in a.probe_audit(root,201,req,res,err)["rows"] if r["id"]==call_id)
                self.assertIsNone(row["schema_valid"],kind)
                self.assertFalse(row["passed"],kind)

    def test_equal_case_weight_and_two_repeat_completeness(self):
        model="synthetic"
        runs=[{"model":model,"cohort":"main","seed":s,"annotation_audit":{"strict_pairs":{"harmful-p0":True}}} for s in range(201,209)]
        episodes=[]
        for seed,matched in ((201,[0,1]),(202,[1,1])):
            for condition in ("matched","facts_only"):
                for rep in (0,1):
                    harm=matched[rep] if condition=="matched" else 0
                    episodes.append({"model":model,"eligible":True,"seed":seed,"mode":"harmful","condition":condition,"repeat":rep,
                        "outcome":{k:harm if k=="harmful_joint" else 0 for k in a.METRICS},
                        "role_metrics":{r:{"nominal_source_plan_followed":None} for r in a.ROLES},"actions":{"A":"T1","B":"T2"}})
        def contrast(result):
            return next(c for c in result["contrasts"] if c["mode"]=="harmful" and c["contrast"]=="matched_minus_facts_only" and c["subset"].startswith("primary"))
        complete=contrast(a.aggregate_model(model,runs,episodes))
        self.assertEqual((complete["complete_cases"],complete["mean_case_differences"]["harmful_joint"]),(2,.75))
        partial=[e for e in episodes if not (e["seed"]==202 and e["condition"]=="matched" and e["repeat"]==1)]
        incomplete=contrast(a.aggregate_model(model,runs,partial))
        self.assertEqual((incomplete["complete_cases"],incomplete["mean_case_differences"]["harmful_joint"]),(1,.5))
        self.assertEqual(incomplete["planned_cases"],8)

    def test_empty_raw_choices_and_missing_usage_are_durable_errors_not_analyzer_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            config={**v4.load_config("mock",None,"qualification",902),"backend":"hf"}
            folder=root/"calls/test"
            write(folder/"invocation.json",{"at":"2026-01-01T00:00:00+00:00","kind":"probe"})
            request={"id":"test","generation":{k:config[k] for k in ("model","provider","max_tokens")},
                "temperature":config["temperature"],"top_p":config["top_p"],"messages":[{"role":"user","content":"x"}],"metadata_not_sent_to_model":{"kind":"probe"}}
            write(folder/"request.json",request)
            write(folder/"response.json",{"model":config["model"],"text":None,"finish_reason":None,"usage":{},
                "provider_response":{"model":config["model"],"choices":[],"usage":None}})
            _,_,_,costs,issues=a.call_audit(root,config)
            self.assertIn("raw_provider_schema_error",issues["test"])
            self.assertIn("missing_or_invalid_usage",issues["test"])
            self.assertIsNone(costs[0]["provider_estimated_usd"])

    def test_top_level_usage_cannot_disagree_with_preserved_raw_usage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            config={**v4.load_config("mock",None,"qualification",902),"backend":"hf","reserved_usd_per_call":1}
            folder=root/"calls/test"
            write(folder/"invocation.json",{"at":"2026-01-01T00:00:00+00:00","kind":"probe"})
            write(folder/"request.json",{"id":"test","generation":{k:config[k] for k in ("model","provider","max_tokens")},
                "temperature":config["temperature"],"top_p":config["top_p"],"messages":[],"metadata_not_sent_to_model":{"kind":"probe"}})
            usage={"prompt_tokens":1,"completion_tokens":1,"estimated_cost":.1}
            raw={"model":config["model"],"choices":[{"finish_reason":"stop","message":{"content":"{}"}}],"usage":{**usage,"estimated_cost":.9}}
            write(folder/"response.json",{"model":config["model"],"text":"{}","finish_reason":"stop","usage":usage,"provider_response":raw})
            audit=a.call_audit(root,config)
            self.assertIn("raw_provider_usage_inconsistent",audit[-1]["test"])
            self.assertIsNone(audit[-2][0]["provider_estimated_usd"])
            self.assertIsNone(audit[-2][0]["catalog_estimated_usd"])
            self.assertEqual(audit[-2][0]["unverified_top_level_estimated_usd"],.1)

    def test_model_wide_usage_stop_is_not_reported_as_partial_or_completed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=build(tmp,complete=False)
            write(root/"model_usage_stop.json",{"status":"usage_validation_failed","blocked_by_run":"other-case"})
            result=a.analyze(tmp)
            run=next(r for r in result["runs"] if r["run_id"]=="main-201")
            self.assertEqual(run["status"],"usage_budget_error")
            self.assertIn("model_usage_stop.json",run["error_artifacts"])


if __name__=="__main__":
    unittest.main()

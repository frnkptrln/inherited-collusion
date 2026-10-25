import contextlib,io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import close_v6

class CloseoutTests(unittest.TestCase):
    def fixture(self,root,status,cost):
        def write(path,value):
            p=root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value))
        write('runs/phase6-budget.json',{'allocations':{'v6-qwen-301':{'config':'configs/test.json'}}})
        write('docs/v6-freeze.json',{'artifacts':{}})
        write('configs/test.json',{'reserved_usd_per_call':.01})
        write('runs/v6-qwen-301/summary.json',{'status':status})
        write('runs/v6-qwen-301/invocation_logs/test.start.json',{})
        write('runs/v6-qwen-301/invocation_logs/test.result.json',{'returncode':2})
        write('runs/v6-qwen-301/calls/c1/request.json',{})
        write('runs/v6-qwen-301/calls/c1/response.json',{'usage':{'estimated_cost':cost}})
    def test_invalid_usage_is_sealed_with_full_reservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp);self.fixture(r,'usage_validation_failed',None)
            with patch.object(sys,'argv',['close','--project',str(r)]),contextlib.redirect_stdout(io.StringIO()):close_v6.main()
            result=json.loads((r/'docs/v6-closeout-record.json').read_text())
            self.assertFalse(result['returned_cost_coverage_complete']);self.assertEqual(result['new_reserved_usd'],.01)
            self.assertEqual(len(result['unverified_cost_responses']),1)
    def test_partial_worker_cannot_be_sealed(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp);self.fixture(r,'partial',.002)
            with patch.object(sys,'argv',['close','--project',str(r)]),self.assertRaises(AssertionError):close_v6.main()
            self.assertFalse((r/'docs/v6-closeout-record.json').exists())
if __name__=='__main__':unittest.main()

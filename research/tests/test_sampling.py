import types
import sys
import unittest
from unittest.mock import patch
from inherited_collusion.backends import HFBackend
from inherited_collusion.runner import Calls
from inherited_collusion.storage import read
import tempfile
from pathlib import Path

class SamplingTests(unittest.TestCase):
    def test_backend_sends_and_request_records_sampling(self):
        seen = {}
        class Response(dict):
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content='{"task":"T1"}'), finish_reason='stop')]
            model='fixture'
            usage={}
        class Client:
            def __init__(self, **kwargs): seen['client']=kwargs
            def chat_completion(self, **kwargs): seen['request']=kwargs;return Response()
        config={'backend':'hf','model':'fixture','provider':'explicit','max_tokens':4096,'max_calls':1,'max_total_usd':1,'reserved_usd_per_call':.015,'max_request_bytes':16000,'temperature':.6,'top_p':.95}
        messages=[{'role':'user','content':'test'}]
        with tempfile.TemporaryDirectory() as tmp, patch.dict(sys.modules, {'huggingface_hub':types.SimpleNamespace(InferenceClient=Client)}):
            Calls(tmp,config,HFBackend()).call('test',messages,{'kind':'probe'})
            saved=read(Path(tmp)/'calls/test/request.json')
            for key in ('temperature','top_p'):
                self.assertEqual(saved[key],config[key]);self.assertEqual(seen['request'][key],config[key])
            self.assertEqual(seen['client']['timeout'],180)
            self.assertEqual(seen['request']['max_tokens'],4096)

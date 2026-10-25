from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,inspect,re
from decimal import Decimal
from types import SimpleNamespace
import huggingface_hub
from huggingface_hub.inference._providers.deepinfra import DeepInfraConversationalTask
root=Path(__file__).resolve().parent
model='openai/gpt-oss-120b'
load=lambda f:json.loads((root/f).read_text())
tok=load('gpt-oss-tokenizer.json');mapping=load('gpt-oss-mapping.json');catalog=next(x for x in load('router-models.json')['data'] if x['id']==model);provider=next(x for x in catalog['providers'] if x['provider']=='deepinfra')
bs=list(range(ord('!'),ord('~')+1))+list(range(0xA1,0xAD))+list(range(0xAE,0x100));cs=bs.copy();extra=0
for b in range(256):
 if b not in bs:bs.append(b);cs.append(256+extra);extra+=1
symbols=[chr(x)for x in cs];missing=[ord(x)for x in symbols if x not in tok['model']['vocab']]
assert not missing and len(set(symbols))==256
assert tok['normalizer'] is None and tok['model']['type']=='BPE'
steps=tok['pre_tokenizer']['pretokenizers'];assert steps[0]['type']=='Split' and steps[0]['behavior']=='Isolated' and steps[1]['type']=='ByteLevel' and steps[1]['add_prefix_space'] is False
bound={'model':model,'tokenizer_sha256':hashlib.sha256((root/'gpt-oss-tokenizer.json').read_bytes()).hexdigest(),'normalizer':None,'pretokenizer':tok['pre_tokenizer'],'post_processor':tok['post_processor'],'model_options':{k:v for k,v in tok['model'].items() if k not in ('vocab','merges')},'vocabulary_size':len(tok['model']['vocab']),'bytelevel_alphabet_present':256,'missing_alphabet_symbols':missing,'claim':'For this downloaded tokenizer, ordinary text token count cannot exceed raw UTF-8 bytes before chat framing: split isolates without duplication, ByteLevel adds no prefix space, all 256 one-byte symbols exist, BPE merges or whole-vocabulary lookup do not increase count. max(raw,NFC) serialized message bytes is conservative for this no-normalizer tokenizer.','limits':['Does not verify the provider tokenizer or served weights','Chat-template/server framing has a separately assumed 2048-token allowance','Only text messages without tools or attachments covered']}
(root/'tokenizer-bound-inspection.json').write_text(json.dumps(bound,indent=2)+'\n')
helper=DeepInfraConversationalTask();params={'model':'ignored-caller-copy','max_tokens':8192,'temperature':.6,'top_p':.95}
payload=helper._prepare_payload_as_dict([{'role':'user','content':'Offline payload construction only.'}],params,SimpleNamespace(provider_id=model))
assert payload['model']==model and 'reasoning_effort' not in payload and 'extra_body' not in payload
package=Path(huggingface_hub.__file__).resolve().parent
sdkfiles=['inference/_client.py','inference/_providers/_common.py','inference/_providers/deepinfra.py']
sdk={'huggingface_hub_version':huggingface_hub.__version__,'scope':'Pure payload construction and source read only. No client instantiation, token lookup, request preparation or HTTP request.','source_sha256':{f:hashlib.sha256((package/f).read_bytes()).hexdigest()for f in sdkfiles},'payload_model':payload['model'],'payload_generation':{k:v for k,v in payload.items()if k!='messages'},'reasoning_effort_sent':False,'extra_body_sent':False,'provider':'deepinfra','route':'https://router.huggingface.co/deepinfra/v1/openai/chat/completions','response_validation':'SDK parses returned model field; study runner must strictly compare it.'}
(root/'sdk-inspection.json').write_text(json.dumps(sdk,indent=2)+'\n')
input_tokens=10000+2048;output_tokens=8192;cost=(Decimal(input_tokens)*Decimal('.037')+Decimal(output_tokens)*Decimal('.17'))/Decimal(1000000)
assert cost<Decimal('.002')
sourceindex=load('retrieval-index.json')
for row in sourceindex:
 if row.get('status')==200:assert hashlib.sha256((root/row['file']).read_bytes()).hexdigest()==row['sha256']
openai_doc={'file':'openai-model-doc.md','url':'https://developers.openai.com/api/docs/models/gpt-oss-120b','retrieved_by':'OpenAI documentation connector, searched then fetched','sha256':hashlib.sha256((root/'openai-model-doc.md').read_bytes()).hexdigest()}
report={'checked_at':datetime.now(timezone.utc).isoformat(),'candidate_selection':'One parent-prespecified additional reasoning family chosen before any successor-effect observation; no further model search after a failed six-probe gate.','requested_hub_id':model,'provider':'deepinfra','provider_mapping':mapping['inferenceProviderMapping']['deepinfra'],'hub_revision':mapping['sha'],'provider_catalog':provider,'generation':{'temperature':.6,'top_p':.95,'max_tokens':8192,'extra_body':None,'reasoning_effort_sent':False,'effective_reasoning_effort':'provider default unspecified; not established as medium or high'},'reasoning_documentation':{'author_template_default':'medium','author_template_lines':'gpt-oss-chat-template.jinja:203-206','provider_generic_documentation_default':'high for reasoning models','provider_model_specific_schema_default':None,'interpretation':'Defaults conflict across author and generic provider documentation; neither establishes effective routed service setting. Parent explicitly chose to omit override before freeze.'},'reservation':{'max_request_bytes':10000,'byte_measure':'max(raw,NFC) UTF8 serialized messages','assumed_framing_tokens':2048,'input_token_reservation':input_tokens,'output_token_limit':output_tokens,'input_usd_per_million':.037,'output_usd_per_million':.17,'catalog_upper_estimate_usd':float(cost),'reserved_usd_per_call':.002,'remaining_reservation_usd':float(Decimal('.002')-cost),'context_limit':131072,'reserved_context_tokens':input_tokens+output_tokens,'context_headroom_tokens':131072-input_tokens-output_tokens,'six_probe_reservation_usd':.012,'not_invoice_or_server_enforced_cap':True},'response_convention':{'documented_response_model':model,'source':'https://deepinfra.com/openai/gpt-oss-120b/api','observed_live_response':False,'require_strict_exact_id':True,'matching_id_proves_weights':False},'tokenizer_bound':bound,'sdk_inspection':sdk,'official_openai_doc':openai_doc,'paid_calls':0,'jobs':0,'credentials_read':False,'remaining_pre_dispatch_conditions':['Freeze whole new protocol, model list, decoding controls and no-more-candidate stopping rule','Record provider-default reasoning as unspecified in config/manifests/report','Require all six competence/note probes, exact reported identity and complete finish','Save complete raw response before parsing and check returned usage/estimated cost against reservation before continuing'],'source_snapshots':sourceindex}
(root/'model-preflight.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k]for k in ('requested_hub_id','provider_mapping','hub_revision','generation','reservation')},indent=2))

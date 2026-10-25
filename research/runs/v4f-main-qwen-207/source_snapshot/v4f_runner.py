#!/usr/bin/env python3
"""V4F: disclosed format-only continuation with byte-exact raw replay.

The frozen V4 package/script are imported unchanged. Only this module supplies
an expanded JSON envelope parser and explicit derivative provenance/accounting.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import re
import sys
import unicodedata

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
SPEC=importlib.util.spec_from_file_location('frozen_v4_for_format_continuation',Path(__file__).with_name('v4_runner.py'))
v4=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(v4)
import inherited_collusion.runner as legacy
import inherited_collusion.v3_runner as v3
from inherited_collusion.storage import RunLock,atomic_json,canonical,digest,immutable_json,read

POLICY='bare_or_exact_single_whole_json_fence_v1'
ORIGINAL_V4_SOURCE='c2eb3261a675d530d1c33f61a462f7f04424503dd6721da2023538e79aed09f7'
CALL_FILES=('request.json','response.json','dispatch.json','invocation.json')
GENERATION=('backend','model','provider','temperature','top_p','max_tokens','max_request_bytes','reserved_usd_per_call','input_usd_per_million','output_usd_per_million')
STRICT_OBJECT=legacy.parse_object
FENCE=re.compile(r'\A[ \t\r\n]*```json\r?\n(?P<body>[\s\S]*?)\r?\n```[ \t\r\n]*\Z')

def now():return datetime.now(timezone.utc).isoformat()
def filehash(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def require(ok,message):
    if not ok:raise ValueError(message)

def envelope(text):
    try:
        STRICT_OBJECT(text)
        return 'bare_json',text
    except (ValueError,TypeError):
        match=FENCE.fullmatch(text) if isinstance(text,str) else None
        if not match or text.count('```')!=2:raise ValueError('Expected bare JSON or exactly one whole-response ```json wrapper')
        body=match.group('body')
        STRICT_OBJECT(body)
        return 'single_json_fence',body

def parse_object(text):return STRICT_OBJECT(envelope(text)[1])
def parse_action(response,checkpoint,donor=False):
    require(response.get('finish_reason') in ('stop','eos_token'),'Incomplete generation')
    value=parse_object(response['text'])
    require(value.get('task') in checkpoint['tasks'],'Unknown or missing task')
    if donor:require(isinstance(value.get('note'),str) and value['note'].strip() and len(value['note'])<=2000,'Expected nonempty note of at most 2000 characters')
    return value

# All imported probe/action/donor/successor paths resolve to this one parser.
# No source file is changed; snapshot includes this adaptation explicitly.
v4.parse_action=parse_action
v3.parse_action=parse_action
v3.parse_object=parse_object
v4.parse_probe=v3.parse_probe

def sources():
    original,package_hash,original_hash=v4.sources()
    require(original_hash==ORIGINAL_V4_SOURCE,'Frozen V4 source changed')
    combined={**original,'v4f_runner.py':Path(__file__).read_bytes()}
    return combined,package_hash,digest({name:hashlib.sha256(data).hexdigest() for name,data in combined.items()})

def inventory(root):
    root=Path(root)
    files={}
    for path in sorted(root.rglob('*')):
        if path.name=='.lock':continue
        require(not path.is_symlink(),'Source run contains a symlink')
        if path.is_file():files[str(path.relative_to(root))]=filehash(path)
    return files

def source_validate(source,config,seed,cohort):
    source=Path(source).resolve();manifest=read(source/'manifest.json')
    require(manifest.get('schema_version')==4 and manifest['seed']==seed and manifest['cohort']==cohort,'Unexpected strict-V4 source identity')
    require(manifest['source_hash']==ORIGINAL_V4_SOURCE and manifest['config_hash']==digest(manifest['config']) and manifest['protocol_hash']==digest(manifest['protocol']),'Source manifest/configuration/protocol integrity failed')
    snapshot=read(source/'source_snapshot/manifest.json')
    actual={name:filehash(source/'source_snapshot'/name) for name in snapshot['files']}
    require(actual==snapshot['files'] and digest(actual)==ORIGINAL_V4_SOURCE,'Original source snapshot mismatch')
    require(all(manifest['config'].get(k)==config.get(k) for k in GENERATION),'Continuation may not change generation, pricing, model or input bounds')
    require(config.get('source_run_id')==source.name,'source_run_id does not match source root')
    require(config['max_calls']==v4.design(cohort,seed)['maximum_calls'],'Full original call ceiling must include reused calls')
    return manifest

def exact_copy(source,target):
    source,target=Path(source),Path(target);data=source.read_bytes()
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():require(target.read_bytes()==data,'Refusing changed byte-exact copied artifact')
    else:
        with target.open('xb') as stream:stream.write(data)

def prepare(root,source,config,seed,cohort,protocol):
    root,source=Path(root).resolve(),Path(source).resolve()
    require(root!=source,'Derivative run must use a separate directory')
    v4.validate_budget_binding(root,config,[seed],v4.design(cohort,seed)['repeats'])
    with (source/'.lock').open('r') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('Strict source run is still executing') from None
        old=source_validate(source,config,seed,cohort)
        before=inventory(source)
        with RunLock(root):
            blobs,package_hash,source_hash=sources()
            manifest={'schema_version':'4f','runner':'scripts/v4f_runner.py','parser_policy':POLICY,'source_hash':source_hash,'package_source_hash':package_hash,
                      'config':config,'config_hash':digest(config),'protocol':protocol,'protocol_hash':digest(protocol),'seed':seed,'cohort':cohort,
                      'conditions':list(v4.CONDITIONS),'successor_repeats':v4.design(cohort,seed)['repeats'],'expected_max_calls':v4.design(cohort,seed)['maximum_calls'],
                      'expected_episodes':v4.design(cohort,seed)['episodes'],'source_root':str(source),'source_manifest_hash':digest(old),'original_v4_source_hash':old['source_hash']}
            immutable_json(root/'manifest.json',manifest)
            v4.save_source_snapshot(root,blobs)
            copied={}
            for folder in sorted((source/'calls').glob('*')):
                if not folder.is_dir():continue
                copied[folder.name]={}
                for name in CALL_FILES:
                    p=folder/name
                    if p.exists():
                        exact_copy(p,root/'calls'/folder.name/name)
                        copied[folder.name][name]=filehash(p)
            original_reviews={}
            for p in sorted((source/'reviews').glob('*')):
                if p.is_file():
                    exact_copy(p,root/'original_reviews'/p.name)
                    original_reviews[p.name]=filehash(p)
            require(before==inventory(source),'Strict source changed during preparation')
            provenance={'schema_version':'4f','source_root':str(source),'source_manifest_hash':digest(old),'source_config_hash':old['config_hash'],'source_protocol_hash':old['protocol_hash'],
                        'source_source_hash':old['source_hash'],'source_inventory':before,'source_inventory_hash':digest(before),'copied_calls':copied,'original_reviews':original_reviews,
                        'source_strict_status':read(source/'summary.json').get('status') if (source/'summary.json').exists() else None,
                        'source_ledger':old['config'].get('budget_binding',{}).get('ledger'),'source_run_id':source.name}
            immutable_json(root/'source_provenance.json',provenance)
            require(len(list((root/'calls').glob('*/request.json')))<=config['max_calls'],'Copied reservations exceed fixed allocation')
    return manifest

def verify_copies(root,full_source=False):
    root=Path(root);manifest=read(root/'manifest.json');p=read(root/'source_provenance.json');source=Path(p['source_root'])
    require(digest(read(source/'manifest.json'))==p['source_manifest_hash']==manifest['source_manifest_hash'],'Source manifest changed')
    if full_source:require(inventory(source)==p['source_inventory'],'Strict source inventory changed')
    for call_id,files in p['copied_calls'].items():
        for name,sha in files.items():require(filehash(root/'calls'/call_id/name)==sha and filehash(source/'calls'/call_id/name)==sha,'Copied/source call bytes changed')
    for name,sha in p['original_reviews'].items():require(filehash(root/'original_reviews'/name)==sha and filehash(source/'reviews'/name)==sha,'Original review bytes changed')
    require(digest(manifest['config'])==manifest['config_hash'] and digest(manifest['protocol'])==manifest['protocol_hash'],'Derivative manifest binding changed')
    return p

def original_blockers(ledger):
    found=[]
    for name in ledger['allocations']:
        root=Path(ledger['_path']).parent/name
        if not (root/'source_provenance.json').exists():continue
        source=Path(read(root/'source_provenance.json')['source_root'])
        model=ledger['allocations'][name]['model']
        for pattern in ('*/model_identity_error.json','*/truncation_error.json','*/usage_error.json'):
            for path in (source/'calls').glob(pattern):found.append({'model':model,'source':str(path),'kind':path.name})
        if (source/'model_usage_stop.json').exists():found.append({'model':model,'source':str(source/'model_usage_stop.json'),'kind':'model_usage_stop.json'})
    return found

def preparation_payload(ledger_path):
    ledger_path=Path(ledger_path).resolve();ledger=read(ledger_path)
    require(len(ledger['allocations'])==18,'V4F preparation must include both qualifications and all16 main cases')
    closure=read(ledger['source_closure_record'])
    require(closure.get('strict_v4_finished') is True,'Strict V4 is not certified finished')
    archive=read(ledger['source_ledger_archive'])
    require(abs(sum(a['max_total_usd'] for a in archive['allocations'].values())-sum(a['max_total_usd'] for a in ledger['allocations'].values()))<1e-9,'Consolidated allocation must equal archived V4 allocation')
    roots={};source_ids=[];retired={}
    for name,allocation in sorted(ledger['allocations'].items()):
        root=ledger_path.parent/name;manifest=read(root/'manifest.json');p=verify_copies(root,full_source=True)
        require(manifest['config']['source_run_id'] in archive['allocations'],'Source was not allocated in original V4 ledger')
        original=read(Path(p['source_root'])/'manifest.json');allocated=archive['allocations'][p['source_run_id']]
        original_config={k:v for k,v in original['config'].items() if k not in ('backend','budget_binding')}
        require(allocated.get('config_digest')==digest(original_config) and allocated['model']==original['config']['model'] and allocated['max_total_usd']==original['config']['max_total_usd'] and allocated['seed']==original['seed'] and allocated.get('cohort',allocated.get('phase'))==original['cohort'],'Original manifest differs from archived authorized allocation')
        require(allocation['max_total_usd']==allocated['max_total_usd'] and allocation['model']==allocated['model'] and allocation['seed']==allocated['seed'] and allocation.get('cohort',allocation.get('phase'))==allocated.get('cohort',allocated.get('phase')),'Continuation changes an original per-case allocation')
        v4.validate_budget_binding(root,manifest['config'],[manifest['seed']],v4.design(manifest['cohort'],manifest['seed'])['repeats'])
        old_path=Path(p['source_ledger']);old=read(old_path)
        require(old['allocations'][p['source_run_id']]['status']=='retired_consolidated_into_v4f' and old.get('replacement_ledger')==str(ledger_path),'Original ledger still executable or lacks exact replacement binding')
        retired[str(old_path)]=filehash(old_path);source_ids.append(p['source_run_id'])
        roots[name]={'manifest_hash':digest(manifest),'provenance_hash':digest(p),'source_inventory_hash':p['source_inventory_hash']}
    require(len(set(source_ids))==18 and set(source_ids)==set(archive['allocations']),'Preparation must map every original allocation exactly once')
    require(sorted(closure.get('source_run_ids',[]))==sorted(source_ids),'Closeout must cover all18 original runs exactly')
    freeze=read(ledger['freeze_record'])
    validate_artifacts(freeze)
    require(freeze['ledger_sha256']==filehash(ledger_path),'Freeze ledger bytes mismatch')
    for name in roots:
        m=read(ledger_path.parent/name/'manifest.json')
        require(freeze['source_hash']==m['source_hash']==sources()[2] and freeze['protocol_hash']==m['protocol_hash'] and freeze['config_hashes'][name]==m['config_hash'],'Freeze does not bind exact prepared source/protocol/configuration')
    ledger['_path']=str(ledger_path)
    return {'schema_version':'4f','ledger_sha256':filehash(ledger_path),'source_ledger_archive_sha256':filehash(ledger['source_ledger_archive']),
            'closure_record_sha256':filehash(ledger['source_closure_record']),'freeze_record_sha256':filehash(ledger['freeze_record']),
            'retired_source_ledgers':retired,'prepared_runs':roots,'inherited_global_blockers':original_blockers(ledger)}

def finalize_preparation(ledger_path):
    ledger=read(ledger_path);payload=preparation_payload(ledger_path)
    immutable_json(ledger['preparation_manifest'],payload)
    return payload

def validate_artifacts(freeze):
    artifacts=freeze.get('artifacts')
    require(isinstance(artifacts,dict) and artifacts,'Freeze must bind execution/configuration artifacts')
    for path,sha in artifacts.items():
        require(Path(path).is_absolute() and filehash(path)==sha,'Frozen artifact changed')

def check_barrier(root,config,new_call=True):
    if config['backend']!='hf':return
    ledger_path=Path(config['budget_binding']['ledger']);ledger=read(ledger_path)
    seal=read(ledger['preparation_manifest'])
    validate_artifacts(read(ledger['freeze_record']))
    require(seal['ledger_sha256']==filehash(ledger_path) and len(seal['prepared_runs'])==18,'All18 frozen preparations are required before HF dispatch')
    require(seal['freeze_record_sha256']==filehash(ledger['freeze_record']) and seal['closure_record_sha256']==filehash(ledger['source_closure_record']) and seal['source_ledger_archive_sha256']==filehash(ledger['source_ledger_archive']),'Closure/archive/freeze drifted')
    for source_path,sha in seal['retired_source_ledgers'].items():require(filehash(source_path)==sha,'Retired source ledger changed')
    for name,bindings in seal['prepared_runs'].items():
        directory=ledger_path.parent/name
        require(digest(read(directory/'manifest.json'))==bindings['manifest_hash'] and digest(read(directory/'source_provenance.json'))==bindings['provenance_hash'],'Prepared manifest/provenance changed')
    require(read(Path(root)/'manifest.json')['source_hash']==sources()[2],'V4F source changed after preparation')
    ledger['_path']=str(ledger_path)
    if new_call:
        for blocker in original_blockers(ledger):require(blocker['model']!=config['model'],'Inherited identity, incomplete-generation or usage failure blocks this model')

def expected_request(call_id,messages,meta,config):
    return {'id':call_id,'messages':messages,'metadata_not_sent_to_model':meta,'generation':{k:config[k] for k in ('model','provider','max_tokens')},'temperature':config.get('temperature',0.0),'top_p':config.get('top_p',1.0)}

def raw_validate(response,request,config):
    require(response.get('model')==config['model'] or config['backend']=='mock','Wrong/missing reported model ID')
    require(response.get('finish_reason') in ('stop','eos_token'),'Incomplete generation cannot be rescued')
    require(not v4.usage_errors(response,request['messages'],config),'Missing/invalid usage cannot be rescued')
    if config['backend']=='hf':
        provider=response.get('provider_response')
        require(isinstance(provider,dict) and provider.get('model')==response.get('model') and provider.get('choices') and provider['choices'][0].get('message',{}).get('content')==response.get('text') and provider['choices'][0].get('finish_reason')==response.get('finish_reason') and provider.get('usage')==response.get('usage'),'Raw provider result does not match saved response fields')

class CachedReplayStopped(RuntimeError):
    """A reserved source slot cannot be resolved by issuing another request."""

class V4FCalls(v4.V4Calls):
    def call(self,call_id,messages,meta):
        p=read(self.root/'source_provenance.json');folder=self.directory/call_id
        reused=call_id in p['copied_calls']
        if reused:
            if not {'request.json','response.json'} <= set(p['copied_calls'][call_id]):
                raise CachedReplayStopped('Ambiguous inherited call cannot be dispatched again')
            for name,sha in p['copied_calls'][call_id].items():require(filehash(folder/name)==sha,'Reused call changed')
            require(read(folder/'request.json')==expected_request(call_id,messages,meta,self.config),'Reused request messages/metadata/generation differ')
        if (folder/'response.json').exists():
            # Validate each response at its original schedule position. A bad or
            # unresolved later response must not erase an already valid prefix.
            require(read(folder/'request.json')==expected_request(call_id,messages,meta,self.config),'Cached request messages/metadata/generation differ')
            serialized=canonical(messages)
            request_bytes=max(len(serialized.encode('utf-8')),len(unicodedata.normalize('NFC',serialized).encode('utf-8')))
            require(request_bytes<=self.config['max_request_bytes'],'Cached request exceeds approved input bound')
            response=self.check_response_identity(folder,read(folder/'response.json'))
        else:
            if any(not {'request.json','response.json'} <= set(files) for files in p['copied_calls'].values()):
                raise CachedReplayStopped('An ambiguous inherited slot blocks every new call in this case')
            check_barrier(self.root,self.config)
            response=super().call(call_id,messages,meta)
        raw_validate(response,read(folder/'request.json'),self.config)
        try:kind,body=envelope(response['text']);parse_valid=True
        except (ValueError,TypeError):kind,parse_valid='unsupported_or_invalid',False
        receipt={'call_id':call_id,'parser_policy':POLICY,'execution_source':'inherited_v4' if reused else 'newly_dispatched_v4f',
                 'parsing_envelope':kind,'json_object_valid':parse_valid,'raw_response_sha256':filehash(folder/'response.json'),
                 'source_response_sha256':p['copied_calls'].get(call_id,{}).get('response.json')}
        immutable_json(self.root/'parse_receipts'/f'{call_id}.json',receipt)
        return response

def qualification(root,config,protocol_hash,source_hash):
    if config['backend']=='mock':return {'status':'software_simulation_bypass','not_model_evidence':True}
    directory=Path(root).parent/config['qualification_run_id'];m=read(directory/'manifest.json')
    require(m['schema_version']=='4f' and m['cohort']=='qualification' and m['seed']==902 and m['source_hash']==source_hash and m['protocol_hash']==protocol_hash,'Qualification does not match V4F frozen protocol/source')
    require(all(m['config'].get(k)==config.get(k) for k in GENERATION),'Qualification generation differs')
    verify_copies(directory,full_source=True)
    class Cached:
        def call(self,call_id,messages,meta):
            request=read(directory/'calls'/call_id/'request.json');response=read(directory/'calls'/call_id/'response.json')
            require(request==expected_request(call_id,messages,meta,m['config']),'Qualification raw request changed')
            raw_validate(response,request,m['config']);return response
    expected={f's902-probe-{r}-{k}' for r in ('A','B') for k in ('comprehension','note_T1','note_T2')}
    require({p.parent.name for p in (directory/'calls').glob('*/request.json')}==expected and {p.parent.name for p in (directory/'calls').glob('*/response.json')}==expected,'Qualification must have exactly six resolved calls')
    gate=v4.probes(Cached(),902)
    require(gate['passed'] and gate==read(directory/'gates/s902-probes.json'),'Recomputed V4F qualification did not pass')
    return {'status':'passed','run_id':directory.name,'manifest_hash':digest(m),'probe_gate_hash':digest(gate),'responses':6,'parser_policy':POLICY}

def annotation_review(root,checkpoint,pairs):
    root=Path(root);seed=checkpoint['seed'];stem=f's{seed}-annotations';old=root/'original_reviews'/f'{stem}.recorded.json'
    if not old.exists():return v4.annotation_review(root,checkpoint,pairs)
    bundle={f'{mode}-{plan}':pairs[mode,plan] for mode in v4.MODES for plan in ('p0','p1')}
    review=read(old);original_receipt=read(root/'original_reviews'/f'{stem}.completion.json');p=read(root/'source_provenance.json')
    v4.validate_annotations(review,bundle)
    require(original_receipt['annotation_hash']==digest(review) and original_receipt['donor_bundle_hash']==digest(bundle),'Inherited review receipt binding mismatch')
    require(original_receipt['successor_requests_observed']==original_receipt['episodes_observed']==0,'Original review was not pre-successor')
    reviewed=datetime.fromisoformat(review['reviewed_at']);recorded=datetime.fromisoformat(original_receipt['at'])
    require(reviewed<=recorded,'Original review timestamp follows receipt')
    invocations=[]
    for call_id,files in p['copied_calls'].items():
        if 'invocation.json' in files:
            inv=read(root/'calls'/call_id/'invocation.json')
            if inv['kind']=='successor':
                require(recorded<=datetime.fromisoformat(inv['at']),'Original successor invocation predates inherited annotation')
                invocations.append(call_id)
    receipt_path=root/'reviews'/f'{stem}.completion.json'
    if receipt_path.exists():
        receipt=read(receipt_path);require(receipt['annotation_hash']==digest(review) and receipt['original_receipt_hash']==digest(original_receipt),'Inherited annotation receipt changed')
    else:
        new_successors=[p for p in (root/'calls').glob('*/request.json') if p.parent.name not in read(root/'source_provenance.json')['copied_calls'] and read(p).get('metadata_not_sent_to_model',{}).get('kind')=='successor']
        require(not new_successors,'Cannot first inherit annotations after new successor dispatch')
        immutable_json(root/'reviews'/f'{stem}.recorded.json',review)
        immutable_json(receipt_path,{'kind':'inherited_pre_successor_annotation','at':now(),'annotation_hash':digest(review),'donor_bundle_hash':digest(bundle),
                                   'original_receipt_hash':digest(original_receipt),'original_review_hash':digest(review),'original_receipt_at':original_receipt['at'],
                                   'source_provenance_hash':digest(p),'inherited_successor_invocations':len(invocations),'inherited_successor_call_ids':sorted(invocations),
                                   'new_successor_requests_at_inheritance':0,'meaning':'Original pre-successor annotation inherited; existing original successor calls are explicitly acknowledged'})
    return 'completed'

def summarize(root):
    result=v4.summarize(root);p=read(Path(root)/'source_provenance.json')
    inherited=sum('request.json' in files for files in p['copied_calls'].values())
    result.update(schema_version='4f',parser_policy=POLICY,source_strict_status=p['source_strict_status'],inherited_reserved_calls=inherited,new_reserved_calls=result['reserved_calls']-inherited,
                  cost_interpretation='All requests/responses include inherited V4 once; do not add V4 totals again')
    atomic_json(Path(root)/'summary.json',result);return result

def run(root,config,seed,cohort,stage='all',backend=None,stop_after=None):
    root=Path(root);m=read(root/'manifest.json')
    require(m['config']==config and m['seed']==seed and m['cohort']==cohort and m['source_hash']==sources()[2],'Prepared run configuration/source differs')
    require(stage in ('probes','donors','all'),'Unknown stage')
    v4.validate_budget_binding(root,config,[seed],v4.design(cohort,seed)['repeats'])
    if config['backend']=='hf':check_barrier(root,config,new_call=False)
    with RunLock(root):
        verify_copies(root,full_source=True)
        calls=V4FCalls(root,config,backend or (v4.V3MockBackend() if config['backend']=='mock' else v4.HFBackend()))
        try:
            summarize(root)
            if cohort=='main':immutable_json(root/'qualification.json',qualification(root,config,m['protocol_hash'],m['source_hash']))
            cp=v4.make_checkpoint(seed);immutable_json(root/'checkpoints'/f's{seed}.json',cp)
            gate=v4.probes(calls,seed);immutable_json(root/'gates'/f's{seed}-probes.json',gate)
            if not gate['passed'] or cohort=='qualification' or stage=='probes':return summarize(root)
            pairs={}
            for mode in v4.MODES:
                for plan in ('p0','p1'):
                    donor=v4.donors(calls,root,cp,mode,plan);pairs[mode,plan]=donor
                    if not donor['technical_passed']:return summarize(root)
            state=annotation_review(root,cp,pairs)
            if stage=='donors' or state!='completed':return summarize(root)
            order=[(mode,condition,repeat) for mode in v4.MODES for condition in v4.CONDITIONS for repeat in (0,1)]
            random.Random(seed).shuffle(order);immutable_json(root/'checkpoints'/f's{seed}-order.json',order)
            for mode,condition,repeat in order:
                ep=v4.episode(calls,root,cp,mode,condition,repeat,pairs[mode,'p0'],pairs[mode,'p1'])
                result=summarize(root)
                if ep['status']!='completed' or (stop_after and result['episodes']>=stop_after):return result
            return summarize(root)
        except CachedReplayStopped:return summarize(root)
        except (ValueError,RuntimeError,FileNotFoundError):summarize(root);raise

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('prepare','run','finalize-preparation','source-info'))
    parser.add_argument('--source',type=Path);parser.add_argument('--out',type=Path);parser.add_argument('--approval',type=Path);parser.add_argument('--protocol',type=Path)
    parser.add_argument('--cohort',choices=('qualification','main'));parser.add_argument('--seed',type=int);parser.add_argument('--seeds',nargs='+',type=int)
    parser.add_argument('--backend',choices=('hf','mock'),default='hf');parser.add_argument('--stage',choices=('probes','donors','all'),default='all');parser.add_argument('--ledger',type=Path);parser.add_argument('--stop-after',type=int)
    args=parser.parse_args()
    try:
        if args.command=='source-info':print(json.dumps({'source_hash':sources()[2],'parser_policy':POLICY}));return 0
        if args.command=='finalize-preparation':finalize_preparation(args.ledger);print('All18 source preparations sealed.');return 0
        seeds=args.seeds or [args.seed];require(len(seeds)==1 and seeds[0] is not None,'Exactly one fixed seed required');seed=seeds[0]
        require(args.out and args.approval and args.protocol and args.cohort,'out/approval/protocol/cohort required')
        config=read(args.approval);config={**config,'backend':args.backend}
        if args.backend=='hf':config=legacy.load_config('hf',args.approval,[seed])
        if args.command=='prepare':
            require(args.source is not None,'Source run required')
            prepare(args.out,args.source,config,seed,args.cohort,read(args.protocol));print('Prepared byte-exact derivative run; no model call.');return 0
        require(read(args.protocol)==read(args.out/'manifest.json')['protocol'],'Protocol differs from preparation')
        result=run(args.out,config,seed,args.cohort,args.stage,stop_after=args.stop_after)
        print(json.dumps({k:result[k] for k in ('status','complete','episodes','reserved_calls','inherited_reserved_calls','new_reserved_calls')},indent=2))
        return 0 if result['status'] in ('completed','partial','annotation_required') else 2
    except (ValueError,RuntimeError,FileNotFoundError,TypeError) as error:print(str(error),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())

"""Software-only full-cohort fixture; never calls a model or network."""
import importlib.util
from pathlib import Path

SPEC=importlib.util.spec_from_file_location('fixture_v4f',Path(__file__).resolve().parents[1]/'scripts/v4f_runner.py')
f=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(f)

class FixtureBackend(f.v4.V3MockBackend):
    def complete(self,messages,meta,config):
        response=super().complete(messages,meta,config)
        response['model']=config['model']
        return response

def full_cohort(base,seal=True):
    base=Path(base);runs=base/'runs';runs.mkdir();(base/'docs').mkdir();(base/'configs').mkdir()
    (base/'scripts').mkdir()
    artifacts={}
    for filename in ('v4f_runner.py','run_v4f_study.py'):
        destination=base/'scripts'/filename
        f.exact_copy(Path(f.__file__).with_name(filename),destination)
        artifacts[str(destination.resolve())]=f.filehash(destination)
    oldledger=runs/'phase4-budget.json';newledger=runs/'phase4f-budget.json';archive=base/'docs/original-ledger.json'
    old={'schema_version':1,'authorized_total_usd':15,'historical_allocated_usd':1.594,'phase_max_usd':9,'allocations':{}}
    new={**old,'allocations':{},'source_ledger_archive':str(archive),'source_closure_record':str(base/'docs/closure.json'),'preparation_manifest':str(base/'docs/preparation.json'),'freeze_record':str(base/'docs/freeze.json')}
    configs={};sources={}
    for family,rate in (('qwen',.010),('gptoss',.002)):
        for cohort,seed in [('qualification',902)]+[('main',s) for s in range(201,209)]:
            oldname=f'v4-{cohort}-{family}-{seed}';name=f'v4f-{cohort}-{family}-{seed}'
            cfg=f.v4.load_config('mock',None,cohort,seed)
            cfg.update(model=f'simulated-{family}',reserved_usd_per_call=rate,max_total_usd=round(cfg['max_calls']*rate,6),budget_binding={'ledger':str(oldledger),'run_id':oldname})
            old['allocations'][oldname]={'status':'allocated','model':cfg['model'],'cohort':cohort,'seed':seed,'repeats':0 if cohort=='qualification' else 2,'max_total_usd':cfg['max_total_usd'],'config_digest':f.digest({k:v for k,v in cfg.items() if k not in ('backend','budget_binding')})}
            source=runs/oldname
            f.v4.run(source,cfg,seed,cohort,'probes',backend=FixtureBackend())
            continued={**cfg,'source_run_id':oldname,'qualification_run_id':f'v4f-qualification-{family}-902','budget_binding':{'ledger':str(newledger),'run_id':name}}
            config_path=base/'configs'/f'{name}.json';f.atomic_json(config_path,continued)
            new['allocations'][name]={**old['allocations'][oldname],'config_digest':f.digest({k:v for k,v in continued.items() if k not in ('backend','budget_binding')}),'config':str(config_path),'source_run_id':oldname}
            configs[name]=continued;sources[name]=source
    f.atomic_json(oldledger,old);f.exact_copy(oldledger,archive)
    retired={**old,'replacement_ledger':str(newledger),'allocations':{name:{**allocation,'status':'retired_consolidated_into_v4f'} for name,allocation in old['allocations'].items()}}
    f.atomic_json(oldledger,retired);f.atomic_json(newledger,new)
    f.atomic_json(new['source_closure_record'],{'strict_v4_finished':True,'source_run_ids':list(old['allocations']),'closed_at':f.now()})
    protocol={'version':'SOFTWARE_TEST_ONLY_V4F'};f.atomic_json(base/'docs/protocol.json',protocol)
    for name,cfg in configs.items():
        allocation=new['allocations'][name]
        f.prepare(runs/name,sources[name],cfg,allocation['seed'],allocation['cohort'],protocol)
    freeze={'frozen_at':f.now(),'source_hash':f.sources()[2],'protocol_hash':f.digest(protocol),'ledger_sha256':f.filehash(newledger),
            'config_hashes':{name:f.digest(cfg) for name,cfg in configs.items()},'artifacts':artifacts}
    f.atomic_json(new['freeze_record'],freeze)
    if seal:f.finalize_preparation(newledger)
    return {'project':base,'ledger':newledger,'configs':configs,'sources':sources,'freeze':Path(new['freeze_record']),'preparation':Path(new['preparation_manifest'])}

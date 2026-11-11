"""Execute synthetic flexible-duct restriction controls with an official source."""
import argparse
import copy
import json
from pathlib import Path
import shutil

from bsa.cli import digest
from bsa.regulations import run

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'regulations/hk/flex-routing-2026.11.11/pack.json'


def project(pack):
    return dict(jurisdiction='HK',rule_pack=pack['id'],
        edition_decisions=dict(fsd_mv_2023=dict(edition='Circular 2/2023',basis='Explicit synthetic scope control only;not real works applicability')),
        facts=dict(mechanical_ventilating_system_scope_confirmed=dict(value=True,source='Synthetic mechanical ventilation scope')),
        flexible_duct_inventory=dict(source='Synthetic inventory;no real installation or model claim',complete=True,connections=[dict(
            id='F1',source='Synthetic final connection assertion',role='final_connection',penetrations_complete=True,penetrations=[],
            ends=[dict(kind='other',source='Synthetic rigid-duct end'),dict(kind='other',source='Synthetic terminal end')])]))


def execute(pdf,out):
    pdf,out=Path(pdf).resolve(),Path(out).resolve()
    pack=json.loads(PACK.read_text());source=pack['sources']['fsd_mv_2023']
    if digest(pdf)!=source['sha256']:raise ValueError('Exact reviewed official PDF required')
    if out.exists() or not out.is_relative_to(ROOT) or pdf.is_relative_to(out):raise ValueError('New repository-local output outside source required')
    (out/'sources').mkdir(parents=True)
    shutil.copyfile(pdf,out/'sources'/source['cache_filename'])
    saved_pack=out/'pack.json';saved_pack.write_text(json.dumps(pack,indent=2))
    statuses={}
    for case in ('clear','main','boundary','damper','unknown','known_and_unknown'):
        data=project(pack);inventory=data['flexible_duct_inventory'];connection=inventory['connections'][0]
        if case in ('main','known_and_unknown'):connection['role']='main_distribution'
        if case=='boundary':connection['penetrations']=[dict(id='B1',kind='wall',fire_resisting=True,source='Synthetic fire-resisting wall')]
        if case=='damper':connection['ends'][1]['kind']='fire_smoke_damper'
        if case in ('unknown','known_and_unknown'):
            inventory['complete']=None;connection['penetrations_complete']=None;connection['ends'][0]['kind']=None
        path=out/(case+'.json');path.write_text(json.dumps(data,indent=2))
        result=run(saved_pack,path,out/'sources',out/case)
        assert not result['design_accepted'] and result['regulatory_compliance']=='not_established'
        statuses[case]=[r['status'] for r in result['checks']]
    expected=dict(clear=['pass']*3,main=['review_required','pass','pass'],boundary=['pass','review_required','pass'],
        damper=['pass','pass','review_required'],unknown=['pending']*3,
        known_and_unknown=['review_required','pending','pending'])
    if statuses!=expected:raise ValueError('Restriction controls did not retain expected scope states')
    receipt=dict(scope='Synthetic sourced-assertion software controls with actual pinned official PDF;not a completed design',
        cases=statuses,expected_states_verified=True,source_sha256=digest(pdf),pack_sha256=digest(PACK),
        inputs_unchanged=digest(pdf)==source['sha256'],design_accepted=False)
    (out/'controls.json').write_text(json.dumps(receipt,indent=2))
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--pdf',required=True);parser.add_argument('--out',required=True)
    args=parser.parse_args();print(json.dumps(execute(args.pdf,args.out),indent=2))

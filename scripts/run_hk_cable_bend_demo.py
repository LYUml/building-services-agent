"""Official-source-backed synthetic saved cable bend pass/fail/unknown/HV controls."""
import argparse
import json
import math
from pathlib import Path
import runpy
import shutil
import ifcopenshell
import ifcopenshell.api as api
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.cable_bend_regulations import run as check

ROOT=Path(__file__).resolve().parents[1]


def run(out,sources):
    out=Path(out).resolve()
    if not out.is_relative_to(ROOT) or out.exists():raise ProjectError('new repository demonstration output required')
    author=runpy.run_path(str(ROOT/'scripts/author_three_phase_ifc_fixture.py'))['run']
    cases=[];pack=ROOT/'regulations/hk/cable-bends-2026.11.10/pack.json'
    for name,radius,expected in [('scoped-pass',.3,'pass'),('too-tight',.06,'fail'),('unknown-construction',.3,'pending'),('unsupported-hv',.3,'pending')]:
        case=out/name;source=case/'source';shutil.copytree(ROOT/'examples/cable-coordination',source)
        geo=json.loads((source/'geometry.json').read_text());geo['quarter_bends']['feeder']['radius_m']=radius
        geo['buses_m']={'source':[radius,0.,2.],'DB-A':[0.,0.,2.-radius]}
        geo['scope']='Synthetic HK cable-table geometry only; dimensions/classification assumed, not real selected equipment'
        (source/'geometry.json').write_text(json.dumps(geo,indent=2),encoding='utf-8')
        project=json.loads((source/'project.json').read_text());project['lines'][0]['length_m']=radius*math.pi/2
        project['sources']['route']=dict(path='geometry.json',sha256=digest(source/'geometry.json'),locator='Synthetic radius/anchors',kind='assumption')
        project['lines'][0]['length_source']='route';(source/'project.json').write_text(json.dumps(project,indent=2),encoding='utf-8')
        binding=author(source/'project.json',source/'geometry.json',case/'base-model','mixed-revolution')
        classification=dict(source='assumed',product_reference='synthetic-PVC-stranded-Cu-20',overall_diameter_mm=20.,overall_diameter_is_actual=True,
            wiring_scope_confirmed=True,low_voltage=False if name=='unsupported-hv' else True,pvc_insulated=None if name=='unknown-construction' else True,stranded_copper=True,armoured=False)
        text=source/'classification.txt'
        text.write_text('Synthetic software scenario only. Select Wiring CoP 2025 for this scoped example; not a statutory determination or manufacturer record.\n'+json.dumps(classification,indent=2),encoding='utf-8')
        basis=dict(version=1,sources={'assumed':dict(path='classification.txt',sha256=digest(text),locator='Whole explicit synthetic classification and edition decision',kind='assumption')},jurisdiction='HK',rule_pack='hk-cable-bends-2026.11.10',edition_decision=dict(edition='2025',source='assumed'),bends={'feeder':classification})
        (source/'rule-basis.json').write_text(json.dumps(basis,indent=2),encoding='utf-8')
        selected=case/'selected-model';selected.mkdir()
        for filename in ('cables.ifc','geometry-source.json'):shutil.copyfile(case/'base-model'/filename,selected/filename)
        model=ifcopenshell.open(str(selected/'cables.ifc'));cable=model.by_guid(binding['lines']['feeder']['element_guid'])
        ps=api.run('pset.add_pset',model,product=cable,name='BSA_CableSelection')
        api.run('pset.edit_pset',model,pset=ps,properties=dict(ProductReference=classification['product_reference'],SourceSHA256=digest(text),InstallationCondition='installed'))
        model.write(str(selected/'cables.ifc'));binding['ifc_sha256']=digest(selected/'cables.ifc')
        (selected/'binding.json').write_text(json.dumps(binding,indent=2),encoding='utf-8')
        result=check(source/'project.json',selected/'cables.ifc',selected/'binding.json',source/'rule-basis.json',pack,sources,case/'check')
        if result['status']!=expected:raise ProjectError('unexpected '+name+' regulatory result: '+result['status'])
        cases.append(dict(scenario=name,expected_status=expected,report=result))
    report=dict(scope='Synthetic product classifications and geometry against pinned official cable table; no real equipment or full conformity',scenarios=cases,expected_behaviors_pass=True,design_accepted=False)
    (out/'demonstration.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('out','sources'):parser.add_argument('--'+key,type=Path,required=True)
    r=run(**vars(parser.parse_args()));print(json.dumps({key:r[key] for key in ('expected_behaviors_pass','design_accepted')}))

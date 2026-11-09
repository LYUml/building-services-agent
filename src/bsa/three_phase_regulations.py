"""Bind verified phase currents to a source-pinned current-unbalance rule pack."""
import argparse
import copy
import json
import math
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from .regulations import evaluate,source_paths
from .three_phase import fields,ROOT
from .three_phase_drawing import context


def unbalance(currents):
    if not isinstance(currents,list) or len(currents)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in currents):
        raise ProjectError('three finite nonnegative current magnitudes required')
    average=math.fsum(v/3 for v in currents)
    return None if average==0 else max(abs(v-average) for v in currents)/average*100


def run(project,study_root,basis_path,pack_path,sources,out):
    project,basis_path,pack_path,out=[Path(v).resolve() for v in (project,basis_path,pack_path,out)]
    p,study,before=context(project,study_root,require_targets=False)
    basis=json.loads(basis_path.read_text(encoding='utf-8-sig'));pack=json.loads(pack_path.read_text(encoding='utf-8-sig'))
    fields(basis,'jurisdiction rule_pack edition_decisions sources circuits')
    if len(pack.get('rules',[]))!=1:raise ProjectError('one current-unbalance rule required')
    rule=pack['rules'][0]
    if rule.get('method')!='prescriptive_maximum' or rule.get('metric')!='phase_current_unbalance_percent' or rule.get('unit')!='%':raise ProjectError('current-unbalance rule metric/unit required')
    threshold=rule.get('minimum_protective_device_rating_a')
    if type(threshold) not in (int,float) or not math.isfinite(threshold) or threshold<=0:raise ProjectError('sourced positive protective-device threshold required')
    if not isinstance(basis['circuits'],dict) or set(basis['circuits'])!={r['id'] for r in p['lines']}:raise ProjectError('exact line/circuit basis coverage required')
    if not isinstance(basis['sources'],dict):raise ProjectError('basis source mapping required')
    before.update({str(f):digest(f) for f in (basis_path,pack_path,Path(__file__).resolve(),Path(__file__).with_name('three_phase_drawing.py'))})
    for record in basis['sources'].values():
        fields(record,'path sha256 locator kind')
        if not isinstance(record['path'],str) or Path(record['path']).is_absolute():raise ProjectError('relative basis source required')
        f=(basis_path.parent/record['path']).resolve()
        if not f.is_relative_to(basis_path.parent) or not f.is_file() or digest(f)!=record['sha256']:raise ProjectError('basis source path/hash mismatch')
        if not isinstance(record['locator'],str) or not record['locator'].strip() or record['kind'] not in ('course_given','measured','manufacturer','design_target','assumption'):raise ProjectError('basis source kind/locator required')
        before[str(f)]=digest(f)
    official={str(f):digest(f) if f.is_file() else None for f in source_paths(pack,sources)}
    if not out.is_relative_to(ROOT) or any(out==Path(f) or out in Path(f).parents for f in list(before)+list(official)):raise ProjectError('separate repository output required')
    if out.exists():raise ProjectError('refusing to overwrite regulation result')
    reports={};derived={}
    conditions=rule.get('applicability')
    if not isinstance(conditions,list) or not conditions or any(not isinstance(c,dict) or not isinstance(c.get('fact'),str) or not c['fact'] or type(c.get('equals')) is not bool for c in conditions):
        raise ProjectError('explicit rule-pack applicability facts required')
    allowed_facts=({c['fact'] for c in conditions}-{'protective_device_rating_at_threshold'})|{'design_normal_service_rms_confirmed','sinusoidal_design_model_applicable'}
    def source_name(value):
        if not isinstance(value,str) or value not in basis['sources']:return None
        return value+' '+json.dumps(basis['sources'][value],sort_keys=True)
    for line in study['lines']:
        id=line['id'];b=basis['circuits'][id]
        if not isinstance(b,dict) or set(b)-{'protective_device_rating','facts'} or not isinstance(b.get('facts',{}),dict) or set(b.get('facts',{}))-allowed_facts:
            raise ProjectError('circuit basis accepts protective rating and supported sourced facts only; currents/metrics cannot be overridden')
        facts={}
        for name,item in b.get('facts',{}).items():
            if isinstance(item,dict) and set(item)=={'value','source'} and type(item['value']) is bool and source_name(item['source']):facts[name]=dict(value=item['value'],source=source_name(item['source']))
        rating=b.get('protective_device_rating')
        valid_rating=isinstance(rating,dict) and set(rating)=={'value','unit','source'} and type(rating['value']) in (int,float) and math.isfinite(rating['value']) and rating['value']>0 and rating['unit']=='A' and source_name(rating['source'])
        if valid_rating:facts['protective_device_rating_at_threshold']=dict(value=rating['value']>=threshold,source=source_name(rating['source'])+'; explicit protective device rating, not study max_current_a')
        metric=unbalance(line['phase_current_a'])
        facts[rule['metric']]=dict(value=metric,unit='%',source='Exact study '+before[str(Path(study_root).resolve()/'native/study.json')]+' circuit '+id+'; maximum absolute deviation from phase average divided by average')
        regulatory=dict(jurisdiction=basis['jurisdiction'],rule_pack=basis['rule_pack'],edition_decisions=copy.deepcopy(basis['edition_decisions']),facts=facts)
        report=evaluate(pack,regulatory,sources)
        prerequisites=[name for name in ('design_normal_service_rms_confirmed','sinusoidal_design_model_applicable') if facts.get(name,{}).get('value') is not True]
        if prerequisites:
            row=report['checks'][0];row['status']='pending';row['reasons']=row.get('reasons',[])+['Missing supported design-current/model basis: '+', '.join(prerequisites)]
            report['supported_checks_pass']=False
        report.update(phase_current_a=line['phase_current_a'],computed_unbalance_percent=metric,protective_device_rating=rating,
            basis_sources=basis['sources'],model_prerequisites_pending=prerequisites)
        reports[id]=report;derived[id]=regulatory
    if any(not Path(f).is_file() or digest(Path(f))!=h for f,h in before.items()) or any((digest(Path(f)) if Path(f).is_file() else None)!=h for f,h in official.items()):raise ProjectError('regulation inputs changed')
    before.update({f:h for f,h in official.items() if h is not None})
    applicable=[c for r in reports.values() for c in r['checks'] if c['status']!='not_applicable']
    passed=bool(applicable) and all(c['status']=='pass' for c in applicable)
    result=dict(inputs=before,inputs_unchanged=True,missing_sources=[f for f,h in official.items() if h is None],circuit_checks=reports,
        supported_checks_pass=passed,study_targets_pass=study['study_targets_pass'],
        status='fail' if not study['study_targets_pass'] else 'pass' if passed else 'pending',
        regulatory_compliance='not_established',design_accepted=False,
        scope='Selected current-unbalance rule with explicit protective rating, circuit and sinusoidal normal-service RMS design basis; no neutral/harmonic/protection/full conformity acceptance')
    out.mkdir(parents=True)
    (out/'derived-projects.json').write_text(json.dumps(derived,indent=2),encoding='utf-8')
    (out/'phase-regulations.json').write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project',type=Path)
    for key in ('study','basis','pack','sources','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();r=run(a.project,a.study,a.basis,a.pack,a.sources,a.out)
    print(json.dumps({k:r[k] for k in ('status','supported_checks_pass','regulatory_compliance','design_accepted')}))
    return 0 if r['status']=='pass' else 2


if __name__=='__main__':raise SystemExit(main())

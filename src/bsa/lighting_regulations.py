"""Bind shared electrical/light-envelope/room sources to per-space rule checks."""
import argparse
import copy
import json
from pathlib import Path
from .cli import digest
from .coordination import compile_model
from .engine import calculate, ProjectError
from .regulations import evaluate,source_paths


def prepare(electrical,geometry,bases):
    compile_model(electrical,geometry)
    devices={d['id']:d for d in electrical['devices']}
    rooms={s['id']:s for s in geometry['spaces']}
    lights={}
    omitted=[]
    for d in geometry['devices']:
        if d['ifc_class']=='IfcLightFixture':lights.setdefault(d['space'],[]).append(d['id'])
        else:omitted.append(dict(id=d['id'],ifc_class=d['ifc_class'],source=geometry['sources'][d['source']]))
    if not lights or not isinstance(bases,dict) or set(bases)!=set(lights):
        raise ProjectError('regulatory bases must exactly cover every shared space containing light fixtures')
    result={}
    for room,ids in lights.items():
        basis=bases[room]
        if not isinstance(basis,dict) or 'lighting_space' in basis:
            raise ProjectError('space basis must not repeat area or luminaire power inventory')
        p=copy.deepcopy(basis);s=rooms[room]
        p['lighting_space']=dict(internal_floor_area=dict(value=s['size_m'][0]*s['size_m'][1],unit='m2',
            source='Shared rectangular space '+room+' XY dimensions; '+geometry['sources'][s['source']]),luminaires=[])
        for ident in ids:
            d=devices[ident]
            p['lighting_space']['luminaires'].append(dict(id=ident,full_output_circuit_power=dict(value=d['electrical_kw']*1000,unit='W',
                source='Shared electrical device '+ident+' electrical_kw * 1000; '+electrical['sources'][d['source']])))
        result[room]=p
    return result,omitted


def run(project,geometry,basis,pack,sources,out):
    files=[Path(p).resolve() for p in (project,geometry,basis,pack)];out=Path(out).resolve()
    before={str(p):digest(p) for p in files}
    electrical,geometric,bases,data=[json.loads(p.read_text(encoding='utf-8-sig')) for p in files]
    official=source_paths(data,sources)
    if any(out==p or out in p.parents for p in set(files)|official):raise ProjectError('output must not contain source inputs')
    cached={str(p):digest(p) if p.is_file() else None for p in official}
    projects,omitted=prepare(electrical,geometric,bases)
    calculation=calculate(electrical);checks={room:evaluate(data,p,sources) for room,p in projects.items()}
    branch_pass=calculation['calculated_checks_pass'];rules_pass=all(c['supported_checks_pass'] for c in checks.values())
    status='fail' if not branch_pass else ('pass' if rules_pass else 'pending')
    if any(digest(Path(p))!=h for p,h in before.items()) or any((digest(Path(p)) if Path(p).is_file() else None)!=h for p,h in cached.items()):raise ProjectError('lighting rule source changed')
    before.update({p:h for p,h in cached.items() if h is not None})
    result=dict(inputs=before,inputs_unchanged=True,missing_sources=[p for p,h in cached.items() if h is None],space_checks=checks,
                omitted_non_light_devices=omitted,branch_calculation=calculation,status=status,design_accepted=False,
                regulatory_compliance='not_established',scope='Shared source rectangular space areas and full electrical fixture watts; actual saved IFC not reopened',
                pending=['actual space/internal-area/classification applicability','circuit watts including driver/controlgear loss','saved IFC geometry binding','other lighting controls, photometry and full engineering acceptance'])
    out.mkdir(parents=True,exist_ok=False)
    (out/'bound-space-projects.json').write_text(json.dumps(projects,indent=2),encoding='utf-8')
    (out/'lighting-regulation-checks.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project',type=Path)
    for k in ('geometry','basis','pack','sources','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();r=run(a.project,a.geometry,a.basis,a.pack,a.sources,a.out)
    return 0 if r['status']=='pass' else 2


if __name__=='__main__':raise SystemExit(main())

"""Source-bound identical-appliance demand study; engineering acceptance separate."""
import argparse
import json
from pathlib import Path
from .cli import digest
from .plumbing_demand import identical


def pinned_references(project,spec):
    if not isinstance(spec['references'],dict) or not spec['references']:raise ValueError('At least one pinned reference required')
    pins={str(project):digest(project)}
    for relative,sha in spec['references'].items():
        if not isinstance(relative,str) or not relative.strip() or Path(relative).is_absolute():raise ValueError('Relative reference paths required')
        path=(project.parent/relative).resolve()
        if not path.is_file() or digest(path)!=sha:raise ValueError('Demand reference hash mismatch')
        pins[str(path)]=sha
    return pins


def run(project,output):
    project,output=(Path(p).resolve() for p in (project,output))
    project_hash=digest(project);spec=json.loads(project.read_text(encoding='utf-8'))
    if set(spec)!={'inputs','model_facts','basis','references'}:raise ValueError('Exact demand inputs, model facts, basis and references required')
    names={'count':'1','operating_probability':'1','fixture_flow_L_s':'L/s','exceedance_probability':'1'}
    if not isinstance(spec['inputs'],dict) or set(spec['inputs'])!=set(names):raise ValueError('Exact four demand quantities required')
    for name,unit in names.items():
        row=spec['inputs'][name]
        if not isinstance(row,dict) or set(row)!={'value','unit','classification','source'} or row['unit']!=unit or row['classification'] not in ('given','measured','assumed','secondary_transcription') or not isinstance(row['source'],str) or not row['source'].strip():
            raise ValueError('Each quantity requires units, source and classification')
    facts=spec['model_facts']
    if not isinstance(facts,dict) or set(facts)!={'identical_appliances','independent_use'} or any(type(v) not in (bool,type(None)) for v in facts.values()):raise ValueError('Explicit Boolean/unknown model facts required')
    if not isinstance(spec['basis'],str) or not spec['basis'].strip():raise ValueError('Explicit applicability basis required')
    pins=pinned_references(project,spec)
    if pins[str(project)]!=project_hash:raise ValueError('Demand project changed during validation')
    if output.exists() or any(output==Path(p) or output in Path(p).parents for p in pins):raise ValueError('New output outside source files required')
    values={k:r['value'] for k,r in spec['inputs'].items()}
    status='inapplicable' if any(v is False for v in facts.values()) else 'pending' if any(v is None for v in facts.values()) or any(v is None for v in values.values()) else 'calculated'
    calculation=identical(**values,basis=spec['basis']) if status=='calculated' else None
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Demand source changed during execution')
    result=dict(inputs=pins,classified_quantities=spec['inputs'],model_facts=facts,basis=spec['basis'],status=status,
        calculation=calculation,design_accepted=False,scope='Declared identical/independent model only; reference bytes do not authenticate source values or project applicability')
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2),encoding='utf-8');return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project');p.add_argument('--out',required=True)
    a=p.parse_args();r=run(a.project,a.out);print(r['status'],'engineering acceptance pending');raise SystemExit(2)

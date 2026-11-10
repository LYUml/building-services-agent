"""Source-bound wastewater DU arithmetic with declared connection/use scope."""
import argparse
import json
from pathlib import Path
from .cli import digest
from .plumbing_demand import discharge_units
from .plumbing_demand_study import pinned_references


def run(project,output):
    project,output=(Path(p).resolve() for p in (project,output))
    before=digest(project);spec=json.loads(project.read_text(encoding='utf-8'))
    if set(spec)!={'fixtures','frequency_factor','model_facts','basis','references'}:raise ValueError('Exact DU study fields required')
    facts=spec['model_facts']
    if not isinstance(facts,dict) or set(facts)!={'connected_inventory_verified','frequency_classification_verified'} or any(type(v) not in (bool,type(None)) for v in facts.values()):raise ValueError('Exact Boolean/unknown connection and use facts required')
    factor=spec['frequency_factor']
    if not isinstance(factor,dict) or set(factor)!={'value','source','classification'} or factor['classification'] not in ('given','assumed','secondary_transcription') or not isinstance(factor['source'],str) or not factor['source'].strip():raise ValueError('Factor requires value/source/classification')
    if not isinstance(spec['basis'],str) or not spec['basis'].strip():raise ValueError('Explicit source and connected scope required')
    pins=pinned_references(project,spec)
    if pins[str(project)]!=before:raise ValueError('DU project changed during validation')
    if output.exists() or any(output==Path(p) or output in Path(p).parents for p in pins):raise ValueError('New output outside sources required')
    status='inapplicable' if any(v is False for v in facts.values()) else 'pending' if any(v is None for v in facts.values()) or factor['value'] is None else 'calculated'
    calculation=discharge_units(spec['fixtures'],frequency_factor=factor['value'],basis=spec['basis']) if status=='calculated' else None
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('DU study source changed during execution')
    result=dict(inputs=pins,fixtures=spec['fixtures'],frequency_factor=factor,model_facts=facts,basis=spec['basis'],status=status,calculation=calculation,
        design_accepted=False,scope='Wastewater DU relation only; source declarations, other inflows, full pipe/stack/vent sizing and jurisdiction acceptance remain separate')
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2),encoding='utf-8');return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project');p.add_argument('--out',required=True)
    a=p.parse_args();r=run(a.project,a.out);print(r['status'],'full drainage acceptance pending');raise SystemExit(2)

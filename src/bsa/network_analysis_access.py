"""Compact MCP access to existing source-native analysis; no replacement solver."""
import json
from pathlib import Path
from . import source_network_analysis as network, source_fitting_data as fittings
from .cli import digest


def summary(out, record, data):
    path=Path(out)/record
    return dict(status='pending',design_accepted=False,pressure_budget_complete=False,
        critical_path=None,original_requirement_count=len(data['original_requirement_ids']),
        outlet_path_count=len(data['boundary_paths']),
        fitting_path_count=data.get('unique_fitting_paths',len(data.get('missing_fitting_path_losses',[]))),
        conditional_table_path_count=data.get('calculated_table_paths',0),
        transition_end_straight_study_count=len(data.get('transition_end_straight_study',[])),
        artifacts=[dict(path=str(path),sha256=digest(path),bytes=path.stat().st_size)],
        scope='Source/native execution and conditional calculations only. Missing losses, physical '
        'applicability, source assumptions, native drawings and complete design acceptance remain separate.')


def run_network(source,out):
    result=network.run(source,out)
    return summary(out,'analysis.json',result)


def run_fittings(analysis,basis,out):
    result=fittings.run(analysis,basis,out)
    return summary(out,'fitting-data.json',result)


def inspect(out,kind):
    if kind not in ('network','fittings'):
        raise ValueError('Fixed network or fittings inspection required')
    record='analysis.json' if kind=='network' else 'fitting-data.json'
    path=Path(out)/record;before=digest(path)
    receipt=(network if kind=='network' else fittings).verify(out)
    data=json.loads(path.read_text(encoding='utf-8'))
    result=summary(out,record,data)
    if digest(path)!=before or result['artifacts'][0]['sha256']!=before:
        raise ValueError('Analysis record changed during inspection')
    result['integrity_pass']=receipt['integrity_pass']
    return result

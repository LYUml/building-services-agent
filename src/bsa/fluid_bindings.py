"""Reject conflicting declared densities in a connected hydraulic workflow."""
import json
import math
from .engine import ProjectError


def density_declarations(task, basis_path):
    basis=json.loads(basis_path.read_text(encoding='utf-8-sig'))
    if task['kind']=='circulation_duty':
        quantities=[(row['link'],row['density']) for row in basis['targets']]
    else:
        quantities=[('all_pipes',basis.get('density'))]
    result=[]
    for location,q in quantities:
        if not isinstance(q,dict):raise ProjectError('sourced density required for fluid binding')
        value=q.get('value')
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0 or q.get('unit')!='kg/m3':
            raise ProjectError('fluid binding requires positive finite density in kg/m3')
        if not isinstance(q.get('source'),str) or not q['source'].strip():raise ProjectError('density evidence required')
        result.append(dict(task=task['id'],location=location,value=value,unit='kg/m3',source=q['source'],basis=str(basis_path)))
    return result


def check_density_consistency(declarations):
    if declarations and any(q['value']!=declarations[0]['value'] for q in declarations):
        raise ProjectError('conflicting density declarations for the same hydraulic scenario: '+', '.join(f"{q['task']}/{q['location']}={q['value']} kg/m3" for q in declarations))

"""Level rectangular air-tree pressure budgets using actual area and hydraulic diameter."""
import argparse
import copy
import json
import math
from pathlib import Path

from .engine import ProjectError
from .network import _calculate,_run

MODEL='steady incompressible rectangular air tree'


def calculate(project):
    if not isinstance(project,dict) or project.get('model')!=MODEL:raise ProjectError('explicit rectangular air-tree model required')
    basis=project.get('method_basis')
    keys={'source','constant_density_air','fully_developed','hydraulic_diameter_applicable','level_common_reference'}
    if not isinstance(basis,dict) or set(basis)!=keys or any(basis[k] is not True for k in keys-{'source'}):raise ProjectError('explicit sourced rectangular method applicability required')
    if not isinstance(basis['source'],str) or basis['source'] not in project.get('sources',{}):raise ProjectError('known method applicability source required')
    p=copy.deepcopy(project);p['model']='steady incompressible circular tree'
    areas={};dimensions={}
    if not isinstance(p.get('segments'),list):raise ProjectError('rectangular segments required')
    for row in p['segments']:
        if not isinstance(row,dict) or 'diameter_m' in row:raise ProjectError('rectangular width/height required; no circular diameter input')
        width,height=row.pop('width_m',None),row.pop('height_m',None)
        if any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in (width,height)):raise ProjectError('positive finite internal width and height required')
        area=width*height;dh=2*area/(width+height)
        if not math.isfinite(area) or not math.isfinite(dh) or min(area,dh)<=0:raise ProjectError('rectangular geometry overflow/underflow')
        name=row.get('id')
        if not isinstance(name,str):raise ProjectError('rectangular segment ID required')
        areas[name]=area;dimensions[name]=dict(width_m=width,height_m=height,hydraulic_diameter_m=dh)
        row['diameter_m']=dh
    nodes=p.get('nodes')
    if not isinstance(nodes,list) or not nodes or any(not isinstance(n,dict) for n in nodes):raise ProjectError('level nodes required')
    if any(n.get('elevation_m')!=nodes[0].get('elevation_m') for n in nodes):raise ProjectError('rectangular air-tree supports level common-reference nodes only')
    result=_calculate(p,areas,turbulent_only=True)
    for row in result['segments']:row.update(dimensions[row['id']])
    result.update(model=MODEL,method_basis=basis,
        methods=['Actual rectangular area w*h; hydraulic diameter 2*w*h/(w+h)',
            'Darcy-Weisbach with local actual velocity and hydraulic-diameter Colebrook friction',
            'K loss referenced to actual local rectangular mean velocity; no equivalent-round velocity',
            'https://fluids.readthedocs.io/fluids.friction.html',
            'https://handbook.ashrae.org/Handbooks/F17/SI/f17_ch21/f17_ch21_si.aspx'],
        scope='Prescribed level constant-density air withdrawals; rectangular actual area and turbulent hydraulic-diameter approximation; no loops, flow balancing or fan operating point',
        geometry_bound=False,regulatory_compliance='not_established')
    result['pending']+=['hydraulic-diameter correlation and fully-developed applicability','rectangular fittings and local-velocity coefficient basis','duct leakage, acoustic, insulation and fire/smoke design']
    return result


def run(project,out):return _run(project,out,calculate)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('project',type=Path);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    try:result=run(args.project,args.out)
    except (ProjectError,OSError,ValueError) as exc:parser.exit(2,str(exc)+'\n')
    print(json.dumps({k:result[k] for k in ('calculated_checks_pass','required_source_total_pressure_pa','design_accepted')}))
    return 0 if result['calculated_checks_pass'] else 2


if __name__=='__main__':raise SystemExit(main())

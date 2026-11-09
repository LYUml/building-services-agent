"""Finite supplied-catalogue rectangular duct sizing using existing search and pressure engines."""
import argparse
import json
from pathlib import Path
from . import network_design as engine
from .rectangular_network import prepare,calculate,run as analyse
from .cli import digest
from .engine import ProjectError

DIMENSIONS=('width_m','height_m')


def selected_input(producer,project,catalogue):
    producer=Path(producer).resolve();project=Path(project).resolve();catalogue=Path(catalogue).resolve()
    report=json.loads((producer/'design-comparison.json').read_text(encoding='utf-8-sig'))
    if report.get('feasible_design_found') is not True or report.get('selected_rerun_pass') is not True:raise ProjectError('no verified rectangular selection available')
    if report.get('inputs')!={str(p):digest(p) for p in (project,catalogue)}:raise ProjectError('rectangular selection source identity differs')
    required={'selected-network.json','selected/network.json','selected/manifest.json'}
    if not required<=set(report.get('artifacts',{})):raise ProjectError('rectangular selected artifact coverage missing')
    for name,sha in report['artifacts'].items():
        path=(producer/name).resolve()
        if not path.is_relative_to(producer) or not path.is_file() or digest(path)!=sha:raise ProjectError('rectangular selection artifact changed')
    expected,network=search(json.loads(project.read_text(encoding='utf-8-sig')),json.loads(catalogue.read_text(encoding='utf-8-sig')))
    selected=producer/'selected-network.json'
    if expected['selected']!=report.get('selected') or network!=json.loads(selected.read_text(encoding='utf-8-sig')):raise ProjectError('rectangular selection differs from source reconstruction')
    saved=json.loads((producer/'selected/network.json').read_text(encoding='utf-8-sig'))
    if saved.get('input_sha256')!=digest(selected) or saved.get('calculated_checks_pass') is not True:raise ProjectError('rectangular selected rerun identity/checks differ')
    return selected


def validate_catalogue(project,catalogue):
    return engine._validate_catalogue(project,catalogue,prepare,DIMENSIONS)


def derive(project,catalogue,options,choices):
    return engine._derive(project,catalogue,options,choices,DIMENSIONS)


def search(project,catalogue):
    result,selected=engine._search(project,catalogue,validate_catalogue,derive,calculate)
    result['scope']='Finite supplied rectangular catalogue optimum under prescribed level air-tree assumptions; not product selection, spatial fit or Hong Kong acceptance'
    result['pending']+=['rectangular size-dependent fitting K and fully-developed correlation applicability','duct spatial fit, insulation, leakage, fire/smoke and acoustic review']
    return result,selected


def run(project,catalogue,out):return engine._run(project,catalogue,out,search,analyse)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('project',type=Path)
    parser.add_argument('--catalogue',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();result=run(args.project,args.catalogue,args.out)
    print(json.dumps({k:result[k] for k in ('candidate_count','feasible_count','selected','design_accepted')}))
    return 0 if result['feasible_design_found'] and result['selected_rerun_pass'] else 2


if __name__=='__main__':raise SystemExit(main())

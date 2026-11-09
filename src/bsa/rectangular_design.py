"""Finite supplied-catalogue rectangular duct sizing using existing search and pressure engines."""
import argparse
import json
from pathlib import Path
from . import network_design as engine
from .rectangular_network import prepare,calculate,run as analyse

DIMENSIONS=('width_m','height_m')


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

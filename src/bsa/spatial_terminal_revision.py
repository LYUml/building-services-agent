"""Replay explicitly declared terminal alternatives against the same verified room balance."""
import argparse
import json
from pathlib import Path
from .cli import digest
from .module_contract import read_json
from .workspace import allowed
from . import spatial_air_allocation as allocation
from . import spatial_terminal_performance as performance


def comparison(before,after,old_allocation,new_allocation):
    if old_allocation['balance_result']!=new_allocation['balance_result']:raise ValueError('Candidate replaced original room balance')
    a,b=before['calculation'],after['calculation']
    return dict(original_outside_cases=a['outside_catalogue_cases'],candidate_outside_cases=b['outside_catalogue_cases'],
        original_terminal_count=old_allocation['calculation']['terminal_count'],candidate_terminal_count=new_allocation['calculation']['terminal_count'],
        original_maximum_flow_L_s=old_allocation['calculation']['maximum_flow_L_s'],candidate_maximum_flow_L_s=new_allocation['calculation']['maximum_flow_L_s'],
        catalogue_range_covered=b['outside_catalogue_cases']==0,design_accepted=False,
        scope='Explicit candidate comparison only;range coverage is not product selection,ADPI,acoustics,physical installation,regulatory or full engineering acceptance')


def run(original,basis,products,out):
    original,basis,products,out=[Path(p).resolve() for p in (original,basis,products,out)]
    if not all(allowed(p) for p in (original,basis,products,out)) or out.exists():raise ValueError('Selected sources and new candidate output required')
    if original.name!='terminal-performance.json':raise ValueError('Exact verified original performance report required')
    before_sha=digest(original);before=performance.verify(original.parent)
    old=allocation.verify(Path(before['allocation_result']).parent)
    pins=dict(before['inputs']);pins[str(original)]=before_sha;pins[str(basis)]=digest(basis)
    _,selected_pins=performance.selections(products);pins.update(selected_pins);pins[str(Path(__file__).resolve())]=digest(Path(__file__))
    if any(out==Path(p) or out in Path(p).parents for p in pins):raise ValueError('Candidate output overlaps source inputs')
    # Producers validate exact room/terminal coverage and inherit original thermal inputs.
    candidate=allocation.run(old['balance_result'],basis,out/'allocation')
    after=performance.run(out/'allocation/terminal-allocation.json',products,out/'performance')
    performance.verify(original.parent)
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Candidate source changed during replay')
    result=dict(original=str(original),basis=str(basis),products=str(products),inputs=pins,comparison=comparison(before,after,old,candidate),design_accepted=False)
    (out/'candidate-comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8');verify(out);return result


def verify(folder):
    folder=Path(folder).resolve()
    if not allowed(folder):raise ValueError('Selected candidate workspace required')
    result=read_json(folder/'candidate-comparison.json')
    if set(result)!={'original','basis','products','inputs','comparison','design_accepted'} or result['design_accepted'] is not False:raise ValueError('Exact unaccepted candidate report required')
    original=Path(result['original']);basis=Path(result['basis']);products=Path(result['products'])
    if not all(allowed(p) for p in (original,basis,products)) or original.name!='terminal-performance.json':raise ValueError('Selected original/basis/product sources required')
    before=performance.verify(original.parent);old=allocation.verify(Path(before['allocation_result']).parent)
    new=allocation.verify(folder/'allocation');after=performance.verify(folder/'performance')
    if Path(new['basis'])!=basis or Path(after['basis'])!=products or Path(after['allocation_result'])!=(folder/'allocation/terminal-allocation.json'):raise ValueError('Candidate replaced declared inputs')
    pins=dict(before['inputs']);pins[str(original)]=digest(original);pins[str(basis)]=digest(basis)
    _,selected_pins=performance.selections(products);pins.update(selected_pins);pins[str(Path(__file__).resolve())]=digest(Path(__file__))
    if result['inputs']!=pins or any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Candidate source/method pins differ')
    if result['comparison']!=comparison(before,after,old,new):raise ValueError('Candidate comparison differs from replay')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('original');parser.add_argument('--basis',required=True);parser.add_argument('--products',required=True);parser.add_argument('--out',required=True)
    args=parser.parse_args();run(args.original,args.basis,args.products,args.out)

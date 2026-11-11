"""Reuse existing rectangular native reconciliation and pressure budget on a saved IFC."""
import argparse
import json
from pathlib import Path
import shutil
import ifcopenshell
from bsa.cli import digest
from bsa.network_binding import _prepare
from bsa.rectangular_binding import inspect_saved
from bsa.rectangular_network import run as analyse


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('project','model','binding','ifc','out'):parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args();paths={k:v.resolve() for k,v in vars(args).items()};out=paths.pop('out')
    pins={str(p):digest(p) for p in paths.values()}
    data={k:json.loads(p.read_text(encoding='utf-8-sig')) for k,p in paths.items() if k!='ifc'}
    if ifcopenshell.open(str(paths['ifc'])).schema!='IFC4':raise ValueError('Saved IFC4 required')
    derived,evidence=_prepare(data['project'],data['model'],data['binding'],rectangular=True)
    used={n for chain in data['binding']['segments'].values() for n in chain}
    if used!={d['id'] for d in data['model']['devices'] if d['ifc_class'] in ('IfcDuctSegment','IfcDuctFitting')}:raise ValueError('Exact source duct coverage required')
    out.mkdir(parents=True,exist_ok=False)
    generated=out/'network-input.json';generated.write_text(json.dumps(derived,indent=2),encoding='utf-8')
    inspect_saved(paths['ifc'],data['model'],generated,data['binding'])
    shutil.copyfile(paths['ifc'],out/'verified-model.ifc')
    result=analyse(generated,out/'analysis')
    if any(digest(Path(p))!=h for p,h in pins.items()) or digest(out/'verified-model.ifc')!=pins[str(paths['ifc'])]:raise ValueError('Saved analysis source changed')
    report=dict(inputs=pins,segments=evidence,saved_ifc_geometry_match=True,complete_source_duct_coverage=True,calculated_checks_pass=result['calculated_checks_pass'],design_accepted=False)
    (out/'network-binding.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return 0 if result['calculated_checks_pass'] else 2


if __name__=='__main__':raise SystemExit(main())

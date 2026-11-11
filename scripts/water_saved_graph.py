"""Fixed worker around the existing saved-native water binding adapter."""
import argparse
from pathlib import Path
import ifcopenshell
from bsa.water_binding import run


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('project','ifc','binding','out'):parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args()
    if ifcopenshell.open(str(args.ifc)).schema!='IFC4':raise ValueError('Saved IFC4 required')
    result=run(args.project,args.ifc,args.binding,args.out)
    raise SystemExit(0 if result['calculated_checks_pass'] else 2)

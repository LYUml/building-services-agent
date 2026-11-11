"""Neutral geometry exchange using the existing native IfcOpenShell box extractor."""
import argparse
import importlib.metadata
import json
from pathlib import Path
from bsa.thermal_binding import extract
from moosas_space_exchange import space_contacts


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('ifc','binding','frame','out'):parser.add_argument('--'+name,required=True,type=Path)
    args=parser.parse_args()
    if importlib.metadata.version('ifcopenshell')!='0.8.5':raise ValueError('Pinned IfcOpenShell0.8.5 required')
    binding=json.loads(args.binding.read_text(encoding='utf-8-sig'))
    rows,audit=extract(args.ifc,binding)
    if not rows:raise ValueError('At least one source-verified box space is required')
    payload=dict(schema='bsa.spatial-boxes/1',coordinate_frame=json.loads(args.frame.read_text(encoding='utf-8')),
        units=dict(length='m',area='m2'),classification='geometry-derived',
        spaces=[dict(id=r['guid'],origin_m=r['origin_m'],size_m=r['size_m'],floor_area_m2=r['floor_area_m2']) for r in audit['spaces']],
        contacts=space_contacts(rows,binding),simulation_ready=False)
    args.out.write_text(json.dumps(dict(geometry=audit,payload=payload),indent=2),encoding='utf-8')


if __name__=='__main__':main()

"""Isolated pinned CadQuery ruled-loft worker; no pressure/product acceptance."""
import argparse
import hashlib
import importlib.metadata as metadata
import json
import math
from pathlib import Path
import re
from .workspace import allowed

DIMENSIONS=('width_m','height_m','diameter_m','section_offset_m',
            'taper_length_m','start_length_m','end_length_m')


def validate(spec):
    if not isinstance(spec,dict) or set(spec)!={'source','cases'} or not isinstance(spec['source'],str) or not spec['source'].strip():
        raise ValueError('Exact source declaration and cases required')
    if not isinstance(spec['cases'],list) or not spec['cases']:raise ValueError('Nonempty case list required')
    ids=set()
    for row in spec['cases']:
        if not isinstance(row,dict) or set(row)!={'id',*DIMENSIONS}:raise ValueError('Exact local loft dimensions required')
        name=row['id']
        reserved={'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}
        if not isinstance(name,str) or re.fullmatch(r'[A-Za-z0-9_-]+',name) is None or name in ids or name.upper() in reserved:raise ValueError('Unique path-safe case IDs required')
        ids.add(name)
        if any(type(row[k]) not in (int,float) or not math.isfinite(row[k]) or row[k]<=0 for k in DIMENSIONS):raise ValueError('Finite positive dimensions required')
        if 2*row['section_offset_m']>=min(row['width_m'],row['height_m'],row['diameter_m']):raise ValueError('Section offset must be smaller than half each bore dimension')
    return spec


def run(source,out):
    source,out=Path(source).resolve(),Path(out).resolve()
    if not allowed(source) or not allowed(out) or out.exists() or out==source or out in source.parents:raise ValueError('Fresh host-selected output outside source required')
    before=hashlib.sha256(source.read_bytes()).hexdigest()
    spec=validate(json.loads(source.read_text(encoding='utf-8-sig')))
    versions={p:metadata.version(p) for p in ['cadquery','cadquery-ocp']}
    if versions!={'cadquery':'2.6.1','cadquery-ocp':'7.8.1.1.post1'}:raise ValueError('Pinned CadQuery/OCP isolated runtime required')
    import cadquery as cq
    out.mkdir(parents=True);results=[]
    for row in spec['cases']:
        w,h,d,t,L,a,b=[row[k] for k in DIMENSIONS]
        def solid(offset,extension):
            ww,hh,rr=w+2*offset,h+2*offset,d/2+offset
            loft=cq.Workplane('XY').rect(ww,hh).workplane(offset=L).circle(rr).loft(ruled=True)
            entry=cq.Workplane('XY',origin=(0,0,-a-extension)).rect(ww,hh).extrude(a+extension)
            exit=cq.Workplane('XY',origin=(0,0,L)).circle(rr).extrude(b+extension)
            return loft.union(entry).union(exit)
        outer=solid(t,0);inner=solid(0,.0001);wall=outer.cut(inner).val()
        if not wall.isValid() or len(wall.Solids())!=1 or wall.Volume()<=0:raise ValueError('Closed positive single CAD wall required')
        artifacts={}
        for suffix,value in [('',wall),('-outer',outer.val()),('-inner',inner.val())]:
            if not value.isValid():raise ValueError('CAD operand validity failed')
            target=out/(row['id']+suffix+'.brep')
            if not value.exportBrep(str(target)):raise ValueError('BRep export failed')
            artifacts[target.name]=hashlib.sha256(target.read_bytes()).hexdigest()
        step=out/(row['id']+'.step');cq.exporters.export(wall.scale(1000),str(step))
        # Reimport actual STEP to catch metre/mm export mismatches.
        imported=cq.importers.importStep(str(step)).val()
        if not imported.isValid() or not math.isclose(imported.Volume()/1e9,wall.Volume(),rel_tol=1e-7,abs_tol=1e-12):raise ValueError('STEP units/geometry verification failed')
        artifacts[step.name]=hashlib.sha256(step.read_bytes()).hexdigest()
        results.append(dict(id=row['id'],solid_valid=True,solid_count=1,volume_m3=wall.Volume(),
            brep_sha256=artifacts[row['id']+'.brep'],artifacts=artifacts,STEP_reimport_units_pass=True))
    if hashlib.sha256(source.read_bytes()).hexdigest()!=before:raise ValueError('Input changed during CAD execution')
    report=dict(versions=versions,source_sha256=before,worker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        results=results,brep_coordinate_unit='m',step_coordinate_unit='mm',bore_extension_m=.0001,
        scope='Ruled loft with section-plane-offset wall, not constant sheet-normal thickness; local CAD worker only',
        IFC_verified=False,network_merged=False,product_selected=False,pressure_verified=False,design_accepted=False)
    (out/'kernel-review.json').write_text(json.dumps(report,indent=2))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();r=run(args.source,args.out)
    print(json.dumps(dict(cases=len(r['results']),CAD_checks_pass=True,design_accepted=False)))

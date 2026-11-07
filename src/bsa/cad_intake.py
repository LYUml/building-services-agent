"""Read-only source drawing inventory and explicitly selected spatial measurements."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import shutil
from .cli import digest
from .engine import ProjectError
from .native_cad import DEFAULT_EXE, execute, lisp_string

METRES_PER_UNIT={1:0.0254,2:0.3048,4:0.001,5:0.01,6:1.0}


def export_dwg(source,out,exe=DEFAULT_EXE,timeout=120):
    source,out,exe=(Path(p).resolve() for p in (source,out,exe))
    if source.suffix.lower()!='.dwg' or not source.is_file() or not exe.is_file():
        raise ProjectError('existing DWG and AutoCAD executable required')
    if out==source or out in source.parents:raise ProjectError('output must not contain source')
    before=digest(source);out.mkdir(parents=True,exist_ok=False)
    copied=out/'source-copy.dwg';shutil.copyfile(source,copied)
    dxf=out/'source-export.dxf';script=out/'export.scr'
    condition=f'(= (strcase (vl-string-translate (chr 92) "/" (strcat (getvar "DWGPREFIX") (getvar "DWGNAME")))) (strcase {lisp_string(copied)}))'
    # Core Console QUIT asks whether to DISCARD changes; Y preserves the on-disk copy.
    script.write_text(f'(if {condition} (progn (setvar "FILEDIA" 0) (setvar "CMDDIA" 0) (command "_.DXFOUT" {lisp_string(dxf)} "16")) (princ "BSA WRONG DOCUMENT"))\n_.QUIT\n_Y\n',encoding='ascii')
    execute(exe,copied,script,out/'export.log',timeout)
    if not dxf.is_file():raise ProjectError('AutoCAD DXF export missing; inspect export.log')
    if digest(source)!=before or digest(copied)!=before:raise ProjectError('DWG source or isolated copy changed')
    return dxf


def inventory(path):
    import ezdxf
    doc=ezdxf.readfile(path);audit=doc.audit()
    if audit.errors or audit.fixes:raise ProjectError('DXF requires repair; preserve source and review separately')
    records=[]
    def vector(v):
        values=[float(x) for x in v]
        if len(values)!=3 or not all(math.isfinite(x) for x in values):raise ProjectError('invalid drawing coordinates')
        return values
    for entity in doc.modelspace():
        kind=entity.dxftype()
        row=dict(handle=entity.dxf.handle,type=kind,layer=entity.dxf.layer,layout='Model')
        if kind=='LINE':row.update(start=vector(entity.dxf.start),end=vector(entity.dxf.end))
        elif kind=='LWPOLYLINE':
            row.update(vertices=[vector(p) for p in entity.vertices_in_wcs()],closed=entity.closed,
                       bulges=[p[4] for p in entity],has_width=entity.has_width)
        elif kind in ('CIRCLE','ARC'):
            row.update(centre=vector(entity.ocs().to_wcs(entity.dxf.center)),radius=entity.dxf.radius,
                       extrusion=vector(entity.dxf.extrusion))
            if kind=='ARC':row.update(start_angle=entity.dxf.start_angle,end_angle=entity.dxf.end_angle)
        elif kind in ('TEXT','MTEXT'):
            row.update(text=entity.dxf.text if kind=='TEXT' else entity.plain_text(),
                       insert=vector(entity.ocs().to_wcs(entity.dxf.insert) if kind=='TEXT' else entity.dxf.insert))
        elif kind=='INSERT':
            row.update(block=entity.dxf.name,insert=vector(entity.ocs().to_wcs(entity.dxf.insert)),
                       rotation_deg=entity.dxf.rotation,scale=[entity.dxf.xscale,entity.dxf.yscale,entity.dxf.zscale],
                       attributes=[dict(tag=a.dxf.tag,text=a.dxf.text) for a in entity.attribs],
                       geometry_status='unexpanded block; nested geometry not measured')
        else:row['geometry_status']='unsupported; retained in inventory only'
        records.append(row)
    references=[dict(name=b.name,path=b.block.dxf.get('xref_path','')) for b in doc.blocks if b.block.dxf.flags & 12]
    code=int(doc.header.get('$INSUNITS',0))
    return dict(dxf_sha256=digest(Path(path)),drawing_sha256=digest(Path(path)),dxf_version=doc.dxfversion,insunits=code,
                metres_per_unit=METRES_PER_UNIT.get(code),counts=dict(Counter(r['type'] for r in records)),
                layers=[dict(name=l.dxf.name,off=l.is_off(),frozen=l.is_frozen(),locked=l.is_locked()) for l in doc.layers],
                entities=records,external_references=references,
                pending=['block/xref/proxy/nested geometry interpretation','paper-space and viewport scale review','original drawing visual review'])


def polygon_area(points):
    """Area of a simple horizontal straight polygon; touching/crossed boundaries rejected."""
    if any(len(p)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in p) for p in points):
        raise ProjectError('finite 3D polygon coordinates required')
    if len(points)>1 and points[0]==points[-1]:points=points[:-1]
    if len(points)<3 or len({tuple(p) for p in points})!=len(points):raise ProjectError('simple polygon vertices required')
    if max(p[2] for p in points)-min(p[2] for p in points)>1e-9:raise ProjectError('horizontal polygon required')
    origin=points[0];xy=[(p[0]-origin[0],p[1]-origin[1]) for p in points]
    def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    def on(a,b,p):return abs(cross(a,b,p))<=1e-12 and min(a[0],b[0])-1e-12<=p[0]<=max(a[0],b[0])+1e-12 and min(a[1],b[1])-1e-12<=p[1]<=max(a[1],b[1])+1e-12
    edges=list(zip(xy,xy[1:]+xy[:1]))
    for i,(a,b) in enumerate(edges):
        for j,(c,d) in enumerate(edges):
            if j<=i or j==i+1 or (i==0 and j==len(edges)-1):continue
            if (cross(a,b,c)*cross(a,b,d)<0 and cross(c,d,a)*cross(c,d,b)<0) or any((on(a,b,c),on(a,b,d),on(c,d,a),on(c,d,b))):
                raise ProjectError('self-intersecting or touching polygon')
    area=abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in edges))/2
    if not math.isfinite(area) or area<=1e-12:raise ProjectError('nondegenerate polygon required')
    return area


def measure(data,selection):
    if not isinstance(selection,dict) or set(selection)!={'drawing_sha256','source','unit_check','areas'} or not isinstance(selection['source'],str) or not selection['source'].strip():
        raise ProjectError('explicit sourced selection required')
    if selection['drawing_sha256']!=data['drawing_sha256']:raise ProjectError('selected source drawing changed; review and rebind handles')
    scale=data['metres_per_unit']
    if scale is None:raise ProjectError('known drawing INSUNITS required before spatial measurement')
    entities={e['handle']:e for e in data['entities']}
    check=selection['unit_check']
    if not isinstance(check,dict) or set(check)!={'handle','known_length_m','absolute_tolerance_m','source'}:
        raise ProjectError('source-linked independent LINE dimension check required')
    if not isinstance(check['source'],str) or not check['source'].strip():raise ProjectError('dimension evidence required')
    expected,tolerance=check['known_length_m'],check['absolute_tolerance_m']
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in (expected,tolerance)) or expected<=0 or tolerance<0:
        raise ProjectError('finite positive length and nonnegative tolerance required')
    reference=entities.get(check['handle'])
    if not reference or reference['type']!='LINE':raise ProjectError('unit reference must be a model-space LINE')
    actual=math.dist(reference['start'],reference['end'])*scale
    if abs(actual-expected)>tolerance:raise ProjectError('drawing units disagree with independent dimension')
    if not isinstance(selection['areas'],list):raise ProjectError('explicit area selection list required')
    result=[];ids=set();handles=set()
    for row in selection['areas']:
        if not isinstance(row,dict) or set(row)!={'id','handle','source'} or not isinstance(row['id'],str) or not row['id'].strip() or row['id'] in ids or row['handle'] in handles:
            raise ProjectError('unique sourced area IDs and handles required')
        if not isinstance(row['source'],str) or not row['source'].strip():raise ProjectError('area boundary interpretation source required')
        entity=entities.get(row['handle'])
        if not entity or entity['type']!='LWPOLYLINE' or not entity['closed'] or any(entity['bulges']) or entity['has_width']:
            raise ProjectError('area requires explicit closed straight zero-width LWPOLYLINE')
        points=[[x*scale for x in p] for p in entity['vertices']]
        result.append(dict(**row,area_m2=polygon_area(points),vertices_world_m=points,layer=entity['layer'],
                           evidence_dxf_sha256=data['dxf_sha256']))
        ids.add(row['id']);handles.add(row['handle'])
    return dict(source=selection['source'],unit_check=dict(**check,measured_length_m=actual,pass_check=True),areas=result,
                scope='Selected model-space horizontal polygon geometry only; boundary meaning requires source review',design_accepted=False)


def run(source,out,selection=None,exe=None):
    source,out=Path(source).resolve(),Path(out).resolve()
    selection=Path(selection).resolve() if selection else None
    inputs=[source]+([selection] if selection else [])
    if not source.is_file() or source.suffix.lower() not in ('.dwg','.dxf'):raise ProjectError('existing DWG or DXF required')
    if any(out==p or out in p.parents for p in inputs):raise ProjectError('output must not contain inputs')
    if source.suffix.lower()=='.dwg' and exe is None:raise ProjectError('AutoCAD executable required for DWG intake')
    before={str(p):digest(p) for p in inputs};out.mkdir(parents=True,exist_ok=False)
    if source.suffix.lower()=='.dwg':dxf=export_dwg(source,out/'native',exe)
    else:dxf=out/'source-copy.dxf';shutil.copyfile(source,dxf)
    data=inventory(dxf)
    data['drawing_sha256']=before[str(source)]
    (out/'inventory.json').write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
    measurement=measure(data,json.loads(selection.read_text(encoding='utf-8-sig'))) if selection else None
    if measurement:(out/'measurements.json').write_text(json.dumps(measurement,indent=2,ensure_ascii=False),encoding='utf-8')
    if any(digest(Path(p))!=h for p,h in before.items()):raise ProjectError('source changed during intake')
    result=dict(inputs=before,inputs_unchanged=True,drawing_inventory_pass=True,measurements_pass=measurement is not None,
                design_accepted=False,scope='Read-only drawing extraction; no DWG fidelity, semantic or plot acceptance',
                artifacts={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()})
    (out/'cad-intake.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--selection',type=Path);p.add_argument('--autocad',type=Path)
    a=p.parse_args();r=run(a.source,a.out,a.selection,a.autocad)
    print(json.dumps({k:r[k] for k in ('inputs_unchanged','drawing_inventory_pass','measurements_pass','design_accepted')}))

if __name__=='__main__':main()

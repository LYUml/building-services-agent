"""Editable source-bound room outlines and terminal centre/airflow schematic."""
import argparse
import importlib.metadata
import json
import math
from pathlib import Path
import ezdxf
from .cli import digest
from .module_contract import read_json
from .workspace import allowed
from . import spatial_air_allocation as allocation
from . import spatial_air_balance as balance
from .modules import verify_result


def expected(report,producer,settings):
    if set(settings)!={'annotation_height_m','source'} or not isinstance(settings['source'],str) or not settings['source'].strip():raise ValueError('Explicit sourced annotation settings required')
    height=settings['annotation_height_m']
    if type(height) not in (int,float) or not math.isfinite(height) or not .001<=height<=1:raise ValueError('Annotation height must be .001 to1 metre')
    rows=[]
    for room_number,space in enumerate(producer['payload']['spaces'],1):
        room=report['calculation']['rooms'][space['id']]
        if producer['payload_schema']=='bsa.spatial-polygons/1':vertices=space['boundary_vertices']
        else:
            x,y,_=space['origin_m'];a,b,_=space['size_m'];vertices=[[x,y],[x+a,y],[x+a,y+b],[x,y+b]]
        rows.append(dict(kind='LWPOLYLINE',layer='BSA_ROOM',points=[[float(x),float(y)] for x,y in vertices],closed=True))
        for terminal_number,terminal in enumerate(room['allocation']['terminals'],1):
            x,y=terminal['center_m'];q=terminal['maximum_flow_L_s'];minimum=terminal['minimum_flow_L_s']
            rows.append(dict(kind='POINT',layer='BSA_TERMINAL_CENTER',point=[float(x),float(y),0.]))
            text=f"R{room_number}-T{terminal_number}"
            rows.append(dict(kind='TEXT',layer='BSA_FLOW',text=text,point=[float(x+height),float(y+height),0.],height=height))
            rows.append(dict(kind='TEXT',layer='BSA_FLOW',text=f'{q:.1f}/{minimum:.1f} L/s',point=[float(x+height),float(y-height*2),0.],height=height))
        x,y=vertices[0]
        rows.append(dict(kind='TEXT',layer='BSA_ROOM_LABEL',text=f"R{room_number} | floor z={room['floor_elevation_m']:.3f} m",point=[float(x),float(y-height*2),0.],height=height))
    return rows


def inspect(doc):
    if doc.units!=ezdxf.units.M:raise ValueError('Saved schematic must use metres')
    rows=[]
    for entity in doc.modelspace():
        kind=entity.dxftype();row=dict(kind=kind,layer=entity.dxf.layer)
        if kind=='LWPOLYLINE':
            if entity.dxf.elevation!=0 or any(p[2]!=0 or p[3]!=0 or p[4]!=0 for p in entity.get_points()):raise ValueError('Unmodified planar room boundaries required')
            row.update(points=[[float(x),float(y)] for x,y in entity.get_points('xy')],closed=entity.closed)
        elif kind=='POINT':row['point']=list(entity.dxf.location)
        elif kind=='TEXT':
            if entity.dxf.rotation!=0 or entity.dxf.width!=1 or entity.dxf.oblique!=0 or entity.dxf.style!='Standard' or entity.dxf.halign!=0 or entity.dxf.valign!=0 or tuple(entity.dxf.extrusion)!=(0.,0.,1.):raise ValueError('Unmodified plain schematic text required')
            row.update(text=entity.dxf.text,point=list(entity.dxf.insert),height=entity.dxf.height)
        else:raise ValueError('Unexpected schematic entity')
        rows.append(row)
    return rows


def source(path,settings):
    report=allocation.verify(path.parent)
    if path.name!='terminal-allocation.json':raise ValueError('Exact verified allocation report required')
    upstream=balance.verify(Path(report['balance_result']).parent);producer=verify_result(upstream['producer_result'])
    if importlib.metadata.version('ezdxf')!='1.4.5':raise ValueError('Pinned ezdxf1.4.5 required')
    pins=dict(report['inputs']);pins[str(path)]=digest(path);pins[str(settings)]=digest(settings);pins[str(Path(__file__).resolve())]=digest(Path(__file__))
    return expected(report,producer,read_json(settings)),pins


def run(path,settings,out):
    path,settings,out=[Path(p).resolve() for p in (path,settings,out)]
    if not all(allowed(p) for p in (path,settings,out)) or out.exists():raise ValueError('Selected source workspace and new output required')
    rows,pins=source(path,settings)
    if any(out==Path(p) or out in Path(p).parents for p in pins):raise ValueError('Drawing output overlaps sources')
    doc=ezdxf.new('R2013');doc.units=ezdxf.units.M
    for name,color in [('BSA_ROOM',7),('BSA_TERMINAL_CENTER',7),('BSA_FLOW',7),('BSA_ROOM_LABEL',7)]:doc.layers.new(name,dxfattribs={'color':color})
    model=doc.modelspace()
    for row in rows:
        attrs=dict(layer=row['layer'])
        if row['kind']=='LWPOLYLINE':model.add_lwpolyline(row['points'],close=True,dxfattribs=attrs)
        elif row['kind']=='POINT':model.add_point(row['point'],dxfattribs=attrs)
        else:model.add_text(row['text'],dxfattribs=dict(attrs,height=row['height'],insert=row['point']))
    doc.header['$PDMODE']=3;doc.header['$PDSIZE']=read_json(settings)['annotation_height_m']
    out.mkdir(parents=True);drawing=out/'Terminal Airflow Schematic.dxf';doc.saveas(drawing)
    if inspect(ezdxf.readfile(drawing))!=rows:raise ValueError('Saved drawing differs from inherited geometry/flows')
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Drawing source changed')
    bindings={f'R{i}':dict(room_id=guid,terminals={f'R{i}-T{j}':t['id'] for j,t in enumerate(room['allocation']['terminals'],1)}) for i,(guid,room) in enumerate(allocation.verify(path.parent)['calculation']['rooms'].items(),1)}
    result=dict(id_bindings=bindings,allocation=str(path),settings=str(settings),inputs=pins,dxf_sha256=digest(drawing),entity_count=len(rows),saved_dxf_correspondence=True,native_reopen_pass=False,plot_visual_review='pending',design_accepted=False,
        scope='World XY source room boundaries and terminal centre/airflow schematic only;centres have no physical size or mounting elevation. No duct routing,installation or native DWG acceptance')
    (out/'drawing.json').write_text(json.dumps(result,indent=2),encoding='utf-8');verify(out);return result


def verify(folder):
    folder=Path(folder).resolve()
    if not allowed(folder):raise ValueError('Selected drawing workspace required')
    r=read_json(folder/'drawing.json')
    if set(r)!={'id_bindings','allocation','settings','inputs','dxf_sha256','entity_count','saved_dxf_correspondence','native_reopen_pass','plot_visual_review','design_accepted','scope'}:raise ValueError('Exact scoped drawing report required')
    path=Path(r['allocation']);settings=Path(r['settings'])
    if not all(allowed(p) for p in (path,settings)) or r.get('design_accepted') is not False or r.get('native_reopen_pass') is not False:raise ValueError('Scoped unaccepted drawing and selected sources required')
    rows,pins=source(path,settings)
    bindings={f'R{i}':dict(room_id=guid,terminals={f'R{i}-T{j}':t['id'] for j,t in enumerate(room['allocation']['terminals'],1)}) for i,(guid,room) in enumerate(allocation.verify(path.parent)['calculation']['rooms'].items(),1)}
    if r.get('id_bindings')!=bindings:raise ValueError('Drawing source identity bindings differ')
    drawing=folder/'Terminal Airflow Schematic.dxf'
    if r['inputs']!=pins or any(digest(Path(p))!=sha for p,sha in pins.items()) or r['dxf_sha256']!=digest(drawing):raise ValueError('Drawing source/output pins differ')
    if inspect(ezdxf.readfile(drawing))!=rows or r['entity_count']!=len(rows) or r['saved_dxf_correspondence'] is not True or r['plot_visual_review']!='pending':raise ValueError('Saved drawing differs from source replay')
    return r


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('allocation');parser.add_argument('--settings',required=True);parser.add_argument('--out',required=True)
    args=parser.parse_args();run(args.allocation,args.settings,args.out)

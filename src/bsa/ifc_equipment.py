"""Verified saved PTAC boxes/results to a GUID-linked plan and equipment schedule."""
import argparse
import csv
import json
import math
from pathlib import Path
import re
from .cli import digest
from .engine import ProjectError
from .hvac_devices import PSET,PROPERTIES


def validate_settings(p):
    if not isinstance(p,dict) or set(p)!={'source','annotation_height_m','tags'} or not isinstance(p['source'],str) or not p['source'].strip():raise ProjectError('sourced equipment plan settings required')
    if type(p['annotation_height_m']) not in (int,float) or not math.isfinite(p['annotation_height_m']) or not .05<=p['annotation_height_m']<=1:raise ProjectError('equipment annotation height must be 0.05..1 metre')
    if not isinstance(p['tags'],list) or not p['tags']:raise ProjectError('explicit equipment callouts required')
    ids=set();tags=set()
    for row in p['tags']:
        if not isinstance(row,dict) or set(row)!={'guid','tag'} or not isinstance(row['guid'],str) or not isinstance(row['tag'],str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,15}',row['tag']) or row['guid'] in ids or row['tag'].upper() in tags:raise ProjectError('unique GUID and ASCII equipment tags required')
        ids.add(row['guid']);tags.add(row['tag'].upper())
    return p


def extract(ifc,report,settings):
    import ifcopenshell
    import ifcopenshell.geom
    import ifcopenshell.util.element as element
    import numpy as np
    from .box_geometry import box_mesh
    data=json.loads(Path(report).read_text(encoding='utf-8-sig'));root=Path(report).resolve().parent
    if not data.get('calculated_checks_pass') or 'hvac_device_binding' not in data or 'annotated_ifc' not in data:raise ProjectError('passing saved HVAC binding report required')
    if data['annotated_ifc']['sha256']!=digest(Path(ifc)):raise ProjectError('equipment source differs from annotated IFC hash')
    for name,sha in data['artifacts'].items():
        path=(root/name).resolve()
        if root not in path.parents or not path.is_file() or digest(path)!=sha:raise ProjectError('HVAC producer artifact missing/changed: '+name)
    annotated={r['device_guid']:r['properties'] for r in data['annotated_ifc']['devices']}
    records=data['hvac_device_binding']['devices'];tags={r['guid']:r['tag'] for r in settings['tags']}
    if set(tags)!={r['device_guid'] for r in records} or set(tags)!=set(annotated):raise ProjectError('equipment callouts must cover every bound HVAC device')
    model=ifcopenshell.open(str(ifc));native=ifcopenshell.geom.settings();native.set(native.USE_WORLD_COORDS,True)
    def bounds(obj):
        shape=ifcopenshell.geom.create_shape(native,obj)
        vertices=np.asarray(shape.geometry.verts).reshape(-1,3);faces=np.asarray(shape.geometry.faces).reshape(-1,3)
        lo,size,volume=box_mesh(vertices,faces)
        return lo.tolist(),size.tolist()
    rooms=[]
    for obj in model.by_type('IfcSpace'):
        origin,size=bounds(obj);rooms.append(dict(guid=obj.GlobalId,name=obj.Name or obj.GlobalId,origin_m=origin,size_m=size))
    rows=[]
    for record in records:
        obj=model.by_guid(record['device_guid']);props=element.get_psets(obj);simulation=props.get(PSET,{})
        for key,expected in annotated[obj.GlobalId].items():
            value=simulation.get(key)
            good=type(value) in (int,float) and math.isclose(value,expected,rel_tol=1e-12,abs_tol=1e-12) if type(expected) is float else value==expected
            if not good:raise ProjectError('saved equipment result property differs from producer report')
        if not obj.is_a('IfcUnitaryEquipment') or element.get_container(obj).GlobalId!=record['space_guid']:raise ProjectError('saved equipment class/space differs')
        origin,size=bounds(obj);design=props['BSA_DesignInputs']
        rows.append(dict(tag=tags[obj.GlobalId],guid=obj.GlobalId,name=obj.Name or '',zone=record['zone_id'],space_guid=record['space_guid'],system_guid=record['system_guid'],origin_m=origin,size_m=size,
                         cooling_capacity_thermal_kw=design[PROPERTIES['cooling_capacity_w']]/1000,heating_capacity_thermal_kw=design[PROPERTIES['heating_capacity_w']]/1000,
                         supply_flow_l_s=design[PROPERTIES['supply_flow_m3_s']]*1000,baseline_simulated_electricity_kwh=simulation['BaselineAnnualElectricity_kWh'],variant_simulated_electricity_kwh=simulation['VariantAnnualElectricity_kWh'],baseline_simulated_peak_electricity_kw=simulation['BaselinePeakElectricity_kW'],source=record['source']))
    excluded=[dict(guid=o.GlobalId,name=o.Name,ifc_class=o.is_a()) for o in model.by_type('IfcElement') if o.GlobalId not in tags]
    return sorted(rows,key=lambda r:r['tag']),rooms,excluded


def draw(rows,rooms,height,out):
    import ezdxf
    doc=ezdxf.new('R2018');doc.header['$INSUNITS']=6;doc.appids.new('BSA_IFC')
    for layer,color in (('BSA_SPACE',8),('BSA_EQUIPMENT',4),('BSA_EQUIPMENT_REFERENCE',4),('BSA_LABEL',7),('BSA_LEADER',8),('BSA_TABLE',7)):doc.layers.new(layer,dxfattribs={'color':color})
    ms=doc.modelspace()
    def link(entity,guid):entity.set_xdata('BSA_IFC',[(1000,guid)]);return entity
    def text(value,x,y,guid=None,h=None):
        entity=ms.add_text(value,dxfattribs={'insert':(x,y),'height':h or height,'layer':'BSA_LABEL'})
        return link(entity,guid) if guid else entity
    def rectangle(row,room=False):
        x,y,_=row['origin_m'];w,d,_=row['size_m'];points=[(x,y),(x+w,y),(x+w,y+d),(x,y+d)]
        for i,(a,b) in enumerate(zip(points,points[1:]+points[:1])):
            layer='BSA_SPACE' if room else 'BSA_EQUIPMENT_REFERENCE' if i==0 else 'BSA_EQUIPMENT'
            link(ms.add_line(a,b,dxfattribs={'layer':layer}),row['guid'])
    for room in rooms:
        rectangle(room,True);x,y,_=room['origin_m'];w,d,_=room['size_m'];text(room['name'],x+.3,y+d/2,room['guid'])
    xmax=max(r['origin_m'][0]+r['size_m'][0] for r in rooms);label_x=xmax+1
    ymax=max(r['origin_m'][1]+r['size_m'][1] for r in rooms)
    for i,row in enumerate(rows):
        rectangle(row);x,y,_=row['origin_m'];w,d,_=row['size_m'];label_y=ymax-i*4*height
        link(ms.add_line((x+w/2,y+d),(x+w/2,y+d+3*height),dxfattribs={'layer':'BSA_LEADER'}),row['guid'])
        text(row['tag'],x,y+d+3.5*height,row['guid'])
        text(row['tag']+'  '+row['name'],label_x,label_y,row['guid']);text(row['guid'],label_x,label_y-1.5*height,row['guid'])
    xmin=min(r['origin_m'][0] for r in rooms);ymin=min(r['origin_m'][1] for r in rooms)
    text('HVAC EQUIPMENT ENVELOPE PLAN',xmin,ymax+11*height,h=1.4*height)
    text('IFC thermal-space outlines; generic device boxes; installation details pending',xmin,ymax+8*height)
    text('IFC X/Y coordinates in metres; orientation/georeferencing as supplied',xmin,ymax+5.5*height)
    columns=[0,1.4,4.4,7.4,10.4,13.4,17.4,22.5]
    headers=['Tag','Zone','Cool kWth','Heat kWth','Flow L/s','Base sim kWh','Var sim kWh','Peak sim kW']
    table_y=ymin-3*height;row_height=2.5*height
    for i,header in enumerate(headers):text(header,xmin+columns[i],table_y)
    for j,row in enumerate(rows,1):
        values=[row['tag'],row['zone'],f"{row['cooling_capacity_thermal_kw']:.3f}",f"{row['heating_capacity_thermal_kw']:.3f}",f"{row['supply_flow_l_s']:.1f}",f"{row['baseline_simulated_electricity_kwh']:.2f}",f"{row['variant_simulated_electricity_kwh']:.2f}",f"{row['baseline_simulated_peak_electricity_kw']:.3f}"]
        for i,value in enumerate(values):text(value,xmin+columns[i],table_y-j*row_height,row['guid'])
    text('Simulated electricity is operating output; nameplate and feeder design values remain separate.',xmin,table_y-(len(rows)+2)*row_height)
    from .cad_overlay import snapshot,reconcile
    from .ifc_native import identity
    expected=snapshot(doc);path=out/'equipment.dxf';doc.saveas(path)
    reconcile(expected,path);saved=ezdxf.readfile(path)
    if identity(doc)!=identity(saved):raise ProjectError('saved equipment DXF identities differ')
    references=list(saved.modelspace().query('LINE[layer=="BSA_EQUIPMENT_REFERENCE"]'))
    if len(references)!=len(rows) or {e.get_xdata('BSA_IFC')[0].value for e in references}!={r['guid'] for r in rows}:raise ProjectError('saved equipment reference coverage differs')
    checks=dict(geometry_layers_annotations_match=True,ifc_xdata_match=True,equipment_reference_count=len(references),metre_units=saved.header['$INSUNITS']==6)
    return dict(device_count=len(rows),space_count=len(rooms),checks=checks)


def run(ifc,report,settings_path,out):
    ifc,report,settings_path,out=[Path(p).resolve() for p in (ifc,report,settings_path,out)]
    if any(out==p or out in p.parents for p in (ifc,report,settings_path)):raise ProjectError('separate equipment drawing output required')
    before={str(p):digest(p) for p in (ifc,report,settings_path)}
    settings=validate_settings(json.loads(settings_path.read_text(encoding='utf-8-sig')));rows,rooms,excluded=extract(ifc,report,settings)
    out.mkdir(parents=True,exist_ok=False);drawing=draw(rows,rooms,settings['annotation_height_m'],out)
    with (out/'equipment.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    if any(digest(Path(p))!=sha for p,sha in before.items()):raise ProjectError('equipment drawing source changed')
    result=dict(inputs=before,inputs_unchanged=True,settings=settings,equipment=rows,spaces=rooms,excluded_elements=excluded,drawing=drawing,calculated_checks_pass=True,design_accepted=False,pending=['native DWG/PDF reopen/scale/visual review','actual products, installation access, duct/port topology and engineering acceptance'])
    result['artifacts']={p.name:digest(p) for p in out.iterdir() if p.is_file()};(out/'equipment.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('ifc',type=Path)
    for key in ('report','settings','out'):p.add_argument('--'+key,required=True,type=Path)
    a=p.parse_args();print(json.dumps(run(a.ifc,a.report,a.settings,a.out),indent=2));return 0


if __name__=='__main__':raise SystemExit(main())

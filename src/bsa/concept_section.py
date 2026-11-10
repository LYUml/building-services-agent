"""Saved native facade horizontal sections and audited CAD, not full architectural plans."""
from collections import Counter
import csv
import json
import math
import re
from pathlib import Path
import numpy as np
from .cli import digest
from .engine import ProjectError
from .concept_layout import geometry_handoff,validate_settings as layout_settings
from .concept_facade import inspect,settings as facade_settings,specs


def section(model,z,storey):
    import ifcopenshell.geom
    import trimesh
    from shapely.geometry import LineString
    from shapely.ops import unary_union,polygonize_full
    from .circular_geometry import configure
    geom=ifcopenshell.geom.settings();geom.set(geom.USE_WORLD_COORDS,True);configure(geom)
    rows=[]
    for obj in model.by_type('IfcWall')+model.by_type('IfcWindow'):
        if obj.ContainedInStructure[0].RelatingStructure.Name!=storey:continue
        shape=ifcopenshell.geom.create_shape(geom,obj);v=np.array(shape.geometry.verts).reshape(-1,3);f=np.array(shape.geometry.faces).reshape(-1,3)
        segments=trimesh.intersections.mesh_plane(trimesh.Trimesh(v,f,process=False),[0,0,1],[0,0,z])
        polygons=[]
        if len(segments):
            lines=[LineString(np.round(line[:,:2],8)) for line in segments]
            p,cuts,dangles,invalid=polygonize_full(unary_union(lines))
            if not cuts.is_empty or not dangles.is_empty or not invalid.is_empty or p.is_empty:raise ProjectError('native section is not closed polygon linework')
            for poly in p.geoms:
                poly=poly.simplify(1e-8,preserve_topology=True)
                if not poly.is_valid or poly.area<=0:raise ProjectError('valid positive section polygon required')
                polygons.append(dict(exterior=list(poly.exterior.coords),holes=[list(r.coords) for r in poly.interiors]))
        rows.append(dict(guid=obj.GlobalId,name=obj.Name,ifc_class=obj.is_a(),polygons=polygons,area_m2=sum(__import__('shapely').geometry.Polygon(r['exterior'],r['holes']).area for r in polygons)))
    return rows


def records(rows,space,level,basis):
    w,d,_=space['size_m'];x,y,_=space['origin_m'];h=basis['annotation_height_m'];g=space['guid']
    lines=[];texts=[]
    def line(a,b,layer,guid=g):lines.append(dict(a=list(a),b=list(b),layer=layer,guid=guid))
    def text(value,p):texts.append(dict(text=value,point=p,guid=g))
    for row in rows:
        layer='BSA_SECTION_WALL' if row['ifc_class']=='IfcWall' else 'BSA_SECTION_WINDOW'
        for poly in row['polygons']:
            for ring in [poly['exterior']]+poly['holes']:
                for a,b in zip(ring,ring[1:]):line(a,b,layer,row['guid'])
    line([x,y-2],[x+w,y-2],'BSA_SECTION_REFERENCE')
    for end in (x,x+w):line([end,y-2.3],[end,y-1.7],'BSA_SECTION_NOTE')
    text(f'{w:g} m SPACE WIDTH',[x+w/2-4*h,y-1.5])
    text(f"CONCEPT {level['id']}  CUT +{basis['cut_height_above_storey_m']:g} m  Z={level['elevation_m']+basis['cut_height_above_storey_m']:g} m",[x,y+d+2])
    text(f"1:{basis['scale_denominator']:g} AT A4  /  UNAPPROVED GEOMETRY",[x,y+d+2+2*h])
    text('SPACE ENVELOPE ONLY',[x+w/2-6*h,y+d/2+2*h])
    text('NO ROOM PROGRAM OR MEP',[x+w/2-7*h,y+d/2])
    for i,value in enumerate(('ACTUAL SAVED WALL/OPENING SECTION; WINDOW ENVELOPES ONLY','CORNERS / SLABS / PRODUCTS / INSTALLATION UNRESOLVED','* LOCAL +Y SHOWN; NO SURVEYED SITE NORTH OR GEOREFERENCING')):text(value,[x,y-3.8-i*2*h])
    a=[x+w-4,y+d-7];b=[x+w-4,y+d-3]
    line(a,b,'BSA_SECTION_NOTE');line(b,[b[0]-.5,b[1]-.8],'BSA_SECTION_NOTE');line(b,[b[0]+.5,b[1]-.8],'BSA_SECTION_NOTE');text('LOCAL +Y*',[x+w-max(7,11*h),y+d-1.7])
    return lines,texts


def audit(path,rows,space,level,basis):
    import ezdxf
    from .route_drawing_qa import raw_space_markers,precise
    expected_lines,expected_texts=records(rows,space,level,basis);expected=Counter();actual=Counter();doc=ezdxf.readfile(path);raw=raw_space_markers(Path(path))
    def pt(p):return tuple(round(float(v),7) for v in p[:2])
    def lk(layer,g,a,b):return ('LINE',layer,g,*sorted((pt(a),pt(b))))
    for r in expected_lines:expected[lk(r['layer'],r['guid'],r['a'],r['b'])]+=1
    for r in expected_texts:expected[('TEXT','BSA_SECTION_NOTE',r['guid'],r['text'],pt(r['point']))]+=1
    if doc.header.get('$INSUNITS')!=6:raise ProjectError('saved section units must be metres')
    for e in doc.modelspace():
        flags=raw.get(e.dxf.handle.upper(),[]);layer=doc.layers.get(e.dxf.layer)
        if e.dxf.color!=256 or e.dxf.hasattr('true_color') or len(flags)!=1 or flags[0] not in ([],['0']) or e.dxf.invisible or e.dxf.paperspace or layer.is_off() or layer.is_frozen() or layer.dxf.plot!=1:raise ProjectError('saved section must be visible and plot in model space')
        tags=[(t.code,t.value) for t in e.get_xdata('BSA_IFC')] if e.has_xdata('BSA_IFC') else []
        if len(tags)!=1 or tags[0][0]!=1000:raise ProjectError('saved section exact GUID required')
        g=tags[0][1]
        if e.dxftype()=='LINE':
            a,b=list(e.dxf.start),list(e.dxf.end);precise([a,b])
            if abs(a[2])+abs(b[2])>1e-8:raise ProjectError('saved section must be in XY')
            actual[lk(e.dxf.layer,g,a,b)]+=1
        elif e.dxftype()=='TEXT':
            p=list(e.dxf.insert);precise([p]);d=e.dxf
            if abs(p[2])>1e-8 or not math.isclose(d.height,basis['annotation_height_m']) or d.rotation or d.oblique or d.halign or d.valign or d.width!=1 or d.text_generation_flag or not d.extrusion.isclose((0,0,1),abs_tol=1e-8):raise ProjectError('saved section source text style differs')
            actual[('TEXT',d.layer,g,d.text,pt(p))]+=1
        else:raise ProjectError('saved section only supports LINE/TEXT')
    if actual!=expected:raise ProjectError('saved section geometry/notes/GUID coverage differs')
    return dict(entity_count=sum(actual.values()),saved_geometry_notes_identity_pass=True,model_space_visibility_pass=True,design_accepted=False)


def validate_basis(b,source=None):
    if set(b)!={'source','cut_height_above_storey_m','annotation_height_m','scale_denominator'} or not isinstance(b['source'],str) or not b['source'].strip() or any(type(b[k]) not in (int,float) or not math.isfinite(b[k]) or b[k]<=0 for k in ('cut_height_above_storey_m','annotation_height_m','scale_denominator')):raise ProjectError('explicit sourced cut/annotation/scale required')
    if source is not None:
        if any(not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}',r['id']) for r in source['storeys']):raise ProjectError('path-safe ASCII storey identifiers required for section sheets')
        if any(b['cut_height_above_storey_m']>=r['height_m'] for r in source['storeys']):raise ProjectError('cut must be strictly inside each storey')
    return b


def run(ifc,project,layout,facade_basis,drawing_basis,out,autocad=None):
    import ifcopenshell
    import ezdxf
    from importlib import metadata
    ifc,project,layout,facade_basis,drawing_basis,out=map(lambda p:Path(p).resolve(),(ifc,project,layout,facade_basis,drawing_basis,out))
    pins={str(p):digest(p) for p in (ifc,project,layout,facade_basis,drawing_basis)}
    source=json.loads(project.read_text(encoding='utf-8-sig'));l=layout_settings(json.loads(layout.read_text(encoding='utf-8-sig')));f=facade_settings(json.loads(facade_basis.read_text(encoding='utf-8-sig')));b=json.loads(drawing_basis.read_text(encoding='utf-8-sig'))
    validate_basis(b,source)
    h=geometry_handoff(ifc,source,l['window_wall_ratio']);model=ifcopenshell.open(str(ifc));inspect(model,source,h,f)
    represented=[o for o in model.by_type('IfcElement') if o.Representation]
    if any(o.is_a() not in ('IfcWall','IfcWindow','IfcOpeningElement') for o in represented):raise ProjectError('complete facade-only represented context required')
    spaces={r['id']:dict(r,guid=next(o.GlobalId for o in model.by_type('IfcSpace') if o.Name==r['id'])) for r in source['spaces']}
    out.mkdir(parents=True,exist_ok=False);results={}
    for level in source['storeys']:
        matched=[r for r in spaces.values() if r['storey']==level['id']]
        if len(matched)!=1:raise ProjectError('one concept space per storey required for this sheet')
        space=matched[0];z=level['elevation_m']+b['cut_height_above_storey_m'];rows=section(model,z,level['id'])
        for w,row,m,length,height in specs(h,source,f):
            if row['storey']!=level['id']:continue
            inside=w['sill_m']<b['cut_height_above_storey_m']<w['sill_m']+w['height_m']
            expected={'IfcWall':(length-(w['width_m'] if inside else 0))*f['wall_thickness_m'],'IfcWindow':w['width_m']*f['window_envelope_thickness_m'] if inside else 0}
            for cls,area in expected.items():
                r=next(r for r in rows if r['name']==cls+'_'+w['id'])
                if not math.isclose(r['area_m2'],area,abs_tol=1e-6,rel_tol=1e-7):raise ProjectError('native cut area differs from source opening/thickness')
        folder=out/level['id'];folder.mkdir();doc=ezdxf.new('R2018');doc.header['$INSUNITS']=6;doc.appids.new('BSA_IFC')
        for name,color,weight in [('BSA_SECTION_WALL',7,25),('BSA_SECTION_WINDOW',4,13),('BSA_SECTION_REFERENCE',7,18),('BSA_SECTION_NOTE',7,18)]:doc.layers.new(name,dxfattribs=dict(color=color,lineweight=weight))
        lines,texts=records(rows,space,level,b)
        for r in lines:doc.modelspace().add_line(r['a'],r['b'],dxfattribs=dict(layer=r['layer'])).set_xdata('BSA_IFC',[(1000,r['guid'])])
        for r in texts:doc.modelspace().add_text(r['text'],dxfattribs=dict(insert=r['point'],height=b['annotation_height_m'],layer='BSA_SECTION_NOTE')).set_xdata('BSA_IFC',[(1000,r['guid'])])
        path=folder/'section.dxf';doc.saveas(path);checked=audit(path,rows,space,level,b)
        x,y,_=space['origin_m'];w,d,_=space['size_m'];sheet=dict(source=b['source'],window_drawing_units=[x-2.5,y-max(7,4.6+4*b['annotation_height_m']),x+w+2.5,y+d+max(5,2.8+3*b['annotation_height_m'])],scale_denominator=b['scale_denominator'],reference_ifc_guid=space['guid'],pdf_tolerance_mm=.5,reference_layer='BSA_SECTION_REFERENCE',drawing_name='section')
        from .ifc_native import validate_settings,run as native
        validate_settings(sheet);(folder/'sheet.json').write_text(json.dumps(sheet,indent=2),encoding='utf-8')
        native_result=None
        if autocad:
            native_result=native(path,folder/'sheet.json',folder/'native',Path(autocad))
            audit(folder/'native/native-reopen/source-export.dxf',rows,space,level,b)
        results[level['id']]=dict(cut_world_z_m=z,sections=rows,dxf_audit=checked,native=native_result)
        (folder/'sections.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ProjectError('section source changed')
    result=dict(inputs=pins,runtime={n:metadata.version(n) for n in ('trimesh','shapely','ifcopenshell','ezdxf')},storeys=results,native_reopen_pass=bool(autocad) and all(r['native']['native_reopen_pass'] for r in results.values()),design_accepted=False,pending=['actual PDF visual review','room program, architectural corner/slab/roof and product details','MEP, site north and full engineering/delivery acceptance'])
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()};(out/'section-delivery.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('ifc','project','layout','facade-basis','drawing-basis','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--autocad',type=Path);a=p.parse_args();r=run(a.ifc,a.project,a.layout,a.facade_basis,a.drawing_basis,a.out,a.autocad);print(json.dumps(dict(storeys=list(r['storeys']),native_reopen_pass=r['native_reopen_pass'],design_accepted=False)))

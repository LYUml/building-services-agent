"""Extract closed vertical IFC space prisms into source-linked MOOSAS surfaces.

Reuse native IfcOpenShell world-SI geometry,Manifold solid validation and Shapely
planar unions;do not infer building heights from plan outlines or area metadata.
"""
import argparse
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import os
from .cli import digest
from .workspace import allowed


def read_settings(path):
    from .module_contract import read_json
    values=read_json(path)
    if not isinstance(values,dict) or set(values)!={'length_tolerance_m','area_tolerance_m2'} or any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in values.values()):
        raise ValueError('Exact explicit positive source length/area tolerances required')
    return values


def prepare(source, *, length_tolerance_m, area_tolerance_m2):
    import ifcopenshell
    import ifcopenshell.geom
    import ifcopenshell.util.unit
    import numpy as np
    from shapely import union_all
    from shapely.geometry import Polygon,Point
    from shapely.geometry.polygon import orient
    from .solid_clash import from_mesh
    if any(type(v) not in (float,int) or not math.isfinite(v) or v<=0 for v in (length_tolerance_m,area_tolerance_m2)):
        raise ValueError('Explicit positive source geometry tolerances required')
    for name,version in [('ifcopenshell','0.8.5'),('manifold3d','3.5.4'),('shapely','2.2.0'),('numpy','2.5.4')]:
        if importlib.metadata.version(name)!=version:raise ValueError('Pinned '+name+version+' required')
    source=Path(source).resolve();before=digest(source);model=ifcopenshell.open(str(source))
    pins={str(source):before,str(Path(__file__).resolve()):digest(Path(__file__)),str(Path(__file__).with_name('solid_clash.py').resolve()):digest(Path(__file__).with_name('solid_clash.py'))}
    if model.schema!='IFC4':raise ValueError('Scoped IFC4 space body intake required')
    projects=model.by_type('IfcProject')
    units=[u for u in projects[0].UnitsInContext.Units if getattr(u,'UnitType',None)=='LENGTHUNIT'] if len(projects)==1 and projects[0].UnitsInContext else []
    if len(units)!=1 or not units[0].is_a('IfcSIUnit') or units[0].Name!='METRE':raise ValueError('One explicit SI metre-based length unit required')
    factor=ifcopenshell.util.unit.calculate_unit_scale(model)
    if not math.isfinite(factor) or factor<=0:raise ValueError('Positive native unit scale required')
    spaces=model.by_type('IfcSpace')
    if not 1<=len(spaces)<=100 or len({s.GlobalId for s in spaces})!=len(spaces):raise ValueError('Complete unique one-to-100 saved IFC spaces required')
    settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True)
    expected=[];audits=[];faces=[]
    for space in sorted(spaces,key=lambda s:s.GlobalId):
        bodies=[r for r in space.Representation.Representations if r.RepresentationIdentifier=='Body'] if space.Representation else []
        if len(bodies)!=1:raise ValueError('One explicit saved space Body required')
        for item in bodies[0].Items:
            if item.is_a('IfcExtrudedAreaSolid'):
                profile=item.SweptArea
                if profile.is_a('IfcRectangleProfileDef'):continue
                curves=[getattr(profile,'OuterCurve',None),*getattr(profile,'InnerCurves',())]
                if not curves or any(c is None or not c.is_a('IfcPolyline') for c in curves):raise ValueError('Only explicit linear polygon/rectangle space profiles supported')
            elif not any(item.is_a(k) for k in ('IfcPolygonalFaceSet','IfcTriangulatedFaceSet','IfcFacetedBrep')):
                raise ValueError('Only saved planar faceted or linear-extruded space bodies supported')
        shape=ifcopenshell.geom.create_shape(settings,space)
        vertices=np.asarray(shape.geometry.verts,dtype=float).reshape(-1,3);triangles=np.asarray(shape.geometry.faces,dtype=int).reshape(-1,3)
        if not len(vertices) or not len(triangles) or not np.isfinite(vertices).all():raise ValueError('Finite saved space mesh required')
        solid=from_mesh((vertices,triangles))
        if len(solid.decompose())!=1:raise ValueError('One connected closed space solid required')
        bottom=float(vertices[:,2].min());top=float(vertices[:,2].max());height=top-bottom
        if height<=length_tolerance_m or np.any(np.minimum(abs(vertices[:,2]-bottom),abs(vertices[:,2]-top))>length_tolerance_m):raise ValueError('Only constant-height vertical space prisms supported')
        floors=[];ceilings=[];sides=[]
        for triangle in vertices[triangles]:
            if np.all(abs(triangle[:,2]-bottom)<=length_tolerance_m):floors.append(Polygon(triangle[:,:2]))
            elif np.all(abs(triangle[:,2]-top)<=length_tolerance_m):ceilings.append(Polygon(triangle[:,:2]))
            else:sides.append(triangle)
        floor=union_all(floors);ceiling=union_all(ceilings)
        if floor.geom_type!='Polygon' or not floor.is_valid or floor.area<=0 or floor.interiors:raise ValueError('Single valid floor ring without holes required;holes are not filled')
        if ceiling.geom_type!='Polygon' or floor.symmetric_difference(ceiling).area>area_tolerance_m2:raise ValueError('Matching native floor/ceiling footprint required')
        side_area=0.0
        for triangle in sides:
            if Polygon(triangle[:,:2]).area>area_tolerance_m2 or any(floor.boundary.distance(Point(p[:2]))>length_tolerance_m for p in triangle):raise ValueError('Space side triangle differs from vertical footprint boundary')
            side_area+=float(np.linalg.norm(np.cross(triangle[1]-triangle[0],triangle[2]-triangle[0]))/2)
        if abs(side_area-floor.length*height)>area_tolerance_m2 or abs(solid.volume()-floor.area*height)>area_tolerance_m2*height:raise ValueError('Saved space side area/volume differs from vertical prism')
        floor=orient(floor.normalize(),sign=1);xy=[list(map(float,p)) for p in floor.exterior.coords];ring=xy[:-1]
        expected.append(dict(id=space.GlobalId,boundary_vertices=xy,height_m=height,floor_elevation_m=bottom))
        audits.append(dict(guid=space.GlobalId,name=space.Name,floor_area_m2=floor.area,height_m=height,floor_elevation_m=bottom,native_volume_m3=solid.volume(),triangles=len(triangles)))
        faces.extend([(list(reversed([(x,y,bottom) for x,y in ring])),(0,0,-1)),([(x,y,top) for x,y in ring],(0,0,1))])
        for i,(x,y) in enumerate(ring):
            a,b=ring[i],ring[(i+1)%len(ring)];dx=b[0]-a[0];dy=b[1]-a[1];length=math.hypot(dx,dy)
            faces.append(([(a[0],a[1],bottom),(b[0],b[1],bottom),(b[0],b[1],top),(a[0],a[1],top)],(dy/length,-dx/length,0)))
    text=''.join('f,0,'+str(i)+'\nfn,'+','.join(map(str,n))+'\n'+''.join('fv,'+','.join(map(str,v))+'\n' for v in points)+';\n' for i,(points,n) in enumerate(faces))
    declaration=dict(source_sha256=hashlib.sha256(text.encode('utf-8')).hexdigest(),classification='Geometry-derived saved IFC space bodies;not surveyed architecture or thermal readiness',length_unit='m',expected=expected,length_tolerance_m=length_tolerance_m,area_tolerance_m2=area_tolerance_m2)
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Saved IFC or method changed during source extraction')
    return text,declaration,dict(inputs=pins,ifc_sha256=before,length_unit_scale_to_m=factor,complete_saved_space_coverage=True,spaces=audits,design_accepted=False)


def run(source,out,*,length_tolerance_m,area_tolerance_m2):
    source,out=Path(source).resolve(),Path(out).resolve()
    if not allowed(source) or not allowed(out) or out.exists() or source.is_relative_to(out):raise ValueError('Selected source workspace and new separate output required')
    text,declaration,audit=prepare(source,length_tolerance_m=length_tolerance_m,area_tolerance_m2=area_tolerance_m2)
    out.mkdir(parents=True);geometry=out/'space-surfaces.geo';geometry.write_bytes(text.encode('utf-8'))
    expectations=out/'space-expectations.json';expectations.write_text(json.dumps(declaration,indent=2),encoding='utf-8')
    request=dict(schema='bsa.module-request/1',project_id='saved-ifc-spaces',scenario_id='native-source-intake',capability='spatial.surface-room-recognition',coordinate_frame=dict(id='ifc-world-si',kind='source-world-si',length_unit='m',georeferenced=False),sources={k:dict(path=os.path.relpath(p,out),sha256=digest(p)) for k,p in [('geometry',geometry),('expectations',expectations),('ifc_source',source)]})
    (out/'request.json').write_text(json.dumps(request,indent=2),encoding='utf-8');(out/'intake.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    return audit


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source');parser.add_argument('--out',required=True);parser.add_argument('--length-tolerance-m',required=True,type=float);parser.add_argument('--area-tolerance-m2',required=True,type=float)
    args=parser.parse_args();run(args.source,args.out,length_tolerance_m=args.length_tolerance_m,area_tolerance_m2=args.area_tolerance_m2)

"""Source-bound IFC cuts and projections using existing general drawing engines."""
import copy
import importlib.metadata as metadata
import json
from pathlib import Path

from . import drawing_document as drawing, drawing_layout, workspace
from .cli import digest
from .duct_fitting_chain import shape_hash,value

PINS={'ifcopenshell':'0.8.5','trimesh':'5.2.0','numpy':'2.5.4'}


def frame_matrix(value):
    import numpy as np
    a=np.asarray(value,dtype=float)
    if a.shape!=(4,4) or not np.isfinite(a).all() or not np.allclose(a[3],[0,0,0,1],atol=1e-12,rtol=0):
        raise ValueError('Finite homogeneous metre frame required')
    if not np.allclose(a[:3,:3].T@a[:3,:3],np.eye(3),atol=1e-10,rtol=0) or abs(np.linalg.det(a[:3,:3])-1)>1e-10:
        raise ValueError('Right-handed orthonormal section frame required')
    return a


def methods():
    return {name:digest(Path(__file__).with_name(name)) for name in
            ('drawing_ifc_sections.py','circular_geometry.py','drawing_layout.py','source_network_drawing.py','duct_fitting_chain.py')}


def compose(project):
    import numpy as np
    import ifcopenshell,ifcopenshell.geom,ifcopenshell.util.unit,ifcopenshell.util.system
    import trimesh
    from ifcopenshell.util.placement import get_local_placement
    from ifcopenshell.util.shape import get_shape_matrix
    from .circular_geometry import configure
    project=Path(project).resolve()
    if not workspace.allowed(project):raise ValueError('Host project workspace required')
    spec=json.loads(project.read_text(encoding='utf-8-sig'))
    if not isinstance(spec,dict) or set(spec) not in ({'schema','source','ifc','ifc_sha256','layout','views'},{'schema','source','ifc','ifc_sha256','layout','views','mesh_quality'}) or spec['schema']!='bsa.drawing-ifc-sections/1':
        raise ValueError('Exact IFC section drawing fields required')
    drawing.text(spec['source'])
    if not isinstance(spec['ifc'],str) or Path(spec['ifc']).is_absolute():raise ValueError('Recipe-relative IFC required')
    source=(project.parent/spec['ifc']).resolve()
    if not workspace.allowed(source) or source.suffix.lower()!='.ifc' or digest(source)!=spec['ifc_sha256']:raise ValueError('IFC source escaped workspace or changed')
    if any(metadata.version(k)!=v for k,v in PINS.items()):raise ValueError('Pinned IFC section runtimes required')
    layout=copy.deepcopy(spec['layout'])
    if set(layout)!={'source','units','layers','blocks','sheet','content_window','gap_mm'}:raise ValueError('Explicit base layout fields required')
    if layout['units'] not in ('m','mm'):raise ValueError('Explicit m/mm output required')
    if not isinstance(spec['views'],list) or not spec['views']:raise ValueError('Explicit nonempty section views required')
    model=ifcopenshell.open(str(source))
    if ifcopenshell.util.unit.calculate_unit_scale(model)!=1:raise ValueError('Current IFC section reader requires metre source units')
    settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,False);configure(settings)
    quality=spec.get('mesh_quality')
    if quality is not None:
        import math
        if not isinstance(quality,dict) or set(quality)!={'source','classification','linear_deflection_m','angular_deflection_rad'} or quality['classification']!='design_target':raise ValueError('Explicit drawing mesh design target required')
        drawing.text(quality['source'])
        for key in ('linear_deflection_m','angular_deflection_rad'):
            if type(quality[key]) not in (int,float) or not math.isfinite(quality[key]) or quality[key]<=0:raise ValueError('Positive finite drawing mesh targets required')
        if quality['angular_deflection_rad']>math.pi:raise ValueError('Drawing mesh angle must not exceed pi')
        settings.set('mesher-linear-deflection',quality['linear_deflection_m']);settings.set('mesher-angular-deflection',quality['angular_deflection_rad'])
    native_mesh_cache={};projection_cache={};raw_projection_products=[];projection_review_records=[]
    factor=1000 if layout['units']=='mm' else 1;views=[];coverage={};names=set();kinds={};runtimes=dict(PINS)
    for view in spec['views']:
        fields={'id','guids','frame','layer','annotations','port_dimensions'}
        if not isinstance(view,dict) or set(view) not in (fields,fields|{'kind'}):raise ValueError('Exact section view fields required')
        kind=view.get('kind','section')
        if kind not in ('section','projection'):raise ValueError('Supported section/projection view kind required')
        name=drawing.text(view['id'])
        if name in names:raise ValueError('Unique view IDs required')
        names.add(name)
        kinds[name]=kind
        if kind=='projection':
            from .source_network_drawing import project as project_mesh
            if metadata.version('shapely')!='2.2.0':raise ValueError('Pinned Shapely2.2.0 required')
            runtimes['shapely']='2.2.0'
        if not isinstance(view['guids'],list) or not view['guids'] or len(set(view['guids']))!=len(view['guids']):raise ValueError('Unique nonempty product GUIDs required')
        if view['layer'] not in layout['layers']:raise ValueError('Declared section layer required')
        if not isinstance(view['annotations'],list) or not isinstance(view['port_dimensions'],list):raise ValueError('Explicit annotation/dimension lists required')
        frame=frame_matrix(view['frame']);origin=frame[:3,3];axes=frame[:3,:2];normal=frame[:3,2]
        entities=copy.deepcopy(view['annotations']);counts={}
        for guid in view['guids']:
            obj=model.by_guid(guid)
            if not obj.is_a('IfcProduct') or not obj.Representation:raise ValueError('Represented IFC product required')
            # Cache only exact forward geometry within this immutable model/run.
            # Openings are inverse geometry and must never share this cache.
            contexts=tuple(json.dumps(value(r.ContextOfItems),separators=(',',':')) for r in obj.Representation.Representations)
            cache_key=(shape_hash(obj),contexts) if not getattr(obj,'HasOpenings',()) else ('uncached',guid)
            if cache_key not in native_mesh_cache:
                shape=ifcopenshell.geom.create_shape(settings,obj);mesh=shape.geometry
                if not np.allclose(get_shape_matrix(shape),get_local_placement(obj.ObjectPlacement),atol=1e-10,rtol=0):raise ValueError('Native shape placement differs from supported local placement')
                native_mesh_cache[cache_key]=(np.asarray(mesh.verts).reshape(-1,3).copy(),np.asarray(mesh.faces).reshape(-1,3).copy())
            local_vertices,faces=native_mesh_cache[cache_key]
            world=get_local_placement(obj.ObjectPlacement)
            vertices=local_vertices@world[:3,:3].T+world[:3,3]
            counts[guid]=0
            binding=dict(layer=view['layer'],source=f'{spec["source"]}; IFC {spec["ifc_sha256"]}; {guid}',classification='secondary_transcription')
            if kind=='projection':
                # Equal local viewing normals differ only by an in-plane rotation.
                rotation=frame[:3,:3].T@world[:3,:3]
                projection_key=(cache_key,tuple(rotation[2]))
                if projection_key not in projection_cache:
                    projection_review=[]
                    try:polygons=project_mesh(local_vertices@rotation.T,faces,retain_raw_on_cleanup_failure=True,review=projection_review)
                    except Exception as exc:raise ValueError(f'IFC projection failed for {guid}: {exc}') from exc
                    rings=[np.asarray(ring.coords)[:-1].copy() for polygon in polygons for ring in [polygon.exterior,*polygon.interiors]]
                    projection_cache[projection_key]=(rotation.copy(),rings,projection_review)
                reference,rings,projection_review=projection_cache[projection_key]
                if projection_review:projection_review_records.append(dict(view=name,guid=guid,items=projection_review))
                if any(r['kind']=='raw_retained' for r in projection_review):raw_projection_products.append(dict(view=name,guid=guid))
                plane_rotation=rotation@reference.T
                if not np.allclose(plane_rotation[2],[0,0,1],atol=1e-10,rtol=0) or not np.allclose(plane_rotation[:2,2],[0,0],atol=1e-10,rtol=0):raise ValueError('Cached projection planes differ')
                shift=((world[:3,3]-origin)@frame[:3,:3])[:2]
                for ring in rings:
                    points=(ring@plane_rotation[:2,:2].T+shift)*factor
                    entities.append(dict(binding,id=f'{name}:{guid}:outline:{counts[guid]}',kind='polyline',points=points.tolist(),closed=True))
                    counts[guid]+=1
            else:
                segments=trimesh.intersections.mesh_plane(trimesh.Trimesh(vertices,faces,process=False),normal,origin)
                for i,segment in enumerate(segments):
                    xy=((segment-origin)@axes)*factor
                    if np.linalg.norm(xy[1]-xy[0])<1e-10*factor:continue
                    entities.append(dict(binding,id=f'{name}:{guid}:cut:{i}',kind='line',start=xy[0].tolist(),end=xy[1].tolist()))
                    counts[guid]+=1
                if not counts[guid]:raise ValueError('Every selected product must intersect the section plane')
        for d in view['port_dimensions']:
            if not isinstance(d,dict) or set(d)!={'id','ports','layer','distance','text_height'} or not isinstance(d['ports'],list) or len(d['ports'])!=2:raise ValueError('Explicit two-port dimension fields required')
            points=[]
            for guid in d['ports']:
                port=model.by_guid(guid)
                if not port.is_a('IfcDistributionPort') or not port.ObjectPlacement:raise ValueError('Placed native distribution port required')
                owner=ifcopenshell.util.system.get_port_element(port)
                if owner is None or owner.GlobalId not in view['guids']:raise ValueError('Dimension port must belong to a selected product')
                p=get_local_placement(port.ObjectPlacement)[:3,3]-origin
                if abs(float(p@normal))>1e-8:raise ValueError('Dimension ports must lie in the section plane')
                points.append(((p@axes)*factor).tolist())
            entities.append(dict(id=f'{name}:dimension:{d["id"]}',kind='dimension',layer=d['layer'],source=f'Native IFC port separation; {spec["ifc_sha256"]}; '+','.join(d['ports']),classification='secondary_transcription',p1=points[0],p2=points[1],distance=d['distance'],text_height=d['text_height']))
        views.append(dict(id=name,entities=entities));coverage[name]=counts
    layout.update(schema='bsa.drawing-layout/1',views=views)
    drawing_layout.compose(layout)
    if digest(source)!=spec['ifc_sha256']:raise ValueError('IFC changed during section extraction')
    return layout,dict(ifc_sha256=spec['ifc_sha256'],coverage=coverage,mesh_quality=quality,native_mesh_builds=len(native_mesh_cache),native_projection_builds=len(projection_cache),raw_projection_products=raw_projection_products,projection_review_records=projection_review_records,view_kinds=kinds,runtimes=runtimes,methods=methods(),design_accepted=False)


def verify(project,out):
    project,out=Path(project).resolve(),Path(out).resolve()
    if not workspace.allowed(project) or not workspace.intake_output(out):raise ValueError('Host project workspace required')
    record=json.loads((out/'section-result.json').read_text(encoding='utf-8'))
    layout,source=compose(project)
    if record!={'input_sha256':digest(project),'source':source}:raise ValueError('IFC section source or methods changed')
    resolved=out/'resolved-layout.json'
    if json.loads(resolved.read_text(encoding='utf-8'))!=layout:raise ValueError('Resolved IFC section geometry changed')
    result=drawing_layout.verify(resolved,out/'layout')
    for artifact in result['artifacts']:artifact['path']='layout/'+artifact['path']
    result['ifc_sections']=source
    return result


def run(project,out,*,autocad=None):
    project,out=Path(project).resolve(),Path(out).resolve()
    if not workspace.intake_output(out) or out.exists() or out==project or out in project.parents:raise ValueError('Fresh host project output required')
    before=digest(project);layout,source=compose(project)
    out.mkdir(parents=True);resolved=out/'resolved-layout.json'
    resolved.write_text(json.dumps(layout,indent=2)+'\n',encoding='utf-8')
    drawing_layout.run(resolved,out/'layout',autocad=autocad)
    if digest(project)!=before:raise ValueError('Section recipe changed during authoring')
    (out/'section-result.json').write_text(json.dumps(dict(input_sha256=before,source=source),indent=2)+'\n',encoding='utf-8')
    return verify(project,out)

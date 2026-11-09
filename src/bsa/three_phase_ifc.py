"""Saved straight IFC cable geometry versus electrical network route lengths.

Read-only geometric correspondence, not a connected electrical installation.
"""
import argparse
import importlib.metadata
import json
import math
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from .three_phase import prepare,fields,ROOT


def inputs(project,ifc,binding_path):
    """Preflight source inventory without running native geometry."""
    from . import circular_geometry,cad_ifc,solid_clash,quarter_cable,cable_continuity
    _,files=prepare(project)
    ifc,binding_path=Path(ifc).resolve(),Path(binding_path).resolve()
    binding=json.loads(binding_path.read_text(encoding='utf-8-sig'))
    fields(binding,'version ifc_sha256 project_guid system_guid source buses lines')
    source=binding['source'];fields(source,'path sha256 locator kind')
    if not isinstance(source['path'],str) or Path(source['path']).is_absolute():raise ProjectError('relative geometry source required')
    path=(binding_path.parent/source['path']).resolve()
    if not path.is_relative_to(binding_path.parent) or not path.is_file() or digest(path)!=source['sha256']:raise ProjectError('geometry source path/hash mismatch')
    return files|{ifc,binding_path,path,Path(__file__).resolve(),*(Path(m.__file__).resolve() for m in (circular_geometry,cad_ifc,solid_clash,quarter_cable,cable_continuity))}


def inspect(project,ifc,binding_path,*,require_length_match=True):
    if type(require_length_match) is not bool:raise ProjectError('explicit boolean length-match policy required')
    import numpy as np
    import ifcopenshell
    import ifcopenshell.geom
    import ifcopenshell.util.placement as placement
    import ifcopenshell.util.system as system
    import ifcopenshell.util.unit as unit
    from .circular_geometry import configure,BOUNDS_TOLERANCE_M,VOLUME_RELATIVE_TOLERANCE
    from .cad_ifc import mesh_properties
    versions={name:importlib.metadata.version(name) for name in ('ifcopenshell','manifold3d')}
    if versions!={'ifcopenshell':'0.8.5','manifold3d':'3.5.4'}:raise ProjectError('verified IFC/mesh runtime pins required')
    project,ifc,binding_path=[Path(v).resolve() for v in (project,ifc,binding_path)]
    p,_=prepare(project);source_files=inputs(project,ifc,binding_path)
    binding=json.loads(binding_path.read_text(encoding='utf-8-sig'))
    fields(binding,'version ifc_sha256 project_guid system_guid source buses lines')
    if type(binding['version']) is not int or binding['version']!=1 or binding['ifc_sha256']!=digest(ifc):raise ProjectError('version 1 and exact saved IFC hash required')
    source=binding['source'];fields(source,'path sha256 locator kind')
    if not isinstance(source['path'],str) or Path(source['path']).is_absolute():raise ProjectError('relative geometry source required')
    source_path=(binding_path.parent/source['path']).resolve()
    if not source_path.is_relative_to(binding_path.parent) or not source_path.is_file() or digest(source_path)!=source['sha256']:raise ProjectError('geometry source path/hash mismatch')
    if not isinstance(source['locator'],str) or not source['locator'].strip() or source['kind'] not in ('assumption','measured','course_given','manufacturer','design_target'):raise ProjectError('geometry source kind/locator required')
    before={str(f):digest(f) for f in source_files}
    model=ifcopenshell.open(str(ifc));factor=unit.calculate_unit_scale(model)
    if model.schema!='IFC4' or not math.isfinite(factor) or factor<=0:raise ProjectError('IFC4 and positive length-unit scale required')
    projects=model.by_type('IfcProject')
    if len(projects)!=1 or projects[0].GlobalId!=binding['project_guid']:raise ProjectError('IFC project identity differs')
    selected=model.by_guid(binding['system_guid'])
    if not selected or not selected.is_a('IfcDistributionSystem') or selected.PredefinedType!='ELECTRICAL':raise ProjectError('explicit ELECTRICAL distribution system required')
    if not isinstance(binding['buses'],dict) or set(binding['buses'])!={b['id'] for b in p['buses']}:raise ProjectError('exact bus-anchor coverage required')
    if not isinstance(binding['lines'],dict) or set(binding['lines'])!={l['id'] for l in p['lines']}:raise ProjectError('exact electrical line coverage required')
    def vector(v):
        if not isinstance(v,list) or len(v)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in v):raise ProjectError('finite three-coordinate SI bus anchors required')
        return np.array(v,dtype=float)
    anchors={name:vector(v) for name,v in binding['buses'].items()}
    cables={o.GlobalId:o for o in model.by_type('IfcCableSegment') if selected in system.get_element_systems(o)}
    claimed=[]
    for value in binding['lines'].values():
        fields(value,'element_guid from_port_guid to_port_guid');claimed.append(value['element_guid'])
    if len(set(claimed))!=len(claimed) or set(claimed)!=set(cables):raise ProjectError('every selected-system cable must have exactly one analysis-line role')
    settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True);configure(settings)
    rows=[];used_ports=set()
    def line_points(curve):
        if curve.is_a('IfcPolyline'):points=[p.Coordinates for p in curve.Points]
        elif curve.is_a('IfcIndexedPolyCurve'):
            points=curve.Points.CoordList
            if curve.Segments and (len(curve.Segments)!=1 or not curve.Segments[0].is_a('IfcLineIndex') or tuple(curve.Segments[0][0])!=(1,2)):raise ProjectError('only one straight indexed axis segment supported')
        else:raise ProjectError('unsupported cable axis; no endpoint-chord approximation')
        a=np.array(points,dtype=float)
        if a.shape!=(2,3) or not np.isfinite(a).all() or np.linalg.norm(a[1]-a[0])<=1e-8:raise ProjectError('one nonzero straight 3D cable axis required')
        return a
    for line in p['lines']:
        role=binding['lines'][line['id']];obj=cables[role['element_guid']]
        if obj.PredefinedType!='CABLESEGMENT' or {s.GlobalId for s in system.get_element_systems(obj)}!={selected.GlobalId}:raise ProjectError('single-system CABLESEGMENT classification required')
        if not obj.ObjectPlacement or not obj.ObjectPlacement.is_a('IfcLocalPlacement') or not obj.Representation:raise ProjectError('explicit placed cable representations required')
        matrix=placement.get_local_placement(obj.ObjectPlacement)
        if not np.allclose(matrix[3],[0,0,0,1],atol=1e-10,rtol=0) or not np.allclose(matrix[:3,:3].T@matrix[:3,:3],np.eye(3),atol=1e-10,rtol=0) or not math.isclose(float(np.linalg.det(matrix[:3,:3])),1,abs_tol=1e-10):raise ProjectError('rigid right-handed cable placement required')
        axis=[r for r in obj.Representation.Representations if r.RepresentationIdentifier=='Axis']
        body=[r for r in obj.Representation.Representations if r.RepresentationIdentifier=='Body']
        if len(axis)!=1 or len(body)!=1 or len(axis[0].Items)!=1 or len(body[0].Items)!=1:raise ProjectError('one explicit Axis and one Body item required')
        solid=body[0].Items[0]
        quarter=None
        if solid.is_a('IfcBooleanResult'):
            from .cable_continuity import inspect as inspect_continuity
            quarter=inspect_continuity(solid,axis[0].Items[0],matrix,factor,unit.calculate_unit_scale(model,'PLANEANGLEUNIT'))
            ends=quarter['points'][[0,-1]];radius=quarter['radius'];length=quarter['length']
        elif solid.is_a('IfcRevolvedAreaSolid'):
            from .quarter_cable import inspect as inspect_quarter
            quarter=inspect_quarter(solid,axis[0].Items[0],matrix,factor,unit.calculate_unit_scale(model,'PLANEANGLEUNIT'))
            ends=quarter['points'][[0,-1]];radius=quarter['radius'];length=quarter['length']
        else:
            local=line_points(axis[0].Items[0])
            if solid.is_a('IfcSweptDiskSolid') and not solid.is_a('IfcSweptDiskSolidPolygonal'):
                if solid.InnerRadius is not None or solid.StartParam is not None or solid.EndParam is not None:raise ProjectError('full solid cable sweep required')
                body_axis=line_points(solid.Directrix);radius=float(solid.Radius)*factor
            elif solid.is_a('IfcExtrudedAreaSolid'):
                profile=solid.SweptArea
                if profile.is_a()!='IfcCircleProfileDef' or profile.ProfileType!='AREA' or profile.Position is not None:raise ProjectError('unoffset solid circle extrusion profile required')
                if not solid.Position or not solid.Position.is_a('IfcAxis2Placement3D'):raise ProjectError('explicit 3D extrusion placement required')
                frame=placement.get_axis2placement(solid.Position)
                if not np.isfinite(frame).all() or not np.allclose(frame[:3,:3].T@frame[:3,:3],np.eye(3),atol=1e-10,rtol=0) or not math.isclose(float(np.linalg.det(frame[:3,:3])),1,abs_tol=1e-10):raise ProjectError('rigid extrusion frame required')
                vector=np.array(solid.ExtrudedDirection.DirectionRatios,dtype=float)
                depth=float(solid.Depth)
                if vector.shape!=(3,) or not np.isfinite(vector).all() or np.linalg.norm(vector)<=0 or not math.isfinite(depth) or depth<=0:raise ProjectError('finite nonzero extrusion vector and positive depth required')
                vector/=np.linalg.norm(vector)
                if not np.allclose(vector[:2],0,atol=1e-10,rtol=0):raise ProjectError('only perpendicular circular extrusion supported')
                body_axis=np.array([frame[:3,3],(frame@np.append(vector*depth,1))[:3]])
                radius=float(profile.Radius)*factor
            else:raise ProjectError('straight solid circular extrusion or full swept-disk cable required')
            if not (np.allclose(local,body_axis,atol=1e-9,rtol=0) or np.allclose(local,body_axis[::-1],atol=1e-9,rtol=0)):raise ProjectError('body directrix differs from declared Axis')
            ends=np.array([(matrix@np.append(pt,1))[:3]*factor for pt in local])
            length=float(np.linalg.norm(ends[1]-ends[0]))
        if not math.isfinite(radius) or radius<=0:raise ProjectError('positive finite cable envelope radius required')
        ports={port.GlobalId:port for port in system.get_ports(obj)}
        port_ids=[role['from_port_guid'],role['to_port_guid']]
        if len(set(port_ids))!=2 or set(port_ids)!=set(ports) or used_ports.intersection(port_ids):raise ProjectError('two distinct explicitly owned cable ports required')
        used_ports.update(port_ids);points=[]
        for guid in port_ids:
            port=ports[guid]
            if not port.ObjectPlacement or port.PredefinedType!='CABLE' or port.SystemType!='ELECTRICAL' or port.FlowDirection!='SOURCEANDSINK':raise ProjectError('placed bidirectional electrical cable ports required')
            points.append(placement.get_local_placement(port.ObjectPlacement)[:3,3]*factor)
        points=np.array(points)
        if not (np.allclose(points,ends,atol=1e-6,rtol=0) or np.allclose(points,ends[::-1],atol=1e-6,rtol=0)):raise ProjectError('cable ports do not span body/axis ends')
        if quarter:
            for guid,point in zip(port_ids,points):
                index=int(np.argmin(np.linalg.norm(ends-point,axis=1)))
                if not np.allclose(placement.get_local_placement(ports[guid].ObjectPlacement)[:3,2],quarter['end_normals'][index],atol=1e-8,rtol=0):raise ProjectError('quarter-cable port axis differs from outward end-face normal')
        if not np.allclose(points[0],anchors[line['from']],atol=1e-6,rtol=0) or not np.allclose(points[1],anchors[line['to']],atol=1e-6,rtol=0):raise ProjectError('saved cable placement differs from sourced analysis bus anchors')
        shape=ifcopenshell.geom.create_shape(settings,obj)
        vertices=np.array(shape.geometry.verts).reshape(-1,3);faces=np.array(shape.geometry.faces).reshape(-1,3)
        observed=mesh_properties(vertices,faces)
        if quarter:
            expected_bounds=quarter['expected']['bounds'];expected_volume=quarter['expected']['volume'];expected_centroid=quarter['expected']['centroid']
        else:
            direction=(ends[1]-ends[0])/length;offset=radius*np.sqrt(np.maximum(0,1-direction**2))
            expected_bounds=np.array([ends.min(axis=0)-offset,ends.max(axis=0)+offset]);expected_volume=math.pi*radius**2*length
            expected_centroid=ends.mean(axis=0)
        if not np.allclose(observed['bounds'],expected_bounds,atol=BOUNDS_TOLERANCE_M,rtol=0) or not np.allclose(observed['centroid'],expected_centroid,atol=BOUNDS_TOLERANCE_M,rtol=0) or not math.isclose(observed['volume'],expected_volume,rel_tol=VOLUME_RELATIVE_TOLERANCE):raise ProjectError('native solid bounds/centroid/volume differ from cable axis')
        length_match=math.isclose(length,line['length_m'],rel_tol=0,abs_tol=1e-6)
        if require_length_match and not length_match:raise ProjectError('electrical route length differs from saved IFC geometry')
        rows.append(dict(id=line['id'],element_guid=obj.GlobalId,port_guids=port_ids,observed_length_m=length,project_length_m=line['length_m'],
            route_length_match=length_match,route_geometry=quarter.get('route_geometry','quarter circle') if quarter else 'straight',bend_radius_m=quarter['bend_radius'] if quarter else None,
            body_type=solid.is_a(),envelope_radius_m=radius,world_axis_ends_m=ends.tolist(),native_volume_m3=observed['volume'],analytic_volume_m3=expected_volume))
    if any(digest(Path(f))!=h for f,h in before.items()):raise ProjectError('inputs changed during IFC inspection')
    return dict(inputs=before,input_unchanged=True,source_basis=source,ifc_unit_to_m=factor,versions=versions,lines=rows,
        native_geometry_checks_pass=True,geometry_correspondence_pass=all(r['route_length_match'] for r in rows),native_electrical_connectivity_verified=False,design_accepted=False,
        scope='Selected-system straight, canonical quarter-circle or one quarter with tangent straight cable envelopes, placed ports, bus anchors and analysis lengths only; physical connections, general bends, conductor selection, protection and regulatory acceptance remain unverified')


def run(project,ifc,binding,out):
    out=Path(out).resolve()
    if not out.is_relative_to(ROOT) or out.exists():raise ProjectError('new repository output required')
    result=inspect(project,ifc,binding)
    if any(out==Path(f) or out in Path(f).parents for f in result['inputs']):raise ProjectError('output must not contain inputs')
    out.mkdir(parents=True)
    (out/'ifc-electrical-check.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project',type=Path)
    for key in ('ifc','binding','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();r=run(a.project,a.ifc,a.binding,a.out)
    print(json.dumps({k:r[k] for k in ('geometry_correspondence_pass','native_electrical_connectivity_verified','design_accepted')}))


if __name__=='__main__':main()

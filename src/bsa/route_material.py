"""Source-bound local circular-chain material/topology QA using existing engines."""
import argparse
from collections import Counter
import importlib.metadata
import itertools
import json
import math
from pathlib import Path

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.placement as placement
import ifcopenshell.util.system as system
import manifold3d as m
import numpy as np

from . import circular_geometry as circular, circular_elbow as elbow, route_join
from .cli import digest
from .engine import ProjectError
from .module_contract import read_json
from .solid_clash import from_mesh
from .workspace import allowed


def validate(policy):
    keys={'source','classification','overlap_volume_tolerance_m3','relative_volume_tolerance','probe_radius_fraction','probe_half_length_m','maximum_triangles'}
    if not isinstance(policy,dict) or set(policy)!=keys or not isinstance(policy['source'],str) or not policy['source'].strip() or policy['classification'] not in ('assumed','design_choice'):
        raise ProjectError('Exact source-classified numerical geometry QA policy required')
    for key in keys-{'source','classification','maximum_triangles'}:
        if type(policy[key]) not in (float,int) or not math.isfinite(policy[key]) or policy[key]<=0:
            raise ProjectError('Positive finite numerical QA parameters required')
    if policy['overlap_volume_tolerance_m3']>1e-12 or policy['relative_volume_tolerance']>circular.VOLUME_RELATIVE_TOLERANCE or policy['probe_radius_fraction']>.5 or type(policy['maximum_triangles']) is not int or not 0<policy['maximum_triangles']<=1000000:
        raise ProjectError('QA parameters exceed supported numeric/geometry scope')
    return policy


def evaluate(solids,interfaces,expected_volume,boundary_ports,policy):
    validate(policy)
    if not solids or not math.isfinite(expected_volume) or expected_volume<=0 or type(boundary_ports) is not int or boundary_ports!=2:
        raise ProjectError('One positive-volume local two-boundary chain required')
    tolerance=policy['overlap_volume_tolerance_m3']
    pairs=[]
    for a,b in itertools.combinations(sorted(solids),2):
        common=solids[a]^solids[b]
        if common.status()!=m.Error.NoError or not math.isfinite(common.volume()):
            raise ProjectError('Native material intersection could not be evaluated')
        pairs.append(dict(pair=[a,b],overlap_volume_m3=common.volume(),pass_check=abs(common.volume())<=tolerance))
    union=m.Manifold.batch_boolean(list(solids.values()),m.OpType.Add)
    if union.status()!=m.Error.NoError or not math.isfinite(union.volume()):
        raise ProjectError('Native material union could not be evaluated')
    mesh=union.to_mesh64();faces=np.asarray(mesh.tri_verts);vertices=np.asarray(mesh.vert_properties)[:,:3]
    edges=Counter(tuple(sorted((int(a),int(b)))) for face in faces for a,b in zip(face,[face[1],face[2],face[0]]))
    euler=len(vertices)-len(edges)+len(faces)
    probes=[]
    for row in interfaces:
        bore=row['bore_m'];half=policy['probe_half_length_m']
        if not math.isfinite(bore) or bore<=0 or half>.1*bore:
            raise ProjectError('Probe extent exceeds supported local bore scope')
        matrix=np.asarray(row['frame'],dtype=float)
        if matrix.shape!=(4,4) or not np.isfinite(matrix).all() or not np.allclose(matrix[:3,:3].T@matrix[:3,:3],np.eye(3),atol=1e-9,rtol=0) or not np.isclose(np.linalg.det(matrix[:3,:3]),1.,atol=1e-9,rtol=0):
            raise ProjectError('Proper saved interface frame required for bore probe')
        radius=bore/2*policy['probe_radius_fraction']
        probe=m.Manifold.cylinder(2*half,radius,circular_segments=64,center=True).transform(matrix[:3,:])
        common=union^probe
        if common.status()!=m.Error.NoError or not math.isfinite(common.volume()):
            raise ProjectError('Local centre-bore probe could not be evaluated')
        probes.append(dict(ports=row['ports'],radius_m=radius,half_length_m=half,material_overlap_m3=common.volume(),pass_check=abs(common.volume())<=tolerance))
    checks=dict(no_material_interpenetration=all(r['pass_check'] for r in pairs),
        one_connected_material=len(union.decompose())==1,
        independent_volume=math.isclose(union.volume(),expected_volume,rel_tol=policy['relative_volume_tolerance'],abs_tol=tolerance),
        two_boundary_bore_topology=all(n==2 for n in edges.values()) and euler==4-2*boundary_ports,
        sampled_centre_bore_clear=bool(probes) and all(r['pass_check'] for r in probes))
    return dict(checks=checks,calculated_checks_pass=all(checks.values()),design_accepted=False,
        pairs=pairs,probes=probes,union_components=len(union.decompose()),union_volume_m3=union.volume(),
        independent_volume_m3=expected_volume,relative_volume_difference=abs(union.volume()-expected_volume)/expected_volume,
        boundary_ports=boundary_ports,euler_characteristic=euler)


def run(producer,basis,out):
    producer,basis,out=[Path(p).resolve() for p in (producer,basis,out)]
    if out.exists() or not all(allowed(p) for p in (producer,basis,out)) or producer==out or producer in out.parents or out in producer.parents or out==basis or out in basis.parents:
        raise ProjectError('Fresh selected-workspace QA output outside all source inputs required')
    versions={name:importlib.metadata.version(name) for name in ('ifcopenshell','manifold3d','numpy')}
    if versions!={'ifcopenshell':'0.8.5','manifold3d':'3.5.4','numpy':'2.5.4'}:
        raise ProjectError('Pinned native geometry runtimes required')
    policy=validate(read_json(basis));report_path=producer/'route-join.json';report=read_json(report_path)
    if report.get('calculated_checks_pass') is not True or report.get('design_accepted') is not False:
        raise ProjectError('Passing unaccepted source-bound join required')
    model_path=producer/'joined.ifc';snapshot_path=producer/'source-snapshot.json'
    inputs={**report['inputs'],**report['method_inputs'],str(report_path):digest(report_path),str(basis):digest(basis),str(model_path):report['ifc_sha256'],str(snapshot_path):report['snapshot_sha256']}
    for path,sha in inputs.items():
        if not allowed(Path(path)) or digest(Path(path))!=sha:
            raise ProjectError('Joined source, method or saved artifact changed')
    methods={str(Path(p).resolve()):digest(Path(p)) for p in (__file__,route_join.__file__,circular.__file__,elbow.__file__,from_mesh.__code__.co_filename)}
    snapshot=read_json(snapshot_path);route_join.inspect(model_path,snapshot)
    model=ifcopenshell.open(str(model_path));owners=set(snapshot['local_chain_owners'])
    canonical=[Path(p) for p in inputs if Path(p).name=='model-input.json']
    if len(canonical)!=1:raise ProjectError('One exact inherited canonical route model required')
    route=read_json(canonical[0]);objects={o.GlobalId:o for o in model.by_type('IfcElement') if o.GlobalId in owners}
    volumes={};bores={}
    for device in route['devices']:
        matches=[o for o in objects.values() if o.Name==device['id'] and o.is_a()==device['ifc_class']]
        if len(matches)!=1:raise ProjectError('Unambiguous canonical route body identity required')
        spec=(elbow if device.get('body_shape')==elbow.WALL else circular).specification(device)
        guid=matches[0].GlobalId;volumes[guid]=spec['volume_m3'];bores[guid]=spec['inner_m']
    remaining=owners-set(volumes)
    if len(remaining)!=2:raise ProjectError('Exactly two source walls beyond the canonical route required')
    for guid in remaining:
        obj=objects[guid];bodies=[r for r in obj.Representation.Representations if r.RepresentationIdentifier=='Body']
        if len(bodies)!=1 or len(bodies[0].Items)!=1 or not bodies[0].Items[0].is_a('IfcExtrudedAreaSolid') or not bodies[0].Items[0].SweptArea.is_a('IfcCircleHollowProfileDef'):
            raise ProjectError('Source native circular hollow extrusion required')
        solid=bodies[0].Items[0];profile=solid.SweptArea;outer=profile.Radius*2;inner=outer-profile.WallThickness*2
        if not all(math.isfinite(v) for v in (inner,outer,solid.Depth)) or not 0<inner<outer or solid.Depth<=0:
            raise ProjectError('Positive source bore, thickness and extrusion depth required')
        volumes[guid]=math.pi*(outer**2-inner**2)*solid.Depth/4;bores[guid]=inner
    ports={p.GlobalId:p for p in model.by_type('IfcDistributionPort') if system.get_port_element(p).GlobalId in owners}
    links=[r for r in model.by_type('IfcRelConnectsPorts') if r.RelatingPort.GlobalId in ports and r.RelatedPort.GlobalId in ports]
    degree=Counter(p.GlobalId for r in links for p in (r.RelatingPort,r.RelatedPort));boundary=len(set(ports)-set(degree))
    reference=placement.get_local_placement(links[0].RelatingPort.ObjectPlacement)[:3,3]
    interfaces=[]
    for link in links:
        pair=[link.RelatingPort,link.RelatedPort];diameters=[bores[system.get_port_element(p).GlobalId] for p in pair]
        if not math.isclose(*diameters,rel_tol=0,abs_tol=1e-9):raise ProjectError('Equal-bore local interfaces required')
        frame=placement.get_local_placement(pair[0].ObjectPlacement).copy();frame[:3,3]-=reference
        interfaces.append(dict(ports=[p.GlobalId for p in pair],bore_m=diameters[0],frame=frame.tolist()))
    settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True);circular.configure(settings)
    solids={};triangles=0
    for guid,obj in objects.items():
        shape=ifcopenshell.geom.create_shape(settings,obj);vertices=np.asarray(shape.geometry.verts).reshape(-1,3)-reference;faces=np.asarray(shape.geometry.faces).reshape(-1,3)
        triangles+=len(faces)
        if triangles>policy['maximum_triangles']:raise ProjectError('Local material QA exceeds explicit triangle budget')
        solids[guid]=from_mesh((vertices,faces))
    result=evaluate(solids,interfaces,math.fsum(volumes.values()),boundary,policy)
    if any(digest(Path(p))!=sha for p,sha in {**inputs,**methods}.items()):raise ProjectError('Material QA source or method changed during execution')
    result.update(inputs=inputs,method_inputs=methods,runtime_versions=versions,policy=policy,local_chain_owners=sorted(owners),triangle_count=triangles,reference_origin_m=reference.tolist(),analytic_body_volumes_m3=volumes,
        scope='Ideal local circular-wall material union, topology and finite centre-core probes only; no whole-model clearance, product joints, whole-network pressure, full-bore CFD, installation or regulatory acceptance')
    out.mkdir(parents=True);(out/'route-material.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('producer',type=Path);parser.add_argument('--basis',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();result=run(args.producer,args.basis,args.out);print(json.dumps(result,indent=2));raise SystemExit(0 if result['calculated_checks_pass'] else 2)

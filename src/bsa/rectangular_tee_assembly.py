"""Source-declared equal-section rectangular tee with three butt-ended straight walls."""
import argparse
from collections import Counter
import itertools
import json
import math
from pathlib import Path

import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.geom
import ifcopenshell.util.placement as placement
import ifcopenshell.util.element as element
import ifcopenshell.util.system as system
import manifold3d as m
import numpy as np

from . import rectangular_geometry as rectangular
from . import rectangular_tee as tee
from .cli import digest
from .solid_clash import from_mesh
from .tee_geometry import stable_guid


def validate(data):
    if not isinstance(data, dict) or set(data) != {'source', 'classification', 'duct_lengths_m'}:
        raise ValueError('Exact sourced assembly fields required')
    if not isinstance(data['source'], str) or not data['source'].strip() or data['classification'] not in ('given', 'assumed', 'secondary_transcription'):
        raise ValueError('Assembly source and classification required')
    lengths = data['duct_lengths_m']
    if not isinstance(lengths, dict) or set(lengths) != set(tee.NAMES) or any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in lengths.values()):
        raise ValueError('Three positive finite sourced duct lengths required')
    return lengths


def opposite(direction):
    return {'SOURCE': 'SINK', 'SINK': 'SOURCE', 'SOURCEANDSINK': 'SOURCEANDSINK'}[direction]


def local_anchors(spec):
    local = dict(spec, placement=dict(spec['placement'], origin_m=[0, 0, 0], rotation=np.eye(3).tolist()))
    return tee.port_frames(local)


def port_matrix(anchor, length, near):
    matrix = anchor.copy()
    if near:
        matrix[:3, 1:3] *= -1
    else:
        matrix[:3, 3] += length * matrix[:3, 2]
    return matrix


def device(spec, length):
    w, h, t, _, _ = tee.validate(spec)
    return dict(ifc_class='IfcDuctSegment', origin_m=[-(w+2*t)/2, -(h+2*t)/2, 0],
                size_m=[w+2*t, h+2*t, length],
                properties=dict(InternalWidth_m=w, InternalHeight_m=h, WallThickness_m=t),
                ports=[dict(id='near', direction='SINK', offset_m=[(w+2*t)/2, (h+2*t)/2, 0]),
                       dict(id='far', direction='SOURCE', offset_m=[(w+2*t)/2, (h+2*t)/2, length])])


def inspect(path, spec, assembly):
    lengths = validate(assembly)
    tee_checks = tee.inspect(path, spec)  # Includes whole-file schema/EXPRESS.
    model = ifcopenshell.open(str(path))
    fitting = model.by_guid(stable_guid(spec, 'IfcDuctFitting', 'RECTANGULAR-TEE'))
    tee_ports = {p.Name: p for p in system.get_ports(fitting)}
    anchors = tee.port_frames(spec)
    native = ifcopenshell.geom.settings(); native.set(native.USE_WORLD_COORDS, False)
    local_frames = local_anchors(spec)
    objects = [fitting]; expected_links = set(); expected_ids = {p.GlobalId for p in tee_ports.values()}
    w, h, t, L, B = tee.validate(spec)
    expected_volume = tee_checks['independent_material_volume_m3']
    for name in tee.NAMES:
        obj = model.by_guid(stable_guid(spec, 'IfcDuctSegment', 'RECTANGULAR-TEE', name))
        objects.append(obj); anchor = anchors[name]; length = lengths[name]
        expected_volume += rectangular.specification(device(spec, length))['volume']
        if obj.PredefinedType != 'RIGIDSEGMENT' or not np.allclose(placement.get_local_placement(obj.ObjectPlacement), anchor, atol=1e-9, rtol=0):
            raise ValueError('Straight duct type/placement differs from source')
        if obj.ObjectPlacement.PlacementRelTo != fitting.ObjectPlacement or not np.allclose(placement.get_axis2placement(obj.ObjectPlacement.RelativePlacement), local_frames[name], atol=1e-10, rtol=0):
            raise ValueError('Straight duct local assembly frame differs')
        props = element.get_psets(obj).get('BSA_DesignInputs', {})
        expected_props = dict(device(spec, length)['properties'], Source=assembly['source'], Classification=assembly['classification'])
        if any(props.get(k) != v for k, v in expected_props.items()):
            raise ValueError('Straight duct source/dimension metadata differs')
        bodies = obj.Representation.Representations
        if len(bodies) != 1 or bodies[0].RepresentationType != 'SweptSolid' or len(bodies[0].Items) != 1:
            raise ValueError('One straight swept wall required')
        solid = bodies[0].Items[0]; profile = solid.SweptArea
        if not solid.is_a('IfcExtrudedAreaSolid') or not profile.is_a('IfcRectangleHollowProfileDef'):
            raise ValueError('Native rectangular hollow extrusion required')
        if not np.allclose([profile.XDim, profile.YDim, profile.WallThickness, solid.Depth], [w+2*t, h+2*t, t, length], atol=1e-10, rtol=0):
            raise ValueError('Straight wall profile/length differs')
        if profile.Position is not None or any(v not in (None, 0.) for v in (profile.InnerFilletRadius, profile.OuterFilletRadius)) or not np.allclose(placement.get_axis2placement(solid.Position), np.eye(4), atol=1e-10, rtol=0) or tuple(solid.ExtrudedDirection.DirectionRatios) != (0., 0., 1.):
            raise ValueError('Straight wall local placement/direction differs')
        ports = {p.Name: p for p in system.get_ports(obj)}
        if len(system.get_ports(obj)) != 2 or set(ports) != {'near', 'far'}:
            raise ValueError('Two owned straight duct ports required')
        direction = spec['port_directions'][name]
        for end, port in ports.items():
            guid = stable_guid(spec, 'IfcDistributionPort', 'RECTANGULAR-TEE', name, end)
            expected_ids.add(guid)
            if port.GlobalId != guid or port.PredefinedType != 'DUCT' or port.SystemType != 'VENTILATION' or port.FlowDirection != (opposite(direction) if end == 'near' else direction) or not np.allclose(placement.get_local_placement(port.ObjectPlacement), port_matrix(anchor, length, end == 'near'), atol=1e-9, rtol=0):
                raise ValueError('Straight port identity/type/direction/frame differs')
        a, b = tee_ports[name].GlobalId, ports['near'].GlobalId
        if direction in ('SOURCE', 'SOURCEANDSINK'): expected_links.add((a, b))
        if direction in ('SINK', 'SOURCEANDSINK'): expected_links.add((b, a))
    if {o.GlobalId for o in model.by_type('IfcDistributionElement')} != {o.GlobalId for o in objects} or len(model.by_type('IfcDistributionElement')) != 4:
        raise ValueError('Exact four-component assembly required')
    if len(model.by_type('IfcDistributionPort')) != 9 or {p.GlobalId for p in model.by_type('IfcDistributionPort')} != expected_ids:
        raise ValueError('Exact stable nine-port inventory required')
    links = [(r.RelatingPort.GlobalId, r.RelatedPort.GlobalId) for r in model.by_type('IfcRelConnectsPorts')]
    if len(links) != len(expected_links) or set(links) != expected_links:
        raise ValueError('Saved connection topology differs')
    systems = model.by_type('IfcDistributionSystem')
    if len(systems) != 1 or systems[0].GlobalId != stable_guid(spec, 'IfcDistributionSystem', 'RECTANGULAR-TEE') or systems[0].PredefinedType != 'VENTILATION' or {o.GlobalId for rel in systems[0].IsGroupedBy for o in rel.RelatedObjects} != {o.GlobalId for o in objects}:
        raise ValueError('Exact stable ventilation system membership required')
    solids = []
    for obj in objects:
        shape = ifcopenshell.geom.create_shape(native, obj)
        vertices = np.asarray(shape.geometry.verts).reshape(-1, 3)
        # Native local meshes and saved parent-relative transforms avoid a
        # world-coordinate/inverse round trip at coincident butt faces.
        relative = np.eye(4) if obj == fitting else placement.get_axis2placement(obj.ObjectPlacement.RelativePlacement)
        vertices = vertices @ relative[:3, :3].T + relative[:3, 3]
        solids.append(from_mesh((vertices, np.asarray(shape.geometry.faces).reshape(-1, 3))))
    overlaps = [(a ^ b).volume() for a, b in itertools.combinations(solids, 2)]
    if any(abs(v) > 1e-12 for v in overlaps): raise ValueError('Assembly material interpenetrates')
    union = m.Manifold.batch_boolean(solids, m.OpType.Add)
    if union.status() != m.Error.NoError or len(union.decompose()) != 1 or not math.isclose(union.volume(), expected_volume, rel_tol=1e-9, abs_tol=1e-10):
        raise ValueError('Assembly material disconnected or volume differs')
    mesh = union.to_mesh64(); faces = np.asarray(mesh.tri_verts); vertices = np.asarray(mesh.vert_properties)[:, :3]
    edges = Counter(tuple(sorted((int(a), int(b)))) for face in faces for a, b in zip(face, [face[1], face[2], face[0]]))
    euler = len(vertices)-len(edges)+len(faces)
    if any(v != 2 for v in edges.values()) or euler != -2: raise ValueError('Assembly three-bore topology differs')
    z0, z1 = -L-lengths['main-a'], L+lengths['main-b']
    probes = [m.Manifold.cube((w*.5, h*.5, z1-z0+.2), center=True).translate((0, 0, (z0+z1)/2)),
              m.Manifold.cube((B+lengths['branch']+.1, h*.5, w*.5), center=True).translate(((B+lengths['branch']+.1)/2, 0, 0))]
    bore_overlaps = []
    for probe in probes:
        common = union ^ probe
        if common.status() != m.Error.NoError or abs(common.volume()) > 1e-12: raise ValueError('Assembly air path blocked')
        bore_overlaps.append(common.volume())
    return dict(tee=tee_checks, components=4, ports=9, connections=len(links), coincident_opposed_interfaces=3,
                material_overlap_m3=overlaps, one_connected_material=True, euler_characteristic=euler,
                material_volume_m3=union.volume(), independent_material_volume_m3=expected_volume, bore_probe_overlap_m3=bore_overlaps)


def run(tee_spec, assembly_spec, out):
    tee_spec, assembly_spec, out = [Path(p).resolve() for p in (tee_spec, assembly_spec, out)]
    spec = json.loads(tee_spec.read_text(encoding='utf-8-sig')); tee.validate(spec)
    assembly = json.loads(assembly_spec.read_text(encoding='utf-8-sig')); lengths = validate(assembly)
    if out.exists() or not out.is_relative_to(Path(__file__).resolve().parents[2]) or any(out == p or out in p.parents for p in (tee_spec, assembly_spec)):
        raise ValueError('New repository-local output outside sources required')
    pins = {str(p): digest(p) for p in (tee_spec, assembly_spec)}
    tee.run(tee_spec, out/'tee')
    model = ifcopenshell.open(str(out/'tee/rectangular-tee.ifc'))
    fitting = model.by_guid(stable_guid(spec, 'IfcDuctFitting', 'RECTANGULAR-TEE'))
    context = fitting.Representation.Representations[0].ContextOfItems
    tee_ports = {p.Name: p for p in system.get_ports(fitting)}; objects = [fitting]
    for name, anchor in tee.port_frames(spec).items():
        obj = api.run('root.create_entity', model, ifc_class='IfcDuctSegment', predefined_type='RIGIDSEGMENT', name=name)
        obj.GlobalId = stable_guid(spec, 'IfcDuctSegment', 'RECTANGULAR-TEE', name); objects.append(obj)
        description = device(spec, lengths[name]); rectangular.author(model, context, obj, description)
        local = local_anchors(spec)[name]
        relative = model.create_entity('IfcAxis2Placement3D',
            Location=model.create_entity('IfcCartesianPoint', Coordinates=tuple(float(v) for v in local[:3, 3])),
            Axis=model.create_entity('IfcDirection', DirectionRatios=tuple(float(v) for v in local[:3, 2])),
            RefDirection=model.create_entity('IfcDirection', DirectionRatios=tuple(float(v) for v in local[:3, 0])))
        obj.ObjectPlacement = model.create_entity('IfcLocalPlacement', PlacementRelTo=fitting.ObjectPlacement, RelativePlacement=relative)
        pset = api.run('pset.add_pset', model, product=obj, name='BSA_DesignInputs')
        api.run('pset.edit_pset', model, pset=pset, properties=dict(description['properties'], Source=assembly['source'], Classification=assembly['classification']))
        for end in ('near', 'far'):
            port = api.run('system.add_port', model, element=obj); port.Name = end
            port.GlobalId = stable_guid(spec, 'IfcDistributionPort', 'RECTANGULAR-TEE', name, end)
            direction = spec['port_directions'][name]
            port.FlowDirection = opposite(direction) if end == 'near' else direction
            port.PredefinedType = 'DUCT'; port.SystemType = 'VENTILATION'
            api.run('geometry.edit_object_placement', model, product=port, matrix=port_matrix(anchor, lengths[name], end == 'near'), is_si=True)
            if end == 'near': api.run('system.connect_port', model, port1=tee_ports[name], port2=port, direction=direction)
    distribution = api.run('root.create_entity', model, ifc_class='IfcDistributionSystem', name='Declared rectangular tee assembly', predefined_type='VENTILATION')
    distribution.GlobalId = stable_guid(spec, 'IfcDistributionSystem', 'RECTANGULAR-TEE')
    api.run('system.assign_system', model, products=objects, system=distribution)
    target = out/'assembly.ifc'; model.write(str(target)); checks = inspect(target, spec, assembly)
    if any(digest(Path(p)) != sha for p, sha in pins.items()): raise ValueError('Assembly source changed')
    result = dict(inputs=pins, ifc_sha256=digest(target), generator_sha256=digest(Path(__file__)), checks=checks,
                  assembly_checks_pass=True, design_accepted=False,
                  scope='Declared ideal equal-section sharp tee and three butt-ended straight walls only; no joints, products, losses, installation or jurisdiction acceptance')
    (out/'assembly.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tee_spec'); parser.add_argument('assembly_spec'); parser.add_argument('--out', required=True)
    args = parser.parse_args(); print(json.dumps(run(args.tee_spec, args.assembly_spec, args.out)['checks'], indent=2))
    raise SystemExit(2)

"""Compose a declared ideal rectangular tee with explicit centred transition arms."""
import argparse
from collections import Counter
import itertools
import json
import math
from pathlib import Path
import uuid

import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.geom
import ifcopenshell.util.element as element
import ifcopenshell.util.placement as placement
import ifcopenshell.util.system as system
import manifold3d as m
import numpy as np

from . import rectangular_tee as tee
from . import rectangular_transition as transition
from .rectangular_tee_assembly import local_anchors, opposite
from .tee_geometry import project_namespace, stable_guid
from .cli import digest
from .solid_clash import from_mesh

ROOT = Path(__file__).resolve().parents[2]
KEY = 'RECTANGULAR-TEE-TRANSITIONS'


def prepare(project):
    project = Path(project).resolve(); data = json.loads(project.read_text(encoding='utf-8-sig'))
    if not isinstance(data, dict) or set(data) != {'source', 'classification', 'tee', 'arms'}: raise ValueError('Exact sourced tee-composition fields required')
    if not isinstance(data['source'], str) or not data['source'].strip() or data['classification'] not in ('given', 'assumed', 'secondary_transcription'): raise ValueError('Composition source/classification required')
    name = data['tee']
    if not isinstance(name, str) or Path(name).is_absolute(): raise ValueError('Relative tee source path required')
    source = (project.parent/name).resolve()
    if not source.is_relative_to(project.parent) or source == project: raise ValueError('Tee source must remain inside project source directory')
    spec = json.loads(source.read_text(encoding='utf-8-sig')); tee.validate(spec)
    if not isinstance(data['arms'], dict) or set(data['arms']) != set(tee.NAMES): raise ValueError('Explicit three-arm composition required')
    children = {}; anchors = tee.port_frames(spec)
    for arm, row in data['arms'].items():
        if row == {'kind': 'bare'}: continue
        if not isinstance(row, dict) or set(row) != {'kind', 'end_section_m', 'start_length_m', 'end_length_m', 'upstream_angle_degrees', 'transition_length_m'} or row['kind'] != 'transition':
            raise ValueError('Each arm requires explicit bare or complete transition declaration')
        direction = spec['port_directions'][arm]; frame = anchors[arm]
        child = dict(project_uuid=str(uuid.uuid5(project_namespace(spec), KEY+':'+arm)),
            source=data['source']+'; declared transition arm '+arm, classification=data['classification'], wall_model='section_plane_offset',
            start_section_m=[spec['internal_width_m'], spec['internal_height_m']], section_offset_m=spec['wall_thickness_m'],
            port_directions={'start': opposite(direction), 'end': direction},
            placement=dict(source='Derived from source tee port '+arm+'; '+spec['placement']['source'], origin_m=frame[:3, 3].tolist(), rotation=frame[:3, :3].tolist()),
            **{k: row[k] for k in ('end_section_m', 'start_length_m', 'end_length_m', 'upstream_angle_degrees', 'transition_length_m')})
        transition.validate(child); children[arm] = child
    if not children: raise ValueError('At least one declared transition required; use tee adapter for a bare tee')
    return project, data, source, spec, children


def relative_placement(model, matrix, parent):
    axis = model.create_entity('IfcAxis2Placement3D',
        Location=model.create_entity('IfcCartesianPoint', Coordinates=tuple(float(v) for v in matrix[:3, 3])),
        Axis=model.create_entity('IfcDirection', DirectionRatios=tuple(float(v) for v in matrix[:3, 2])),
        RefDirection=model.create_entity('IfcDirection', DirectionRatios=tuple(float(v) for v in matrix[:3, 0])))
    return model.create_entity('IfcLocalPlacement', PlacementRelTo=parent, RelativePlacement=axis)


def inspect(path, spec, data, children):
    tee_checks = tee.inspect(path, spec); model = ifcopenshell.open(str(path))
    fitting = model.by_guid(stable_guid(spec, 'IfcDuctFitting', 'RECTANGULAR-TEE'))
    objects = [fitting]; local = local_anchors(spec); expected_ports = {p.GlobalId for p in system.get_ports(fitting)}
    tee_ports = {p.Name: p for p in system.get_ports(fitting)}; expected_links = set(); component_checks = {}
    expected_volume = tee_checks['independent_material_volume_m3']; end_frames = tee.port_frames(spec)
    for arm, child in children.items():
        component_checks[arm] = transition.inspect(path, child, component=True)
        expected_volume += component_checks[arm]['independent_material_volume_m3']
        obj = model.by_guid(stable_guid(child, 'IfcDuctFitting', transition.KEY)); objects.append(obj)
        if obj.ObjectPlacement.PlacementRelTo != fitting.ObjectPlacement or not np.allclose(placement.get_axis2placement(obj.ObjectPlacement.RelativePlacement), local[arm], atol=1e-10, rtol=0):
            raise ValueError('Saved transition assembly-relative frame differs')
        ports = {p.Name: p for p in system.get_ports(obj)}; expected_ports.update(p.GlobalId for p in ports.values())
        a, b = tee_ports[arm].GlobalId, ports['start'].GlobalId; direction = spec['port_directions'][arm]
        if direction in ('SOURCE', 'SOURCEANDSINK'): expected_links.add((a, b))
        if direction in ('SINK', 'SOURCEANDSINK'): expected_links.add((b, a))
        first = placement.get_local_placement(tee_ports[arm].ObjectPlacement); second = placement.get_local_placement(ports['start'].ObjectPlacement)
        if not np.allclose(first[:3, 3], second[:3, 3], atol=1e-9, rtol=0) or not np.allclose(first[:3, 2], -second[:3, 2], atol=1e-9, rtol=0): raise ValueError('Interface port planes differ')
        end_frames[arm] = transition.port_frames(child)['end']
    if len(model.by_type('IfcDistributionElement')) != len(objects) or {o.GlobalId for o in model.by_type('IfcDistributionElement')} != {o.GlobalId for o in objects}: raise ValueError('Exact declared fitting component inventory required')
    ports = model.by_type('IfcDistributionPort')
    if len(ports) != len(expected_ports) or {p.GlobalId for p in ports} != expected_ports: raise ValueError('Exact stable owned port inventory required')
    links = [(r.RelatingPort.GlobalId, r.RelatedPort.GlobalId) for r in model.by_type('IfcRelConnectsPorts')]
    if len(links) != len(expected_links) or set(links) != expected_links: raise ValueError('Saved directed connection topology differs')
    systems = model.by_type('IfcDistributionSystem')
    if len(systems) != 1 or systems[0].GlobalId != stable_guid(spec, 'IfcDistributionSystem', KEY) or systems[0].PredefinedType != 'VENTILATION' or {o.GlobalId for rel in systems[0].IsGroupedBy for o in rel.RelatedObjects} != {o.GlobalId for o in objects}: raise ValueError('Exact stable ventilation system membership required')
    props = element.get_psets(systems[0]).get('BSA_CompositionInputs', {})
    if props.get('Source') != data['source'] or props.get('Classification') != data['classification']: raise ValueError('Composition source/classification differs')
    native = ifcopenshell.geom.settings(); native.set(native.USE_WORLD_COORDS, False); solids = []
    for obj in objects:
        shape = ifcopenshell.geom.create_shape(native, obj); vertices = np.asarray(shape.geometry.verts).reshape(-1, 3)
        matrix = np.eye(4) if obj == fitting else placement.get_axis2placement(obj.ObjectPlacement.RelativePlacement)
        vertices = vertices @ matrix[:3, :3].T + matrix[:3, 3]
        solids.append(from_mesh((vertices, np.asarray(shape.geometry.faces).reshape(-1, 3))))
    overlaps = [(a ^ b).volume() for a, b in itertools.combinations(solids, 2)]
    if any(abs(v) > 1e-12 for v in overlaps): raise ValueError('Composed fitting material interpenetrates')
    union = m.Manifold.batch_boolean(solids, m.OpType.Add)
    if union.status() != m.Error.NoError or len(union.decompose()) != 1 or not math.isclose(union.volume(), expected_volume, rel_tol=1e-9, abs_tol=1e-10): raise ValueError('Composed material disconnected or independent volume differs')
    mesh = union.to_mesh64(); faces = np.asarray(mesh.tri_verts); vertices = np.asarray(mesh.vert_properties)[:, :3]
    edges = Counter(tuple(sorted((int(a), int(b)))) for face in faces for a, b in zip(face, [face[1], face[2], face[0]]))
    euler = len(vertices)-len(edges)+len(faces)
    if any(v != 2 for v in edges.values()) or euler != -2: raise ValueError('Composed three-ended wall topology differs')
    w, h, t, L, B = tee.validate(spec)
    extension = {arm: transition.total_length(child) for arm, child in children.items()}
    sizes = {arm: children[arm]['end_section_m'] if arm in children else [w, h] for arm in tee.NAMES}
    main_w = min(w, sizes['main-a'][0], sizes['main-b'][0]); main_h = min(h, sizes['main-a'][1], sizes['main-b'][1])
    z0, z1 = -L-extension.get('main-a', 0), L+extension.get('main-b', 0); branch_end = B+extension.get('branch', 0)
    probes = [m.Manifold.cube((main_w*.5, main_h*.5, z1-z0+.2), center=True).translate((0, 0, (z0+z1)/2)),
        m.Manifold.cube((branch_end+.1, min(h, sizes['branch'][1])*.5, min(w, sizes['branch'][0])*.5), center=True).translate(((branch_end+.1)/2, 0, 0))]
    bore = []
    for probe in probes:
        common = union ^ probe
        if common.status() != m.Error.NoError or abs(common.volume()) > 1e-12: raise ValueError('Composed centre air path blocked')
        bore.append(common.volume())
    return dict(tee=tee_checks, transitions=component_checks, components=len(objects), ports=len(ports), connections=len(links),
        coincident_opposed_interfaces=len(children), material_overlap_m3=overlaps, one_connected_material=True, euler_characteristic=euler,
        material_volume_m3=union.volume(), independent_material_volume_m3=expected_volume, bore_probe_overlap_m3=bore,
        external_end_frames={n: v.tolist() for n, v in end_frames.items()})


def run(project, out):
    project, data, source, spec, children = prepare(project); out = Path(out).resolve()
    if out.exists() or not out.is_relative_to(ROOT) or any(out == p or out in p.parents for p in (project, source)): raise ValueError('New repository-local output outside sources required')
    inputs = {str(p): digest(p) for p in (project, source)}
    tee.run(source, out/'tee'); model = ifcopenshell.open(str(out/'tee/rectangular-tee.ifc'))
    fitting = model.by_guid(stable_guid(spec, 'IfcDuctFitting', 'RECTANGULAR-TEE')); tee_ports = {p.Name: p for p in system.get_ports(fitting)}
    objects = [fitting]; local = local_anchors(spec)
    for arm, child in children.items():
        child_source = out/(arm+'-transition.json'); child_source.write_text(json.dumps(child, indent=2), encoding='utf-8')
        transition.run(child_source, out/arm)
        library = ifcopenshell.open(str(out/arm/'transition.ifc')); original = library.by_guid(stable_guid(child, 'IfcDuctFitting', transition.KEY))
        added = api.run('project.append_asset', model, library=library, element=original, assume_asset_uniqueness_by_name=False)
        added.ObjectPlacement = relative_placement(model, local[arm], fitting.ObjectPlacement); objects.append(added)
        if {p.Name for p in system.get_ports(added)} != {'start', 'end'}: raise ValueError('Upstream append lost owned transition ports')
        ports = {p.Name: p for p in system.get_ports(added)}
        for name, port in ports.items():
            matrix = np.diag([1., -1. if name == 'start' else 1., -1. if name == 'start' else 1., 1.])
            if name == 'end': matrix[2, 3] = transition.total_length(child)
            port.ObjectPlacement = relative_placement(model, matrix, added.ObjectPlacement)
        api.run('system.connect_port', model, port1=tee_ports[arm], port2=ports['start'], direction=spec['port_directions'][arm])
    distribution = api.run('root.create_entity', model, ifc_class='IfcDistributionSystem', name='Declared tee and transition composition', predefined_type='VENTILATION')
    distribution.GlobalId = stable_guid(spec, 'IfcDistributionSystem', KEY)
    api.run('system.assign_system', model, products=objects, system=distribution)
    pset = api.run('pset.add_pset', model, product=distribution, name='BSA_CompositionInputs')
    api.run('pset.edit_pset', model, pset=pset, properties=dict(Source=data['source'], Classification=data['classification']))
    source_artifacts = {p.relative_to(out).as_posix(): digest(p) for p in out.rglob('*') if p.is_file()}
    target = out/'assembly.ifc'; model.write(str(target)); checks = inspect(target, spec, data, children)
    if any(digest(Path(p)) != sha for p, sha in inputs.items()) or any(digest(out/p) != sha for p, sha in source_artifacts.items()): raise ValueError('Composition inputs or component artifacts changed')
    result = dict(inputs=inputs, source_artifacts=source_artifacts, generator_sha256=digest(Path(__file__)), ifc_sha256=digest(target),
        checks=checks, assembly_checks_pass=True, design_accepted=False,
        scope='Declared ideal equal-section core tee with centred section-plane-offset transitions; no product joints, constant sheet-normal taper walls, pressure loss or actual installation/regulatory acceptance')
    (out/'assembly.json').write_text(json.dumps(result, indent=2), encoding='utf-8'); return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('project'); parser.add_argument('--out', required=True)
    args = parser.parse_args(); print(json.dumps(run(args.project, args.out)['checks'], indent=2)); raise SystemExit(2)

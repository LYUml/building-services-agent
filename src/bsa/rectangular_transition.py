"""Pinned upstream centred rectangular transition with explicit section-plane wall offset."""
import argparse
from contextlib import redirect_stdout
import importlib.metadata
import io
import json
import math
from pathlib import Path

import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.geom
import ifcopenshell.util.element as element
import ifcopenshell.util.placement as placement
import ifcopenshell.util.system as system
import ifcopenshell.validate
from ifcopenshell.util.shape_builder import ShapeBuilder
import ifcopenshell.util.shape_builder as shape_builder
import manifold3d as m
import numpy as np

from .cli import digest
from .circular_geometry import verify_closed_wall
from .cad_ifc import mesh_properties
from .solid_clash import from_mesh
from .tee_geometry import project_namespace, stable_guid, placement_matrix

ROOT = Path(__file__).resolve().parents[2]
EXTENSION_M = .0001  # Boolean bore construction beyond caps, not a joint allowance.
KEY = 'RECTANGULAR-TRANSITION'


def validate(data):
    fields = {'project_uuid', 'source', 'classification', 'placement', 'wall_model', 'start_section_m', 'end_section_m',
        'section_offset_m', 'start_length_m', 'end_length_m', 'upstream_angle_degrees', 'transition_length_m', 'port_directions'}
    if not isinstance(data, dict) or set(data) != fields: raise ValueError('Exact sourced transition fields required')
    project_namespace(data); placement_matrix(data)
    if not isinstance(data['source'], str) or not data['source'].strip() or data['classification'] not in ('given', 'assumed', 'secondary_transcription'):
        raise ValueError('Transition source and classification required')
    if data['wall_model'] != 'section_plane_offset': raise ValueError('Explicit section-plane offset wall interpretation required')
    for name in ('start_section_m', 'end_section_m'):
        value = data[name]
        if not isinstance(value, list) or len(value) != 2: raise ValueError('Explicit width/height metre pairs required')
    values = data['start_section_m'] + data['end_section_m'] + [data[k] for k in ('section_offset_m', 'start_length_m', 'end_length_m', 'upstream_angle_degrees', 'transition_length_m')]
    if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in values): raise ValueError('Positive finite transition dimensions/angle required')
    if data['start_section_m'] == data['end_section_m']: raise ValueError('Distinct nominal end sections required')
    if min(data['start_length_m'], data['end_length_m']) <= EXTENSION_M or data['upstream_angle_degrees'] >= 90:
        raise ValueError('Straight ends must exceed bore construction extension; upstream angle must be below90 degrees')
    directions = data['port_directions']
    if not isinstance(directions, dict) or set(directions) != {'start', 'end'} or set(directions.values()) not in ({'SOURCE', 'SINK'}, {'SOURCEANDSINK'}):
        raise ValueError('Explicit opposed directed or bidirectional end ports required')
    return data


def total_length(data):
    return data['start_length_m'] + data['transition_length_m'] + data['end_length_m']


def port_frames(data):
    transform = placement_matrix(data); result = {}
    for name, z, sign in [('start', 0., -1.), ('end', total_length(data), 1.)]:
        local = np.diag([1., sign, sign, 1.]); local[2, 3] = z
        result[name] = transform @ local
    return result


def integral(start, end, a, b, taper):
    """Independent area-polynomial volume and axial first moment."""
    w, h = start; dw, dh = np.subtract(end, start)
    c0, c1, c2 = w*h, w*dh+h*dw, dw*dh
    v = taper*(c0+c1/2+c2/3)
    moment = a*v + taper*taper*(c0/2+c1/3+c2/4)
    v0, v1 = a*w*h, b*end[0]*end[1]
    return v+v0+v1, moment+v0*a/2+v1*(a+taper+b/2)


def expected_rings(data, inner):
    offset = 0 if inner else data['section_offset_m']
    a = data['start_length_m']; taper = data['transition_length_m']
    stations = [-EXTENSION_M if inner else 0, a, a+taper, total_length(data)+(EXTENSION_M if inner else 0)]
    dimensions = [data['start_section_m']]*2 + [data['end_section_m']]*2
    return np.array([(sx*(w+2*offset)/2, sy*(h+2*offset)/2, z) for (w, h), z in zip(dimensions, stations) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))])


def inspect(path, data):
    validate(data); model = ifcopenshell.open(str(path)); logger = ifcopenshell.validate.json_logger()
    largest_change = max(abs(a-b) for a, b in zip(data['start_section_m'], data['end_section_m']))
    angle = math.degrees(2*math.atan(largest_change/(2*data['transition_length_m'])))
    if not math.isclose(angle, data['upstream_angle_degrees'], abs_tol=1e-8, rel_tol=0):
        raise ValueError('Declared centred transition length and angle disagree')
    ifcopenshell.validate.validate(model, logger, express_rules=True)
    if logger.statements: raise ValueError('Saved transition schema/EXPRESS issues')
    fitting = model.by_guid(stable_guid(data, 'IfcDuctFitting', KEY))
    if len(model.by_type('IfcDistributionElement')) != 1 or fitting.PredefinedType != 'TRANSITION' or not np.allclose(placement.get_local_placement(fitting.ObjectPlacement), placement_matrix(data), atol=1e-9, rtol=0):
        raise ValueError('Exact single transition type/placement required')
    props = element.get_psets(fitting).get('BSA_DesignInputs', {})
    if any(props.get(k) != v for k, v in dict(Source=data['source'], Classification=data['classification'], WallModel=data['wall_model'], SectionOffset_m=data['section_offset_m']).items()):
        raise ValueError('Transition source/wall metadata differs')
    body = fitting.Representation.Representations
    if len(body) != 1 or body[0].RepresentationType != 'CSG' or len(body[0].Items) != 1: raise ValueError('One native CSG transition wall required')
    wall = body[0].Items[0]
    if not wall.is_a('IfcBooleanResult') or wall.Operator != 'DIFFERENCE': raise ValueError('Explicit outer-minus-inner transition required')
    for inner, brep in ((False, wall.FirstOperand), (True, wall.SecondOperand)):
        if not brep.is_a('IfcFacetedBrep'): raise ValueError('Upstream-derived faceted BRep operands required')
        coordinates = []; faces = brep.Outer.CfsFaces
        if len(faces) != 14: raise ValueError('Expected centred rectangular transition face coverage')
        for face in faces:
            if len(face.Bounds) != 1 or not face.Bounds[0].is_a('IfcFaceOuterBound') or face.Bounds[0].Orientation is not True or not face.Bounds[0].Bound.is_a('IfcPolyLoop'):
                raise ValueError('Single oriented polygonal face boundary required')
            points = np.asarray([p.Coordinates for p in face.Bounds[0].Bound.Polygon], dtype=float)
            if len(points) < 3 or points.shape[1] != 3 or not np.isfinite(points).all() or np.linalg.matrix_rank(points-points[0], tol=1e-10) != 2:
                raise ValueError('Finite planar transition faces required')
            coordinates.extend(points)
        expected = expected_rings(data, inner); actual = np.unique(coordinates, axis=0)
        if len(actual) != 16 or any(np.min(np.linalg.norm(actual-point, axis=1)) > 1e-9 for point in expected) or any(np.min(np.linalg.norm(expected-point, axis=1)) > 1e-9 for point in actual):
            raise ValueError('Saved transition stations/section corners differ from source')
    ports = system.get_ports(fitting)
    if len(ports) != 2 or len(model.by_type('IfcDistributionPort')) != 2 or {p.Name for p in ports} != {'start', 'end'}: raise ValueError('Two owned transition ports required')
    for port in ports:
        if port.GlobalId != stable_guid(data, 'IfcDistributionPort', KEY, port.Name) or port.FlowDirection != data['port_directions'][port.Name] or port.PredefinedType != 'DUCT' or port.SystemType != 'VENTILATION' or not np.allclose(placement.get_local_placement(port.ObjectPlacement), port_frames(data)[port.Name], atol=1e-9, rtol=0):
            raise ValueError('Saved transition port identity/type/direction/frame differs')
    shape = ifcopenshell.geom.create_shape(ifcopenshell.geom.settings(), fitting)
    vertices = np.asarray(shape.geometry.verts).reshape(-1, 3); faces = np.asarray(shape.geometry.faces).reshape(-1, 3)
    args = [data[k] for k in ('start_length_m', 'end_length_m', 'transition_length_m')]
    inner_v, inner_m = integral(data['start_section_m'], data['end_section_m'], *args)
    offset = data['section_offset_m']; outer_sections = [[v+2*offset for v in data[k]] for k in ('start_section_m', 'end_section_m')]
    outer_v, outer_m = integral(*outer_sections, *args); expected_volume = outer_v-inner_v
    volume, error, euler = verify_closed_wall(vertices, faces, expected_volume)
    mass = mesh_properties(vertices, faces)
    if not np.allclose(mass['centroid'], [0, 0, (outer_m-inner_m)/expected_volume], atol=1e-8, rtol=0): raise ValueError('Transition material centroid differs from independent integration')
    bounds = [[-max(s[0] for s in outer_sections)/2, -max(s[1] for s in outer_sections)/2, 0], [max(s[0] for s in outer_sections)/2, max(s[1] for s in outer_sections)/2, total_length(data)]]
    if not np.allclose(mass['bounds'], bounds, atol=1e-9, rtol=0): raise ValueError('Transition outer bounds differ')
    solid = from_mesh((vertices, faces)); w, h = np.minimum(data['start_section_m'], data['end_section_m'])
    probe = m.Manifold.cube((w*.5, h*.5, total_length(data)+.2), center=True).translate((0, 0, total_length(data)/2))
    overlap = solid ^ probe
    if overlap.status() != m.Error.NoError or abs(overlap.volume()) > 1e-12: raise ValueError('Transition centre air path blocked')
    return dict(schema_express_issue_count=0, ports=2, material_volume_m3=volume, independent_material_volume_m3=expected_volume,
        material_centroid_m=mass['centroid'].tolist(), relative_volume_error=error, euler_characteristic=euler,
        one_connected_closed_material=True, independent_maximum_included_angle_degrees=angle,
        centre_bore_overlap_m3=overlap.volume(), bounds_m=mass['bounds'].tolist())


def upstream_brep(model, builder, sections, a, b, angle, expected_length, translate_z=0):
    placeholders = []
    for dims in sections:
        obj = api.run('root.create_entity', model, ifc_class='IfcDuctSegment', name='Temporary upstream profile holder')
        profile = model.create_entity('IfcRectangleProfileDef', ProfileType='AREA', XDim=float(dims[0]), YDim=float(dims[1]))
        material = model.create_entity('IfcMaterialProfileSet', MaterialProfiles=[model.create_entity('IfcMaterialProfile', Profile=profile)])
        model.create_entity('IfcRelAssociatesMaterial', GlobalId=ifcopenshell.guid.new(), RelatedObjects=[obj], RelatingMaterial=material)
        placeholders.append(obj)
    representation, parameters = builder.mep_transition_shape(*placeholders, a, b, angle=angle, profile_offset=(0., 0.))
    if representation is None or not math.isclose(parameters['transition_length'], expected_length, abs_tol=1e-9, rel_tol=0): raise ValueError('Upstream transition length differs from explicit source; no geometry substituted')
    if translate_z: builder.translate(representation, (0., 0., translate_z))
    if len(representation.Items) != 1 or not representation.Items[0].is_a('IfcPolygonalFaceSet'): raise ValueError('Expected single upstream rectangular face set')
    item = representation.Items[0]
    brep = builder.faceted_brep(item.Coordinates.CoordList, [[i-1 for i in face.CoordIndex] for face in item.Faces])
    api.run('geometry.remove_representation', model, representation=representation)
    for obj in placeholders: api.run('root.remove_product', model, product=obj)
    return brep


def run(project, out):
    project, out = Path(project).resolve(), Path(out).resolve()
    data = validate(json.loads(project.read_text(encoding='utf-8-sig')))
    if out.exists() or not out.is_relative_to(ROOT) or out == project or out in project.parents: raise ValueError('New repository-local output outside source required')
    versions = {name: importlib.metadata.version(name) for name in ('ifcopenshell', 'manifold3d')}
    if versions != {'ifcopenshell': '0.8.5', 'manifold3d': '3.5.4'}: raise ValueError('Pinned IFC/Boolean runtimes required')
    before = digest(project); out.mkdir(parents=True)
    model = api.run('project.create_file', version='IFC4'); api.run('root.create_entity', model, ifc_class='IfcProject', name='Declared centred rectangular transition')
    unit = api.run('unit.add_si_unit', model, unit_type='LENGTHUNIT'); api.run('unit.assign_unit', model, units=[unit])
    context = api.run('context.add_context', model, context_type='Model')
    body = api.run('context.add_context', model, context_type='Model', context_identifier='Body', target_view='MODEL_VIEW', parent=context)
    builder = ShapeBuilder(model); offset = data['section_offset_m']; sections = [data[k] for k in ('start_section_m', 'end_section_m')]
    a, b, angle, taper = [data[k] for k in ('start_length_m', 'end_length_m', 'upstream_angle_degrees', 'transition_length_m')]
    log = io.StringIO()
    try:
        with redirect_stdout(log):
            outer = upstream_brep(model, builder, [[v+2*offset for v in dims] for dims in sections], a, b, angle, taper)
            inner = upstream_brep(model, builder, sections, a+EXTENSION_M, b+EXTENSION_M, angle, taper, -EXTENSION_M)
    finally:
        (out/'upstream.log').write_text(log.getvalue(), encoding='utf-8')
    wall = model.create_entity('IfcBooleanResult', Operator='DIFFERENCE', FirstOperand=outer, SecondOperand=inner)
    representation = model.create_entity('IfcShapeRepresentation', ContextOfItems=body, RepresentationIdentifier='Body', RepresentationType='CSG', Items=[wall])
    fitting = api.run('root.create_entity', model, ifc_class='IfcDuctFitting', predefined_type='TRANSITION', name=KEY)
    fitting.GlobalId = stable_guid(data, 'IfcDuctFitting', KEY)
    api.run('geometry.assign_representation', model, product=fitting, representation=representation)
    api.run('geometry.edit_object_placement', model, product=fitting, matrix=placement_matrix(data), is_si=True)
    for name, matrix in port_frames(data).items():
        port = api.run('system.add_port', model, element=fitting); port.Name = name
        port.GlobalId = stable_guid(data, 'IfcDistributionPort', KEY, name); port.FlowDirection = data['port_directions'][name]
        port.PredefinedType = 'DUCT'; port.SystemType = 'VENTILATION'
        api.run('geometry.edit_object_placement', model, product=port, matrix=matrix, is_si=True)
    pset = api.run('pset.add_pset', model, product=fitting, name='BSA_DesignInputs')
    api.run('pset.edit_pset', model, pset=pset, properties=dict(Source=data['source'], Classification=data['classification'], WallModel=data['wall_model'], SectionOffset_m=offset))
    target = out/'transition.ifc'; model.write(str(target)); checks = inspect(target, data)
    if digest(project) != before: raise ValueError('Transition source changed')
    result = dict(inputs={str(project): before}, versions=versions, upstream_builder_sha256=digest(Path(shape_builder.__file__)), generator_sha256=digest(Path(__file__)),
        ifc_sha256=digest(target), upstream_log_sha256=digest(out/'upstream.log'), checks=checks, geometry_checks_pass=True, design_accepted=False, numerical_bore_extension_m=EXTENSION_M,
        scope='Centred rectangular section-plane-offset transition only; not constant sheet-normal thickness, products, joints, loss coefficients, assembly or jurisdiction acceptance')
    (out/'transition.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('project'); parser.add_argument('--out', required=True)
    args = parser.parse_args(); print(json.dumps(run(args.project, args.out)['checks'], indent=2)); raise SystemExit(2)

"""Derive and author a straight candidate between two independently source-bound fittings."""
import argparse
import importlib.metadata
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
import numpy as np

from .cli import digest
from . import rectangular_geometry as rectangular
from . import rectangular_tee as tee
from . import rectangular_transition as transition
from . import rectangular_tee_transitions as composition
from . import duct_fitting_fit
from .tee_geometry import project_namespace, stable_guid
from .circular_geometry import verify_closed_wall
from .cad_ifc import mesh_properties
from .solid_clash import from_mesh

import manifold3d as m

ROOT = Path(__file__).resolve().parents[2]
KEY = 'SOURCE-BOUND-DUCT-SPAN'


def prepare(project):
    project = Path(project).resolve(); data = json.loads(project.read_text(encoding='utf-8-sig'))
    if not isinstance(data, dict) or set(data) != {'project_uuid', 'source', 'plan', 'workflow', 'native_task', 'section', 'endpoints'}: raise ValueError('Exact source-bound span project fields required')
    project_namespace(data)
    if any(not isinstance(data[k], str) or not data[k].strip() for k in ('source', 'native_task', 'section')): raise ValueError('Explicit source, native task and section required')
    def local(name):
        if not isinstance(name, str) or not name or Path(name).is_absolute(): raise ValueError('Relative source path required')
        path = (project.parent/name).resolve()
        if not path.is_relative_to(project.parent): raise ValueError('Span sources must remain within project source directory')
        return path
    if not isinstance(data['endpoints'], list) or len(data['endpoints']) != 2: raise ValueError('Two explicit fitting endpoints required')
    ends = []
    for row in data['endpoints']:
        if not isinstance(row, dict) or set(row) != {'project', 'model', 'binding'}: raise ValueError('Endpoint requires source project, model directory and binding')
        ends.append({k: local(v) for k, v in row.items()})
    if ends[0] == ends[1]: raise ValueError('Distinct fitting endpoints required')
    return project, data, local(data['plan']), local(data['workflow']), ends


def endpoint(project, model, binding, fit, section):
    _, data, _, spec, children = composition.prepare(project)
    rows = [r for r in fit['arms'] if r['section'] == section]
    if len(rows) != 1: raise ValueError('Selected section must occur once at each fitting')
    row = rows[0]; arm = row['arm']; child = children.get(arm)
    guid = stable_guid(child, 'IfcDistributionPort', transition.KEY, 'end') if child else stable_guid(spec, 'IfcDistributionPort', 'RECTANGULAR-TEE', arm)
    saved = ifcopenshell.open(str(model/'assembly.ifc')); port = saved.by_guid(guid)
    return dict(node=fit['node'], arm=arm, port_guid=guid, frame=placement.get_local_placement(port.ObjectPlacement),
        flow_direction=port.FlowDirection, width_m=row['width_m'], height_m=row['height_m'], wall_thickness_m=spec['wall_thickness_m'],
        wall_classification=spec['classification'], reach_m=row['outward_reach_m'], source_length_m=row['source_centreline_length_m'],
        model_ifc=str(model/'assembly.ifc'), model_sha256=digest(model/'assembly.ifc'))


def calculate(endpoints):
    if len(endpoints) != 2 or endpoints[0]['node'] == endpoints[1]['node']: raise ValueError('Two different source nodes required')
    if {e['flow_direction'] for e in endpoints} != {'SOURCE', 'SINK'}: raise ValueError('One source and one sink fitting end required')
    start = next(e for e in endpoints if e['flow_direction'] == 'SOURCE'); end = next(e for e in endpoints if e['flow_direction'] == 'SINK')
    for key in ('width_m', 'height_m', 'wall_thickness_m', 'source_length_m'):
        values = [e[key] for e in endpoints]
        if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in values) or not math.isclose(*values, abs_tol=1e-8 if key == 'source_length_m' else 1e-10, rel_tol=0): raise ValueError('Endpoint nominal sections, wall parameters or source lengths disagree')
    for item in endpoints:
        if type(item['reach_m']) not in (int, float) or not math.isfinite(item['reach_m']) or item['reach_m'] <= 0: raise ValueError('Positive source-bound fitting reach required')
    a, b = start['frame'], end['frame']
    if not np.allclose(a[:3, 2], -b[:3, 2], atol=1e-9, rtol=0) or any(not math.isclose(abs(float(np.dot(a[:3, i], b[:3, i]))), 1, abs_tol=1e-9, rel_tol=0) for i in (0, 1)):
        raise ValueError('Opposed fitting normals and matching rectangle section rolls required')
    length = start['source_length_m']-start['reach_m']-end['reach_m']
    if length <= 1e-8:
        return dict(status='fail', straight_available=False, reason='Both fitting extents consume the source section; no positive straight span remains',
            source_length_m=start['source_length_m'], upstream_reach_m=start['reach_m'], downstream_reach_m=end['reach_m'], length_m=length, design_accepted=False)
    delta = b[:3, 3]-a[:3, 3]
    if not np.allclose(delta, length*a[:3, 2], atol=1e-8, rtol=0): raise ValueError('Saved end planes differ from independently trimmed source section or are not collinear')
    return dict(status='review_required', straight_available=True, source_length_m=start['source_length_m'],
        upstream_reach_m=start['reach_m'], downstream_reach_m=end['reach_m'], length_m=length,
        width_m=start['width_m'], height_m=start['height_m'], wall_thickness_m=start['wall_thickness_m'], frame=a.tolist(),
        upstream_node=start['node'], downstream_node=end['node'], upstream_port_guid=start['port_guid'], downstream_port_guid=end['port_guid'],
        endpoint_model_ifc_hashes={e['model_ifc']: e['model_sha256'] for e in endpoints}, design_accepted=False)


def inspect(path, data, span):
    model = ifcopenshell.open(str(path)); logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(model, logger, express_rules=True)
    if logger.statements: raise ValueError('Saved span schema/EXPRESS issues')
    guid = stable_guid(data, 'IfcDuctSegment', KEY, data['section']); obj = model.by_guid(guid)
    if len(model.by_type('IfcDistributionElement')) != 1 or obj.PredefinedType != 'RIGIDSEGMENT' or not np.allclose(placement.get_local_placement(obj.ObjectPlacement), span['frame'], atol=1e-9, rtol=0): raise ValueError('Exact source-placed straight span required')
    w, h, t, length = [span[k] for k in ('width_m', 'height_m', 'wall_thickness_m', 'length_m')]
    body = obj.Representation.Representations
    if len(body) != 1 or body[0].RepresentationType != 'SweptSolid' or len(body[0].Items) != 1: raise ValueError('One native swept straight wall required')
    solid = body[0].Items[0]
    if not solid.is_a('IfcExtrudedAreaSolid') or not solid.SweptArea.is_a('IfcRectangleHollowProfileDef'): raise ValueError('Native rectangular hollow wall required')
    profile = solid.SweptArea
    if not np.allclose([profile.XDim, profile.YDim, profile.WallThickness, solid.Depth], [w+2*t, h+2*t, t, length], atol=1e-10, rtol=0) or profile.Position is not None or any(v not in (None, 0.) for v in (profile.InnerFilletRadius, profile.OuterFilletRadius)) or not np.allclose(placement.get_axis2placement(solid.Position), np.eye(4), atol=1e-10, rtol=0) or tuple(solid.ExtrudedDirection.DirectionRatios) != (0., 0., 1.): raise ValueError('Saved span section/length/local placement differs')
    props = element.get_psets(obj).get('BSA_DesignInputs', {})
    expected = dict(InternalWidth_m=w, InternalHeight_m=h, WallThickness_m=t, Source=data['source'],
        UpstreamPort=span['upstream_port_guid'], DownstreamPort=span['downstream_port_guid'])
    if any(props.get(k) != v for k, v in expected.items()): raise ValueError('Span source/section/endpoint metadata differs')
    ports = system.get_ports(obj)
    if len(ports) != 2 or len(model.by_type('IfcDistributionPort')) != 2 or {p.Name for p in ports} != {'near', 'far'} or model.by_type('IfcRelConnectsPorts'): raise ValueError('Exactly two owned boundary ports and no fabricated external-file connections required')
    for port in ports:
        matrix = np.asarray(span['frame']).copy()
        if port.Name == 'near': matrix[:3, 1:3] *= -1
        else: matrix[:3, 3] += length*matrix[:3, 2]
        if port.GlobalId != stable_guid(data, 'IfcDistributionPort', KEY, data['section'], port.Name) or port.FlowDirection != ('SINK' if port.Name == 'near' else 'SOURCE') or port.PredefinedType != 'DUCT' or port.SystemType != 'VENTILATION' or not np.allclose(placement.get_local_placement(port.ObjectPlacement), matrix, atol=1e-9, rtol=0): raise ValueError('Saved span port identity/direction/frame differs')
    shape = ifcopenshell.geom.create_shape(ifcopenshell.geom.settings(), obj)
    vertices = np.asarray(shape.geometry.verts).reshape(-1, 3); faces = np.asarray(shape.geometry.faces).reshape(-1, 3)
    expected_volume = ((w+2*t)*(h+2*t)-w*h)*length
    volume, error, euler = verify_closed_wall(vertices, faces, expected_volume); mass = mesh_properties(vertices, faces)
    if not np.allclose(mass['centroid'], [0, 0, length/2], atol=1e-8, rtol=0) or not np.allclose(mass['bounds'], [[-(w+2*t)/2, -(h+2*t)/2, 0], [(w+2*t)/2, (h+2*t)/2, length]], atol=1e-8, rtol=0): raise ValueError('Saved span local material centroid/bounds differ')
    return dict(schema_express_issue_count=0, ports=2, wall_volume_m3=volume, independent_wall_volume_m3=expected_volume,
        relative_volume_error=error, euler_characteristic=euler, one_connected_closed_wall=True, saved_source_frames_pass=True,
        external_logical_connections_created=False)


def author(data, span, target):
    if {k: importlib.metadata.version(k) for k in ('ifcopenshell', 'manifold3d')} != {'ifcopenshell': '0.8.5', 'manifold3d': '3.5.4'}: raise ValueError('Pinned native IFC/material runtimes required')
    model = api.run('project.create_file', version='IFC4'); api.run('root.create_entity', model, ifc_class='IfcProject', name='Source-bound straight candidate')
    unit = api.run('unit.add_si_unit', model, unit_type='LENGTHUNIT'); api.run('unit.assign_unit', model, units=[unit])
    context = api.run('context.add_context', model, context_type='Model')
    body = api.run('context.add_context', model, context_type='Model', context_identifier='Body', target_view='MODEL_VIEW', parent=context)
    obj = api.run('root.create_entity', model, ifc_class='IfcDuctSegment', predefined_type='RIGIDSEGMENT', name=data['section'])
    obj.GlobalId = stable_guid(data, 'IfcDuctSegment', KEY, data['section'])
    w, h, t, length = [span[k] for k in ('width_m', 'height_m', 'wall_thickness_m', 'length_m')]
    device = dict(ifc_class='IfcDuctSegment', origin_m=[-(w+2*t)/2, -(h+2*t)/2, 0], size_m=[w+2*t, h+2*t, length],
        properties=dict(InternalWidth_m=w, InternalHeight_m=h, WallThickness_m=t),
        ports=[dict(id='near', direction='SINK', offset_m=[(w+2*t)/2, (h+2*t)/2, 0]), dict(id='far', direction='SOURCE', offset_m=[(w+2*t)/2, (h+2*t)/2, length])])
    rectangular.author(model, body, obj, device)
    api.run('geometry.edit_object_placement', model, product=obj, matrix=np.asarray(span['frame']), is_si=True)
    props = dict(device['properties'], Source=data['source'], UpstreamPort=span['upstream_port_guid'], DownstreamPort=span['downstream_port_guid'])
    pset = api.run('pset.add_pset', model, product=obj, name='BSA_DesignInputs'); api.run('pset.edit_pset', model, pset=pset, properties=props)
    for name in ('near', 'far'):
        port = api.run('system.add_port', model, element=obj); port.Name = name
        port.GlobalId = stable_guid(data, 'IfcDistributionPort', KEY, data['section'], name)
        port.FlowDirection = 'SINK' if name == 'near' else 'SOURCE'; port.PredefinedType = 'DUCT'; port.SystemType = 'VENTILATION'
        matrix = np.asarray(span['frame']).copy()
        if name == 'near': matrix[:3, 1:3] *= -1
        else: matrix[:3, 3] += length*matrix[:3, 2]
        api.run('geometry.edit_object_placement', model, product=port, matrix=matrix, is_si=True)
    model.write(str(target)); return inspect(target, data, span)


def material_intersections(path, endpoints):
    """Actual saved material only; contacts/obstacles outside these models are separate."""
    target = ifcopenshell.open(str(path)); obj = target.by_type('IfcDuctSegment')[0]
    base = placement.get_local_placement(obj.ObjectPlacement)
    settings = ifcopenshell.geom.settings(); settings.set(settings.USE_WORLD_COORDS, False)
    shape = ifcopenshell.geom.create_shape(settings, obj)
    wall = from_mesh((np.asarray(shape.geometry.verts).reshape(-1, 3), np.asarray(shape.geometry.faces).reshape(-1, 3)))
    rows = []
    for source in sorted({e['model_ifc'] for e in endpoints}):
        model = ifcopenshell.open(source)
        for product in model.by_type('IfcDistributionElement'):
            mesh = ifcopenshell.geom.create_shape(settings, product)
            matrix = placement.get_local_placement(product.ObjectPlacement)
            rotation = base[:3, :3].T @ matrix[:3, :3]
            origin = base[:3, :3].T @ (matrix[:3, 3]-base[:3, 3])
            vertices = np.asarray(mesh.geometry.verts).reshape(-1, 3) @ rotation.T + origin
            solid = from_mesh((vertices, np.asarray(mesh.geometry.faces).reshape(-1, 3)))
            common = wall ^ solid
            if common.status() != m.Error.NoError: raise ValueError('Saved material intersection failed')
            rows.append(dict(model_ifc=source, product_guid=product.GlobalId, overlap_volume_m3=common.volume(),
                no_material_interpenetration=abs(common.volume()) <= 1e-12))
    if not rows: raise ValueError('Source material coverage required')
    return dict(pairs=rows, no_material_interpenetration=all(r['no_material_interpenetration'] for r in rows),
        scope='Candidate wall versus all distribution material in the two supplied source models only; no general obstacle or installation clearance acceptance')


def run(project, out):
    from .workflow import verify
    project, data, plan, workflow, ends = prepare(project); out = Path(out).resolve()
    protected = [project, plan]+[e[k] for e in ends for k in ('project', 'binding')]
    if out.exists() or not out.is_relative_to(ROOT) or any(out == p or out in p.parents for p in protected) or any(out.is_relative_to(p) or p.is_relative_to(out) for p in [workflow]+[e['model'] for e in ends]): raise ValueError('New repository-local output outside source workflows/models required')
    pins = {str(p): digest(p) for p in protected+[Path(__file__)]}; out.mkdir(parents=True)
    endpoints = []
    for i, e in enumerate(ends):
        review_directory = out/('endpoint-'+str(i+1))
        fit = duct_fitting_fit.run(plan, workflow, data['native_task'], e['project'], e['model'], e['binding'], review_directory)
        if fit['plan_extent_check_pass'] is not True: raise ValueError('Each local fitting must pass necessary source extent checks')
        junction_path = review_directory/'junction-review.json'
        junction = json.loads(junction_path.read_text(encoding='utf-8'))
        if any(not Path(p).is_file() or digest(Path(p)) != sha for p, sha in junction['inputs'].items()): raise ValueError('Native source review changed before span calculation')
        for addition in (junction['inputs'], fit['inputs']):
            for name, sha in addition.items():
                if name in pins and pins[name] != sha: raise ValueError('Source context changed between endpoint reviews')
                pins[name] = sha
        pins[str(junction_path)] = digest(junction_path)
        endpoints.append(endpoint(e['project'], e['model'], e['binding'], fit, data['section']))
    span = calculate(endpoints)
    if span['straight_available']:
        span['checks'] = author(data, span, out/'span.ifc'); span['ifc_sha256'] = digest(out/'span.ifc')
        span['material_intersections'] = material_intersections(out/'span.ifc', endpoints)
        if not span['material_intersections']['no_material_interpenetration']: span['status'] = 'fail'
    if any(digest(Path(p)) != sha for p, sha in pins.items()) or not verify(workflow)['integrity_pass']: raise ValueError('Span source/model changed during generation')
    span.update(inputs=pins, source_endpoints=[{k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in e.items()} for e in endpoints],
        installation_accepted=False, installation_elevation_verified=False, section_roll_verified=False,
        product_joint_allowances_included=False, design_accepted=False,
        scope='Single source-bound trimmed straight candidate between two separately saved fittings; no merged-system connectivity, product allowances, installation/clearance, pressure or regulatory acceptance')
    (out/'span.json').write_text(json.dumps(span, indent=2), encoding='utf-8'); return span


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('project'); parser.add_argument('--out', required=True)
    args = parser.parse_args(); result = run(args.project, args.out); print(result['status'], result['length_m']); raise SystemExit(1 if result['status'] == 'fail' else 2)

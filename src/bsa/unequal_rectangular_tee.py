"""Reduced-branch sharp tee study using existing IFC/Boolean authoring engines."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path

from . import rectangular_tee as base
from .cli import digest
from .workspace import allowed

VERSIONS = {'ifcopenshell': '0.8.5', 'manifold3d': '3.5.4'}
SCOPE = 'Isolated reduced-branch fitting geometry; no pressure, network merge, physical installation or native CAD acceptance'

def validate(data):
    if not isinstance(data, dict) or set(data) != {'tee', 'branch_section_m'}:
        raise ValueError('Explicit source tee and branch section required')
    w, h, t, length, branch = base.validate(data['tee'])
    section = data['branch_section_m']
    if not isinstance(section, list) or len(section) != 2 or any(
        type(x) not in (int, float) or not math.isfinite(x) or x <= 0 for x in section
    ):
        raise ValueError('Two positive finite branch dimensions required')
    bw, bh = section
    if bw > w or bh > h or section == [w, h]:
        raise ValueError('Strictly reduced branch within main section required')
    return w, h, t, length, branch, bw, bh


def inspect(path, data):
    w, h, t, length, branch, bw, bh = validate(data)
    spec = data['tee']; np = base.np
    model = base.ifcopenshell.open(str(path))
    logger = base.ifcopenshell.validate.json_logger()
    base.ifcopenshell.validate.validate(model, logger, express_rules=True)
    if logger.statements:
        raise ValueError('Saved IFC schema/EXPRESS issues')
    products = model.by_type('IfcDistributionElement')
    guid = base.stable_guid(spec, 'IfcDuctFitting', 'RECTANGULAR-TEE')
    if len(products) != 1 or products[0].GlobalId != guid:
        raise ValueError('Exact single fitting identity required')
    fitting = products[0]; transform = base.placement_matrix(spec)
    if fitting.PredefinedType != 'JUNCTION' or not np.allclose(
        base.placement.get_local_placement(fitting.ObjectPlacement), transform, atol=1e-9, rtol=0
    ):
        raise ValueError('Saved fitting placement/type differs')
    props = base.element_util.get_psets(fitting)['BSA_DesignInputs']
    if props['Source'] != spec['source'] or props['Classification'] != spec['classification'] or json.loads(props['BranchSection_m']) != [bw, bh]:
        raise ValueError('Saved source or branch declaration differs')
    representations = fitting.Representation.Representations
    if len(representations) != 1 or representations[0].RepresentationType != 'CSG' or len(representations[0].Items) != 1:
        raise ValueError('One native CSG representation required')
    wall = representations[0].Items[0]
    if not wall.is_a('IfcBooleanResult') or wall.Operator != 'DIFFERENCE':
        raise ValueError('Outer-minus-inner construction required')
    for union, offset in ((wall.FirstOperand, t), (wall.SecondOperand, 0)):
        if not union.is_a('IfcBooleanResult') or union.Operator != 'UNION':
            raise ValueError('Main/branch prism union required')
        rows = [(union.FirstOperand, w, h, 2*length, (0, 0, -length), (0, 0, 1), (1, 0, 0)),
                (union.SecondOperand, bw, bh, branch, (0, 0, 0), (1, 0, 0), (0, 0, -1))]
        for solid, width, height, depth, origin, axis, reference in rows:
            if not solid.is_a('IfcExtrudedAreaSolid') or not solid.SweptArea.is_a('IfcRectangleProfileDef'):
                raise ValueError('Native rectangular extrusion required')
            profile = solid.SweptArea
            if profile.Position is not None or not np.allclose(
                [profile.XDim, profile.YDim, solid.Depth], [width+2*offset, height+2*offset, depth], atol=1e-10, rtol=0
            ):
                raise ValueError('Saved branch/main profiles differ')
            expected = np.eye(4); expected[:3, :3] = np.column_stack((reference, np.cross(axis, reference), axis)); expected[:3, 3] = origin
            if not np.allclose(base.placement.get_axis2placement(solid.Position), expected, atol=1e-10, rtol=0) or tuple(solid.ExtrudedDirection.DirectionRatios) != (0., 0., 1.):
                raise ValueError('Saved extrusion frame differs')
    ports = base.system_util.get_ports(fitting)
    if len(ports) != 3 or len(model.by_type('IfcDistributionPort')) != 3 or {p.Name for p in ports} != set(base.NAMES):
        raise ValueError('Exactly three owned ports required')
    frames = base.port_frames(spec)
    for port in ports:
        if port.GlobalId != base.stable_guid(spec, 'IfcDistributionPort', 'RECTANGULAR-TEE', port.Name) or port.FlowDirection != spec['port_directions'][port.Name] or not np.allclose(base.placement.get_local_placement(port.ObjectPlacement), frames[port.Name], atol=1e-9, rtol=0):
            raise ValueError('Saved port identity/direction/frame differs')
    settings = base.ifcopenshell.geom.settings(); settings.set(settings.USE_WORLD_COORDS, True)
    shape = base.ifcopenshell.geom.create_shape(settings, fitting)
    vertices = np.asarray(shape.geometry.verts).reshape(-1, 3)
    vertices = (vertices-transform[:3, 3])@transform[:3, :3]
    faces = np.asarray(shape.geometry.faces).reshape(-1, 3)
    solid = base.from_mesh((vertices, faces))
    # Independent inclusion/exclusion of main and branch rectangular volumes.
    def volume(offset):
        mw, mh, sw, sh = w+2*offset, h+2*offset, bw+2*offset, bh+2*offset
        return 2*length*mw*mh + branch*sw*sh - mw/2*sw*sh
    expected_volume = volume(t)-volume(0)
    if len(solid.decompose()) != 1 or not math.isclose(solid.volume(), expected_volume, rel_tol=1e-9, abs_tol=1e-10):
        raise ValueError('Native connected material/independent volume differs')
    edges = Counter(tuple(sorted((int(a), int(b)))) for face in faces for a, b in zip(face, [face[1], face[2], face[0]]))
    euler = len(vertices)-len(edges)+len(faces)
    if any(x != 2 for x in edges.values()) or euler != -2:
        raise ValueError('Three-port bore topology differs')
    if not np.allclose([vertices.min(axis=0), vertices.max(axis=0)], [[-w/2-t, -h/2-t, -length], [branch, h/2+t, length]], atol=1e-8, rtol=0):
        raise ValueError('Native envelope differs')
    probes = [base.m.Manifold.cube((w*.5, h*.5, 2*length+.2), center=True),
              base.m.Manifold.cube((branch+.1, bh*.5, bw*.5), center=True).translate(((branch+.1)/2, 0, 0))]
    intersections = [solid^probe for probe in probes]
    if any(item.status() != base.m.Error.NoError for item in intersections):
        raise ValueError('Bore Boolean failed')
    overlaps = [item.volume() for item in intersections]
    if any(abs(x) > 1e-12 for x in overlaps):
        raise ValueError('Air bore intersects material')
    return dict(schema_express_issue_count=0, ports=3, native_material_volume_m3=solid.volume(),
                independent_material_volume_m3=expected_volume, euler_characteristic=euler,
                bore_probe_overlap_m3=overlaps, native_profiles_and_port_frames_verified=True)


def run(project, output):
    project, output = Path(project).resolve(), Path(output).resolve()
    if not allowed(project) or not allowed(output) or output.exists() or output == project or output in project.parents:
        raise ValueError('Fresh host-selected output outside source required')
    data = json.loads(project.read_text(encoding='utf-8-sig'))
    w, h, t, length, branch, bw, bh = validate(data)
    before = digest(project); output.mkdir(parents=True)
    template = output/'template.json'; template.write_text(json.dumps(data['tee']), encoding='utf-8')
    base.run(template, output/'template')
    model = base.ifcopenshell.open(str(output/'template/rectangular-tee.ifc'))
    fitting = model.by_type('IfcDuctFitting')[0]; builder = base.ShapeBuilder(model)
    context = fitting.Representation.Representations[0].ContextOfItems
    for representation in list(fitting.Representation.Representations):
        base.api.run('geometry.unassign_representation', model, product=fitting, representation=representation)
        base.api.run('geometry.remove_representation', model, representation=representation)
    def union(offset):
        main = builder.extrude(model.create_entity('IfcRectangleProfileDef', ProfileType='AREA', XDim=w+2*offset, YDim=h+2*offset), magnitude=2*length, position=(0., 0., -length))
        side = builder.extrude(model.create_entity('IfcRectangleProfileDef', ProfileType='AREA', XDim=bw+2*offset, YDim=bh+2*offset), magnitude=branch, position_z_axis=(1., 0., 0.), position_x_axis=(0., 0., -1.))
        return base.api.run('geometry.add_boolean', model, first_item=main, second_items=[side], operator='UNION')[-1]
    wall = base.api.run('geometry.add_boolean', model, first_item=union(t), second_items=[union(0)], operator='DIFFERENCE')[-1]
    rep = builder.get_representation(context, [wall], representation_type='CSG')
    base.api.run('geometry.assign_representation', model, product=fitting, representation=rep)
    pset = next(r.RelatingPropertyDefinition for r in fitting.IsDefinedBy if r.RelatingPropertyDefinition.Name == 'BSA_DesignInputs')
    base.api.run('pset.edit_pset', model, pset=pset, properties={'BranchSection_m': json.dumps([bw, bh]), 'Scope': 'Reduced-branch sharp tee; source-declared study, not product or network acceptance'})
    target = output/'unequal-tee.ifc'; model.write(str(target))
    checks = inspect(target, data)
    if digest(project) != before:
        raise ValueError('Source changed during execution')
    result = dict(inputs={str(project): before, str(Path(__file__).resolve()): digest(Path(__file__)), str(Path(base.__file__).resolve()): digest(Path(base.__file__))},
                  ifc_sha256=digest(target), parameters=data, checks=checks,
                  versions={name: base.importlib.metadata.version(name) for name in ('ifcopenshell', 'manifold3d')}, design_accepted=False,
                  scope=SCOPE)
    (output/'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


def verify(output):
    output = Path(output).resolve()
    if not allowed(output):
        raise ValueError('Selected workspace required')
    result = json.loads((output/'result.json').read_text())
    sources = [Path(p) for p in result['inputs'] if Path(p).suffix == '.json']
    required = {str(Path(__file__).resolve()), str(Path(base.__file__).resolve())}
    current_versions = {name: base.importlib.metadata.version(name) for name in VERSIONS}
    if len(sources) != 1 or set(result['inputs']) != required | {str(sources[0])} or result['versions'] != VERSIONS or current_versions != VERSIONS:
        raise ValueError('Exact source/method/runtime pins required')
    if result.get('design_accepted') is not False or result.get('scope') != SCOPE:
        raise ValueError('Incomplete engineering scope must be preserved')
    if any(not allowed(Path(p)) or digest(Path(p)) != sha for p, sha in result['inputs'].items()) or digest(output/'unequal-tee.ifc') != result['ifc_sha256']:
        raise ValueError('Source/method/artifact changed')
    project = sources[0]
    data = json.loads(project.read_text(encoding='utf-8-sig'))
    if data != result['parameters'] or inspect(output/'unequal-tee.ifc', data) != result['checks']:
        raise ValueError('Saved geometry/source reconstruction differs')
    return dict(integrity_pass=True, design_accepted=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('action', choices=['run', 'verify']); parser.add_argument('source'); parser.add_argument('--out')
    args = parser.parse_args()
    print(json.dumps(run(args.source, args.out) if args.action == 'run' else verify(args.source), indent=2))

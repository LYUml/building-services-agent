"""Checked single continuous cable to editable planar true-arc geometry.

Selected cable geometry only, not a coordinated installation drawing.
"""
import argparse
import json
import math
from pathlib import Path
import numpy as np
from .cli import digest
from .engine import ProjectError
from .three_phase import ROOT
from .three_phase_ifc import inspect
from .ifc_drawing import validate_settings, AXES


def project_geometry(points, centre, radius, axes):
    indices = [AXES[a] for a in axes]
    omitted = next(i for i in range(3) if i not in indices)
    points = np.asarray(points, dtype=float)
    centre = np.asarray(centre, dtype=float)
    if points.shape != (4, 3) or centre.shape != (3,) or not np.isfinite(points).all() or not np.isfinite(centre).all():
        raise ProjectError('four finite quarter/straight route points required')
    if not np.allclose(points[:, omitted], centre[omitted], atol=1e-9, rtol=0):
        raise ProjectError('route must lie in the selected projection plane; oblique arcs unsupported')
    p = points[:, indices]
    c = centre[indices]
    if not np.allclose(np.linalg.norm(p[:3] - c, axis=1), radius, atol=1e-9, rtol=0):
        raise ProjectError('projection does not preserve circular radius')
    angle = lambda q: math.degrees(math.atan2(q[1] - c[1], q[0] - c[0])) % 360
    start, middle, end = [angle(q) for q in p[:3]]
    if not math.isclose((end - start) % 360, 90., abs_tol=1e-7):
        start, end = end, start
    if not math.isclose((end - start) % 360, 90., abs_tol=1e-7) or not math.isclose((middle - start) % 360, 45., abs_tol=1e-7):
        raise ProjectError('exact quarter-circle projection required; chord fallback forbidden')
    return dict(points_m=p.tolist(), centre_m=c.tolist(), radius_m=radius,
                start_angle_deg=start, end_angle_deg=end, plane_coordinate_m=float(centre[omitted]))


def run(project, ifc, binding, settings, out, obstacles=None):
    import ezdxf
    import ifcopenshell
    import ifcopenshell.util.placement as placement
    import ifcopenshell.util.unit as unit
    from .cad_overlay import snapshot, reconcile
    from .quarter_cable import points as quarter_points
    project, ifc, binding, settings, out = [Path(p).resolve() for p in (project, ifc, binding, settings, out)]
    if not out.is_relative_to(ROOT) or out.exists():
        raise ProjectError('new repository cable drawing output required')
    config = validate_settings(json.loads(settings.read_text(encoding='utf-8-sig')))
    checked = inspect(project, ifc, binding)
    before = {**checked['inputs'], str(settings): digest(settings), str(Path(__file__).resolve()): digest(Path(__file__))}
    obstacle_rows=[]
    if obstacles is not None:
        from .obstacle_projection import extract
        obstacle_rows,obstacle_inputs=extract(ifc,obstacles,config['projection_axes'])
        if any(p in before and before[p]!=sha for p,sha in obstacle_inputs.items()):raise ProjectError('shared cable/obstacle inputs changed between inspections')
        before.update(obstacle_inputs)
    if any(out == Path(p) or out in Path(p).parents for p in before):
        raise ProjectError('output must not contain inputs')
    if len(checked['lines']) != 1 or checked['lines'][0]['route_geometry'] != 'quarter plus tangent straight':
        raise ProjectError('exactly one checked quarter-plus-tangent cable required')
    row = checked['lines'][0]
    model = ifcopenshell.open(str(ifc))
    cable = model.by_guid(row['element_guid'])
    physical={o.GlobalId for o in model.by_type('IfcElement') if not o.is_a('IfcFeatureElement') and not o.is_a('IfcVirtualElement')}
    if obstacles is not None and physical!={cable.GlobalId,*(o['guid'] for o in obstacle_rows)}:
        raise ProjectError('obstacle-inclusive drawing requires complete physical element coverage')
    solid = next(r for r in cable.Representation.Representations if r.RepresentationIdentifier == 'Body').Items[0]
    frame = placement.get_local_placement(cable.ObjectPlacement) @ placement.get_axis2placement(solid.FirstOperand.Position)
    factor = unit.calculate_unit_scale(model)
    frame[:3, 3] *= factor
    centre = frame[:3, 3]
    points = np.vstack((quarter_points(frame, row['bend_radius_m']), row['world_axis_ends_m'][-1]))
    geometry = project_geometry(points, centre, row['bend_radius_m'], config['projection_axes'])
    p = np.array(geometry['points_m'])
    c = geometry['centre_m']; radius = geometry['radius_m']; envelope = row['envelope_radius_m']
    height = config['annotation_height_m']
    doc = ezdxf.new('R2018'); doc.header['$INSUNITS'] = 6
    doc.appids.new('BSA_IFC')
    for layer, color in [('BSA_CABLE_AXIS', 4), ('BSA_CABLE_OUTLINE', 7), ('BSA_LABEL', 7), ('BSA_DIMENSION', 8)]:
        doc.layers.new(layer, dxfattribs={'color': color})
    if obstacle_rows:doc.layers.new('BSA_OBSTACLE',dxfattribs={'color':3})
    space = doc.modelspace()
    def tag(entity,guid=None):
        entity.set_xdata('BSA_IFC', [(1000, guid or cable.GlobalId)])
        return entity
    def line(a, b, layer):
        return tag(space.add_line(a, b, dxfattribs={'layer': layer}))
    def text(value, point,guid=None):
        return tag(space.add_text(value, dxfattribs={'height': height, 'insert': point, 'layer': 'BSA_LABEL'}),guid)
    for obstacle in obstacle_rows:
        x0,y0,x1,y1=obstacle['projected_bounds_m']
        corners=[[x0,y0],[x1,y0],[x1,y1],[x0,y1]]
        for a,b in zip(corners,corners[1:]+corners[:1]):
            tag(space.add_line(a,b,dxfattribs={'layer':'BSA_OBSTACLE'}),obstacle['guid'])
    for r, layer in [(radius, 'BSA_CABLE_AXIS'), (radius-envelope, 'BSA_CABLE_OUTLINE'), (radius+envelope, 'BSA_CABLE_OUTLINE')]:
        tag(space.add_arc(c, r, geometry['start_angle_deg'], geometry['end_angle_deg'], dxfattribs={'layer': layer}))
    line(p[2], p[3], 'BSA_CABLE_AXIS')
    tangent = p[3]-p[2]; length = float(np.linalg.norm(tangent)); tangent /= length
    normal = np.array([-tangent[1], tangent[0]])
    for sign in (-1, 1):
        line(p[2]+sign*envelope*normal, p[3]+sign*envelope*normal, 'BSA_CABLE_OUTLINE')
    # Explicit LINE/TEXT dimension graphics, regenerated after model changes.
    offset = max(4*height, 3*envelope)
    a, b = p[2]+normal*offset, p[3]+normal*offset
    line(p[2], a+normal*height, 'BSA_DIMENSION'); line(p[3], b+normal*height, 'BSA_DIMENSION')
    line(a, b, 'BSA_DIMENSION')
    text(f'Straight L={length:.6f} m', (a+b)/2+normal*2*height)
    line(c, p[1], 'BSA_DIMENSION')
    top = float(p[:, 1].max()) + 5*height
    left = float(p[:, 0].min())
    notes = [f"{row['id']} / IFC {cable.GlobalId}",
             f"True total L={row['observed_length_m']:.6f} m; envelope OD={2*envelope:.6f} m",
             f'Quarter R={radius:.6f} m; angle=90 deg; arc L={radius*math.pi/2:.6f} m',
             f"{'/'.join(config['projection_axes'])} plane {geometry['plane_coordinate_m']:.6f} m; coordinates m",
             ('Cable and sourced boxes projected; depth intervals below; not an installation drawing' if obstacle_rows else 'Selected cable geometry only; other elements omitted; not an installation drawing')]
    for obstacle in obstacle_rows:
        low,high=obstacle['depth_interval_m']
        notes.append(f"Box {obstacle['id']}: {obstacle['depth_axis']}=[{low:.6f},{high:.6f}] m; projection is not a clash test")
    for i, note in enumerate(notes):
        guid=obstacle_rows[i-5]['guid'] if i>=5 else None
        text(note, [left, top+(len(notes)-i)*1.8*height],guid)
    out.mkdir(parents=True)
    path = out/'cable-route.dxf'; doc.saveas(path)
    reconcile(snapshot(doc), path)
    saved = ezdxf.readfile(path)
    axes = list(saved.modelspace().query('*[layer=="BSA_CABLE_AXIS"]'))
    if sorted(e.dxftype() for e in axes) != ['ARC', 'LINE'] or saved.header['$INSUNITS'] != 6:
        raise ProjectError('saved cable axis/units coverage failed')
    from .ifc_native import identity
    if identity(doc) != identity(saved):raise ProjectError('saved IFC identity failed')
    if any(not Path(p).is_file() or digest(Path(p)) != sha for p, sha in before.items()):
        raise ProjectError('cable drawing input changed')
    included=[cable.GlobalId,*(o['guid'] for o in obstacle_rows)]
    omitted=sorted(physical-set(included))
    report = dict(inputs=before, settings=config, cable=row, geometry=geometry, straight_length_m=length,
                  included_guids=included, omitted_guids=omitted, obstacles=obstacle_rows,saved_dxf_sha256=digest(path),
                  saved_identity_and_geometry_pass=True, design_accepted=False,
                  scope='Single cable planar true arc/straight and envelope OD with explicitly selected source-box projections; depth intervals do not prove clearance; LINE/TEXT dimensions are not associative; installation and engineering review pending')
    (out/'drawing.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    for key in ('ifc', 'binding', 'settings', 'out'):parser.add_argument('--'+key, type=Path, required=True)
    parser.add_argument('--obstacles',type=Path)
    print(json.dumps(run(**vars(parser.parse_args()))['saved_identity_and_geometry_pass']))

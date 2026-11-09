"""Saved native tangent quarter/straight union trial; synthetic geometry only."""
import argparse
import json
import math
from pathlib import Path

import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.geom
import ifcopenshell.validate
import numpy as np

from bsa.cad_ifc import mesh_properties, compare
from bsa.circular_geometry import configure, BOUNDS_TOLERANCE_M, VOLUME_RELATIVE_TOLERANCE
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.three_phase import ROOT
from bsa.cable_continuity import inspect as inspect_continuity
from probe_cable_revolution import run as quarter


def run(out):
    out = Path(out).resolve()
    if not out.is_relative_to(ROOT) or out.exists():
        raise ProjectError('new repository output required')
    quarter(out / 'quarter')
    model = ifcopenshell.open(str(out / 'quarter/quarter-cable.ifc'))
    cable = model.by_type('IfcCableSegment')[0]
    rep = cable.Representation.Representations[0]
    point = lambda xyz: model.create_entity('IfcCartesianPoint', Coordinates=xyz)
    direction = lambda xyz: model.create_entity('IfcDirection', DirectionRatios=xyz)
    profile = model.create_entity('IfcCircleProfileDef', ProfileType='AREA', Radius=.01)
    frame = model.create_entity('IfcAxis2Placement3D', Location=point((0., 0., -.3)),
                                Axis=direction((-1., 0., 0.)), RefDirection=direction((0., 1., 0.)))
    straight = model.create_entity('IfcExtrudedAreaSolid', SweptArea=profile, Position=frame,
                                  ExtrudedDirection=direction((0., 0., 1.)), Depth=2.)
    result = api.run('geometry.add_boolean', model, first_item=rep.Items[0],
                     second_items=[straight], operator='UNION')
    if len(result) != 1:
        raise ProjectError('one native union required')
    # 0.8.5 has no validate_csg helper; set the standard representation explicitly.
    rep.Items = [result[0]]
    rep.RepresentationType = 'CSG'
    arc_points = [[.3, 0., 0.], [.3/math.sqrt(2), 0., -.3/math.sqrt(2)], [0., 0., -.3]]
    arc_curve = model.create_entity('IfcIndexedPolyCurve',
        Points=model.create_entity('IfcCartesianPointList3D', CoordList=arc_points),
        Segments=[model.create_entity('IfcArcIndex', (1, 2, 3))], SelfIntersect=False)
    line_curve = model.create_entity('IfcPolyline', Points=[point((0., 0., -.3)), point((-2., 0., -.3))])
    composite = model.create_entity('IfcCompositeCurve', SelfIntersect=False, Segments=[
        model.create_entity('IfcCompositeCurveSegment', Transition='CONTSAMEGRADIENT', SameSense=True, ParentCurve=arc_curve),
        model.create_entity('IfcCompositeCurveSegment', Transition='DISCONTINUOUS', SameSense=True, ParentCurve=line_curve)])
    context = api.run('context.add_context', model, context_type='Model', context_identifier='Axis',
                      target_view='GRAPH_VIEW', parent=model.by_type('IfcGeometricRepresentationContext', include_subtypes=False)[0])
    axis_rep = model.create_entity('IfcShapeRepresentation', ContextOfItems=context,
        RepresentationIdentifier='Axis', RepresentationType='Curve3D', Items=[composite])
    api.run('geometry.assign_representation', model, product=cable, representation=axis_rep)
    path = out / 'continuous-cable.ifc'
    model.write(str(path))
    saved = ifcopenshell.open(str(path))
    logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(saved, logger, express_rules=True)
    if logger.statements:
        raise ProjectError(str(logger.statements[:2]))
    saved_cable = saved.by_guid(cable.GlobalId)
    reps = {r.RepresentationIdentifier: r for r in saved_cable.Representation.Representations}
    correspondence = inspect_continuity(reps['Body'].Items[0], reps['Axis'].Items[0], np.eye(4), 1., 1.)
    settings = ifcopenshell.geom.settings()
    settings.set('use-world-coords', True)
    configure(settings)
    shape = ifcopenshell.geom.create_shape(settings, saved.by_guid(cable.GlobalId))
    actual = mesh_properties(np.array(shape.geometry.verts).reshape(-1, 3),
                             np.array(shape.geometry.faces).reshape(-1, 3))
    arc = .3 * math.pi / 2
    k = (.3 + .01**2 / (4 * .3)) * 2 / math.pi
    expected = dict(volume=math.pi * .01**2 * (arc + 2),
                    bounds=np.array([[-2., -.01, -.31], [.31, .01, 0.]]),
                    centroid=(arc * np.array([k, 0., -k]) + 2 * np.array([-1., 0., -.3])) / (arc + 2))
    checks = compare(actual, expected, BOUNDS_TOLERANCE_M, VOLUME_RELATIVE_TOLERANCE)
    if not math.isclose(correspondence['length'], arc + 2, abs_tol=1e-10):
        raise ProjectError('composite true length mismatch')
    checks.update({'axis_' + key: value for key, value in compare(actual, correspondence['expected'], BOUNDS_TOLERANCE_M, VOLUME_RELATIVE_TOLERANCE).items()})
    report = dict(scope='Synthetic tangent quarter plus straight envelope and independent composite Axis; no ports, electrical binding or installation acceptance',
                  inputs_kind='assumption', schema_express_pass=True, single_connected_native_mesh_pass=True,
                  analytic_length_m=arc + 2, checks=checks, ifc_sha256=digest(path),
                  probe_sha256=digest(Path(__file__)), design_accepted=False,
                  actual={k: v.tolist() if isinstance(v, np.ndarray) else v for k, v in actual.items()})
    (out / 'probe.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    if not all(checks.values()):
        raise ProjectError('saved union does not match independent analytic geometry')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    print(json.dumps(run(parser.parse_args().out), indent=2))

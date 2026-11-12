"""Read standard saved circular hollow extrusions and their actual owned cap frames."""
import math

import ifcopenshell.util.placement as placement
import ifcopenshell.util.system as system
import ifcopenshell.util.unit as unit
import numpy as np

from .engine import ProjectError
from .product_alignment import aligned_placement


def straight_wall(obj):
    if obj.is_a() not in ('IfcDuctSegment','IfcPipeSegment') or obj.file.schema!='IFC4' or not math.isclose(unit.calculate_unit_scale(obj.file),1.,rel_tol=0,abs_tol=1e-12):
        raise ProjectError('Saved IFC4 metre circular pipe/duct wall required')
    bodies=[r for r in obj.Representation.Representations if r.RepresentationIdentifier=='Body'] if obj.Representation else []
    if len(bodies)!=1 or len(bodies[0].Items)!=1 or not bodies[0].Items[0].is_a('IfcExtrudedAreaSolid'):
        raise ProjectError('One native straight hollow extrusion required')
    solid=bodies[0].Items[0];profile=solid.SweptArea
    if not profile.is_a('IfcCircleHollowProfileDef') or profile.Position is not None:
        raise ProjectError('Centred native hollow circle required')
    outer=2*profile.Radius;inner=2*(profile.Radius-profile.WallThickness)
    if not all(math.isfinite(x) for x in (outer,inner,solid.Depth)) or not 0<inner<outer or solid.Depth<=0:
        raise ProjectError('Positive native wall bore, gauge and depth required')
    matrix=placement.get_local_placement(obj.ObjectPlacement)@placement.get_axis2placement(solid.Position)
    aligned_placement(matrix,np.eye(4),0)
    direction=np.asarray(solid.ExtrudedDirection.DirectionRatios,dtype=float)
    if direction.shape!=(3,) or not np.isfinite(direction).all() or not math.isclose(float(np.linalg.norm(direction)),1.,rel_tol=0,abs_tol=1e-9):
        raise ProjectError('Unit finite native extrusion direction required')
    axis=matrix[:3,:3]@direction;caps=[(matrix[:3,3],-axis),(matrix[:3,3]+solid.Depth*axis,axis)]
    native=system.get_ports(obj)
    if len(native)!=2 or {p.FlowDirection for p in native}!={'SINK','SOURCE'}:
        raise ProjectError('Exactly one directed inlet and outlet required')
    records={};used=set()
    for port in native:
        frame=placement.get_local_placement(port.ObjectPlacement);aligned_placement(frame,np.eye(4),0)
        matches=[i for i,(point,normal) in enumerate(caps) if np.allclose(frame[:3,3],point,atol=1e-8,rtol=0) and np.allclose(frame[:3,2],normal,atol=1e-8,rtol=0)]
        if len(matches)!=1 or matches[0] in used or system.get_port_element(port)!=obj:
            raise ProjectError('Owned port position/normal must cover each true native wall cap once')
        used.add(matches[0]);records[port.GlobalId]=dict(point_m=frame[:3,3].tolist(),outward_axis=frame[:3,2].tolist(),frame=frame.tolist(),direction=port.FlowDirection)
    return dict(length_m=solid.Depth,inner_m=inner,outer_m=outer,ports=records)

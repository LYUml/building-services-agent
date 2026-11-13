"""Native rectangular quarter-bend quantities for explicit source-table queries."""
import math
import numpy as np
import ifcopenshell.util.placement as placement
import ifcopenshell.util.system as system
from .circular_elbow import saved_arc_length

QUANTITIES={'bend_radius_over_radial_width','bend_height_over_radial_width','bend_angle_deg',
    'bend_centerline_radius_m','bend_centerline_arc_length_m','bend_radial_internal_width_m',
    'bend_normal_internal_height_m','bend_hydraulic_diameter_m','bend_hydraulic_reynolds'}


def calculate(obj,inlet_name,outlet_name,flow_m3_s,air):
    if not obj.is_a('IfcDuctFitting') or obj.PredefinedType!='BEND':raise ValueError('Supported native rectangular BEND required')
    bodies=[r for r in obj.Representation.Representations if r.RepresentationIdentifier=='Body']
    if len(bodies)!=1 or len(bodies[0].Items)!=1:raise ValueError('One native rectangular bend body required')
    body=bodies[0].Items[0]
    if not body.is_a('IfcRevolvedAreaSolid') or not body.SweptArea.is_a('IfcRectangleHollowProfileDef') or not math.isclose(body.Angle,math.pi/2,abs_tol=1e-10,rel_tol=0):raise ValueError('Native hollow rectangular quarter revolution required')
    p=body.SweptArea;t=p.WallThickness;w=p.XDim-2*t;h=p.YDim-2*t
    if p.Position is None or len(p.Position.Location.Coordinates)!=2:raise ValueError('Explicit native bend profile radius offset required')
    r,y=p.Position.Location.Coordinates
    if any(not math.isfinite(v) or v<=0 for v in (t,w,h,r)) or r<=p.XDim/2 or abs(y)>1e-10 or p.Position.RefDirection is not None and not np.allclose(p.Position.RefDirection.DirectionRatios,[1,0],atol=1e-10,rtol=0) or any(v not in (None,0) for v in (p.InnerFilletRadius,p.OuterFilletRadius)):raise ValueError('Supported sharp-corner section and positive smooth bend radius required')
    expected=np.array([[1,0,0,0],[0,0,-1,0],[0,1,0,0],[0,0,0,1]])
    if not np.allclose(placement.get_axis2placement(body.Position),expected,atol=1e-10,rtol=0) or tuple(body.Axis.Location.Coordinates)!=(0.,0.,0.) or tuple(body.Axis.Axis.DirectionRatios)!=(0.,1.,0.):raise ValueError('Native rectangular radial/normal revolution convention differs')
    length,ends,arc_r=saved_arc_length(obj)
    if not math.isclose(r,arc_r,abs_tol=1e-9,rel_tol=0) or not math.isclose(length,math.pi*r/2,abs_tol=1e-9,rel_tol=0):raise ValueError('Native solid radius and independent circular Axis differ')
    ports={p.Name:p for p in system.get_ports(obj)}
    if len(ports)!=2 or set(ports)!={inlet_name,outlet_name} or ports[inlet_name].FlowDirection!='SINK' or ports[outlet_name].FlowDirection!='SOURCE':raise ValueError('One owned directed native bend flow path required')
    frames=[placement.get_local_placement(ports[n].ObjectPlacement) for n in (inlet_name,outlet_name)]
    if any(min(np.linalg.norm(f[:3,3]-np.array(point)) for point in ends)>1e-8 for f in frames) or np.allclose(frames[0][:3,3],frames[1][:3,3],atol=1e-8,rtol=0):raise ValueError('Native bend port end planes differ from circular Axis')
    a,b=-frames[0][:3,2],frames[1][:3,2];angle=math.degrees(math.atan2(np.linalg.norm(np.cross(a,b)),np.dot(a,b)))
    if not math.isclose(angle,90,abs_tol=1e-8,rel_tol=0):raise ValueError('Bend saved flow axes are not a quarter turn')
    if type(flow_m3_s) not in (int,float) or not math.isfinite(flow_m3_s) or flow_m3_s<=0 or any(type(air.get(k)) not in (int,float) or not math.isfinite(air[k]) or air[k]<=0 for k in ('density_kg_m3','viscosity_Pa_s')):raise ValueError('Positive source flow/density/viscosity required')
    dh=2*w*h/(w+h);velocity=flow_m3_s/(w*h);re=air['density_kg_m3']*velocity*dh/air['viscosity_Pa_s']
    quantities=dict(bend_radius_over_radial_width=r/w,bend_height_over_radial_width=h/w,bend_angle_deg=math.degrees(body.Angle),bend_centerline_radius_m=r,bend_centerline_arc_length_m=length,bend_radial_internal_width_m=w,bend_normal_internal_height_m=h,bend_hydraulic_diameter_m=dh,bend_hydraulic_reynolds=re)
    if any(not math.isfinite(v) or v<=0 for v in quantities.values()):raise ValueError('Finite positive native bend quantities required')
    return dict(quantities=quantities,inlet_section_m=[w,h],outlet_section_m=[w,h],construction='Native smooth quarter-revolved hollow rectangular profile; no vanes represented',reynolds_basis='Source design flow and air properties; actual clear area velocity and hydraulic diameter 4A/P. Source-correlation applicability remains review-required.',scope='Native dimensions/Axis/port correspondence after full producer inspection; not a loss correlation, fabricated product or measured installation acceptance')

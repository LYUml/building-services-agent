"""Read the scoped centred ruled-loft CSG family; not fitting-loss acceptance."""
import math
import numpy as np
from ifcopenshell.util import placement,system
from ifcopenshell.util.unit import calculate_unit_scale


def _normal(position):
    value=np.array(position.Axis.DirectionRatios if position.Axis else [0.,0.,1.])
    if value.shape!=(3,) or not np.isfinite(value).all() or np.linalg.norm(value)==0:raise ValueError('Finite nonzero native surface axis required')
    return value/np.linalg.norm(value)


def _operand(solid):
    if not solid.is_a('IfcAdvancedBrep'):raise ValueError('Analytic positive loft operand required')
    points=[];planes=[];cylinders=[];ruled=[]
    for face in solid.Outer.CfsFaces:
        vertices=[]
        for bound in face.Bounds:
            if not bound.Bound.is_a('IfcEdgeLoop'):raise ValueError('Native edge loops required')
            for edge in bound.Bound.EdgeList:
                for vertex in [edge.EdgeElement.EdgeStart,edge.EdgeElement.EdgeEnd]:
                    if not vertex.is_a('IfcVertexPoint') or not vertex.VertexGeometry.is_a('IfcCartesianPoint'):raise ValueError('Explicit native vertex coordinates required')
                    vertices.append(vertex.VertexGeometry.Coordinates)
        values=np.asarray(vertices,dtype=float)
        if values.ndim!=2 or values.shape[1]!=3 or not np.isfinite(values).all():raise ValueError('Finite native loft vertices required')
        points.extend(vertices);surface=face.FaceSurface
        if surface.is_a('IfcPlane'):
            normal=_normal(surface.Position)
            if np.max(abs((values-np.array(surface.Position.Location.Coordinates))@normal))>1e-10:raise ValueError('Plane geometry differs from its native loop')
            if np.ptp(values[:,2])>1e-8:planes.append(values)
        elif surface.is_a('IfcCylindricalSurface'):
            normal=_normal(surface.Position)
            if abs(abs(normal[2])-1)>1e-10 or np.linalg.norm(np.array(surface.Position.Location.Coordinates)[:2])>1e-10:raise ValueError('Centred coaxial cylindrical collar required')
            cylinders.append((float(surface.Radius),float(values[:,2].min()),float(values[:,2].max())))
        elif surface.is_a('IfcBSplineSurfaceWithKnots'):
            if surface.VDegree!=1 or any(len(row)!=2 for row in surface.ControlPointsList):raise ValueError('Axially ruled degree-one loft required')
            ruled.append(np.array([[p.Coordinates for p in row] for row in surface.ControlPointsList]))
        else:raise ValueError('Unsupported native loft surface')
    if not planes or not cylinders or not ruled:raise ValueError('Rectangle collar, ruled taper and circular collar required')
    radius=cylinders[0][0];taper_end=min(r[1] for r in cylinders);end=max(r[2] for r in cylinders)
    if not math.isfinite(radius) or radius<=0 or taper_end<=0 or end<=taper_end or any(not math.isfinite(r[0]) or abs(r[0]-radius)>1e-10 or abs(r[1]-taper_end)>1e-10 or abs(r[2]-end)>1e-10 for r in cylinders):raise ValueError('One coaxial round collar required')
    entry_start=min(float(v[:,2].min()) for v in planes)
    if entry_start>=0 or any(abs(v[:,2].max())>1e-10 for v in planes):raise ValueError('Rectangle collar must end at native taper station zero')
    for control in ruled:
        if not np.isfinite(control).all() or any(not np.allclose(sorted(pair[:,2]),[0,taper_end],atol=1e-10,rtol=0) for pair in control):raise ValueError('Native ruled taper stations differ')
    allpoints=np.array(points);ring=allpoints[abs(allpoints[:,2]-entry_start)<1e-10,:2]
    lo,hi=ring.min(axis=0),ring.max(axis=0)
    if not np.allclose(lo,-hi,atol=1e-10,rtol=0) or np.any(hi<=0):raise ValueError('Centred rectangle required')
    for x in [-hi[0],hi[0]]:
        for y in [-hi[1],hi[1]]:
            if np.min(np.linalg.norm(ring-[x,y],axis=1))>1e-10:raise ValueError('Native rectangle corners missing')
    return dict(width_m=2*float(hi[0]),height_m=2*float(hi[1]),radius_m=radius,
        rectangle_start_m=entry_start,taper_length_m=taper_end,end_m=end)


def calculate(obj,flow_m3_s,air):
    model=obj.file
    projects=model.by_type('IfcProject')
    units=projects[0].UnitsInContext.Units if len(projects)==1 and projects[0].UnitsInContext else []
    if model.schema!='IFC4' or len(projects)!=1 or sum(getattr(u,'UnitType',None)=='LENGTHUNIT' for u in units)!=1 or not math.isclose(calculate_unit_scale(model),1.,abs_tol=1e-12,rel_tol=0):raise ValueError('One explicit metre IFC4 project required')
    if not obj.is_a('IfcDuctFitting') or obj.PredefinedType!='TRANSITION':raise ValueError('Native transition required')
    reps=[r for r in obj.Representation.Representations if r.RepresentationIdentifier=='Body']
    if len(reps)!=1 or len(reps[0].Items)!=1:raise ValueError('One native body required')
    item=reps[0].Items[0]
    if item.is_a('IfcMappedItem'):
        if not np.allclose(placement.get_mappeditem_transformation(item),np.eye(4),atol=1e-10,rtol=0):raise ValueError('Only identity local representation mapping supported')
        items=item.MappingSource.MappedRepresentation.Items
        if len(items)!=1:raise ValueError('One mapped native body required')
        item=items[0]
    if not item.is_a('IfcBooleanResult') or item.Operator!='DIFFERENCE':raise ValueError('Native outer-minus-inner loft required')
    outer,inner=[_operand(s) for s in [item.FirstOperand,item.SecondOperand]]
    t=outer['radius_m']-inner['radius_m']
    if t<=0 or not math.isclose(outer['width_m']-inner['width_m'],2*t,abs_tol=1e-10) or not math.isclose(outer['height_m']-inner['height_m'],2*t,abs_tol=1e-10) or not math.isclose(outer['taper_length_m'],inner['taper_length_m'],abs_tol=1e-10):raise ValueError('Consistent section-plane-offset wall required')
    if inner['rectangle_start_m']>outer['rectangle_start_m']+1e-10 or inner['end_m']<outer['end_m']-1e-10:raise ValueError('Inner bore must span both wall caps')
    ports=system.get_ports(obj)
    if len(ports)!=2 or {p.FlowDirection for p in ports}!={'SINK','SOURCE'}:raise ValueError('One directed rectangle-to-circle path required')
    frame=placement.get_local_placement(obj.ObjectPlacement)
    for port in ports:
        local=np.linalg.inv(frame)@placement.get_local_placement(port.ObjectPlacement)
        inlet=port.FlowDirection=='SINK';z=outer['rectangle_start_m'] if inlet else outer['end_m']
        if not np.allclose(local[:3,3],[0,0,z],atol=1e-9,rtol=0) or not np.allclose(local[:3,2],[0,0,-1 if inlet else 1],atol=1e-9,rtol=0):raise ValueError('Native owned port station/direction differs')
    w,h,D,L=inner['width_m'],inner['height_m'],2*inner['radius_m'],inner['taper_length_m']
    values=[flow_m3_s,air['density_kg_m3'],air['viscosity_Pa_s']]
    if any(type(x) not in (int,float) or not math.isfinite(x) or x<=0 for x in values):raise ValueError('Finite positive prescribed flow and air properties required')
    area=math.pi*D*D/4;ratio=area/(w*h);velocity=flow_m3_s/area
    Re=air['density_kg_m3']*velocity*D/air['viscosity_Pa_s']
    return dict(width_m=w,height_m=h,diameter_m=D,taper_length_m=L,
        start_collar_m=-outer['rectangle_start_m'],end_collar_m=outer['end_m']-L,
        source_quantities=dict(Re_divided_by_1e4=Re*1e-4,L_over_D=L/D,B=(w/h)*ratio**2,outlet_to_inlet_area_ratio=ratio),
        reference_velocity_m_s=velocity,reference_velocity_pressure_Pa=air['density_kg_m3']*velocity**2/2,
        source_family_conditions=dict(H_less_than_D=h<D,contraction=ratio<1,rectangle_width_not_less_than_height=w>=h),
        scope='Parameters of the supported native centred ruled-loft CSG family only; mesh/material checks and physical source applicability remain separate',
        physical_applicability_verified=False)

"""Read supported saved sharp-tee profiles without assuming an equal branch."""
import copy
import math
import numpy as np
from ifcopenshell.util.placement import get_axis2placement, get_local_placement
from ifcopenshell.util.system import get_ports
from ifcopenshell.util.unit import calculate_unit_scale


def sections(obj, *, bullhead_area_sum=False):
    """Validate literal CSG and relative cap frames; return clear internal sizes.

    Default: equal/reduced branch. Explicit bullhead mode additionally requires
    a common branch inlet and equal main outlets whose areas sum to the inlet.
    Neither mode establishes source-correlation or product acceptance.
    """
    if not obj.is_a('IfcDuctFitting') or obj.PredefinedType!='JUNCTION':
        raise ValueError('Saved sharp rectangular junction required')
    if not math.isclose(calculate_unit_scale(obj.file),1.,abs_tol=1e-12,rel_tol=0):
        raise ValueError('Explicit metre model required; no implicit unit conversion')
    reps=obj.Representation.Representations
    if len(reps)!=1 or len(reps[0].Items)!=1:
        raise ValueError('Single saved CSG body required')
    wall=reps[0].Items[0]
    if not wall.is_a('IfcBooleanResult') or wall.Operator!='DIFFERENCE':
        raise ValueError('Outer-minus-inner sharp tee required')
    dims=[];solids=[]
    for union in (wall.FirstOperand,wall.SecondOperand):
        if not union.is_a('IfcBooleanResult') or union.Operator!='UNION':
            raise ValueError('Two rectangular prism unions required')
        pair=(union.FirstOperand,union.SecondOperand)
        for solid in pair:
            if not solid.is_a('IfcExtrudedAreaSolid') or not solid.SweptArea.is_a('IfcRectangleProfileDef'):
                raise ValueError('Literal rectangular extrusions required')
            if solid.SweptArea.Position is not None or tuple(solid.ExtrudedDirection.DirectionRatios)!=(0.,0.,1.):
                raise ValueError('Canonical rectangular profile and extrusion required')
            if any(not math.isfinite(x) or x<=0 for x in (solid.Depth,solid.SweptArea.XDim,solid.SweptArea.YDim)):
                raise ValueError('Positive finite dimensions required')
        solids.append(pair)
        dims.append([[s.SweptArea.XDim,s.SweptArea.YDim] for s in pair])
    outer,inner=np.asarray(dims[0]),np.asarray(dims[1])
    thickness=(outer-inner)/2
    if not (np.all(thickness>0) and np.allclose(thickness,thickness[0,0],atol=1e-10,rtol=0)):
        raise ValueError('Uniform positive main and branch wall thickness required')
    if type(bullhead_area_sum) is not bool:raise ValueError('Explicit boolean family selection required')
    if not bullhead_area_sum and np.any(inner[1]>inner[0]):raise ValueError('Only equal or reduced branch supported')
    length=solids[1][0].Depth/2;branch=solids[1][1].Depth
    if length<=inner[1,0]/2 or branch<=outer[0,0]/2:
        raise ValueError('Distinct unobstructed end caps required')
    def frame(origin,axis,reference):
        m=np.eye(4);m[:3,:3]=np.column_stack((reference,np.cross(axis,reference),axis));m[:3,3]=origin
        return m
    main=frame((0,0,-length),(0,0,1),(1,0,0))
    side=frame((0,0,0),(1,0,0),(0,0,-1))
    for pair in solids:
        for solid,expected,depth in zip(pair,(main,side),(2*length,branch)):
            if not math.isclose(solid.Depth,depth,abs_tol=1e-10,rel_tol=0) or not np.allclose(get_axis2placement(solid.Position),expected,atol=1e-10,rtol=0):
                raise ValueError('Literal prism frame or depth differs')
    ports=get_ports(obj)
    expected={'main-a':frame((0,0,-length),(0,0,-1),(1,0,0)),
              'main-b':frame((0,0,length),(0,0,1),(1,0,0)),
              'branch':frame((branch,0,0),(1,0,0),(0,0,-1))}
    if len(ports)!=3 or {p.Name for p in ports}!=set(expected):
        raise ValueError('Three unique named tee caps required')
    transform=get_local_placement(obj.ObjectPlacement)
    for port in ports:
        relative=np.linalg.solve(transform,get_local_placement(port.ObjectPlacement))
        if not np.allclose(relative,expected[port.Name],atol=1e-9,rtol=0):
            raise ValueError('Saved cap frame differs from literal prism end')
    if bullhead_area_sum:
        units=obj.file.by_type('IfcProject')
        if obj.file.schema!='IFC4' or len(units)!=1 or not units[0].UnitsInContext or len([u for u in units[0].UnitsInContext.Units if getattr(u,'UnitType',None)=='LENGTHUNIT'])!=1:
            raise ValueError('Explicit metre IFC4 project units required')
        if any(p.FlowDirection!=('SINK' if p.Name=='branch' else 'SOURCE') for p in ports):
            raise ValueError('Bullhead common inlet and two main outlets required')
        if not math.isclose(float(np.prod(inner[1])),2*float(np.prod(inner[0])),rel_tol=0,abs_tol=1e-12):
            raise ValueError('Common area must equal sum of equal outlet areas')
    return {p.GlobalId:inner[1 if p.Name=='branch' else 0].tolist() for p in ports}


def canonical_case(model,case,product_guids):
    """Reconcile literal sections against independent material-cap analysis."""
    if not isinstance(product_guids,list) or not product_guids or len(set(product_guids))!=len(product_guids):
        raise ValueError('Explicit unique supported tee selection required')
    result=copy.deepcopy(case)
    for guid in product_guids:
        obj=model.by_guid(guid)
        for guid,(w,h) in sections(obj).items():
            row=result['port_flows'][guid]
            if row['owner_guid']!=obj.GlobalId or not np.allclose([w,h],[row['width_m'],row['height_m']],atol=1e-8,rtol=0):
                raise ValueError('Literal tee section differs from recovered material cap')
            q=row['flow_m3_s'];rho=result['air']['density_kg_m3']
            if any(type(x) not in (int,float) or not math.isfinite(x) or x<=0 for x in (q,rho)):
                raise ValueError('Positive finite source flow and density required')
            row.update(width_m=w,height_m=h,actual_velocity_m_s=q/(w*h),actual_velocity_pressure_Pa=rho*(q/(w*h))**2/2)
    return result

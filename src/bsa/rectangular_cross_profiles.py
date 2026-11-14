"""Native constant-height equal/reduced-branch cross; no loss acceptance."""
import math
import numpy as np
from ifcopenshell.util import placement, system
from ifcopenshell.util.unit import calculate_unit_scale


def sections(obj):
    projects=obj.file.by_type('IfcProject')
    if obj.file.schema!='IFC4' or len(projects)!=1 or not projects[0].UnitsInContext or len([u for u in projects[0].UnitsInContext.Units if getattr(u,'UnitType',None)=='LENGTHUNIT'])!=1 or calculate_unit_scale(obj.file)!=1:
        raise ValueError('Explicit metre IFC4 required')
    if not obj.is_a('IfcDuctFitting') or obj.PredefinedType!='JUNCTION':raise ValueError('Native junction required')
    reps=obj.Representation.Representations if obj.Representation else []
    if len(reps)!=1 or len(reps[0].Items)!=1:raise ValueError('Single cross body required')
    wall=reps[0].Items[0]
    if not wall.is_a('IfcBooleanResult') or wall.Operator!='DIFFERENCE':raise ValueError('Outer-minus-inner cross required')
    solids=[];dims=[]
    for union in [wall.FirstOperand,wall.SecondOperand]:
        if not union.is_a('IfcBooleanResult') or union.Operator!='UNION':raise ValueError('Two full prism union required')
        pair=[union.FirstOperand,union.SecondOperand]
        for s in pair:
            if not s.is_a('IfcExtrudedAreaSolid') or not s.SweptArea.is_a('IfcRectangleProfileDef') or s.SweptArea.Position is not None or tuple(s.ExtrudedDirection.DirectionRatios)!=(0.,0.,1.):raise ValueError('Canonical rectangular extrusion required')
            if any(not math.isfinite(v) or v<=0 for v in [s.Depth,s.SweptArea.XDim,s.SweptArea.YDim]):raise ValueError('Positive finite prism required')
        solids.append(pair);dims.append([[s.SweptArea.XDim,s.SweptArea.YDim] for s in pair])
    outer,inner=map(np.asarray,dims);g=(outer-inner)/2
    if not np.all(g>0) or not np.allclose(g,g[0,0],atol=1e-12,rtol=0):raise ValueError('Uniform positive wall offset required')
    if inner[1,0]>inner[0,0] or not math.isclose(inner[0,1],inner[1,1],abs_tol=1e-12,rel_tol=0):raise ValueError('Constant-height equal/reduced branch required')
    L,B=[s.Depth/2 for s in solids[1]]
    if L<=outer[1,0]/2 or B<=outer[0,0]/2:raise ValueError('Unobstructed cap planes required')
    def frame(point,axis,x):
        m=np.eye(4);m[:3,:3]=np.column_stack([x,np.cross(axis,x),axis]);m[:3,3]=point;return m
    native=[frame([0,0,-L],[0,0,1],[1,0,0]),frame([-B,0,0],[1,0,0],[0,0,-1])]
    for pair in solids:
        for s,f,depth in zip(pair,native,[2*L,2*B]):
            if abs(s.Depth-depth)>1e-12 or not np.allclose(placement.get_axis2placement(s.Position),f,atol=1e-12,rtol=0):raise ValueError('Native cross prism frame differs')
    expected={'main-a':frame([0,0,-L],[0,0,-1],[1,0,0]),'main-b':frame([0,0,L],[0,0,1],[1,0,0]),'branch-a':frame([-B,0,0],[-1,0,0],[0,0,1]),'branch-b':frame([B,0,0],[1,0,0],[0,0,-1])}
    ports=system.get_ports(obj);world=placement.get_local_placement(obj.ObjectPlacement)
    if len(ports)!=4 or {p.Name for p in ports}!=set(expected):raise ValueError('Four unique owned cross caps required')
    for p in ports:
        if not np.allclose(placement.get_local_placement(p.ObjectPlacement),world@expected[p.Name],atol=1e-9,rtol=0):raise ValueError('Native cap frame differs')
    ins=[p for p in ports if p.FlowDirection=='SINK']
    if len(ins)!=1 or not ins[0].Name.startswith('main-') or any(p.FlowDirection!='SOURCE' for p in ports if p!=ins[0]):raise ValueError('One main inlet and three outlets required')
    return {p.GlobalId:inner[1 if p.Name.startswith('branch') else 0].tolist() for p in ports}

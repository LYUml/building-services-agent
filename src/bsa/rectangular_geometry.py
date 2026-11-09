"""Explicit axis-aligned sharp-corner rectangular hollow duct walls."""
import math
from .engine import ProjectError
from . import circular_geometry as circular

WALL='straight rectangular duct wall'
SCOPE='axis-aligned envelopes and explicit rectangular duct walls'


def face_frame(device,port_id):
    """Source cross-section width/height directions and outward end normal."""
    import numpy as np
    from . import rectangular_elbow
    if device.get('body_shape')==rectangular_elbow.WALL:
        s=rectangular_elbow.specification(device);normal=np.array(s['normals'][port_id])
        u,v,n=[s['matrix'][:3,i] for i in range(3)]
        width=u if np.allclose(normal,-v,atol=1e-8,rtol=0) else v
        return np.column_stack((width,n,normal))
    s=specification(device)
    return np.column_stack((s['matrix'][:3,0],s['matrix'][:3,1],s['normals'][port_id]))


def specification(device):
    import numpy as np
    if device.get('ifc_class')!='IfcDuctSegment':raise ProjectError('rectangular wall requires IfcDuctSegment')
    props=device.get('properties',{});values=[props.get(k) for k in ('InternalWidth_m','InternalHeight_m','WallThickness_m')]
    if any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in values):raise ProjectError('positive sourced internal width/height and wall thickness required')
    width,height,thickness=values;ports=device.get('ports',[])
    if len(ports)!=2 or {p['direction'] for p in ports} not in ({'SOURCE','SINK'},{'SOURCEANDSINK'}):raise ProjectError('rectangular wall requires two directed or bidirectional end ports')
    a,b=[p['offset_m'] for p in ports];axes=[i for i in range(3) if abs(a[i]-b[i])>1e-8]
    if len(axes)!=1:raise ProjectError('rectangular wall requires one straight axis')
    axis=axes[0];normal=np.eye(3)[axis];matrix=circular.frame(normal)
    transverse=[int(np.argmax(abs(matrix[:3,i]))) for i in (0,1)]
    size=device['size_m'];outer=[width+2*thickness,height+2*thickness]
    if any(not math.isclose(size[i],v,abs_tol=1e-8,rel_tol=0) for i,v in zip(transverse,outer)):raise ProjectError('rectangular envelope differs from explicit section')
    normals={}
    for port in ports:
        point=port['offset_m']
        if any(abs(point[i]-size[i]/2)>1e-8 for i in transverse) or min(abs(point[axis]),abs(point[axis]-size[axis]))>1e-8:raise ProjectError('rectangular ports must be opposite end-face centres')
        n=[0.,0.,0.];n[axis]=-1. if abs(point[axis])<1e-8 else 1.;normals[port['id']]=n
    if {n[axis] for n in normals.values()}!={-1.,1.}:raise ProjectError('rectangular ports must span full wall')
    centre=np.array(device['origin_m'],dtype=float)
    for i in transverse:centre[i]+=size[i]/2
    matrix[:3,3]=centre
    return dict(width=width,height=height,thickness=thickness,outer=outer,length=size[axis],matrix=matrix,normals=normals,
        volume=(outer[0]*outer[1]-width*height)*size[axis])


def author(model,context,obj,device):
    import ifcopenshell.api as api
    s=specification(device)
    profile=model.create_entity('IfcRectangleHollowProfileDef',ProfileType='AREA',XDim=float(s['outer'][0]),YDim=float(s['outer'][1]),WallThickness=float(s['thickness']))
    position=model.create_entity('IfcAxis2Placement3D',Location=model.create_entity('IfcCartesianPoint',Coordinates=(0.,0.,0.)))
    solid=model.create_entity('IfcExtrudedAreaSolid',SweptArea=profile,Position=position,ExtrudedDirection=model.create_entity('IfcDirection',DirectionRatios=(0.,0.,1.)),Depth=float(s['length']))
    representation=model.create_entity('IfcShapeRepresentation',ContextOfItems=context,RepresentationIdentifier='Body',RepresentationType='SweptSolid',Items=[solid])
    api.run('geometry.assign_representation',model,product=obj,representation=representation)
    api.run('geometry.edit_object_placement',model,product=obj,matrix=s['matrix'],is_si=True)


def verify(obj,device,shape):
    import numpy as np
    import ifcopenshell.util.placement as placement
    import ifcopenshell.util.element as element
    from .cad_ifc import mesh_properties
    s=specification(device);bodies=[r for r in obj.Representation.Representations if r.RepresentationIdentifier=='Body']
    if len(bodies)!=1 or bodies[0].RepresentationType!='SweptSolid' or len(bodies[0].Items)!=1:raise ProjectError('one rectangular swept wall required')
    solid=bodies[0].Items[0]
    if not solid.is_a('IfcExtrudedAreaSolid') or not solid.SweptArea.is_a('IfcRectangleHollowProfileDef'):raise ProjectError('rectangular hollow profile required')
    p=solid.SweptArea
    metadata=element.get_psets(obj).get('BSA_DesignInputs',{})
    for key,value in (('InternalWidth_m',s['width']),('InternalHeight_m',s['height']),('WallThickness_m',s['thickness'])):
        if type(metadata.get(key)) not in (int,float) or not math.isclose(metadata[key],value,rel_tol=0,abs_tol=1e-10):raise ProjectError('rectangular dimension metadata differs from source')
    for actual,expected in ((p.XDim,s['outer'][0]),(p.YDim,s['outer'][1]),(p.WallThickness,s['thickness']),(solid.Depth,s['length'])):
        if not math.isclose(actual,expected,rel_tol=0,abs_tol=1e-10):raise ProjectError('saved rectangular dimensions differ')
    if any(v not in (None,0.) for v in (p.InnerFilletRadius,p.OuterFilletRadius)):raise ProjectError('rounded rectangular corners unsupported')
    if p.Position is not None or not np.allclose(placement.get_axis2placement(solid.Position),np.eye(4),atol=1e-10,rtol=0) or tuple(solid.ExtrudedDirection.DirectionRatios)!=(0.,0.,1.):raise ProjectError('rectangular solid local placement/direction differs')
    if not np.allclose(placement.get_local_placement(obj.ObjectPlacement),s['matrix'],atol=1e-8,rtol=0):raise ProjectError('rectangular wall world placement differs')
    v=np.array(shape.geometry.verts).reshape(-1,3);f=np.array(shape.geometry.faces).reshape(-1,3)
    volume,relative,euler=circular.verify_closed_wall(v,f,s['volume']);actual=mesh_properties(v,f)
    expected_centre=np.array(device['origin_m'])+np.array(device['size_m'])/2
    if not np.allclose(actual['centroid'],expected_centre,atol=2e-5,rtol=0):raise ProjectError('rectangular wall centroid differs')
    return dict(body_shape=WALL,saved_internal_width_m=p.XDim-2*p.WallThickness,saved_internal_height_m=p.YDim-2*p.WallThickness,
        saved_wall_thickness_m=p.WallThickness,saved_length_m=solid.Depth,analytic_wall_volume_m3=s['volume'],mesh_wall_volume_m3=volume,
        relative_volume_error=relative,euler_characteristic=euler,closed_mesh=True,one_connected_wall=True)

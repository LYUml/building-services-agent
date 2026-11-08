"""Explicit straight circular IFC wall geometry, distinct from envelope boxes."""
from collections import Counter,defaultdict
import math
from .engine import ProjectError

WALL='straight circular wall'
MIXED_SCOPE='axis-aligned envelopes and explicit straight circular walls'
LINEAR_DEFLECTION_M=1e-5
ANGULAR_DEFLECTION=.02
BOUNDS_TOLERANCE_M=2e-5
VOLUME_RELATIVE_TOLERANCE=.001


def specification(device):
    if device.get('ifc_class') not in ('IfcPipeSegment','IfcDuctSegment'):
        raise ProjectError('circular walls require explicit pipe or duct segments')
    properties=device.get('properties',{})
    inner,outer=properties.get('InternalDiameter_m'),properties.get('OutsideDiameter_m')
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in (inner,outer)) or not 0<inner<outer:
        raise ProjectError('circular wall needs independently sourced 0 < internal < outside diameter')
    ports=device.get('ports',[])
    if len(ports)!=2 or {p['direction'] for p in ports} not in ({'SOURCE','SINK'},{'SOURCEANDSINK'}):
        raise ProjectError('circular wall requires directed ends or two explicit bidirectional ports')
    a,b=[p['offset_m'] for p in ports]
    axes=[i for i in range(3) if abs(a[i]-b[i])>1e-8]
    if len(axes)!=1:raise ProjectError('circular wall requires straight axis-aligned ports')
    axis=axes[0];size=device['size_m'];origin=device['origin_m']
    for i in range(3):
        if i!=axis and abs(size[i]-outer)>1e-8:raise ProjectError('circular outside diameter differs from transverse envelope')
    normals={}
    for port in ports:
        point=port['offset_m']
        if any(abs(point[i]-outer/2)>1e-8 for i in range(3) if i!=axis):raise ProjectError('circular ports must be end-face centres')
        if min(abs(point[axis]),abs(point[axis]-size[axis]))>1e-8:raise ProjectError('circular ports must span full wall length')
        normal=[0.,0.,0.];normal[axis]=-1. if abs(point[axis])<1e-8 else 1.
        normals[port['id']]=normal
    if {normal[axis] for normal in normals.values()}!={-1.,1.}:raise ProjectError('circular ports must occupy opposite ends')
    centre=[origin[i] if i==axis else origin[i]+outer/2 for i in range(3)]
    return dict(axis=axis,length_m=size[axis],inner_m=inner,outer_m=outer,start_centre_m=centre,normals=normals,
                volume_m3=math.pi*(outer**2-inner**2)*size[axis]/4)


def frame(normal):
    import numpy as np
    z=np.array(normal,dtype=float);x=np.array([0.,1.,0.]) if abs(z[0])>.5 else np.array([1.,0.,0.])
    result=np.eye(4);result[:3,:3]=np.column_stack((x,np.cross(z,x),z))
    return result


def configure(settings):
    settings.set('mesher-linear-deflection',LINEAR_DEFLECTION_M)
    settings.set('mesher-angular-deflection',ANGULAR_DEFLECTION)
    settings.set('weld-vertices',True)


def author(model,context,obj,device):
    import ifcopenshell.api as api
    spec=specification(device)
    profile=model.create_entity('IfcCircleHollowProfileDef',ProfileType='AREA',Radius=spec['outer_m']/2,
                                WallThickness=(spec['outer_m']-spec['inner_m'])/2)
    position=model.create_entity('IfcAxis2Placement3D',Location=model.create_entity('IfcCartesianPoint',Coordinates=(0.,0.,0.)))
    solid=model.create_entity('IfcExtrudedAreaSolid',SweptArea=profile,Position=position,
        ExtrudedDirection=model.create_entity('IfcDirection',DirectionRatios=(0.,0.,1.)),Depth=float(spec['length_m']))
    representation=model.create_entity('IfcShapeRepresentation',ContextOfItems=context,RepresentationIdentifier='Body',
                                        RepresentationType='SweptSolid',Items=[solid])
    api.run('geometry.assign_representation',model,product=obj,representation=representation)
    normal=[0.,0.,0.];normal[spec['axis']]=1.;matrix=frame(normal);matrix[:3,3]=spec['start_centre_m']
    api.run('geometry.edit_object_placement',model,product=obj,matrix=matrix,is_si=True)


def verify(obj,device,shape):
    import numpy as np
    import ifcopenshell.util.element as element
    spec=specification(device)
    bodies=[r for r in obj.Representation.Representations if r.RepresentationIdentifier=='Body']
    if len(bodies)!=1 or bodies[0].RepresentationType!='SweptSolid' or len(bodies[0].Items)!=1:
        raise ProjectError('saved circular wall must be one explicit swept-area solid')
    solid=bodies[0].Items[0]
    if not solid.is_a('IfcExtrudedAreaSolid') or not solid.SweptArea.is_a('IfcCircleHollowProfileDef'):
        raise ProjectError('saved circular wall lost its hollow profile')
    profile=solid.SweptArea
    if not math.isclose(profile.Radius,spec['outer_m']/2,abs_tol=1e-10) or not math.isclose(profile.WallThickness,(spec['outer_m']-spec['inner_m'])/2,abs_tol=1e-10) or not math.isclose(solid.Depth,spec['length_m'],abs_tol=1e-10):
        raise ProjectError('saved hollow profile radius/thickness/length mismatch')
    properties=element.get_psets(obj).get('BSA_DesignInputs',{})
    for key,expected in (('InternalDiameter_m',spec['inner_m']),('OutsideDiameter_m',spec['outer_m'])):
        value=properties.get(key)
        if type(value) not in (int,float) or not math.isclose(value,expected,abs_tol=1e-10):
            raise ProjectError('saved circular diameter metadata differs from profile/source')
    verts=np.array(shape.geometry.verts).reshape(-1,3);faces=np.array(shape.geometry.faces).reshape(-1,3)
    edges=Counter(tuple(sorted((int(a),int(b)))) for face in faces for a,b in zip(face,[face[1],face[2],face[0]]))
    if not edges or any(count!=2 for count in edges.values()):raise ProjectError('circular wall triangulation is not a closed two-manifold')
    directions=Counter();links=defaultdict(lambda:defaultdict(set));adjacency=defaultdict(set)
    for a,b,c in faces.tolist():
        if len({a,b,c})!=3:raise ProjectError('degenerate wall triangle')
        for v,u,w in ((a,b,c),(b,c,a),(c,a,b)):
            directions[(v,u)]+=1;links[v][u].add(w);links[v][w].add(u);adjacency[v].update((u,w))
    if any(directions[(a,b)]!=1 or directions[(b,a)]!=1 for a,b in edges):raise ProjectError('wall mesh winding mismatch')
    def connected(graph):
        stack=[next(iter(graph))];seen=set()
        while stack:
            v=stack.pop()
            if v not in seen:seen.add(v);stack.extend(graph[v]-seen)
        return len(seen)==len(graph)
    if not connected(adjacency) or any(any(len(neighbours)!=2 for neighbours in graph.values()) or not connected(graph) for graph in links.values()):
        raise ProjectError('wall mesh is disconnected or has a nonmanifold vertex')
    euler=len(adjacency)-len(edges)+len(faces)
    if euler!=0:raise ProjectError('wall mesh lost the through-bore topology')
    local=verts-(verts.min(axis=0)+verts.max(axis=0))/2
    mesh_volume=abs(math.fsum(float(np.dot(local[a],np.cross(local[b],local[c])))/6 for a,b,c in faces))
    relative=abs(mesh_volume-spec['volume_m3'])/spec['volume_m3']
    if relative>VOLUME_RELATIVE_TOLERANCE:raise ProjectError('native wall mesh volume differs from independent annular-cylinder volume')
    radial_axes=[i for i in range(3) if i!=spec['axis']]
    radial=np.linalg.norm((verts-np.array(spec['start_centre_m']))[:,radial_axes],axis=1)
    if radial.min()<spec['inner_m']/2-BOUNDS_TOLERANCE_M or radial.max()>spec['outer_m']/2+BOUNDS_TOLERANCE_M:
        raise ProjectError('native wall vertices exceed explicit bore/outside radii')
    if not np.any(abs(radial-spec['inner_m']/2)<1e-7) or not np.any(abs(radial-spec['outer_m']/2)<1e-7):
        raise ProjectError('native wall geometry lacks explicit inner/outer surfaces')
    return dict(analytic_wall_volume_m3=spec['volume_m3'],mesh_wall_volume_m3=mesh_volume,relative_volume_error=relative,
                saved_inner_diameter_m=2*(profile.Radius-profile.WallThickness),saved_outside_diameter_m=2*profile.Radius,
                saved_wall_thickness_m=profile.WallThickness,saved_length_m=solid.Depth,
                volume_relative_tolerance=VOLUME_RELATIVE_TOLERANCE,closed_mesh=True,euler_characteristic=euler,saved_diameter_metadata_pass=True,body_shape=WALL,
                linear_deflection_m=LINEAR_DEFLECTION_M,angular_deflection=ANGULAR_DEFLECTION,bounds_tolerance_m=BOUNDS_TOLERANCE_M)

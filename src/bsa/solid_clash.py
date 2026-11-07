"""Robust closed-mesh Boolean supplement for triangle-query blind spots."""
import math
from .engine import ProjectError


def overlaps(elements,meshes,linear_tolerance,volume_tolerance,maximum_pairs):
    import numpy as np
    import manifold3d as manifold
    pairs=[];bounds={};solids={};errors={}
    for element in elements:
        id=element.GlobalId;verts,faces=meshes[id]
        points=np.asarray(verts,dtype=np.float64).reshape(-1,3)
        triangles=np.asarray(faces,dtype=np.uint64).reshape(-1,3)
        bounds[id]=(points.min(axis=0),points.max(axis=0))
        try:
            solid=manifold.Manifold(manifold.Mesh64(vert_properties=points,tri_verts=triangles))
            if solid.status()!=manifold.Error.NoError or not math.isfinite(solid.volume()) or solid.volume()<=0:
                raise ProjectError('mesh is not a positive-volume accepted Manifold solid: '+str(solid.status()))
            solids[id]=solid
        except (RuntimeError,ValueError,ProjectError) as exc:errors[id]=str(exc)
    for i,a in enumerate(elements):
        for b in elements[i+1:]:
            al,ah=bounds[a.GlobalId];bl,bh=bounds[b.GlobalId]
            if np.all(np.minimum(ah,bh)-np.maximum(al,bl)>linear_tolerance):pairs.append((a,b))
    if len(pairs)>maximum_pairs:raise ProjectError('solid-overlap candidate count exceeds explicit Boolean budget')
    findings=[];unverified=[dict(guid=id,reason=reason) for id,reason in errors.items()];checks=[]
    for a,b in pairs:
        pair=sorted((a.GlobalId,b.GlobalId))
        try:
            if any(id in errors for id in pair):raise ProjectError('a pair operand did not form an accepted closed solid')
            common=manifold.Manifold.batch_boolean([solids[a.GlobalId],solids[b.GlobalId]],manifold.OpType.Intersect)
            if common.status()!=manifold.Error.NoError:raise ProjectError('Boolean kernel status: '+str(common.status()))
            volume=common.volume()
            if not math.isfinite(volume) or volume<0:raise ProjectError('invalid Boolean overlap volume')
            checks.append(dict(pair=pair,mesh_common_volume_m3=volume,method='Manifold3D Mesh64 intersection'))
            if volume>volume_tolerance:
                names={a.GlobalId:a.Name,b.GlobalId:b.Name}
                findings.append(dict(pair=pair,names=[names[id] for id in pair],type='manifold_mesh_overlap',overlap_volume_m3=volume,
                                     engine_distance_m=None,p1_world_m=None,p2_world_m=None))
        except (RuntimeError,ValueError,ProjectError) as exc:unverified.append(dict(pair=pair,reason=str(exc)))
    return findings,unverified,len(pairs),checks

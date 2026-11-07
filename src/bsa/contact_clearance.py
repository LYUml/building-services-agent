"""Conservative outside-region clearance proof for explicitly declared joints."""
import math
from .engine import ProjectError
from .circular_geometry import LINEAR_DEFLECTION_M
from .solid_clash import from_mesh


def prove(pair,meshes,contacts,clearance,segments):
    import numpy as np
    import manifold3d as m
    result=dict(pair=list(pair),pass_check=False,status='not_proven',sphere_segments=segments,
                mask_radius_shrink_m=LINEAR_DEFLECTION_M,gap_guard_m=2*LINEAR_DEFLECTION_M,
                required_clearance_m=clearance,proof_threshold_m=clearance+2*LINEAR_DEFLECTION_M,
                scope='both outside-region material parts versus the other full body; conservative clipped-solid lower bounds')
    try:
        solids=[from_mesh(meshes[id]) for id in pair];masks=[];regions=[]
        for contact in contacts:
            radius=contact['region_radius_m'];effective=radius-LINEAR_DEFLECTION_M
            if effective<=0:raise ProjectError('contact radius cannot support conservative mask shrink')
            ball=m.Manifold.sphere(effective,circular_segments=segments)
            if ball.status()!=m.Error.NoError:raise ProjectError('invalid exclusion-mask sphere')
            mesh=ball.to_mesh64();vertices=np.asarray(mesh.vert_properties)[:,:3]
            maximum=float(np.linalg.norm(vertices,axis=1).max())
            if not math.isfinite(maximum) or maximum>=radius:raise ProjectError('exclusion mask is not inside the sourced sphere')
            masks.append(ball.translate(contact['centre_world_m']))
            regions.append(dict(centre_world_m=contact['centre_world_m'],sourced_radius_m=radius,mask_max_vertex_radius_m=maximum))
        mask=m.Manifold.batch_boolean(masks,m.OpType.Add)
        if mask.status()!=m.Error.NoError:raise ProjectError('contact-region union failed')
        directions=[]
        for i in (0,1):
            outside=m.Manifold.batch_boolean([solids[i],mask],m.OpType.Subtract)
            if outside.status()!=m.Error.NoError:raise ProjectError('outside-region clipping failed')
            if outside.is_empty():
                directions.append(dict(outside_guid=pair[i],full_guid=pair[1-i],outside_empty=True,conservative_gap_lower_bound_m=None,pass_check=True))
            else:
                gap=outside.min_gap(solids[1-i],result['proof_threshold_m'])
                if not math.isfinite(gap) or gap<0:raise ProjectError('invalid outside-region gap')
                directions.append(dict(outside_guid=pair[i],full_guid=pair[1-i],outside_empty=False,
                                       conservative_gap_lower_bound_m=gap,pass_check=gap>=result['proof_threshold_m']))
        result.update(regions=regions,directions=directions,pass_check=all(row['pass_check'] for row in directions))
        result['status']='pass' if result['pass_check'] else 'not_proven'
    except (RuntimeError,ValueError,ProjectError) as exc:result.update(status='error',reason=str(exc))
    return result

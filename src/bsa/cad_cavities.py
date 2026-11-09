"""Bounded nested-shell checks using the existing pinned Manifold engine."""
import math
import numpy as np
import manifold3d as m
from .engine import ProjectError
from .solid_clash import from_mesh


def validate(contract):
    if not isinstance(contract,dict) or set(contract)!={'source','count','containment_margin_m','volume_tolerance_m3'}:
        raise ProjectError('exact sourced cavity contract required')
    if not isinstance(contract['source'],str) or not contract['source'].strip():raise ProjectError('cavity source required')
    if type(contract['count']) is not int or not 1<=contract['count']<=8:raise ProjectError('one to eight explicit cavities required')
    for key in ('containment_margin_m','volume_tolerance_m3'):
        if type(contract[key]) not in (int,float) or not math.isfinite(contract[key]) or contract[key]<=0:
            raise ProjectError('positive finite cavity numerical tolerances required')


def check(solid, contract):
    validate(contract)
    tol=contract['volume_tolerance_m3']; margin=contract['containment_margin_m']
    def volume(obj):
        v=obj.volume()
        if obj.status()!=m.Error.NoError or not math.isfinite(v) or v<0:raise ProjectError('cavity Boolean failed')
        return v
    parts=solid.decompose(); outer=[p for p in parts if p.volume()>tol]; negative=[p for p in parts if p.volume() < -tol]
    if len(outer)!=1 or len(negative)!=contract['count'] or len(parts)!=1+contract['count']:
        raise ProjectError('expected one positive shell and declared negative cavities')
    cavities=[]; records=[]; expanded=[]
    pad=m.Manifold.cube((2*margin,)*3,center=True)
    for part in negative:
        mesh=part.to_mesh64()
        cavity=from_mesh((np.array(mesh.vert_properties),np.array(mesh.tri_verts)[:,::-1].copy()))
        enlarged=cavity.minkowski_sum(pad)
        if volume(enlarged-outer[0])>tol:
            raise ProjectError('cavity not strictly contained within the declared numerical margin')
        for other in expanded:
            if volume(enlarged^other)>tol:raise ProjectError('cavities overlap or lack separation')
        cavities.append(cavity);expanded.append(enlarged)
        records.append({'volume_m3':volume(cavity),'bounds_m':list(cavity.bounding_box())})
    material=outer[0]
    for cavity in cavities:material=material-cavity
    if volume(material)<=tol or volume(material-solid)>tol or volume(solid-material)>tol:
        raise ProjectError('nested-shell material differs from reconstructed outer-minus-cavities')
    if not math.isclose(volume(material),volume(outer[0])-sum(volume(c) for c in cavities),abs_tol=tol,rel_tol=1e-10):
        raise ProjectError('nested-shell material volume does not reconcile')
    return {'cavities':sorted(records,key=lambda x:x['bounds_m']), 'material_volume_m3':volume(material),
            'containment_margin_m':margin,'volume_tolerance_m3':tol,
            'method':'Manifold signed decomposition, reversed cavity solids, cube dilation, containment and material differences'}

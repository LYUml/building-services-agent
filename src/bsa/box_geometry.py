"""Strict closed axis-aligned box mesh validation shared by thermal and CAD adapters."""
from collections import Counter
import itertools
import math
import numpy as np
from .engine import ProjectError


def box_mesh(vertices,faces):
    if not len(vertices) or not len(faces) or not np.isfinite(vertices).all():raise ProjectError('finite closed space mesh required')
    lo=vertices.min(axis=0);hi=vertices.max(axis=0);size=hi-lo;tol=1e-7
    if np.any(size<.001):raise ProjectError('positive thermal space solid required')
    # Every vertex must be a box corner, and every triangle must occupy one
    # boundary plane. Bounds alone cannot establish a rectangular solid.
    corners=[]
    for v in vertices:
        if not np.all(np.minimum(abs(v-lo),abs(v-hi))<=tol):raise ProjectError('only actual axis-aligned box spaces supported')
        corners.append(tuple(int(abs(v[k]-hi[k])<=tol) for k in range(3)))
    if set(corners)!=set(itertools.product((0,1),repeat=3)):raise ProjectError('complete box corners required')
    edges=Counter();areas=Counter();volume=0
    for f in faces:
        points=vertices[f]-lo;keys=[corners[i] for i in f]
        if len(set(keys))!=3:raise ProjectError('degenerate space triangle')
        planes=[(axis,side) for axis in range(3) for side in (0,1) if all(k[axis]==side for k in keys)]
        if len(planes)!=1:raise ProjectError('space mesh contains non-boundary triangles')
        area=float(np.linalg.norm(np.cross(points[1]-points[0],points[2]-points[0]))/2)
        areas[planes[0]]+=area
        volume+=float(np.dot(points[0],np.cross(points[1],points[2]))/6)
        for a,b in zip(keys,keys[1:]+keys[:1]):edges[(a,b)]+=1
    if any(count!=1 or edges[(b,a)]!=1 for (a,b),count in list(edges.items())):raise ProjectError('space mesh is not closed with consistent winding')
    if any(not math.isclose(areas[(axis,side)],float(np.prod(np.delete(size,axis))),rel_tol=1e-8,abs_tol=1e-7) for axis in range(3) for side in (0,1)) or not math.isclose(abs(volume),float(np.prod(size)),rel_tol=1e-8,abs_tol=1e-7):
        raise ProjectError('space solid face area/volume differs from box')
    return lo,size,abs(volume)

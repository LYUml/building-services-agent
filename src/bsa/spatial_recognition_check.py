"""Compare recognized planar room boundaries with explicit source expectations.

Shapely performs polygon validity, Hausdorff distance and symmetric difference;
this adapter does not recognize architecture or repair source geometry.
"""
import math
import importlib.metadata
from shapely.geometry import Polygon


def check(spaces, expected, *, length_tolerance_m, area_tolerance_m2):
    if importlib.metadata.version('shapely')!='2.2.0':raise ValueError('Pinned Shapely2.2.0 required')
    if not isinstance(spaces,list) or not isinstance(expected,list) or not expected:raise ValueError('Explicit nonempty expected room coverage required')
    for value in (length_tolerance_m,area_tolerance_m2):
        if type(value) not in (float,int) or not math.isfinite(value) or value<=0:
            raise ValueError('Explicit positive finite geometry tolerances required')
    def polygon(vertices):
        if not isinstance(vertices,list) or any(not isinstance(v,(list,tuple)) or len(v)!=2 or any(type(n) not in (float,int) or not math.isfinite(n) for n in v) for v in vertices):
            raise ValueError('Finite planar metre vertices required')
        p=Polygon(vertices)
        if p.is_empty or not p.is_valid or p.area<=0:raise ValueError('Valid positive room boundary required')
        return p
    def height(value):
        if type(value) not in (float,int) or not math.isfinite(value) or value<=0:raise ValueError('Positive finite metre height required')
        return value
    for rows in (spaces,expected):
        ids=[r['id'] for r in rows]
        if any(not isinstance(i,str) or not i.strip() for i in ids) or len(ids)!=len(set(ids)):
            raise ValueError('Unique nonempty room identities required')
    actual=[(r,polygon(r['boundary_vertices'])) for r in spaces]
    rows=[];matches=[]
    for source in expected:
        boundary=polygon(source['boundary_vertices']);h=height(source['height_m']);candidates=[]
        for room,geometry in actual:
            distance=boundary.hausdorff_distance(geometry)
            difference=boundary.symmetric_difference(geometry).area
            height_error=abs(h-height(room['height_m']))
            passed=distance<=length_tolerance_m and difference<=area_tolerance_m2 and height_error<=length_tolerance_m and room['is_open'] is False
            elevation_error=None
            if 'floor_elevation_m' in source:
                values=(source['floor_elevation_m'],room.get('floor_elevation_m'))
                if any(type(v) not in (int,float) or not math.isfinite(v) for v in values):raise ValueError('Finite floor elevations required')
                elevation_error=abs(values[0]-values[1]);passed=passed and elevation_error<=length_tolerance_m
            candidates.append(dict(recognized_id=room['id'],boundary_hausdorff_m=distance,symmetric_difference_m2=difference,height_error_m=height_error,floor_elevation_error_m=elevation_error,passes=passed))
        accepted=[r['recognized_id'] for r in candidates if r['passes']]
        if len(accepted)==1:matches.extend(accepted)
        rows.append(dict(source_id=source['id'],source_area_m2=boundary.area,matching_ids=accepted,candidates=candidates,pass_check=len(accepted)==1))
    passed=len(spaces)==len(expected) and all(r['pass_check'] for r in rows) and len(matches)==len(set(matches))==len(expected)
    return dict(source_geometry_matches=passed,expected_count=len(expected),recognized_count=len(spaces),rooms=rows,
        length_tolerance_m=length_tolerance_m,area_tolerance_m2=area_tolerance_m2,
        design_accepted=False,scope='Declared planar boundary/height correspondence only;source interpretation,thermal/MEP and physical acceptance remain separate')

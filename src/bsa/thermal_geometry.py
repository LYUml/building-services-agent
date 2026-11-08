"""Source-declared axis-aligned thermal boxes; exact whole-face adjacency only."""
import math
import re
from .engine import ProjectError


def boxes(p):
    if 'spaces' not in p:
        return [dict(id=f'Zone {i+1}', source=p['source'],
                     origin_m=[i*p['zone_width_m'], 0, 0],
                     size_m=[p['zone_width_m'], p['zone_depth_m'], p['height_m']])
                for i in range(2)]
    spaces=p['spaces']
    if not isinstance(spaces,list) or not 1<=len(spaces)<=100:
        raise ProjectError('one to 100 explicit thermal spaces required')
    names=set()
    for s in spaces:
        if not isinstance(s,dict) or set(s)!={'id','source','origin_m','size_m'}:
            raise ProjectError('exact thermal space id/source/origin_m/size_m required')
        if not isinstance(s['id'],str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}',s['id']) or s['id'].upper() in names:
            raise ProjectError('unique case-insensitive ASCII thermal space IDs required')
        names.add(s['id'].upper())
        if not isinstance(s['source'],str) or not s['source'].strip():
            raise ProjectError('thermal space geometry source required')
        for key in ('origin_m','size_m'):
            v=s[key]
            if not isinstance(v,list) or len(v)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) or abs(x)>100000 for x in v):
                raise ProjectError('finite bounded three-dimensional thermal geometry required')
        if min(s['size_m'])<0.001:
            raise ProjectError('positive thermal space dimensions required')
    adjacency(spaces)
    return spaces


def adjacency(spaces):
    """Reject overlaps and partial face contacts rather than expose interior faces."""
    pairs=[]
    tol=1e-7
    for i,a in enumerate(spaces):
        for b in spaces[i+1:]:
            lo=[max(a['origin_m'][k],b['origin_m'][k]) for k in range(3)]
            hi=[min(a['origin_m'][k]+a['size_m'][k],b['origin_m'][k]+b['size_m'][k]) for k in range(3)]
            overlap=[hi[k]-lo[k] for k in range(3)]
            if all(v>tol for v in overlap):raise ProjectError('overlapping thermal spaces')
            for axis in range(3):
                other=[k for k in range(3) if k!=axis]
                if abs(overlap[axis])<=tol and all(overlap[k]>tol for k in other):
                    if any(abs(a['origin_m'][k]-b['origin_m'][k])>tol or abs(a['size_m'][k]-b['size_m'][k])>tol for k in other):
                        raise ProjectError('partial face adjacency requires subdivided source geometry')
                    pairs.append(dict(spaces=[a['id'],b['id']],axis=axis,area_m2=math.prod(overlap[k] for k in other)))
    return pairs

"""Append explicitly sourced routing obstacles to a separate saved IFC copy."""
import argparse
import json
import math
from pathlib import Path

from .cli import digest
from .engine import ProjectError
from .route_search import search


def contract(routing,heights):
    if routing.get('coordinate_plane','world-xy')!='world-xy':raise ProjectError('World-XY obstacle extrusion does not support local routing frames')
    search(routing)  # Validate planar source contract; no search result is trusted as BIM evidence.
    rows=routing['obstacles']
    if not isinstance(heights,dict) or set(heights)!={r['id'] for r in rows}:
        raise ProjectError('exact obstacle height/source coverage required')
    result=[]
    for row in rows:
        z=heights[row['id']]
        if not isinstance(z,dict) or not isinstance(z.get('source'),str) or not z['source'].strip():raise ProjectError('obstacle height provenance required')
        lo,hi=z.get('min_z_m'),z.get('max_z_m')
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in (lo,hi)) or hi-lo<.001:
            raise ProjectError('finite positive obstacle height required')
        result.append(dict(id=row['id'],origin_m=[*row['min_m'],lo],size_m=[row['max_m'][i]-row['min_m'][i] for i in (0,1)]+[hi-lo],source=row['source']+'; height: '+z['source']))
    if not result:raise ProjectError('nonempty obstacle inventory required')
    return result


def run(ifc,routing,heights,out):
    from .obstacle_boxes import append
    paths=[Path(p).resolve() for p in (ifc,routing,heights)]
    rows=contract(*(json.loads(p.read_text(encoding='utf-8-sig')) for p in paths[1:]))
    return append(paths[0],rows,paths[1:],out,prefix='ROUTING_OBSTACLE_',pset_name='BSA_RoutingObstacle',
                  metadata={'RoutingInputSHA256':digest(paths[1]),'HeightInputSHA256':digest(paths[2])})


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('ifc',type=Path)
    for key in ('routing','heights','out'):parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args();print(json.dumps(run(args.ifc,args.routing,args.heights,args.out),indent=2))


if __name__=='__main__':main()

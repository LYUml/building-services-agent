"""Append source-linked obstacle boxes without a water-route search contract."""
import argparse
import json
import math
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from .three_phase import fields
from .obstacle_boxes import append


def prepare(path):
    path=Path(path).resolve();p=json.loads(path.read_text(encoding='utf-8-sig'))
    fields(p,'version sources obstacles')
    if type(p['version']) is not int or p['version']!=1 or not isinstance(p['sources'],dict) or not p['sources'] or not isinstance(p['obstacles'],list) or not p['obstacles']:raise ProjectError('version 1 and nonempty sourced obstacle inventory required')
    files={path,Path(__file__).resolve()};seen=set();rows=[]
    for source in p['sources'].values():
        fields(source,'path sha256 locator kind')
        if not isinstance(source['path'],str) or Path(source['path']).is_absolute():raise ProjectError('relative obstacle source required')
        target=(path.parent/source['path']).resolve()
        if not target.is_relative_to(path.parent) or not target.is_file() or digest(target)!=source['sha256']:raise ProjectError('obstacle source path/hash mismatch')
        if source['kind'] not in ('assumption','measured','course_given','manufacturer','design_target') or not isinstance(source['locator'],str) or not source['locator'].strip():raise ProjectError('obstacle source kind and locator required')
        files.add(target)
    for row in p['obstacles']:
        fields(row,'id origin_m size_m source')
        if not isinstance(row['id'],str) or not row['id'].strip() or row['id'] in seen or row['source'] not in p['sources']:raise ProjectError('unique sourced obstacle IDs required')
        seen.add(row['id'])
        for key in ('origin_m','size_m'):
            values=row[key]
            if not isinstance(values,list) or len(values)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) or (key=='size_m' and v<=0) for v in values):raise ProjectError('finite SI obstacle origin and positive sizes required')
        source=p['sources'][row['source']]
        rows.append(dict(id=row['id'],origin_m=row['origin_m'],size_m=row['size_m'],source=source['path']+'; '+source['locator'],
                         properties=dict(SourceSHA256=source['sha256'],SourceKind=source['kind'])))
    return rows,files


def run(ifc,inventory,out):
    from . import obstacle_boxes
    rows,files=prepare(inventory);files.add(Path(obstacle_boxes.__file__).resolve())
    return append(ifc,rows,files,out,prefix='COORDINATION_OBSTACLE_',pset_name='BSA_CoordinationObstacle',metadata=dict(InventorySHA256=digest(Path(inventory))))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('ifc',type=Path)
    p.add_argument('--inventory',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();r=run(a.ifc,a.inventory,a.out)
    print(json.dumps({k:r[k] for k in ('original_entities_unchanged','calculated_checks_pass','design_accepted')}))

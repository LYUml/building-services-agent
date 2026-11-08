"""Draw complete supported route/obstacle IFC coverage with source-bound outlines."""
import argparse
import csv
import json
from pathlib import Path
import uuid

from .cli import digest
from .engine import ProjectError
from .route_obstacles import contract
from .ifc_route_drawing import extract,draw,validate_settings


def obstacle_rows(ifc,routing,heights,settings,routing_hash,height_hash):
    import ifcopenshell
    import ifcopenshell.geom
    import ifcopenshell.util.element as element
    import numpy as np
    from .box_geometry import box_mesh
    if settings['projection_axes']!=['X','Y']:raise ProjectError('routing obstacle drawings require explicit X/Y projection')
    rows=contract(routing,heights);model=ifcopenshell.open(str(ifc))
    projects=model.by_type('IfcProject')
    if len(projects)!=1:raise ProjectError('one obstacle drawing project required')
    namespace=uuid.UUID(hex=ifcopenshell.guid.expand(projects[0].GlobalId))
    geom=ifcopenshell.geom.settings();geom.set(geom.USE_WORLD_COORDS,True)
    for row in rows:
        name='ROUTING_OBSTACLE_'+row['id'];guid=ifcopenshell.guid.compress(uuid.uuid5(namespace,name).hex)
        matches=[o for o in model.by_type('IfcBuildingElementProxy') if o.GlobalId==guid and o.Name==name]
        if len(matches)!=1:raise ProjectError('exact sourced obstacle identity required')
        obj=matches[0];props=element.get_psets(obj).get('BSA_RoutingObstacle',{})
        expected={'InputID':row['id'],'Source':row['source'],'RoutingInputSHA256':routing_hash,'HeightInputSHA256':height_hash}
        if any(props.get(k)!=v for k,v in expected.items()):raise ProjectError('saved obstacle provenance differs from drawing sources')
        shape=ifcopenshell.geom.create_shape(geom,obj)
        lo,size,volume=box_mesh(np.array(shape.geometry.verts).reshape(-1,3),np.array(shape.geometry.faces).reshape(-1,3))
        if not np.allclose(lo,row['origin_m'],atol=1e-8,rtol=0) or not np.allclose(size,row['size_m'],atol=1e-8,rtol=0):raise ProjectError('saved obstacle geometry differs from drawing sources')
        row.update(guid=guid,bounds_m=[float(lo[0]),float(lo[1]),float(lo[0]+size[0]),float(lo[1]+size[1])],volume_m3=volume)
    return rows


def run(ifc,model,routing,heights,settings,out):
    paths=[Path(p).resolve() for p in (ifc,model,routing,heights,settings)];out=Path(out).resolve()
    if any(out==p or out in p.parents for p in paths):raise ProjectError('output must not contain sources')
    before={str(p):digest(p) for p in paths}
    source,routing_data,height_data,config=[json.loads(p.read_text(encoding='utf-8-sig')) for p in paths[1:]]
    config=validate_settings(config)
    obstacles=obstacle_rows(paths[0],routing_data,height_data,config,before[str(paths[2])],before[str(paths[3])])
    pieces=extract(paths[0],source,config,[r['guid'] for r in obstacles])
    out.mkdir(parents=True,exist_ok=False);annotation=draw(pieces,config,out,obstacles)
    for name,rows,fields in [('segments',pieces,['guid','name','ifc_class','length_m','inner_diameter_m','outside_diameter_m','centreline_radius_m','source']),('obstacles',obstacles,['guid','id','source','volume_m3'])]:
        with (out/(name+'.csv')).open('w',newline='',encoding='utf-8') as stream:
            writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    if any(digest(Path(p))!=h for p,h in before.items()):raise ProjectError('coordination drawing source changed')
    result=dict(inputs=before,inputs_unchanged=True,settings=config,pieces=pieces,obstacles=obstacles,annotation_layout=annotation,
                calculated_checks_pass=True,design_accepted=False,
                scope='complete source-checked supported route and obstacle XY projection; linked geometry and obstacle-avoiding leaders',
                pending=['native DWG reopen and PDF scale/visual review','obstacle label glyph extents','product and complete engineering acceptance'])
    (out/'drawing.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('ifc',type=Path)
    for key in ('model','routing','heights','settings','out'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();run(a.ifc,a.model,a.routing,a.heights,a.settings,a.out)


if __name__=='__main__':main()

"""Author source-native untrimmed straight walls with explicit construction assumptions."""
import argparse
import json
import math
from pathlib import Path
from .cli import digest
from . import bim,rectangular_geometry,circular_geometry
from .duct_junction_review import from_workflow
from .duct_system_paths import calculate as source_paths

ROOT=Path(__file__).resolve().parents[2]


def compile_model(junction,schedule,basis):
    if not isinstance(basis,dict) or set(basis)!={'project_uuid','elevation_m','wall_thickness_m','profile_interpretation'}:
        raise ValueError('Explicit namespace,elevation,wall and nominal/internal interpretation required')
    for name in ('elevation_m','wall_thickness_m','profile_interpretation'):
        row=basis[name]
        if not isinstance(row,dict) or set(row)!={'value','classification','source'} or row['classification'] not in ('given','measured','assumed','design_target') or not isinstance(row['source'],str) or not row['source'].strip():
            raise ValueError('Every construction/coordinate input requires classification and source')
    elevation=basis['elevation_m']['value'];thickness=basis['wall_thickness_m']['value']
    if type(elevation) not in (int,float) or not math.isfinite(elevation) or type(thickness) not in (int,float) or not math.isfinite(thickness) or thickness<=0:
        raise ValueError('Finite elevation and positive explicit wall thickness required')
    if basis['profile_interpretation']['value']!='scheduled_nominal_as_clear_internal':raise ValueError('Only explicitly declared nominal-as-internal interpretation supported')
    checked=source_paths(junction,schedule);nodes={r['node']:r for r in junction['nodes']};devices=[]
    for row in checked['sections']:
        a=nodes[row['from_node']]['point_m'][:2]+[elevation];b=nodes[row['to_node']]['point_m'][:2]+[elevation]
        axes=[i for i in range(3) if abs(a[i]-b[i])>1e-8]
        if len(axes)!=1 or axes[0] not in (0,1):raise ValueError('Source backbone requires horizontal axis-aligned straight sections')
        axis=axes[0];length=math.dist(a,b);outer_w=row['width_m']+2*thickness;outer_h=row['height_m']+2*thickness
        size=[length,outer_w,outer_h] if axis==0 else [outer_w,length,outer_h]
        origin=[min(a[0],b[0]),min(a[1],b[1]),elevation-outer_h/2]
        origin[1-axis]-=outer_w/2
        ports=[dict(id=name,direction=direction,offset_m=[v-u for u,v in zip(origin,point)],source='native') for name,direction,point in (('in','SINK',a),('out','SOURCE',b))]
        devices.append(dict(id=row['id'],ifc_class='IfcDuctSegment',space='COORDINATION-ENVELOPE-NOT-ROOM',system='SOURCE-SUPPLY',origin_m=origin,size_m=size,
            body_shape=rectangular_geometry.WALL,source='native',ports=ports,properties=dict(InternalWidth_m=row['width_m'],InternalHeight_m=row['height_m'],WallThickness_m=thickness,
            SourceSectionID=row['id'],SourceLineHandle=row['source_line_handle'],FromNode=row['from_node'],ToNode=row['to_node'],DesignFlow_m3_s=row['flow_m3_s'],
            SourceCentrelineLength_m=length,PhysicalTrimmedLengthKnown=False,FittingsAuthored=False,ConstructionBasis=json.dumps(basis,sort_keys=True))))
    low=[min(d['origin_m'][i] for d in devices) for i in range(3)];high=[max(d['origin_m'][i]+d['size_m'][i] for d in devices) for i in range(3)]
    model=dict(name='Source Supply Backbone - Untrimmed Straight-Wall Study',project_uuid=basis['project_uuid'],geometry_scope=rectangular_geometry.SCOPE,
        sources=dict(native='Exact saved native XY centrelines,source node IDs and selected nominal section/flow;untrimmed at original nodes. No physical fitting reaches or actual installed lengths.',
            construction=json.dumps(basis,sort_keys=True),envelope='Derived AABB of the straight-wall study only;coordination container,not an architectural room,thermal zone,occupancy or floor-area source.'),
        spaces=[dict(id='COORDINATION-ENVELOPE-NOT-ROOM',origin_m=low,size_m=[v-u for u,v in zip(low,high)],source='envelope')],
        systems=[dict(id='SOURCE-SUPPLY',predefined_type='VENTILATION',source='native')],devices=devices,connections=[])
    bim.validate(model)
    return model


def inspect_saved(path,model,junction,schedule,*,storey_container=False):
    import ifcopenshell
    import ifcopenshell.geom
    import ifcopenshell.util.element as element
    import ifcopenshell.util.placement as placement
    import ifcopenshell.util.system as system
    saved=ifcopenshell.open(str(path));objects=saved.by_type('IfcDuctSegment')
    rows={r['id']:r for r in schedule['sections']};nodes={n['node']:n['point_m'] for n in junction['nodes']}
    if len(objects)!=len(rows) or {o.Name for o in objects}!=set(rows) or len(saved.by_type('IfcDistributionPort'))!=2*len(rows) or saved.by_type('IfcRelConnectsPorts'):
        raise ValueError('Exact unlinked source wall/port coverage required')
    devices={d['id']:d for d in model['devices']};links={e['id']:e for e in schedule['flow_aggregation']['sections']}
    settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True);circular_geometry.configure(settings)
    if storey_container and saved.by_type('IfcSpace'):raise ValueError('Export must not contain an artificial architectural space')
    for obj in objects:
        row=rows[obj.Name];edge=links[obj.Name];props=element.get_psets(obj)['BSA_DesignInputs'];ports={p.Name:p for p in system.get_ports(obj)}
        if set(ports)!={'in','out'} or props['SourceSectionID']!=obj.Name or props['FromNode']!=edge['from'] or props['ToNode']!=edge['to']:
            raise ValueError('Saved source section/node/owned-port identity differs')
        if props['ConstructionBasis']!=devices[obj.Name]['properties']['ConstructionBasis']:raise ValueError('Saved construction classification differs')
        rectangular_geometry.verify(obj,devices[obj.Name],ifcopenshell.geom.create_shape(settings,obj))
        if storey_container:
            container=element.get_container(obj)
            if not container.is_a('IfcBuildingStorey') or container.Name!='COORDINATION-REFERENCE-PLANE':raise ValueError('Explicit coordination reference container required')
        for key,value in (('DesignFlow_m3_s',row['inputs']['flow_m3_s']),('InternalWidth_m',row['inputs']['width_m']),('InternalHeight_m',row['inputs']['height_m'])):
            if not math.isclose(props[key],value,rel_tol=1e-12,abs_tol=1e-12):raise ValueError('Saved source flow or nominal dimension differs')
        for name,node in (('in',edge['from']),('out',edge['to'])):
            expected=nodes[node][:2]+[json.loads(devices[obj.Name]['properties']['ConstructionBasis'])['elevation_m']['value']]
            actual=placement.get_local_placement(ports[name].ObjectPlacement)[:3,3]
            if math.dist(actual,expected)>1e-8:raise ValueError('Saved source XY/assumed elevation port placement differs')
    return dict(section_count=len(objects),port_count=2*len(objects),exact_source_dimensions_flows_and_endpoints=True,logical_connection_count=0)


def export_storey(source,target):
    """Reuse official spatial API to remove the authorer's temporary envelope."""
    import ifcopenshell
    import ifcopenshell.api as api
    import ifcopenshell.validate
    file=ifcopenshell.open(str(source));storeys=file.by_type('IfcBuildingStorey');spaces=file.by_type('IfcSpace')
    if len(storeys)!=1 or len(spaces)!=1 or spaces[0].Name!='COORDINATION-ENVELOPE-NOT-ROOM':raise ValueError('Exact internal coordination container required')
    storeys[0].Name='COORDINATION-REFERENCE-PLANE'
    api.run('spatial.assign_container',file,products=file.by_type('IfcDuctSegment'),relating_structure=storeys[0])
    api.run('root.remove_product',file,product=spaces[0]);file.write(str(target))
    logger=ifcopenshell.validate.json_logger();ifcopenshell.validate.validate(ifcopenshell.open(str(target)),logger,express_rules=True)
    if logger.statements:raise ValueError('Exported reference-storey IFC schema validation failed')


def run(plan,workflow,native_task,basis_path,out):
    from .delivery import context
    from .workflow import verify
    from . import duct_system_paths,duct_equivalent
    plan,workflow,basis_path,out=[Path(p).resolve() for p in (plan,workflow,basis_path,out)]
    if out.exists() or not out.is_relative_to(ROOT) or out.is_relative_to(workflow) or workflow.is_relative_to(out) or any(out==p or out in p.parents for p in (plan,basis_path)):
        raise ValueError('New repository output outside workflow and sources required')
    pins={str(p):digest(p) for p in (plan,basis_path,workflow/'workflow.json')}
    _,record,integrity=context(plan,workflow)
    if not integrity['integrity_pass']:raise ValueError('Current source workflow integrity required')
    for values in (record['inputs'],record.get('runtime_inputs',{}),{str(workflow/n):sha for n,sha in record['artifact_hashes'].items()}):pins.update(values)
    for module in (bim,rectangular_geometry,circular_geometry,duct_system_paths,duct_equivalent):pins[str(Path(module.__file__).resolve())]=digest(Path(module.__file__))
    pins[str(Path(__file__).resolve())]=digest(Path(__file__))
    basis=json.loads(basis_path.read_text(encoding='utf-8-sig'))
    junction=from_workflow(plan,workflow,native_task,out/'junction-review.json');pins.update(junction['inputs'])
    schedule=json.loads((workflow/junction['lineage'][-1]/'results.json').read_text())
    model=compile_model(junction,schedule,basis);model_path=out/'model-input.json';model_path.write_text(json.dumps(model,indent=2))
    result=bim.run(model_path,out/'bim')
    final_ifc=out/'Supply Backbone.ifc';export_storey(out/'bim/model.ifc',final_ifc)
    source_check=inspect_saved(final_ifc,model,junction,schedule,storey_container=True)
    if any(digest(Path(p))!=sha for p,sha in pins.items()) or not verify(workflow)['integrity_pass']:raise ValueError('Backbone source or method changed during authoring')
    if not result['model_checks_pass'] or any(not d.get('rectangular_checks',{}).get('closed_mesh') for d in result['devices']):raise ValueError('Saved native straight walls did not pass geometry checks')
    report=dict(inputs=pins,source_checks=source_check,ifc_sha256=digest(final_ifc),model_input_sha256=digest(model_path),basis=basis,
        native_wall_geometry_pass=True,all_original_requirements=record['requirements'],connections_complete=False,physical_trim_complete=False,design_accepted=False,
        scope='All source rigid sections as untrimmed straight hollow-wall scenario only. Unlinked ports and junction interference remain;no fittings,VAV,flex,terminals,architectural space,installation or complete BIM/engineering acceptance.')
    report['artifact_hashes']={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'backbone.json').write_text(json.dumps(report,indent=2));return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('plan','workflow','native_task','basis'):p.add_argument(name)
    p.add_argument('--out',required=True);a=p.parse_args();r=run(a.plan,a.workflow,a.native_task,a.basis,a.out)
    print(r['source_checks']['section_count'],'saved source walls;untrimmed junctions and full design pending')

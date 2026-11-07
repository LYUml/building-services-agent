"""Size a bound network and author new source-backed IFC envelope/wall bodies."""
import argparse
import copy
import json
import math
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from .network_binding import prepare as bind,run as coordinate
from .network_design import validate_catalogue,run as design
from .bim import validate as validate_bim,run as author

GEOMETRY_BASIS='circular outside-diameter envelopes; fixed centrelines and endpoints'


def prepare(network,model,binding,catalogue,geometry):
    if not isinstance(model,dict) or not model.get('project_uuid'):raise ProjectError('source model project_uuid required for stable revision identities')
    baseline,_=bind(network,model,binding)
    options,ids,count=validate_catalogue(baseline,catalogue)
    if not isinstance(geometry,dict) or set(geometry)!={'sources','basis','options'} or geometry['basis']!=GEOMETRY_BASIS:
        raise ProjectError('explicit fixed-centreline outside-envelope contract required')
    sources=geometry['sources']
    if not isinstance(sources,dict) or not sources or any(not isinstance(k,str) or not k or not isinstance(v,str) or not v.strip() for k,v in sources.items()):
        raise ProjectError('outside-envelope sources required')
    rows=geometry['options']
    if not isinstance(rows,dict) or set(rows)!=set(options):raise ProjectError('outside geometry must cover exactly the sizing catalogue options')
    for id,row in rows.items():
        if not isinstance(row,dict) or set(row)!={'outside_diameter_m','source'} or not isinstance(row['source'],str) or row['source'] not in sources:
            raise ProjectError('each outside diameter needs an explicit known source')
        value=row['outside_diameter_m']
        if type(value) not in (int,float) or not math.isfinite(value) or value<options[id]['diameter_m']:
            raise ProjectError('finite outside diameter must not be smaller than internal diameter')
    return baseline,options,ids,count


def resize(model,binding,choices,catalogue,geometry):
    result=copy.deepcopy(model);devices={d['id']:d for d in result['devices']}
    options={o['id']:o for o in catalogue['options']}
    for segment,option_id in choices.items():
        option=options[option_id];outside=geometry['options'][option_id];diameter=outside['outside_diameter_m']
        for id in binding['segments'][segment]:
            device=devices[id]
            world={p['id']:[a+b for a,b in zip(device['origin_m'],p['offset_m'])] for p in device['ports']}
            inlet=next(p for p in device['ports'] if p['direction']=='SINK');outlet=next(p for p in device['ports'] if p['direction']=='SOURCE')
            a,b=world[inlet['id']],world[outlet['id']]
            axes=[i for i in range(3) if abs(a[i]-b[i])>1e-8]
            if len(axes)!=1:raise ProjectError('resizing requires validated straight route pieces')
            axis=axes[0]
            for i in range(3):
                if i!=axis:device['origin_m'][i]=a[i]-diameter/2;device['size_m'][i]=diameter
            for port in device['ports']:port['offset_m']=[v-o for v,o in zip(world[port['id']],device['origin_m'])]
            key='resize/'+id
            while key in result['sources']:key+='/next'
            result['sources'][key]=(model['sources'][device['source']]+'; selected size: '+catalogue['sources'][option['source']]
                                    +'; outside envelope: '+geometry['sources'][outside['source']])
            device['source']=key
            device.setdefault('properties',{}).update(InternalDiameter_m=option['diameter_m'],OutsideDiameter_m=diameter,SelectedSizeOption=option_id)
    validate_bim(result)
    return result


def filter_geometry(network,model,binding,catalogue,geometry):
    filtered=copy.deepcopy(catalogue);rejected=[]
    options={o['id']:o for o in catalogue['options']}
    for segment,allowed in catalogue['allowed_options'].items():
        kept=[]
        for id in sorted(allowed):
            try:
                revised=resize(model,binding,{segment:id},catalogue,geometry)
                probe=copy.deepcopy(network)
                next(s for s in probe['segments'] if s['id']==segment)['roughness_m']=options[id]['roughness_m']
                bind(probe,revised,binding)
                kept.append(id)
            except ProjectError as exc:rejected.append(dict(segment=segment,option=id,reason=str(exc)))
        filtered['allowed_options'][segment]=kept
    return filtered,rejected


def verify_saved(original,ifc_path,binding,choices,catalogue,geometry):
    import ifcopenshell
    import ifcopenshell.geom
    import ifcopenshell.util.element as element
    import ifcopenshell.util.system as system
    import ifcopenshell.util.placement as placement
    import numpy as np
    from . import circular_geometry as circular
    native=ifcopenshell.open(str(ifc_path));by_id={d.Name:d for d in native.by_type('IfcDistributionElement')}
    original_devices={d['id']:d for d in original['devices']};options={o['id']:o for o in catalogue['options']}
    settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True)
    circular.configure(settings)
    for segment,option_id in choices.items():
        outside=geometry['options'][option_id]['outside_diameter_m']
        for id in binding['segments'][segment]:
            old=original_devices[id];obj=by_id[id];props=element.get_psets(obj)['BSA_DesignInputs']
            if props.get('SelectedSizeOption')!=option_id or not math.isclose(props.get('OutsideDiameter_m',-1),outside,abs_tol=1e-9) or not math.isclose(props.get('InternalDiameter_m',-1),options[option_id]['diameter_m'],abs_tol=1e-9):
                raise ProjectError('saved IFC selected catalogue dimensions/identity mismatch')
            ports={p.Name:p for p in system.get_ports(obj)};world=[]
            for p in old['ports']:
                expected=np.array(old['origin_m'])+p['offset_m'];actual=placement.get_local_placement(ports[p['id']].ObjectPlacement)[:3,3]
                if not np.allclose(actual,expected,atol=1e-8,rtol=0):raise ProjectError('resizing moved an original route endpoint')
                world.append(expected)
            axis=next(i for i in range(3) if abs(world[0][i]-world[1][i])>1e-8)
            shape=ifcopenshell.geom.create_shape(settings,obj);vertices=np.array(shape.geometry.verts).reshape(-1,3)
            low,high=vertices.min(axis=0),vertices.max(axis=0)
            for i in range(3):
                expected_low=min(world[0][i],world[1][i]) if i==axis else world[0][i]-outside/2
                expected_high=max(world[0][i],world[1][i]) if i==axis else world[0][i]+outside/2
                tolerance=circular.BOUNDS_TOLERANCE_M if old.get('body_shape')==circular.WALL else 1e-8
                if not np.allclose([low[i],high[i]],[expected_low,expected_high],atol=tolerance,rtol=0):raise ProjectError('saved IFC outside envelope/centreline mismatch')
    return True


def verify_identities(baseline_path,selected_path):
    import ifcopenshell
    import ifcopenshell.util.system as system
    def identities(path):
        native=ifcopenshell.open(str(path));rows={}
        for obj in native.by_type('IfcObjectDefinition'):
            if obj.is_a('IfcDistributionPort'):
                key=(obj.is_a(),system.get_port_element(obj).Name,obj.Name)
            else:key=(obj.is_a(),'Project' if obj.is_a('IfcProject') else obj.Name)
            if key in rows:raise ProjectError('duplicate semantic object identity in IFC revision')
            rows[key]=obj.GlobalId
        return rows
    if identities(baseline_path)!=identities(selected_path):raise ProjectError('baseline/selected IFC object or port identity mismatch')
    return True


def run(network,model,binding,catalogue,geometry,out):
    paths=[Path(p).resolve() for p in (network,model,binding,catalogue,geometry)];out=Path(out).resolve()
    if any(out==p or out in p.parents for p in paths):raise ProjectError('output must not contain source inputs')
    before={str(p):digest(p) for p in paths};data=[json.loads(p.read_text(encoding='utf-8-sig')) for p in paths]
    n,m,b,c,g=data;baseline,_,_,original_count=prepare(*data)
    filtered,rejected=filter_geometry(*data)
    out.mkdir(parents=True,exist_ok=False)
    author(paths[1],out/'baseline-bim')
    baseline_path=out/'baseline-network.json';baseline_path.write_text(json.dumps(baseline,indent=2),encoding='utf-8')
    filtered_path=out/'filtered-catalogue.json';filtered_path.write_text(json.dumps(filtered,indent=2),encoding='utf-8')
    result=dict(original_candidate_count=original_count,geometry_feasible_candidate_count=math.prod(len(v) for v in filtered['allowed_options'].values()),
                rejected_geometry_options=rejected,calculated_checks_pass=False,saved_ifc_resize_checks_pass=False,stable_object_port_ids_match=False,
                design_accepted=False,selected=None,pending=['manufacturer-specific product/fitting geometry','clearance and clash checks','K applicability, operating point and full professional acceptance'])
    from .network import run as analyse
    try:
        base_result=analyse(baseline_path,out/'baseline-analysis')
        result['baseline_analysis']=dict(calculated_checks_pass=base_result['calculated_checks_pass'],required_source_total_pressure_pa=base_result['required_source_total_pressure_pa'])
    except ProjectError as exc:result['baseline_analysis']=dict(analysis_error=str(exc),calculated_checks_pass=False)
    if all(filtered['allowed_options'].values()):
        sizing=design(baseline_path,filtered_path,out/'sizing');result['sizing_feasible']=sizing['feasible_design_found']
        if sizing['selected']:
            choices=sizing['selected']['choices'];revised=resize(m,b,choices,c,g)
            revised_path=out/'selected-model.json';revised_path.write_text(json.dumps(revised,indent=2),encoding='utf-8')
            selected=json.loads((out/'sizing/selected-network.json').read_text())
            skeleton=copy.deepcopy(selected)
            for node in skeleton['nodes']:node.pop('elevation_m')
            for segment in skeleton['segments']:segment.pop('length_m');segment.pop('diameter_m')
            skeleton_path=out/'selected-skeleton.json';skeleton_path.write_text(json.dumps(skeleton,indent=2),encoding='utf-8')
            coordinated=coordinate(skeleton_path,revised_path,paths[2],out/'selected-coordination')
            verify_saved(m,out/'selected-coordination/bim/model.ifc',b,choices,c,g)
            verify_identities(out/'baseline-bim/model.ifc',out/'selected-coordination/bim/model.ifc')
            measured=json.loads((out/'selected-coordination/analysis/network.json').read_text())
            if not math.isclose(measured['required_source_total_pressure_pa'],sizing['selected']['required_source_total_pressure_pa'],rel_tol=1e-9,abs_tol=1e-8):
                raise ProjectError('authored IFC-derived pressure differs from selected design')
            result.update(selected=sizing['selected'],calculated_checks_pass=coordinated['calculated_checks_pass'],saved_ifc_resize_checks_pass=True,stable_object_port_ids_match=True)
    else:result['sizing_feasible']=False;result['failure']='at least one segment has no space-contained envelope option'
    if any(digest(Path(p))!=h for p,h in before.items()):raise ProjectError('source changed during model iteration')
    result.update(inputs=before,inputs_unchanged=True,scope='Fixed-endpoint circular sizing, explicit envelope/wall bodies, space containment and independent saved IFC/pressure reconciliation')
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'model-design.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project',type=Path)
    for name in ('model','binding','catalogue','geometry','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();r=run(a.project,a.model,a.binding,a.catalogue,a.geometry,a.out)
    print(json.dumps({k:r[k] for k in ('original_candidate_count','selected','calculated_checks_pass','design_accepted')}))
    return 0 if r['calculated_checks_pass'] else 2

if __name__=='__main__':raise SystemExit(main())

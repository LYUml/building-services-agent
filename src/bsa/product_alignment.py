"""Source-bound model-node alignment of a junction and connector; no joint approval."""
import argparse
import importlib.metadata
import json
import math
from pathlib import Path
import numpy as np
import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.util.placement as placement
import ifcopenshell.util.system as system
import ifcopenshell.util.unit as unit
import ifcopenshell.util.element as element
from .product_ports import mesh
from .solid_clash import from_mesh
from .cli import digest
from .engine import ProjectError


def aligned_placement(target_port, connector_local_port, roll_degrees):
    if type(roll_degrees) not in (int,float) or not math.isfinite(roll_degrees):raise ProjectError('finite sourced roll angle required')
    for matrix in (target_port,connector_local_port):
        if np.shape(matrix)!=(4,4) or not np.isfinite(matrix).all() or not np.allclose(matrix[3],[0,0,0,1],atol=1e-10,rtol=0) or not np.allclose(matrix[:3,:3].T@matrix[:3,:3],np.eye(3),atol=1e-9,rtol=0) or not np.isclose(np.linalg.det(matrix[:3,:3]),1):raise ProjectError('proper rigid port frames required')
    a=math.radians(roll_degrees);rotation=np.array([[math.cos(a),-math.sin(a),0,0],[math.sin(a),math.cos(a),0,0],[0,0,1,0],[0,0,0,1]])
    reverse=np.diag([1.,-1.,-1.,1.])
    return target_port@rotation@reverse@np.linalg.inv(connector_local_port)


def load_bundle(folder,kind):
    report_name,filename,flag={'junction':('product-ports.json','placed-fitting.ifc','product_ports_pass'),
        'connector':('connector-ports.json','placed-connector.ifc','connector_ports_pass')}[kind]
    report_path=folder/report_name;r=json.loads(report_path.read_text());target=folder/filename
    if r.get(flag) is not True or not r.get('checks') or not all(x is True for x in r['checks'].values()):raise ProjectError('passing source placement checks required')
    if digest(target)!=r['ifc_sha256']:raise ProjectError('saved source IFC changed')
    inputs={str(report_path):digest(report_path),str(target):digest(target)}
    for path,expected in r['inputs'].items():
        if digest(Path(path))!=expected:raise ProjectError('source placement input changed')
        inputs[path]=expected
    f=ifcopenshell.open(str(target))
    if unit.calculate_unit_scale(f)!=1 or len(f.by_type('IfcElement'))!=1 or len(f.by_type('IfcPipeFitting'))!=1:raise ProjectError('one source fitting in metre units required')
    obj=f.by_type('IfcPipeFitting')[0]
    if obj.GlobalId!=r['guid'] or obj.PredefinedType!=('JUNCTION' if kind=='junction' else 'CONNECTOR'):raise ProjectError('source identity/type mismatch')
    if f.by_type('IfcRelConnectsPorts'):raise ProjectError('source already has external connections')
    return f,obj,inputs


def overlap_locations(common, port_frame):
    """Local mesh component bounds; no geometric tolerance or contact exemption."""
    aligned_placement(port_frame, np.eye(4), 0)  # Validate the reference frame.
    import manifold3d as m
    if common.status() != m.Error.NoError:
        raise ProjectError('material intersection failed')
    records = []
    for part in common.decompose():
        volume = float(part.volume())
        vertices = np.asarray(part.to_mesh64().vert_properties)[:, :3]
        if not len(vertices):
            continue
        if not np.isfinite(vertices).all() or not math.isfinite(volume) or volume <= 0:
            raise ProjectError('positive finite overlap component required')
        local = (vertices-port_frame[:3,3]) @ port_frame[:3,:3]
        records.append({'volume_m3': volume,
                        'port_frame_bounds_m': [local.min(axis=0).tolist(), local.max(axis=0).tolist()],
                        'maximum_radius_from_port_axis_m': float(np.linalg.norm(local[:,:2],axis=1).max())})
    return sorted(records, key=lambda r: (-r['volume_m3'], r['port_frame_bounds_m'][0]))


def run(junction,connector,basis_path,out):
    if {k:importlib.metadata.version(k) for k in ('ifcopenshell','manifold3d')}!={'ifcopenshell':'0.8.5','manifold3d':'3.5.4'}:raise ProjectError('pinned geometry runtimes required')
    junction,connector,basis_path,out=[Path(p).resolve() for p in (junction,connector,basis_path,out)]
    b=json.loads(basis_path.read_text(encoding='utf-8-sig'))
    if not isinstance(b,dict) or set(b)!={'source','target_port_guid','connector_port_guid','roll_degrees','alignment_tolerance_m','overlap_volume_tolerance_m3'}:raise ProjectError('exact sourced alignment basis required')
    for k in ('source','target_port_guid','connector_port_guid'):
        if not isinstance(b[k],str) or not b[k].strip():raise ProjectError('alignment source and identities required')
    for k in ('alignment_tolerance_m','overlap_volume_tolerance_m3'):
        if type(b[k]) not in (float,int) or not math.isfinite(b[k]) or b[k]<=0:raise ProjectError('positive finite comparison tolerances required')
    if out.exists() or not out.is_relative_to(Path(__file__).resolve().parents[2]) or any(out.is_relative_to(p) or p.is_relative_to(out) for p in (junction,connector)) or out in basis_path.parents:raise ProjectError('new repository output separate from source bundles required')
    f,j,ji=load_bundle(junction,'junction');library,c,ci=load_bundle(connector,'connector');inputs={**ji,**ci,str(basis_path):digest(basis_path)}
    if {e.GlobalId for e in f.by_type('IfcRoot')} & {e.GlobalId for e in library.by_type('IfcRoot')}:raise ProjectError('source IFC root identities overlap')
    jp={p.GlobalId:p for p in system.get_ports(j)};cp={p.GlobalId:p for p in system.get_ports(c)}
    if b['target_port_guid'] not in jp or b['connector_port_guid'] not in cp:raise ProjectError('selected port not owned by source fitting')
    jv,jf=mesh(j,True);cv,cf=mesh(c)
    target_frame=placement.get_local_placement(jp[b['target_port_guid']].ObjectPlacement)
    original=placement.get_local_placement(c.ObjectPlacement)
    port_frames={guid:np.linalg.inv(original)@placement.get_local_placement(p.ObjectPlacement) for guid,p in cp.items()}
    junction_frames={guid:placement.get_local_placement(p.ObjectPlacement).copy() for guid,p in jp.items()}
    metadata={guid:{k:v for k,v in element.get_psets(p).get('BSA_ConnectorAnchor',{}).items() if k!='id'} for guid,p in cp.items()}
    transform=aligned_placement(target_frame,port_frames[b['connector_port_guid']],b['roll_degrees'])
    source_rep=c.Representation.Representations[0].Items[0];coords,indices=source_rep.Coordinates.CoordList,source_rep.CoordIndex
    added=api.run('project.append_asset',f,library=library,element=c,assume_asset_uniqueness_by_name=False)
    if {p.GlobalId for p in system.get_ports(added)}!=set(cp):raise ProjectError('upstream asset append lost connector ports')
    api.run('geometry.edit_object_placement',f,product=added,matrix=transform,is_si=True,should_transform_children=True)
    container=j.ContainedInStructure[0].RelatingStructure if j.ContainedInStructure else None
    if container:api.run('spatial.assign_container',f,products=[added],relating_structure=container)
    ps=api.run('pset.add_pset',f,product=added,name='BSA_ModelAlignment')
    api.run('pset.edit_pset',f,pset=ps,properties={'Source':b['source'],'TargetPort':b['target_port_guid'],'ConnectorPort':b['connector_port_guid'],'Scope':'Model node alignment only; no physical joint or hydraulic connection approved'})
    out.mkdir(parents=True);path=out/'alignment.ifc';f.write(str(path));saved=ifcopenshell.open(str(path));sj=saved.by_guid(j.GlobalId);sc=saved.by_guid(c.GlobalId)
    sjv,sjf=mesh(sj,True);scv,scf=mesh(sc,True);expected=cv@transform[:3,:3].T+transform[:3,3]
    rep=sc.Representation.Representations[0].Items[0]
    checks={'element_coverage':{x.GlobalId for x in saved.by_type('IfcElement')}=={j.GlobalId,c.GlobalId},
        'port_coverage':{p.GlobalId for p in saved.by_type('IfcDistributionPort')}==set(jp)|set(cp),
        'connector_tessellation':rep.Coordinates.CoordList==coords and rep.CoordIndex==indices,
        'junction_geometry':np.array_equal(sjf,jf) and bool(np.allclose(sjv,jv,atol=1e-9,rtol=0)),
        'connector_world_geometry':np.array_equal(scf,cf) and bool(np.allclose(scv,expected,atol=1e-9,rtol=0)),
        'no_physical_connection_claim':not saved.by_type('IfcRelConnectsPorts')}
    for guid,local in port_frames.items():
        port=saved.by_guid(guid)
        checks['port_'+guid]=bool(np.allclose(placement.get_local_placement(port.ObjectPlacement),transform@local,atol=1e-9,rtol=0))
        checks['metadata_'+guid]={k:v for k,v in element.get_psets(port).get('BSA_ConnectorAnchor',{}).items() if k!='id'}==metadata[guid]
    for guid,original_frame in junction_frames.items():checks['junction_port_'+guid]=bool(np.allclose(placement.get_local_placement(saved.by_guid(guid).ObjectPlacement),original_frame,atol=1e-9,rtol=0))
    selected=placement.get_local_placement(saved.by_guid(b['connector_port_guid']).ObjectPlacement)
    gap=float(np.linalg.norm(selected[:3,3]-target_frame[:3,3]));dot=float(np.dot(selected[:3,2],target_frame[:3,2]))
    checks['node_alignment']=gap<=b['alignment_tolerance_m'] and abs(dot+1)<=1e-9
    common=from_mesh((sjv,sjf))^from_mesh((scv,scf))
    import manifold3d as m
    overlap=common.volume()
    if common.status()!=m.Error.NoError or not math.isfinite(overlap) or overlap<0:raise ProjectError('material intersection failed')
    if any(digest(Path(p))!=h for p,h in inputs.items()):raise ProjectError('alignment sources changed')
    result={'inputs':inputs,'basis':b,'checks':checks,'model_alignment_pass':all(checks.values()),'node_gap_m':gap,'axis_dot':dot,
        'calculated_checks_pass':all(checks.values()) and overlap<=b['overlap_volume_tolerance_m3'],
        'material_overlap_m3':overlap,'material_overlap_above_tolerance':overlap>b['overlap_volume_tolerance_m3'],
        'overlap_reference_port_guid':b['target_port_guid'],
        'overlap_components':overlap_locations(common,target_frame),
        'connector_transform':transform.tolist(),'ifc_sha256':digest(path),'design_accepted':False,
        'scope':'Model node alignment and saved material intersection only; overlap is retained without joint-contact exemption',
        'pending':['source node/installed pipe-end correspondence','intended contact and gasket/pipe compatibility','full joint and hydraulic connections','engineering and regulatory acceptance']}
    (out/'alignment.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('junction');p.add_argument('connector');p.add_argument('basis');p.add_argument('--out',required=True)
    a=p.parse_args();r=run(a.junction,a.connector,a.basis,a.out);print(json.dumps(r,indent=2));raise SystemExit(0 if r['calculated_checks_pass'] else 2)

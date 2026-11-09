"""Place a converted connector using explicit source POINT anchors and LINE axis."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import numpy as np
import ezdxf
import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.util.placement as placement
import ifcopenshell.util.system as system
import ifcopenshell.util.element as element
from .cad_ifc import mass_properties, mesh_properties, compare
from .cad_intake import METRES_PER_UNIT
from .product_ports import mesh, frame
from .tee_geometry import stable_guid, placement_matrix
from .cli import digest
from .engine import ProjectError


def anchors(doc, basis, scale):
    line=doc.entitydb.get(basis['axis_line_handle'])
    if line is None or line.dxftype()!='LINE' or line not in doc.modelspace():raise ProjectError('source model-space axis LINE required')
    start,end=np.array(line.dxf.start)*scale,np.array(line.dxf.end)*scale
    length=float(np.linalg.norm(end-start))
    if not np.isfinite([start,end]).all() or length<=1e-8:raise ProjectError('finite nonzero source axis required')
    direction=(end-start)/length
    rows=basis['ports']
    if not isinstance(rows,list) or len(rows)!=2:raise ProjectError('two explicit source POINT ports required')
    frames={};points={};definitions={}
    for row in rows:
        if not isinstance(row,dict) or set(row)!={'id','source','point_handle','axis_endpoint'}:raise ProjectError('exact point anchor fields required')
        if any(not isinstance(row[k],str) or not row[k].strip() for k in row):raise ProjectError('nonempty point anchor identity/source required')
        if row['id'] in frames or row['axis_endpoint'] not in ('start','end'):raise ProjectError('unique anchor IDs and source axis endpoint required')
        point=doc.entitydb.get(row['point_handle'])
        if point is None or point.dxftype()!='POINT' or point not in doc.modelspace():raise ProjectError('source model-space POINT required')
        pos=np.array(point.dxf.location)*scale; axial=float(np.dot(pos-start,direction))
        if not np.isfinite(pos).all() or np.linalg.norm(pos-start-axial*direction)>1e-8 or not 0<=axial<=length:
            raise ProjectError('anchor must lie on the source axis segment')
        frames[row['id']]=frame(pos,direction if row['axis_endpoint']=='end' else -direction)
        points[row['axis_endpoint']]=axial;definitions[row['id']]=row
    if set(points)!={'start','end'} or points['end']-points['start']<=1e-8:raise ProjectError('distinct ordered opposing source anchors required')
    return frames,definitions


def run(producer,basis_path,out):
    if {k:importlib.metadata.version(k) for k in ('ifcopenshell','manifold3d','ezdxf')}!={'ifcopenshell':'0.8.5','manifold3d':'3.5.4','ezdxf':'1.4.5'}:
        raise ProjectError('verified pinned geometry runtimes required')
    producer,basis_path,out=[Path(p).resolve() for p in (producer,basis_path,out)]
    report_path=producer/'cad-ifc.json';report=json.loads(report_path.read_text())
    b=json.loads(basis_path.read_text(encoding='utf-8-sig'))
    if not isinstance(b,dict) or set(b)!={'source','placement','axis_line_handle','ports'}:raise ProjectError('exact connector placement basis required')
    if any(not isinstance(b[k],str) or not b[k].strip() for k in ('source','axis_line_handle')):raise ProjectError('connector source and axis identity required')
    transform=placement_matrix(b)
    if not report.get('geometry_conversion_pass') or report['basis'].get('predefined_type')!='CONNECTOR':raise ProjectError('passing CONNECTOR conversion required')
    before={str(p):digest(p) for p in (report_path,basis_path)}
    for name,expected in report['artifacts'].items():
        p=(producer/name).resolve()
        if not p.is_relative_to(producer) or digest(p)!=expected:raise ProjectError('converted artifact changed')
        before[str(p)]=expected
    for name,expected in report['inputs'].items():
        if digest(Path(name))!=expected:raise ProjectError('original conversion input changed')
        before[name]=expected
    if any(k not in report['artifacts'] for k in ('fitting.ifc','intake/source-export.dxf','solid.mpr')):raise ProjectError('source geometry evidence missing')
    doc=ezdxf.readfile(producer/'intake/source-export.dxf');audit=doc.audit()
    if audit.errors or audit.fixes or doc.units!=report['basis']['insunits']:raise ProjectError('source CAD units/audit failed')
    scale=METRES_PER_UNIT[doc.units];frames,definitions=anchors(doc,b,scale)
    f=ifcopenshell.open(str(producer/'fitting.ifc'))
    if len(f.by_type('IfcElement'))!=1 or len(f.by_type('IfcPipeFitting'))!=1 or f.by_type('IfcDistributionPort'):raise ProjectError('one unconnected fitting required')
    obj=f.by_type('IfcPipeFitting')[0]
    if obj.PredefinedType!='CONNECTOR' or obj.GlobalId!=report['guid'] or obj.GlobalId!=stable_guid(report['basis'],'IfcPipeFitting',report['basis']['id']):raise ProjectError('connector identity/type mismatch')
    if not np.allclose(placement.get_local_placement(obj.ObjectPlacement),np.eye(4),atol=1e-12,rtol=0):raise ProjectError('identity source placement required')
    v,faces=mesh(obj);contract=report['basis'].get('cavity_contract');props=mesh_properties(v,faces,contract)
    native=mass_properties((producer/'solid.mpr').read_text())
    reference={'volume':native['volume']*scale**3,'bounds':native['bounds']*scale,'centroid':native['centroid']*scale}
    if not all(compare(props,reference,report['basis']['linear_tolerance_m'],report['basis']['relative_volume_tolerance']).values()):raise ProjectError('source/native geometry mismatch')
    if out.exists() or not out.is_relative_to(Path(__file__).resolve().parents[2]) or out.is_relative_to(producer) or producer.is_relative_to(out) or out in basis_path.parents:raise ProjectError('new repository output outside inputs required')
    rep=obj.Representation.Representations[0].Items[0]
    if not rep.is_a('IfcTriangulatedFaceSet'):raise ProjectError('source tessellation required')
    coords,indices=rep.Coordinates.CoordList,rep.CoordIndex
    api.run('geometry.edit_object_placement',f,product=obj,matrix=transform,is_si=True)
    metadata={}
    for name,local in frames.items():
        port=api.run('system.add_port',f,element=obj);port.Name=name;port.FlowDirection='SOURCEANDSINK'
        port.GlobalId=stable_guid(report['basis'],'IfcDistributionPort',report['basis']['id'],name)
        api.run('geometry.edit_object_placement',f,product=port,matrix=transform@local,is_si=True)
        row=definitions[name]
        values={'Source':row['source'],'PointHandle':row['point_handle'],'AxisLineHandle':b['axis_line_handle'],
                'AxisEndpoint':row['axis_endpoint'],'SourceDXFSHA256':digest(producer/'intake/source-export.dxf'),
                'Scope':'Source CAD model node only; installed pipe end and joint compatibility unverified'}
        ps=api.run('pset.add_pset',f,product=port,name='BSA_ConnectorAnchor');api.run('pset.edit_pset',f,pset=ps,properties=values)
        metadata[name]=values
    out.mkdir(parents=True);target=out/'placed-connector.ifc';f.write(str(target));saved=ifcopenshell.open(str(target));obj=saved.by_guid(obj.GlobalId)
    saved_ports={p.Name:p for p in system.get_ports(obj)};sr=obj.Representation.Representations[0].Items[0]
    checks={'port_coverage':set(saved_ports)==set(frames) and len(saved.by_type('IfcDistributionPort'))==2,
            'tessellation_preserved':sr.Coordinates.CoordList==coords and sr.CoordIndex==indices,
            'placement':bool(np.allclose(placement.get_local_placement(obj.ObjectPlacement),transform,atol=1e-9,rtol=0)),
            'connector_type':obj.PredefinedType=='CONNECTOR','no_external_connections':not saved.by_type('IfcRelConnectsPorts')}
    for name,local in frames.items():
        port=saved_ports[name];values=element.get_psets(port).get('BSA_ConnectorAnchor',{})
        checks['port_'+name]=(all(values.get(k)==value for k,value in metadata[name].items())
            and port.GlobalId==stable_guid(report['basis'],'IfcDistributionPort',report['basis']['id'],name)
            and port.FlowDirection=='SOURCEANDSINK'
            and bool(np.allclose(placement.get_local_placement(port.ObjectPlacement),transform@local,atol=1e-9,rtol=0)))
    world,wf=mesh(obj,world=True);expected=v@transform[:3,:3].T+transform[:3,3]
    checks.update({'world_'+k:value for k,value in compare(mesh_properties(world,wf,contract),mesh_properties(expected,faces,contract),1e-8,1e-8).items()})
    if any(digest(Path(p))!=h for p,h in before.items()):raise ProjectError('connector source changed')
    result={'inputs':before,'basis':b,'guid':obj.GlobalId,'checks':checks,'connector_ports_pass':all(checks.values()),
            'source_node_separation_m':float(np.linalg.norm(frames[b['ports'][0]['id']][:3,3]-frames[b['ports'][1]['id']][:3,3])),
            'ifc_sha256':digest(target),'design_accepted':False,
            'pending':['source node versus installed pipe-end semantics','bore and gasket compatibility','physical external connections','hydraulic and regulatory acceptance']}
    (out/'connector-ports.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('producer');p.add_argument('basis');p.add_argument('--out',required=True)
    a=p.parse_args();r=run(a.producer,a.basis,a.out);print(json.dumps(r['checks'],indent=2));raise SystemExit(0 if r['connector_ports_pass'] else 2)

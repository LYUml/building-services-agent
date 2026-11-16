"""Extract explicit directed IFC port topology for the existing graph CAD adapter."""
import copy
import csv
import importlib.metadata as metadata
import io
import json
import os
from pathlib import Path

from . import drawing_graph,workspace
from .cli import digest


def compose(project,out):
    import ifcopenshell
    from ifcopenshell.util.system import get_ports,get_port_element
    project,out=Path(project).resolve(),Path(out).resolve()
    if not workspace.allowed(project) or not workspace.intake_output(out):raise ValueError('Host project workspace required')
    spec=json.loads(project.read_text(encoding='utf-8-sig'))
    if not isinstance(spec,dict) or set(spec)!={'schema','source','ifc','ifc_sha256','products','marked_products','graph'} or spec['schema']!='bsa.drawing-ifc-graph/1':raise ValueError('Exact IFC graph fields required')
    if not isinstance(spec['source'],str) or not spec['source'].strip():raise ValueError('Explicit graph source required')
    if not isinstance(spec['ifc'],str) or Path(spec['ifc']).is_absolute():raise ValueError('Recipe-relative source IFC required')
    source=(project.parent/spec['ifc']).resolve()
    if not workspace.allowed(source) or source.suffix.lower()!='.ifc' or digest(source)!=spec['ifc_sha256']:raise ValueError('IFC graph source escaped workspace or changed')
    if metadata.version('ifcopenshell')!='0.8.5':raise ValueError('Pinned IfcOpenShell0.8.5 required')
    model=ifcopenshell.open(str(source))
    if model.schema!='IFC4':raise ValueError('Current directed topology reader requires IFC4')
    selection=spec['products']
    if selection=='all_distribution':objects=model.by_type('IfcDistributionElement')
    elif isinstance(selection,list) and selection and all(isinstance(g,str) for g in selection) and len(set(selection))==len(selection):objects=[model.by_guid(g) for g in selection]
    else:raise ValueError('Explicit product GUID list or all_distribution selector required')
    if not objects or any(not o.is_a('IfcDistributionElement') for o in objects):raise ValueError('Nonempty distribution-element selection required')
    objects=sorted(objects,key=lambda o:o.GlobalId);selected={o.GlobalId for o in objects}
    if len(selected)!=len(objects):raise ValueError('Unique selected product GUIDs required')
    marks=spec['marked_products']
    if not isinstance(marks,list) or not all(isinstance(g,str) for g in marks) or len(set(marks))!=len(marks) or not set(marks)<=selected:raise ValueError('Unique selected marked products required')
    graph=copy.deepcopy(spec['graph'])
    if not isinstance(graph,dict) or set(graph)!={'source','source_files','layers','sheet','notes','layout','node_layer','marked_layer','edge_layer'}:raise ValueError('Explicit base graph fields required')
    node_layer=graph.pop('node_layer');marked_layer=graph.pop('marked_layer');edge_layer=graph.pop('edge_layer')
    files=[dict(path=spec['ifc'],sha256=spec['ifc_sha256']),*graph['source_files']];rebased=[];seen=set()
    for row in files:
        if not isinstance(row,dict) or set(row)!={'path','sha256'} or not isinstance(row['path'],str) or Path(row['path']).is_absolute():raise ValueError('Relative source file hash pairs required')
        path=(project.parent/row['path']).resolve()
        if path in seen or not workspace.allowed(path) or digest(path)!=row['sha256']:raise ValueError('Additional graph source escaped, repeated or changed')
        seen.add(path);rebased.append(dict(path=os.path.relpath(path,out),sha256=row['sha256']))
    owned={};ports={};names={o.GlobalId:f'N{i+1:03d}' for i,o in enumerate(objects)}
    for obj in objects:
        values=get_ports(obj)
        if not values:raise ValueError('Every selected product needs owned flow ports')
        for port in values:
            if port.GlobalId in ports or get_port_element(port)!=obj:raise ValueError('Unique native port ownership required')
            if port.FlowDirection not in ('SOURCE','SINK'):raise ValueError('Explicit SOURCE/SINK directions required; ambiguous/bidirectional ports unsupported')
            ports[port.GlobalId]=port;owned[port.GlobalId]=obj.GlobalId
    interfaces=[];external=[];connected=set()
    for rel in model.by_type('IfcRelConnectsPorts'):
        a,b=rel.RelatingPort,rel.RelatedPort
        if a.GlobalId not in ports and b.GlobalId not in ports:continue
        if a.FlowDirection=='SINK':a,b=b,a
        if a.FlowDirection!='SOURCE' or b.FlowDirection!='SINK':raise ValueError('Directed source-to-sink peer relation required')
        for p in (a,b):
            if p.GlobalId in ports:
                if p.GlobalId in connected:raise ValueError('Only one peer per selected flow port supported')
                connected.add(p.GlobalId)
        if a.GlobalId in owned and b.GlobalId in owned:
            interfaces.append(dict(from_guid=owned[a.GlobalId],to_guid=owned[b.GlobalId],source_port=a.GlobalId,sink_port=b.GlobalId))
        else:
            p=a if a.GlobalId in ports else b;peer=b if p==a else a;other=get_port_element(peer)
            external.append(dict(selected_port=p.GlobalId,direction=p.FlowDirection,peer_port=peer.GlobalId,peer_product=other.GlobalId if other else None))
    interfaces.sort(key=lambda e:(e['source_port'],e['sink_port']));external.sort(key=lambda e:e['selected_port'])
    boundary=[dict(port_guid=g,product_guid=owned[g],direction=ports[g].FlowDirection) for g in sorted(ports.keys()-connected)]
    nodes=[dict(id=o.GlobalId,label=names[o.GlobalId]+('!' if o.GlobalId in marks else ''),layer=marked_layer if o.GlobalId in marks else node_layer,source=f'{spec["source"]}; IFC {spec["ifc_sha256"]}; {o.GlobalId}',classification='secondary_transcription') for o in objects]
    edges=[dict(id=f'E{i:03d}',**{'from':r['from_guid'],'to':r['to_guid']},layer=edge_layer,source=f'Native directed IFC ports {r["source_port"]} > {r["sink_port"]}',classification='secondary_transcription') for i,r in enumerate(interfaces)]
    graph.update(schema='bsa.drawing-graph/1',source_files=rebased,nodes=nodes,edges=edges)
    stream=io.StringIO(newline='');writer=csv.writer(stream);writer.writerow(['diagram_id','ifc_guid','source_name','marked'])
    for obj in objects:writer.writerow([names[obj.GlobalId],obj.GlobalId,obj.Name or '',obj.GlobalId in marks])
    if digest(source)!=spec['ifc_sha256']:raise ValueError('IFC changed during topology extraction')
    return graph,dict(ifc_sha256=spec['ifc_sha256'],ifcopenshell_version='0.8.5',generator_sha256=digest(Path(__file__)),products=len(objects),ports=len(ports),interfaces=interfaces,open_boundary_ports=boundary,external_selected_connections=external,marked_products=marks,scope='Directed native port relations only; no coordinate/contact/material/pressure verification',design_accepted=False),stream.getvalue()


def verify(project,out):
    project,out=Path(project).resolve(),Path(out).resolve();graph,source,key=compose(project,out)
    record=json.loads((out/'ifc-graph-result.json').read_text(encoding='utf-8'));resolved=out/'graph-input.json'
    if record!={'input_sha256':digest(project),'source':source}:raise ValueError('IFC graph source/method changed')
    if json.loads(resolved.read_text(encoding='utf-8'))!=graph or (out/'Component Key.csv').read_bytes()!=key.encode('utf-8'):raise ValueError('Resolved IFC graph or component key changed')
    result=drawing_graph.verify(resolved,out/'graph')
    for artifact in result['artifacts']:artifact['path']='graph/'+artifact['path']
    result['artifacts'].append(dict(path='Component Key.csv',sha256=digest(out/'Component Key.csv'),bytes=(out/'Component Key.csv').stat().st_size))
    result['ifc_topology']=source
    return result


def run(project,out,*,autocad=None,graphviz=None):
    project,out=Path(project).resolve(),Path(out).resolve()
    if not workspace.intake_output(out) or out.exists() or out==project or out in project.parents:raise ValueError('Fresh host IFC graph output required')
    before=digest(project);graph,source,key=compose(project,out)
    if graphviz is None:raise ValueError('Explicit host Graphviz runtime required')
    out.mkdir(parents=True);resolved=out/'graph-input.json';resolved.write_text(json.dumps(graph,indent=2)+'\n',encoding='utf-8');(out/'Component Key.csv').write_bytes(key.encode('utf-8'))
    drawing_graph.run(resolved,out/'graph',autocad=autocad,graphviz=graphviz)
    if digest(project)!=before:raise ValueError('IFC graph recipe changed during authoring')
    (out/'ifc-graph-result.json').write_text(json.dumps(dict(input_sha256=before,source=source),indent=2)+'\n',encoding='utf-8')
    return verify(project,out)

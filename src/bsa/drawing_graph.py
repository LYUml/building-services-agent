"""Declared source-bound system graphs using evaluated Graphviz and general CAD."""
import copy
import json
from pathlib import Path
import subprocess

from . import drawing_document as drawing, workspace
from .cli import digest
from .three_phase_drawing import DOT_SHA256


def configuration(project):
    project=Path(project).resolve()
    if not workspace.allowed(project):raise ValueError('Host project workspace required')
    s=json.loads(project.read_text(encoding='utf-8-sig'))
    if not isinstance(s,dict) or set(s)!={'schema','source','source_files','nodes','edges','layers','sheet','notes','layout'} or s['schema']!='bsa.drawing-graph/1':raise ValueError('Exact graph drawing fields required')
    drawing.text(s['source'])
    if s['sheet'].get('scale')!=1:raise ValueError('Graph schematic requires explicit 1:1 paper-coordinate scale')
    if not isinstance(s['source_files'],list):raise ValueError('Explicit source file list required')
    paths=set()
    for row in s['source_files']:
        if set(row)!={'path','sha256'} or not isinstance(row['path'],str) or Path(row['path']).is_absolute():raise ValueError('Relative source paths and SHA256 required')
        path=(project.parent/row['path']).resolve()
        if path in paths or not workspace.allowed(path) or digest(path)!=row['sha256']:raise ValueError('Graph source escaped workspace, repeated or changed')
        paths.add(path)
    if not isinstance(s['nodes'],list) or not s['nodes'] or not isinstance(s['edges'],list):raise ValueError('Declared nodes and edges required')
    ids=set();edgeids=set()
    for node in s['nodes']:
        if set(node)!={'id','label','layer','source','classification'}:raise ValueError('Exact graph node fields required')
        for key in ('id','label','source'):drawing.text(node[key])
        if node['id'] in ids or not node['label'].isascii():raise ValueError('Unique node identity and ASCII label required')
        ids.add(node['id'])
    for edge in s['edges']:
        if set(edge)!={'id','from','to','layer','source','classification'}:raise ValueError('Exact graph edge fields required')
        drawing.text(edge['id']);drawing.text(edge['source'])
        if edge['id'] in edgeids or edge['from'] not in ids or edge['to'] not in ids:raise ValueError('Unique edge identity and declared endpoints required')
        edgeids.add(edge['id'])
    c=s['layout']
    if set(c)!={'origin','factor','node_width_mm','node_height_mm','text_height_mm','ranksep_mm','nodesep_mm','rankdir'}:raise ValueError('Explicit graph paper layout fields required')
    drawing.point(c['origin'])
    for k in ('factor','node_width_mm','node_height_mm','text_height_mm','ranksep_mm','nodesep_mm'):drawing.number(c[k],positive=True)
    if c['rankdir'] not in ('LR','TB'):raise ValueError('Supported LR/TB graph direction required')
    return s


def dot_source(s):
    c=s['layout'];names={n['id']:f'n{i}' for i,n in enumerate(s['nodes'])}
    rows=[f'digraph G {{ graph [rankdir={c["rankdir"]},splines=ortho,nodesep={c["nodesep_mm"]/25.4},ranksep={c["ranksep_mm"]/25.4}];',f'node [shape=box,fixedsize=true,width={c["node_width_mm"]/25.4},height={c["node_height_mm"]/25.4},label=""];']
    rows.extend(f'{name};' for name in names.values())
    rows.extend(f'{names[e["from"]]} -> {names[e["to"]]} [id="e{i}"];' for i,e in enumerate(s['edges']))
    return '\n'.join(rows+['}'])


def compose(s,layout):
    import ezdxf
    from ezdxf.math import Bezier4P,Vec2
    from .cad_text_layout import text_box
    c=s['layout'];factor=25.4/72*c['factor'];bounds=[float(v) for v in layout['bb'].split(',')]
    def point(p):return [(float(p[i])-bounds[i])*factor+c['origin'][i] for i in range(2)]
    entities=[];gvid={};temp=ezdxf.new();seen=set()
    def add(id,kind,row,**kw):entities.append(dict(id=id,kind=kind,layer=row['layer'],source=row['source'],classification=row['classification'],**kw))
    objects=layout.get('objects',[]);edges=layout.get('edges',[])
    if len(objects)!=len(s['nodes']) or len(edges)!=len(s['edges']):raise ValueError('Graph layout node/edge coverage differs')
    for obj in objects:
        index=int(obj['name'][1:])
        if obj['name']!=f'n{index}' or not 0<=index<len(s['nodes']) or index in seen:raise ValueError('Graph node identity differs')
        seen.add(index);row=s['nodes'][index];gvid[obj['_gvid']]=row['id']
        for j,op in enumerate(obj['_draw_']):
            if op['op'] in ('p','P'):add(f'node:{row["id"]}:box:{j}','polyline',row,points=[point(p) for p in op['points']],closed=True)
        center=point(obj['pos'].split(','));height=c['text_height_mm']*c['factor'];t=temp.modelspace().add_text(row['label'],dxfattribs={'insert':center,'height':height});box=text_box(t)
        width=float(obj['width'])*25.4*c['factor'];nodeheight=float(obj['height'])*25.4*c['factor']
        if box[2]-box[0]>width-1 or box[3]-box[1]>nodeheight-1:raise ValueError('Graph label does not fit its node')
        add(f'node:{row["id"]}:label','text',row,text=row['label'],insert=[float(2*center[0]-(box[0]+box[2])/2),float(2*center[1]-(box[1]+box[3])/2)],height=height,rotation=0)
    seen=set()
    for obj in edges:
        index=int(obj['id'][1:])
        if obj['id']!=f'e{index}' or not 0<=index<len(s['edges']) or index in seen:raise ValueError('Graph edge identity differs')
        seen.add(index);row=s['edges'][index]
        if gvid[obj['tail']]!=row['from'] or gvid[obj['head']]!=row['to']:raise ValueError('Graph edge endpoints differ')
        for group in ('_draw_','_hdraw_'):
            for j,op in enumerate(obj.get(group,[])):
                if op['op'] in ('p','P'):add(f'edge:{row["id"]}:{group}:{j}','polyline',row,points=[point(p) for p in op['points']],closed=True)
                elif op['op'] in ('b','B'):
                    pts=[point(p) for p in op['points']]
                    if (len(pts)-1)%3:raise ValueError('Graph Bezier point count differs')
                    for k in range(0,len(pts)-1,3):
                        flat=list(Bezier4P([Vec2(p) for p in pts[k:k+4]]).flattening(.01))
                        for n,(a,b) in enumerate(zip(flat,flat[1:])):
                            if a.distance(b)>1e-9:add(f'edge:{row["id"]}:{group}:{j}:{k}:{n}','line',row,start=list(a)[:2],end=list(b)[:2])
    entities.extend(copy.deepcopy(s['notes']))
    document=dict(schema='bsa.drawing-document/1',source=s['source'],units='mm',layers=s['layers'],blocks={},sheet=s['sheet'],entities=entities)
    drawing.validate(document);doc,_=drawing.author(document)
    from ezdxf import bbox
    box=bbox.extents([e for e in doc.modelspace() if not e.dxf.layer.startswith('BSA_DOC_')]);x0,y0,x1,y1=s['sheet']['window']
    if box.extmin.x<x0+8 or box.extmin.y<y0+26 or box.extmax.x>x1-8 or box.extmax.y>y1-18:raise ValueError('Graph exceeds reserved sheet regions; change explicit layout')
    return document


def verify(project,out):
    project,out=Path(project).resolve(),Path(out).resolve()
    if not workspace.intake_output(out):raise ValueError('Host project workspace required')
    s=configuration(project);record=json.loads((out/'graph-result.json').read_text());layout=out/'graphviz.json';resolved=out/'resolved-document.json'
    expected=dict(input_sha256=digest(project),generator_sha256=digest(Path(__file__)),graphviz_sha256=DOT_SHA256,layout_sha256=digest(layout),dot_sha256=digest(out/'graph.dot'))
    if record!=expected or (out/'graph.dot').read_text()!=dot_source(s):raise ValueError('Graph source, method or layout evidence changed')
    document=compose(s,json.loads(layout.read_text()))
    if json.loads(resolved.read_text())!=document:raise ValueError('Resolved graph geometry changed')
    result=drawing.verify(resolved,out/'drawing')
    for artifact in result['artifacts']:artifact['path']='drawing/'+artifact['path']
    result['graph']={'nodes':len(s['nodes']),'edges':len(s['edges']),'source_files':s['source_files'],'graphviz_sha256':DOT_SHA256,'layout_reexecuted_during_inspection':False,'scope':'Declared topology; stored Graphviz layout replay, not independent source interpretation or authenticated provenance'}
    return result


def run(project,out,*,autocad=None,graphviz=None):
    project,out=Path(project).resolve(),Path(out).resolve();s=configuration(project);before=digest(project)
    if graphviz is None or digest(Path(graphviz))!=DOT_SHA256:raise ValueError('Explicit evaluated host Graphviz executable required')
    if not workspace.intake_output(out) or out.exists() or out==project or out in project.parents:raise ValueError('Fresh host project graph output required')
    out.mkdir(parents=True);dot=out/'graph.dot';dot.write_text(dot_source(s));proc=subprocess.run([str(Path(graphviz).resolve()),'-Tjson',str(dot)],capture_output=True,timeout=60)
    (out/'graphviz.log').write_bytes(proc.stderr)
    if proc.returncode:raise ValueError('Graphviz failed; inspect graphviz.log')
    layout=out/'graphviz.json';layout.write_bytes(proc.stdout);document=compose(s,json.loads(proc.stdout));resolved=out/'resolved-document.json';resolved.write_text(json.dumps(document,indent=2)+'\n',encoding='utf-8');drawing.run(resolved,out/'drawing',autocad=autocad)
    if digest(project)!=before:raise ValueError('Graph recipe changed during authoring')
    (out/'graph-result.json').write_text(json.dumps(dict(input_sha256=before,generator_sha256=digest(Path(__file__)),graphviz_sha256=DOT_SHA256,layout_sha256=digest(layout),dot_sha256=digest(dot)),indent=2)+'\n')
    return verify(project,out)

"""Pinned textalloc candidate placement over actual CAD text boxes and lines."""
import copy
import importlib.metadata
import json
import math
from pathlib import Path

from ezdxf import bbox

from . import drawing_document as drawing,workspace
from .cli import digest
from .route_drawing_qa import enters


def upstream():
    import textalloc
    from textalloc.non_overlapping_boxes import get_non_overlapping_boxes,find_nearest_point_on_box
    pin=json.loads((Path(__file__).resolve().parents[2]/'third_party/textalloc-1.2.4.json').read_text())
    if importlib.metadata.version('textalloc')!=pin['version']:raise ValueError('Pinned textalloc1.2.4 required')
    folder=Path(textalloc.__file__).parent
    if any(digest(folder/name)!=sha for name,sha in pin['runtime_files'].items()):raise ValueError('Pinned textalloc source changed')
    for name,version in pin['dependencies'].items():
        if importlib.metadata.version(name)!=version:raise ValueError('Pinned text-layout dependency required: '+name)
    return get_non_overlapping_boxes,find_nearest_point_on_box,pin


def intersects(a,b):
    return min(a[2],b[2])-max(a[0],b[0])>1e-8 and min(a[3],b[3])-max(a[1],b[1])>1e-8


def compose(spec):
    import numpy as np
    from .cad_text_layout import text_box
    from .route_annotations import path as leader_path
    from ezdxf.disassemble import recursive_decompose
    keys={'schema','source','document','labels','avoid','bounds','gap_mm','min_distance_mm','max_distance_mm','candidates','leader_layer'}
    if not isinstance(spec,dict) or set(spec)!=keys or spec['schema']!='bsa.drawing-labels/1':raise ValueError('Exact drawing-labels fields required')
    drawing.text(spec['source']);drawing.validate(spec['document']);document=copy.deepcopy(spec['document'])
    if type(spec['candidates']) is not int or not 8<=spec['candidates']<=5000:raise ValueError('Candidate budget must be8..5000')
    for k in ('gap_mm','min_distance_mm','max_distance_mm'):drawing.number(spec[k],positive=True)
    if spec['min_distance_mm']>=spec['max_distance_mm']:raise ValueError('Minimum distance must be below maximum')
    if spec['leader_layer'] not in document['layers']:raise ValueError('Declared leader layer required')
    bounds=spec['bounds']
    if not isinstance(bounds,list) or len(bounds)!=4:raise ValueError('Explicit label bounds required')
    for v in bounds:drawing.number(v)
    x0,y0,x1,y1=bounds;sheet=document['sheet'];sx0,sy0,sx1,sy1=sheet['window'];factor=sheet['scale']*(1 if document['units']=='mm' else .001)
    if not (sx0+8*factor<=x0<x1<=sx1-8*factor and sy0+26*factor<=y0<y1<=sy1-18*factor):raise ValueError('Label bounds must exclude reserved frame regions')
    entities={e['id']:e for e in document['entities']}
    if not isinstance(spec['labels'],list) or not spec['labels']:raise ValueError('Declared labels/targets required')
    selected=set();anchors=[];labels=[]
    for row in spec['labels']:
        if not isinstance(row,dict) or set(row)!={'id','target'} or row['id'] in selected or row['id'] not in entities or row['target'] not in entities:raise ValueError('Unique existing label and target identities required')
        e=entities[row['id']];target=entities[row['target']]
        if e['kind']!='text' or e['rotation']!=0:raise ValueError('Unrotated source TEXT label required')
        if target['kind']=='line':anchor=[(a+b)/2 for a,b in zip(target['start'],target['end'])]
        elif target['kind']=='circle':anchor=target['center']
        elif target['kind']=='insert':anchor=target['insert']
        elif target['kind']=='polyline':anchor=[(min(p[i] for p in target['points'])+max(p[i] for p in target['points']))/2 for i in range(2)]
        else:raise ValueError('Supported source geometry anchor required')
        selected.add(e['id']);anchors.append(anchor);labels.append(e)
    if not isinstance(spec['avoid'],list) or len(set(spec['avoid']))!=len(spec['avoid']) or any(x not in entities or x in selected for x in spec['avoid']):raise ValueError('Unique declared obstacle identities required')
    doc,_=drawing.author(document);native={e.get_xdata('BSA_DRAWING')[0].value:e for e in doc.modelspace() if e.has_xdata('BSA_DRAWING')}
    old_boxes=[text_box(native[e['id']]).tolist() for e in labels]
    line_obstacles=[];box_obstacles=[]
    for name in spec['avoid']:
        e=entities[name]
        if e['kind']=='line':line_obstacles.append(e['start']+e['end'])
        elif e['kind']=='polyline':
            points=e['points']+([e['points'][0]] if e['closed'] else [])
            line_obstacles.extend(a+b for a,b in zip(points,points[1:]))
        else:
            b=bbox.extents([native[name]])
            if not b.has_data:raise ValueError('Measurable obstacle required')
            box_obstacles.append([b.extmin.x,b.extmin.y,b.extmax.x,b.extmax.y])
    protected_text=[]
    for e in document['entities']:
        if e['kind']=='text' and e['id'] not in selected:
            box=text_box(native[e['id']]).tolist();box_obstacles.append(box);protected_text.append(box)
        elif e['kind']=='dimension':
            for component in recursive_decompose(native[e['id']].virtual_entities()):
                if component.dxftype() in ('TEXT','MTEXT'):
                    box=text_box(component).tolist();box_obstacles.append(box);protected_text.append(box)
    allocate,nearest,pin=upstream();width=x1-x0;height=y1-y0;gap=spec['gap_mm']*factor
    original=[(anchor[0],anchor[1],b[2]-b[0],b[3]-b[1],e['id']) for anchor,b,e in zip(anchors,old_boxes,labels)]
    boxes,unplaced=allocate(original_boxes=original,xlims=(x0,x1),ylims=(y0,y1),aspect_ratio=width/height,margin=gap/width,
        min_distance=spec['min_distance_mm']*factor/width,max_distance=spec['max_distance_mm']*factor/(math.sqrt(2)*width),
        verbose=False,nbr_candidates=spec['candidates'],draw_all=False,scatter_xy=np.asarray(anchors),
        lines_xyxy=np.asarray(line_obstacles).reshape(-1,4),scatter_sizes=None,
        scatter_plot_bbs=np.asarray(box_obstacles).reshape(-1,4),text_scatter_sizes=None,direction=None,
        draw_lines=True,avoid_label_lines_overlap=True,avoid_crossing_label_lines=True,priority_strategy='largest')
    if unplaced or len(boxes)!=len(labels):raise ValueError('Configured upstream candidates did not place every label; no labels may be dropped')
    placements=[];final_boxes=[];leaders=[]
    for x,y,w,h,name,index in boxes:
        e=labels[index];old=old_boxes[index];anchor=anchors[index]
        if e['id']!=name:raise ValueError('Upstream label identity correspondence failed')
        previous=list(e['insert']);e['insert']=[float(x)-(old[0]-previous[0]),float(y)-(old[1]-previous[1])]
        box=[float(x),float(y),float(x+w),float(y+h)];end=list(nearest(x,y,w,h,*anchor))
        if math.dist(anchor,end)>spec['max_distance_mm']*factor+1e-8:raise ValueError('Allocated label exceeds declared anchor distance')
        leaders.append((anchor,end));final_boxes.append(box)
        placements.append({'id':name,'target':spec['labels'][index]['target'],'anchor':anchor,'before_insert':previous,'after_insert':e['insert'],'box':box})
    routes=[];segment_count=0
    for i,((anchor,end),row) in enumerate(zip(leaders,placements)):
        keepouts=[[b[0]-gap,b[1]-gap,b[2]+gap,b[3]+gap] for b in protected_text+[b for j,b in enumerate(final_boxes) if j!=i]]
        vertices=leader_path(anchor,end,keepouts,entities[row['id']]['height'])
        if vertices is None:raise ValueError('Leader cannot avoid protected source/dimension text')
        vertices=[[float(v) for v in point] for point in vertices]
        if any(not x0<=p[0]<=x1 or not y0<=p[1]<=y1 for p in vertices):raise ValueError('Leader route leaves label bounds')
        if sum(math.dist(a,b) for a,b in zip(vertices,vertices[1:]))>spec['max_distance_mm']*factor+1e-8:raise ValueError('Leader route exceeds declared distance')
        row['leader_vertices']=vertices;routes.append(vertices)
        for j,(a,b) in enumerate(zip(vertices,vertices[1:])):
            document['entities'].append({'id':'leader:'+row['id']+(':'+str(j) if j else ''),'kind':'line','layer':spec['leader_layer'],
                'source':spec['source']+'; label '+row['id']+' to source target '+row['target'],
                'classification':'design_target','start':a,'end':b});segment_count+=1
    # Independent saved-CAD checks use existing geometry clipping, not upstream acceptance flags.
    resolved,_=drawing.author(document);read={e.get_xdata('BSA_DRAWING')[0].value:e for e in resolved.modelspace() if e.has_xdata('BSA_DRAWING')}
    for i,row in enumerate(placements):
        actual=text_box(read[row['id']]).tolist();box=final_boxes[i]
        if any(abs(a-b)>1e-7 for a,b in zip(actual,box)):raise ValueError('Actual CAD label box differs from upstream allocation')
        if actual[0]<x0 or actual[1]<y0 or actual[2]>x1 or actual[3]>y1:raise ValueError('Label outside declared bounds')
        expanded=[actual[0]-gap,actual[1]-gap,actual[2]+gap,actual[3]+gap]
        if any(enters(line[:2],line[2:],expanded) for line in line_obstacles) or any(intersects(expanded,b) for b in box_obstacles):raise ValueError('Independent label/geometry collision check failed')
        if any(intersects(expanded,b) for j,b in enumerate(final_boxes) if j!=i):raise ValueError('Independent label/label collision check failed')
        if any(enters(a,b,actual) for j,vertices in enumerate(routes) if j!=i for a,b in zip(vertices,vertices[1:])):raise ValueError('Leader enters another label')
    for vertices in routes:
        if any(enters(a,b,box) for a,b in zip(vertices,vertices[1:]) for box in protected_text):raise ValueError('Leader enters protected source/dimension text')
    before={e['id']:e for e in spec['document']['entities']}
    for e in document['entities'][:len(before)]:
        expected=copy.deepcopy(before[e['id']])
        if e['id'] in selected:expected['insert']=e['insert']
        if e!=expected:raise ValueError('Source geometry or unapproved label fields changed')
    return document,{'placements':placements,'labels':len(labels),'leaders':len(leaders),'leader_segments':segment_count,
                     'protected_source_text_boxes':len(protected_text),'textalloc_version':pin['version'],
                     'all_source_geometry_unchanged':True,'source_entities_reconciled':len(before),
                     'scope':'Declared geometry anchors and obstacles; approximate CAD font boxes and straight leaders; native visual/engineering approval separate'}


def verify(project,out):
    project,out=Path(project).resolve(),Path(out).resolve()
    if not workspace.allowed(project) or not workspace.intake_output(out):raise ValueError('Host workspace required')
    record=json.loads((out/'labels-result.json').read_text(encoding='utf-8'))
    if record['input_sha256']!=digest(project) or record['generator_sha256']!=digest(Path(__file__)):raise ValueError('Label source/method changed')
    document,placements=compose(json.loads(project.read_text(encoding='utf-8-sig')))
    resolved=out/'resolved-document.json'
    if json.loads(resolved.read_text(encoding='utf-8'))!=document or placements!=record['placement']:raise ValueError('Label placement differs from source replay')
    result=drawing.verify(resolved,out/'drawing')
    for artifact in result['artifacts']:artifact['path']='drawing/'+artifact['path']
    result['label_placement']=placements;return result


def run(project,out,*,autocad=None):
    project,out=Path(project).resolve(),Path(out).resolve()
    if not workspace.allowed(project) or not workspace.intake_output(out) or out.exists() or out==project or out in project.parents:raise ValueError('Fresh host workspace output required')
    before=digest(project);document,placements=compose(json.loads(project.read_text(encoding='utf-8-sig')))
    out.mkdir(parents=True);resolved=out/'resolved-document.json';resolved.write_text(json.dumps(document,indent=2)+'\n',encoding='utf-8')
    drawing.run(resolved,out/'drawing',autocad=autocad)
    if digest(project)!=before:raise ValueError('Label source changed during authoring')
    (out/'labels-result.json').write_text(json.dumps({'input_sha256':before,'generator_sha256':digest(Path(__file__)),'placement':placements,'design_accepted':False},indent=2)+'\n',encoding='utf-8')
    return verify(project,out)

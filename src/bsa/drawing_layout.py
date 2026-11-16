"""Pack declared 2D views with pinned rectpack, preserving model dimensions."""
import copy
import importlib.metadata
import json
import math
from pathlib import Path
from decimal import Decimal, ROUND_FLOOR

from ezdxf import bbox

from . import drawing_document as drawing, workspace
from .cad_overlay import equivalent
from .cli import digest


def upstream():
    import rectpack
    pin=json.loads((Path(__file__).resolve().parents[2]/'third_party/rectpack-0.2.2.json').read_text())
    if importlib.metadata.version('rectpack')!=pin['version']:raise ValueError('Pinned rectpack0.2.2 required')
    folder=Path(rectpack.__file__).parent
    if any(digest(folder/name)!=sha for name,sha in pin['runtime_files'].items()):raise ValueError('Pinned rectpack source changed')
    return rectpack,pin


def compose(spec):
    if not isinstance(spec,dict) or set(spec)!={'schema','source','units','layers','blocks','sheet','content_window','gap_mm','views'} or spec['schema']!='bsa.drawing-layout/1':
        raise ValueError('Exact drawing-layout fields required')
    drawing.number(spec['gap_mm'],positive=True)
    if not isinstance(spec['views'],list) or not spec['views']:raise ValueError('Declared nonempty views required')
    names=set();entities=[]
    for view in spec['views']:
        if not isinstance(view,dict) or set(view)!={'id','entities'}:raise ValueError('Explicit view identity and entities required')
        drawing.text(view['id'])
        if view['id'] in names:raise ValueError('Unique view IDs required')
        names.add(view['id']);entities.extend(view['entities'])
    document={k:copy.deepcopy(spec[k]) for k in ('source','units','layers','blocks','sheet')}
    document.update(schema='bsa.drawing-document/1',entities=entities);drawing.validate(document)
    window=spec['content_window']
    if not isinstance(window,list) or len(window)!=4:raise ValueError('Explicit content window required')
    for x in window:drawing.number(x)
    x0,y0,x1,y1=window;s=spec['sheet'];sx0,sy0,sx1,sy1=s['window'];factor=s['scale']*(1 if spec['units']=='mm' else .001)
    if not (sx0+8*factor<=x0<x1<=sx1-8*factor and sy0+26*factor<=y0<y1<=sy1-18*factor):
        raise ValueError('Content window must stay inside reserved frame/title/reference regions')
    rectpack,pin=upstream();packer=rectpack.newPacker(rotation=False);gap=spec['gap_mm']*factor
    # Upstream rounds rectangle sizes upward, avoiding float underestimation.
    floor=lambda x:Decimal(str(x)).quantize(Decimal('.000001'),rounding=ROUND_FLOOR)
    packer.add_bin(floor(x1-x0),floor(y1-y0))
    bounds={}
    for view in spec['views']:
        local=copy.deepcopy(document);local['entities']=view['entities'];doc,_=drawing.author(local)
        box=bbox.extents([e for e in doc.modelspace() if not e.dxf.layer.startswith('BSA_DOC_')])
        if not box.has_data:raise ValueError('Every view needs measurable geometry')
        lo=[box.extmin.x,box.extmin.y];hi=[box.extmax.x,box.extmax.y]
        if not all(math.isfinite(x) for x in lo+hi):raise ValueError('Finite view extents required')
        bounds[view['id']]=lo+hi
        packer.add_rect(rectpack.float2dec(hi[0]-lo[0]+gap,6),rectpack.float2dec(hi[1]-lo[1]+gap,6),rid=view['id'])
    packer.pack();packed=packer.rect_list()
    if len(packed)!=len(spec['views']):raise ValueError('Configured packing did not place all views; enlarge sheet or change explicit layout inputs')
    placements={};placed=[]
    for _,x,y,w,h,name in packed:
        x,y,w,h=map(float,(x,y,w,h));lo=bounds[name][:2];hi=bounds[name][2:]
        delta=[x0+x+gap/2-lo[0],y0+y+gap/2-lo[1]]
        placements[name]={'translation':delta,'source_bounds':bounds[name],
                          'placed_bounds':[lo[0]+delta[0],lo[1]+delta[1],hi[0]+delta[0],hi[1]+delta[1]],
                          'padded_region':[x0+x,y0+y,x0+x+w,y0+y+h]}
        for e in next(v['entities'] for v in spec['views'] if v['id']==name):
            e=copy.deepcopy(e)
            for key in ('start','end','center','insert','p1','p2'):
                if key in e:e[key]=[e[key][i]+delta[i] for i in range(2)]
            if 'points' in e:e['points']=[[p[i]+delta[i] for i in range(2)] for p in e['points']]
            placed.append(e)
    regions=[r['padded_region'] for r in placements.values()]
    for i,a in enumerate(regions):
        if a[0]<x0-1e-8 or a[1]<y0-1e-8 or a[2]>x1+1e-8 or a[3]>y1+1e-8:raise ValueError('Packed view exceeds content window')
        for b in regions[i+1:]:
            if min(a[2],b[2])-max(a[0],b[0])>1e-8 and min(a[3],b[3])-max(a[1],b[1])>1e-8:
                raise ValueError('Packed view regions overlap')
    document['entities']=placed
    return document,{'placements':placements,'rotation':False,'scaling':False,'gap_mm':spec['gap_mm'],
                     'rectpack_version':pin['version'],'rectpack_commit':pin['commit'],
                     'scope':'Inter-view approximate font/geometry bounding boxes; intra-view labels and actual native plots require separate review'}


def verify(project,out):
    project,out=Path(project).resolve(),Path(out).resolve()
    if not workspace.allowed(project) or not workspace.intake_output(out):raise ValueError('Host project workspace required')
    record=json.loads((out/'layout-result.json').read_text(encoding='utf-8'))
    if record['input_sha256']!=digest(project) or record['generator_sha256']!=digest(Path(__file__)):
        raise ValueError('Layout source or method changed')
    doc,placement=compose(json.loads(project.read_text(encoding='utf-8-sig')))
    resolved=out/'resolved-document.json'
    if json.loads(resolved.read_text(encoding='utf-8'))!=doc or not equivalent(placement,record['layout']):raise ValueError('Packed document or placement changed')
    checked=drawing.verify(resolved,out/'drawing')
    for artifact in checked['artifacts']:artifact['path']='drawing/'+artifact['path']
    checked.update(layout=placement,scope='Packed declared views and native drawing correspondence; visual/engineering acceptance separate')
    return checked


def run(project,out,*,autocad=None):
    project,out=Path(project).resolve(),Path(out).resolve()
    if not workspace.allowed(project) or not workspace.intake_output(out):raise ValueError('Host project workspace required')
    if out.exists() or out==project or out in project.parents:raise ValueError('Fresh output outside layout input required')
    before=digest(project);document,placement=compose(json.loads(project.read_text(encoding='utf-8-sig')))
    out.mkdir(parents=True);resolved=out/'resolved-document.json';resolved.write_text(json.dumps(document,indent=2)+'\n',encoding='utf-8')
    drawing.run(resolved,out/'drawing',autocad=autocad)
    if digest(project)!=before:raise ValueError('Layout source changed during authoring')
    record={'input_sha256':before,'generator_sha256':digest(Path(__file__)),'layout':placement,'design_accepted':False}
    (out/'layout-result.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    return verify(project,out)

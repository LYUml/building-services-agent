"""Declarative 2D CAD authoring through pinned ezdxf and isolated AutoCAD.

Coordinates and engineering decisions belong to the caller. This module authors
editable geometry; it does not infer a building design from a brief.
"""
import argparse
from collections import Counter
import json
import math
from pathlib import Path

import ezdxf

from . import workspace
from .cad_intake import export_dwg
from .cad_overlay import equivalent
from .cad_sheet import plot, pdf_lines
from .cli import digest
from .native_cad import execute, lisp_string


FIELDS = {
    'line': {'start', 'end'}, 'polyline': {'points', 'closed'},
    'circle': {'center', 'radius'}, 'arc': {'center', 'radius', 'start_angle', 'end_angle'},
    'text': {'insert', 'text', 'height', 'rotation'},
    'insert': {'block', 'insert', 'scale', 'rotation'},
    'dimension': {'p1', 'p2', 'distance', 'text_height'},
}


def number(value, *, positive=False):
    if type(value) not in (float, int) or not math.isfinite(value) or (positive and value <= 0):
        raise ValueError('Finite numeric drawing value required')
    return value


def point(value):
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError('Explicit XY drawing coordinates required')
    for x in value: number(x)
    return value


def text(value):
    if not isinstance(value, str) or not value.strip() or '\x00' in value or '\n' in value or '\r' in value:
        raise ValueError('Nonempty single-line text required')
    return value


def validate(spec):
    if not isinstance(spec, dict) or set(spec) != {'schema', 'source', 'units', 'layers', 'blocks', 'entities', 'sheet'}:
        raise ValueError('Exact drawing-document fields required')
    if spec['schema'] != 'bsa.drawing-document/1' or spec['units'] not in ('mm', 'm'):
        raise ValueError('Supported drawing schema and explicit mm/m units required')
    text(spec['source'])
    if not isinstance(spec['layers'], dict) or not spec['layers']:
        raise ValueError('Explicit layer definitions required')
    for name, layer in spec['layers'].items():
        text(name)
        if name.startswith('BSA_DOC_') or set(layer) != {'color', 'lineweight'}:
            raise ValueError('Reserved layer name or invalid layer definition')
        if type(layer['color']) is not int or not 1 <= layer['color'] <= 255:
            raise ValueError('Layer ACI color must be 1..255')
        if layer['lineweight'] not in ezdxf.lldxf.const.VALID_DXF_LINEWEIGHTS:
            raise ValueError('Supported DXF lineweight required')
    if not isinstance(spec['blocks'], dict): raise ValueError('Explicit symbol block dictionary required')
    for name in spec['blocks']:
        text(name)
        if name.startswith('*'): raise ValueError('Anonymous block names reserved for CAD')
    ids = set()
    def entities(rows, block=False):
        if not isinstance(rows, list) or not rows: raise ValueError('Nonempty entity list required')
        for e in rows:
            if not isinstance(e, dict) or e.get('kind') not in FIELDS:
                raise ValueError('Supported declarative entity kind required')
            kind = e['kind']
            if set(e) != {'id', 'kind', 'layer', 'source', 'classification'} | FIELDS[kind]:
                raise ValueError('Exact fields required for '+kind)
            text(e['id']);text(e['source'])
            if e['id'] in ids: raise ValueError('Globally unique drawing entity IDs required')
            ids.add(e['id'])
            if e['layer'] not in spec['layers'] or e['classification'] not in ('given', 'assumed', 'design_target', 'secondary_transcription'):
                raise ValueError('Declared layer and explicit fact classification required')
            if block and kind in ('insert', 'dimension'):
                raise ValueError('Nested blocks and dimensions inside symbol definitions are not supported')
            for key in ('start', 'end', 'center', 'insert', 'p1', 'p2'):
                if key in e: point(e[key])
            if kind == 'line' and e['start'] == e['end']: raise ValueError('Nonzero line required')
            if kind == 'polyline':
                if type(e['closed']) is not bool or not isinstance(e['points'], list) or len(e['points']) < (3 if e['closed'] else 2):
                    raise ValueError('Explicit polyline closure and vertices required')
                for p in e['points']: point(p)
            for key in ('radius', 'height', 'scale', 'text_height'):
                if key in e: number(e[key], positive=True)
            for key in ('rotation', 'start_angle', 'end_angle', 'distance'):
                if key in e: number(e[key])
            if kind == 'arc' and (e['end_angle']-e['start_angle']) % 360 == 0: raise ValueError('Nonzero arc sweep required')
            if kind == 'text': text(e['text'])
            if kind == 'insert' and e['block'] not in spec['blocks']: raise ValueError('Declared symbol block required')
            if kind == 'dimension' and (e['p1'] == e['p2'] or e['distance'] == 0):
                raise ValueError('Distinct dimension endpoints and nonzero offset required')
    for rows in spec['blocks'].values(): entities(rows, True)
    entities(spec['entities'])
    s = spec['sheet']
    if not isinstance(s, dict) or set(s) != {'paper', 'window', 'scale', 'title', 'number', 'reference_length'}:
        raise ValueError('Explicit sheet paper/window/scale/title/number/reference required')
    if s['paper'] not in ('A4', 'A1') or not isinstance(s['window'], list) or len(s['window']) != 4:
        raise ValueError('Supported sheet paper and four window coordinates required')
    for v in s['window']: number(v)
    x0, y0, x1, y1 = s['window']
    if x0 >= x1 or y0 >= y1: raise ValueError('Positive sheet window required')
    number(s['scale'], positive=True);number(s['reference_length'], positive=True)
    text(s['title']);text(s['number'])
    return spec


def author(spec):
    validate(spec)
    if ezdxf.__version__ != '1.4.5': raise ValueError('Pinned ezdxf1.4.5 required')
    doc = ezdxf.new('R2018', setup=True);doc.units = 4 if spec['units'] == 'mm' else 6
    doc.appids.new('BSA_DRAWING')
    for name, attrs in spec['layers'].items():
        if name in doc.layers:
            layer=doc.layers.get(name);layer.dxf.color=attrs['color'];layer.dxf.lineweight=attrs['lineweight']
        else: doc.layers.new(name, dxfattribs=dict(attrs))
    def add(layout, e):
        a={'layer':e['layer']};k=e['kind']
        if k=='line': obj=layout.add_line(e['start'],e['end'],dxfattribs=a)
        elif k=='polyline': obj=layout.add_lwpolyline(e['points'],close=e['closed'],dxfattribs=a)
        elif k=='circle': obj=layout.add_circle(e['center'],e['radius'],dxfattribs=a)
        elif k=='arc': obj=layout.add_arc(e['center'],e['radius'],e['start_angle'],e['end_angle'],dxfattribs=a)
        elif k=='text': obj=layout.add_text(e['text'],dxfattribs=dict(a,insert=e['insert'],height=e['height'],rotation=e['rotation']))
        elif k=='insert': obj=layout.add_blockref(e['block'],e['insert'],dxfattribs=dict(a,xscale=e['scale'],yscale=e['scale'],rotation=e['rotation']))
        else:
            dim=layout.add_aligned_dim(e['p1'],e['p2'],e['distance'],dimstyle='EZDXF',override={'dimlfac':1.,'dimscale':1.,'dimtxt':e['text_height'],'dimasz':e['text_height']*.6,'dimgap':e['text_height']*.3,'dimexo':e['text_height']*.3,'dimexe':e['text_height']*.5,'dimdec':2},dxfattribs=a)
            dim.render();obj=dim.dimension
        obj.set_xdata('BSA_DRAWING',[(1000,e['id'])])
    for name, rows in spec['blocks'].items():
        layout=doc.blocks.new(name)
        for e in rows: add(layout,e)
    for e in spec['entities']: add(doc.modelspace(),e)
    # Model-space frame: paper dimensions converted to explicit model units.
    s=spec['sheet'];factor=s['scale']*(1 if spec['units']=='mm' else .001)
    x0,y0,x1,y1=s['window'];margin=5*factor;h=2.5*factor
    if x1-x0 <= 30*factor or y1-y0 <= 30*factor: raise ValueError('Window too small for sheet frame')
    doc.layers.new('BSA_DOC_FRAME');doc.layers.new('BSA_DOC_REFERENCE')
    m=doc.modelspace();m.add_lwpolyline([(x0+margin,y0+margin),(x1-margin,y0+margin),(x1-margin,y1-margin),(x0+margin,y1-margin)],close=True,dxfattribs={'layer':'BSA_DOC_FRAME'})
    m.add_text(s['title'],dxfattribs={'layer':'BSA_DOC_FRAME','insert':(x0+8*factor,y1-11*factor),'height':h*1.3})
    m.add_text(s['number']+' | 1:'+str(s['scale'])+' | '+spec['units'],dxfattribs={'layer':'BSA_DOC_FRAME','insert':(x0+8*factor,y0+8*factor),'height':h})
    start=(x0+8*factor,y0+16*factor);end=(start[0]+s['reference_length'],start[1])
    if end[0]>x1-margin: raise ValueError('Plot reference exceeds frame')
    ref=m.add_line(start,end,dxfattribs={'layer':'BSA_DOC_REFERENCE'})
    m.add_text('Reference '+str(s['reference_length'])+' '+spec['units'],dxfattribs={'layer':'BSA_DOC_FRAME','insert':(start[0],start[1]+2*factor),'height':h*.8})
    return doc, ref.dxf.handle


def _record(entity):
    k=entity.dxftype()
    fields={'LINE':['start','end'],'LWPOLYLINE':['elevation'], 'CIRCLE':['center','radius'],
            'ARC':['center','radius','start_angle','end_angle'],'TEXT':['text','insert','height','rotation','style','width','oblique','halign','valign'],
            'INSERT':['name','insert','xscale','yscale','zscale','rotation'],
            'DIMENSION':['dimtype','defpoint','defpoint2','defpoint3','text','text_midpoint','dimstyle']}[k]
    def plain(v):
        if isinstance(v,(int,float,str,bool)): return v
        return list(v)
    r={'type':k,'layer':entity.dxf.layer}
    for f in ('color','lineweight','linetype','ltscale','invisible'):
        r[f]=plain(getattr(entity.dxf,f))
    if entity.dxf.is_supported('extrusion'):r['extrusion']=plain(entity.dxf.extrusion)
    for f in fields:r[f]=plain(getattr(entity.dxf,f))
    if k=='TEXT' and (entity.dxf.halign or entity.dxf.valign):r['align_point']=plain(entity.dxf.align_point)
    if k=='LWPOLYLINE':r.update(points=[list(v) for v in entity.get_points()],closed=entity.closed)
    if k=='DIMENSION':
        r['measurement']=float(entity.get_measurement())
        style=entity.get_dim_style()
        overrides=entity.get_acad_dstyle(style)
        r['dimension_style']={key:overrides.get(key,getattr(style.dxf,key)) for key in ('dimlfac','dimscale','dimtxt','dimasz','dimgap','dimexo','dimexe','dimdec')}
    if entity.has_xdata('BSA_DRAWING'):r['identity']=[v.value for v in entity.get_xdata('BSA_DRAWING')]
    return r


def audit(source, actual):
    """Compare editable model entities and authored symbol definitions after reopening."""
    return compare_documents(ezdxf.readfile(source),ezdxf.readfile(actual))


def compare_documents(a,b):
    if a.units!=b.units: raise ValueError('Native drawing units changed')
    for layer in a.layers:
        if layer.dxf.name not in b.layers or any(getattr(layer.dxf,k)!=getattr(b.layers.get(layer.dxf.name).dxf,k)
                for k in ('color','flags','linetype','lineweight','plot')):
            raise ValueError('Native layer styling or visibility changed')
    for layout in [None]+[x.name for x in a.blocks if not x.is_any_layout and any(e.has_xdata('BSA_DRAWING') for e in x)]:
        x,y=(a.modelspace(),b.modelspace()) if layout is None else (a.blocks[layout],b.blocks[layout])
        if not equivalent([_record(e) for e in x],[_record(e) for e in y]):
            raise ValueError('Native editable entity or symbol mismatch: '+str(layout))
    return {'model_entities':len(a.modelspace()),'entity_types':dict(Counter(e.dxftype() for e in a.modelspace())),
            'editable_entity_correspondence':True,'dimension_rendering_visual_review':'pending'}


def methods():
    return {name:digest(Path(__file__).with_name(name)) for name in
            ('drawing_document.py','cad_sheet.py','cad_intake.py','cad_overlay.py','native_cad.py')}


def verify(project, output):
    """Reconstruct declared geometry and check actual saved artifacts, without CAD execution."""
    project,output=Path(project).resolve(),Path(output).resolve()
    if not workspace.allowed(project) or not workspace.intake_output(output):raise ValueError('Host project workspace required')
    before=digest(project);result=json.loads((output/'drawing-result.json').read_text(encoding='utf-8'))
    if result['source_sha256']!=before or result['methods']!=methods() or result['design_accepted'] is not False:
        raise ValueError('Drawing source, methods or acceptance record changed')
    expected,reference=author(json.loads(project.read_text(encoding='utf-8-sig')))
    dxf=output/'Drawing.dxf'
    if digest(dxf)!=result['dxf_sha256']:raise ValueError('Drawing DXF changed')
    checked=compare_documents(expected,ezdxf.readfile(dxf))
    if result['native_reopen_pass']:
        if digest(output/'Drawing.dwg')!=result['dwg_sha256'] or digest(output/'Drawing.pdf')!=result['plot']['pdf_sha256']:
            raise ValueError('Drawing DWG or PDF changed')
        exported=output/'reopened/source-export.dxf'
        if digest(exported)!=result['native_export_sha256']:raise ValueError('Native export changed')
        native=audit(dxf,exported)
        if native!=result['native_audit']:raise ValueError('Native drawing audit changed')
        s=json.loads(project.read_text(encoding='utf-8-sig'))['sheet'];window=s['window']
        factor=(1 if expected.units==4 else 1000)/s['scale']
        paper,lines=pdf_lines(output/'Drawing.pdf');target={'A4':[297,210],'A1':[841,594]}[s['paper']]
        if any(abs(v-e)>.2 for v,e in zip(paper,target)):raise ValueError('Drawing PDF paper changed')
        width=(window[2]-window[0])*factor;height=(window[3]-window[1])*factor
        ref=expected.entitydb[reference]
        def paper_point(p):return [(paper[0]-width)/2+(p.x-window[0])*factor,(paper[1]-height)/2+(p.y-window[1])*factor]
        a,b=paper_point(ref.dxf.start),paper_point(ref.dxf.end)
        if not any(min(max(math.dist(a,x),math.dist(b,y)),max(math.dist(a,y),math.dist(b,x)))<=.2 for x,y in lines):
            raise ValueError('Actual drawing PDF reference does not match the source sheet')
    if digest(project)!=before:raise ValueError('Drawing source changed during inspection')
    artifacts=[]
    for name in ['Drawing.dxf']+(['Drawing.dwg','Drawing.pdf'] if result['native_reopen_pass'] else []):
        path=output/name;artifacts.append(dict(path=name,sha256=digest(path),bytes=path.stat().st_size))
    return dict(integrity_pass=True,native_reopen_pass=result['native_reopen_pass'],editable_entities=checked,
                artifacts=artifacts,visual_review='pending',design_accepted=False)


def run(project, output, *, autocad=None):
    project,output=Path(project).resolve(),Path(output).resolve()
    if not workspace.allowed(project) or not workspace.intake_output(output): raise ValueError('Host project workspace required')
    if output.exists() or output==project or output in project.parents: raise ValueError('Fresh output outside inputs required')
    raw=project.read_bytes();spec=validate(json.loads(raw.decode('utf-8-sig')));doc,ref=author(spec)
    output.mkdir(parents=True);dxf=output/'Drawing.dxf';doc.saveas(dxf)
    result={'schema':'bsa.drawing-result/1','source_sha256':digest(project),'dxf_sha256':digest(dxf),'methods':methods(),
            'native_reopen_pass':False,'visual_review':'pending','design_accepted':False}
    if autocad is not None:
        exe=Path(autocad).resolve()
        if not exe.is_file(): raise ValueError('Explicit existing AutoCAD executable required')
        dwg=output/'Drawing.dwg';scr=output/'save.scr'
        condition=f'(= (strcase (vl-string-translate (chr 92) "/" (strcat (getvar "DWGPREFIX") (getvar "DWGNAME")))) (strcase {lisp_string(dxf)}))'
        scr.write_text(f'(if {condition} (progn (setvar "FILEDIA" 0) (setvar "CMDDIA" 0) (command "_.SAVEAS" "2018" {lisp_string(dwg)})))\n_.QUIT\n_Y\n',encoding='ascii')
        execute(exe,dxf,scr,output/'save.log',120)
        exported=export_dwg(dwg,output/'reopened',exe)
        result['native_export_sha256']=digest(exported)
        result['native_audit']=audit(dxf,exported)
        s=spec['sheet'];result['plot']=plot(dwg,dxf,dict(paper=s['paper'],source=spec['source'],window_drawing_units=s['window'],scale_denominator=s['scale'],reference_handle=ref,pdf_tolerance_mm=.2),output/'Drawing.pdf',exe)
        result.update(native_reopen_pass=True,dwg_sha256=digest(dwg),autocad_sha256=digest(exe))
    if project.read_bytes()!=raw: raise ValueError('Drawing input changed during authoring')
    (output/'drawing-result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    verify(project,output)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project');p.add_argument('--out',required=True);p.add_argument('--autocad');a=p.parse_args()
    print(json.dumps(run(a.project,a.out,autocad=a.autocad),indent=2))


if __name__=='__main__':main()

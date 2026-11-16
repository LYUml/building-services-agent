"""Bounded native DWG revisions with whole-entity preservation checks."""
import json
import math
from pathlib import Path
import shutil

import ezdxf
from ezdxf.lldxf.tagwriter import TagCollector

from . import drawing_document, workspace
from .cli import digest
from .native_cad import execute,lisp_string
from .cad_intake import export_dwg
from .cad_sheet import plot

FIELDS={'text':{'text','insert'},'line':{'start','end'},'circle':{'center','radius'},
        'arc':{'center','radius','start_angle','end_angle'}}


def validate_edits(edits):
    if not isinstance(edits,list) or not edits:raise ValueError('Explicit nonempty edits required')
    seen=set()
    for e in edits:
        if not isinstance(e,dict) or set(e) not in ({'handle','expected','replacement'},{'handle','kind','expected','replacement'}):raise ValueError('Exact edit fields required')
        kind=e.get('kind','text')
        if kind not in FIELDS or not isinstance(e['handle'],str) or not e['handle'] or any(c not in '0123456789ABCDEFabcdef' for c in e['handle']):raise ValueError('Supported entity kind and hexadecimal handle required')
        if e['handle'].upper() in seen:raise ValueError('Duplicate edit target')
        seen.add(e['handle'].upper())
        if set(e['expected'])!=FIELDS[kind]|{'layer'} or set(e['replacement'])!=FIELDS[kind]:raise ValueError('Exact source and replacement geometry fields required')
        drawing_document.text(e['expected']['layer'])
        for values in (e['expected'],e['replacement']):
            for k in ('start','end','insert','center'):
                if k in values:drawing_document.point(values[k])
            if kind=='text':
                drawing_document.text(values['text'])
                if not values['text'].isascii():raise ValueError('Current text revision requires ASCII; Unicode not verified')
            if kind=='line' and values['start']==values['end']:raise ValueError('Nonzero replacement line required')
            if 'radius' in values:drawing_document.number(values['radius'],positive=True)
            if kind=='arc':
                drawing_document.number(values['start_angle']);drawing_document.number(values['end_angle'])
                if not all(0<=values[k]<360 for k in ('start_angle','end_angle')):raise ValueError('Normalized arc angles in0..360required')
                if (values['end_angle']-values['start_angle'])%360==0:raise ValueError('Nonzero arc sweep required')


def geometry(obj,kind):
    xy=lambda p:[float(p.x),float(p.y)]
    if kind=='text':return dict(text=obj.dxf.text,insert=xy(obj.dxf.insert))
    if kind=='line':return dict(start=xy(obj.dxf.start),end=xy(obj.dxf.end))
    result=dict(center=xy(obj.dxf.center),radius=float(obj.dxf.radius))
    if kind=='arc':result.update(start_angle=float(obj.dxf.start_angle),end_angle=float(obj.dxf.end_angle))
    return result


def precondition_equal(a,b):
    if isinstance(a,list):return isinstance(b,list) and len(a)==len(b) and all(precondition_equal(x,y) for x,y in zip(a,b))
    if type(a) in (int,float) and type(b) in (int,float):return math.isclose(a,b,abs_tol=1e-8,rel_tol=0)
    return a==b


def configuration(project):
    project=Path(project).resolve()
    if not workspace.allowed(project):raise ValueError('Host project workspace required')
    raw=project.read_bytes();data=json.loads(raw.decode('utf-8-sig'))
    if not isinstance(data,dict) or set(data)!={'schema','source','drawing','drawing_sha256','edits','sheet'} or data['schema']!='bsa.drawing-revision/1':
        raise ValueError('Exact drawing-revision fields required')
    drawing_document.text(data['source'])
    if not isinstance(data['drawing'],str) or Path(data['drawing']).is_absolute():raise ValueError('Recipe-relative existing DWG required')
    source=(project.parent/data['drawing']).resolve()
    if not workspace.allowed(source) or source.suffix.lower()!='.dwg' or digest(source)!=data['drawing_sha256']:
        raise ValueError('Drawing source escaped workspace or changed')
    validate_edits(data['edits'])
    return data,source,raw


def revised(doc,edits):
    validate_edits(edits)
    for e in edits:
        obj=doc.entitydb.get(e['handle'].upper());expected=e['expected'];kind=e.get('kind','text')
        if obj is None or obj.dxftype()!=kind.upper() or obj.dxf.layer!=expected['layer']:raise ValueError('Entity target/type/layer precondition failed')
        if obj.get_layout().name!='Model' or doc.layers.get(obj.dxf.layer).is_locked() or obj.dxf.paperspace:raise ValueError('Unlocked model-space entity precondition required')
        if kind=='text' and (obj.dxf.halign or obj.dxf.valign):raise ValueError('Unaligned TEXT precondition required')
        if kind=='line' and abs(obj.dxf.start.z-obj.dxf.end.z)>1e-10:raise ValueError('Planar line precondition required')
        if kind!='line' and not obj.dxf.extrusion.isclose((0,0,1),abs_tol=1e-12):raise ValueError('WCS XY entity precondition required')
        actual=geometry(obj,kind)
        if any(not precondition_equal(v,expected[k]) for k,v in actual.items()):raise ValueError('Source geometry/content precondition failed')
    for e in edits:
        obj=doc.entitydb[e['handle'].upper()]
        for key,value in e['replacement'].items():
            if key in ('insert','start','end','center'):value=(*value,getattr(obj.dxf,key).z)
            setattr(obj.dxf,key,value)
    return doc


def snapshot(doc):
    """Literal supported DXF serialization, including block and paper entities."""
    if any(b.block.dxf.flags&12 for b in doc.blocks):raise ValueError('External references need separate packaging')
    records={'units':int(doc.header.get('$INSUNITS',0))}
    def tags(e):return [(tag.code,tag.value.hex() if isinstance(tag.value,bytes) else tag.value) for tag in TagCollector.dxftags(e)]
    for layout in doc.layouts:
        for e in layout:records['entity:'+e.dxf.handle]=(layout.name,tags(e))
    for block in doc.blocks:
        if not block.is_any_layout:
            for e in block:records['block:'+e.dxf.handle]=(block.name,tags(e))
    for name in ('layers','styles','linetypes','dimstyles'):
        for e in getattr(doc,name):records[name+':'+e.dxf.name]=tags(e)
    return records


def compare(before,actual,edits):
    wanted=snapshot(revised(ezdxf.readfile(before),edits));saved=snapshot(ezdxf.readfile(actual))
    maximum=0.
    def same(a,b):
        nonlocal maximum
        if isinstance(a,(list,tuple)):
            return isinstance(b,(list,tuple)) and len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
        if type(a) in (float,int) and type(b) in (float,int) and (type(a) is float or type(b) is float):
            if not math.isfinite(a) or not math.isfinite(b):return False
            maximum=max(maximum,abs(a-b));return math.isclose(a,b,abs_tol=1e-7,rel_tol=0)
        return a==b
    differences=[k for k in wanted.keys()|saved.keys() if not same(wanted.get(k),saved.get(k))]
    if differences:
        raise ValueError('Native revision differs outside approved changes: '+str(differences[:8]))
    return dict(preserved_records=len(wanted),edited_texts=sum(e.get('kind','text')=='text' for e in edits),
                edited_entities=len(edits),edited_kinds={k:sum(e.get('kind','text')==k for e in edits) for k in FIELDS if any(e.get('kind','text')==k for e in edits)},blocks_and_paper_entities_preserved=True,
                numeric_absolute_tolerance_drawing_units=1e-7,maximum_numeric_difference_drawing_units=maximum,
                scope='Saved entity/block/paper and layer/style tags, exact strings/integers and 1e-7 drawing-unit float bound; unexamined dictionaries/product semantics and visual acceptance remain separate')


def methods():
    return {name:digest(Path(__file__).with_name(name)) for name in ('drawing_revision.py','drawing_document.py','native_cad.py','cad_intake.py','cad_sheet.py')}


ARTIFACTS={'source/source-copy.dwg','source/source-export.dxf','reopened/source-export.dxf','Revised Drawing.dwg','Revised Drawing.pdf'}


def artifact_checks(out,record):
    if set(record['artifacts'])!=ARTIFACTS or record['native_reopen_pass'] is not True:
        raise ValueError('Complete native revision artifact inventory required')
    for name,sha in record['artifacts'].items():
        path=(out/name).resolve()
        if not path.is_relative_to(out) or digest(path)!=sha:raise ValueError('Revision artifact changed or escaped')
    if record['plot']['pdf_sha256']!=record['artifacts']['Revised Drawing.pdf']:raise ValueError('Revision plot identity differs')


def verify(project,out):
    project,out=Path(project).resolve(),Path(out).resolve()
    if not workspace.intake_output(out):raise ValueError('Host project workspace required')
    data,source,_=configuration(project);record=json.loads((out/'revision-result.json').read_text(encoding='utf-8'))
    if record['project_sha256']!=digest(project) or record['source_sha256']!=digest(source) or record['methods']!=methods() or record['design_accepted'] is not False:raise ValueError('Revision source/method/acceptance changed')
    if digest(out/'source/source-copy.dwg')!=digest(source):raise ValueError('Original DWG copy changed')
    artifact_checks(out,record)
    checked=compare(out/'source/source-export.dxf',out/'reopened/source-export.dxf',data['edits'])
    if checked!=record['preservation']:raise ValueError('Revision preservation record differs')
    return dict(integrity_pass=True,native_reopen_pass=True,preservation=checked,
                artifacts=[dict(path=name,sha256=record['artifacts'][name]) for name in ('Revised Drawing.dwg','Revised Drawing.pdf')],
                visual_review='pending',design_accepted=False)


def run(project,out,*,autocad):
    project,out,exe=Path(project).resolve(),Path(out).resolve(),Path(autocad).resolve()
    data,source,raw=configuration(project)
    if not workspace.intake_output(out) or out.exists() or any(out==p or out in p.parents for p in (project,source,exe)) or not exe.is_file():raise ValueError('Fresh isolated output and host AutoCAD required')
    pins=methods();exe_sha=digest(exe);out.mkdir(parents=True)
    before=export_dwg(source,out/'source',exe)
    expected=revised(ezdxf.readfile(before),data['edits']);snapshot(expected);expected.saveas(out/'expected.dxf')
    copied=out/'working.dxf';shutil.copyfile(out/'expected.dxf',copied);target=out/'Revised Drawing.dwg'
    condition=f'(= (strcase (vl-string-translate (chr 92) "/" (strcat (getvar "DWGPREFIX") (getvar "DWGNAME")))) (strcase {lisp_string(copied)}))'
    script=out/'revise.scr'
    script.write_text(f'(if {condition} (progn (setvar "FILEDIA" 0) (setvar "CMDDIA" 0) (command "_.SAVEAS" "2018" {lisp_string(target)})))\n_.QUIT\n_Y\n',encoding='ascii')
    execute(exe,copied,script,out/'revise.log',120)
    if not target.is_file():raise ValueError('Native revision did not create approved output')
    exported=export_dwg(target,out/'reopened',exe);preserved=compare(before,exported,data['edits'])
    plotted=plot(target,exported,data['sheet'],out/'Revised Drawing.pdf',exe)
    if project.read_bytes()!=raw or digest(source)!=data['drawing_sha256'] or digest(exe)!=exe_sha or methods()!=pins:raise ValueError('Revision input/runtime/method changed')
    names=['source/source-copy.dwg','source/source-export.dxf','reopened/source-export.dxf','Revised Drawing.dwg','Revised Drawing.pdf']
    record=dict(project_sha256=digest(project),source_sha256=digest(source),methods=pins,autocad_sha256=exe_sha,preservation=preserved,plot=plotted,
                artifacts={name:digest(out/name) for name in names},native_reopen_pass=True,design_accepted=False)
    (out/'revision-result.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    return verify(project,out)

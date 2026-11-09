"""Calculation-bound Graphviz/ezdxf schematic, not an installation design."""
import argparse
import csv
import json
import math
from pathlib import Path
import shutil
import subprocess
from .cli import digest
from .engine import ProjectError
from .three_phase import prepare,ROOT
from .three_phase_bridge import inputs as study_inputs,VERSIONS

DOT_SHA256='ff1ce5f13caf4ed7dddb7327b94781e751e4a7e693b4655287b6647d959c879a'
APP='BSA_ELECTRICAL'


def context(project,study_root,require_targets=True):
    p,files=prepare(project);study_root=Path(study_root).resolve()
    bridge=json.loads((study_root/'three-phase.json').read_text(encoding='utf-8'))
    expected=study_inputs(project)
    recorded=bridge['inputs']
    if not expected.issubset({Path(f) for f in recorded}) or len(recorded)!=len(expected)+1:
        raise ProjectError('study source inventory differs')
    if any(not Path(f).is_file() or digest(Path(f))!=h for f,h in recorded.items()):raise ProjectError('study inputs changed')
    study_path=study_root/'native/study.json';network=study_root/'native/network.json'
    study=json.loads(study_path.read_text(encoding='utf-8'))
    if digest(study_path)!=bridge['study_sha256'] or digest(network)!=bridge['network_sha256'] or study['network_sha256']!=digest(network):raise ProjectError('study artifacts changed')
    if study['inputs']!={str(f):digest(f) for f in files} or study['source_records']!=p['sources'] or study['versions']!=VERSIONS:raise ProjectError('study/project correspondence differs')
    if study['verification_pass'] is not True or bridge['status']!=study['status'] or type(study['study_targets_pass']) is not bool or study['status']!=('pass' if study['study_targets_pass'] else 'fail'):
        raise ProjectError('a verified numerical study is required')
    if require_targets and (study['status']!='pass' or study['study_targets_pass'] is not True):
        raise ProjectError('a passing numerical and target study is required before drawing')
    if bridge['design_accepted'] is not False or study['design_accepted'] is not False:raise ProjectError('invalid study acceptance claim')
    before={f:h for f,h in recorded.items()}
    before.update({str(f):digest(f) for f in (study_root/'three-phase.json',study_path,network)})
    return p,study,before


def identities(doc):
    return {e.dxf.handle:[(t.code,t.value) for t in e.get_xdata(APP)] if e.has_xdata(APP) else [] for e in doc.modelspace()}


def native_records(doc):
    from .cad_overlay import snapshot
    records=snapshot(doc)
    for row in records.values():
        # AutoCAD recomputes DXF group 10 for baseline centre/right text.
        # Group 11 is the actual placement anchor for these two modes.
        if row.get('type')=='TEXT' and row['halign'] in (1,2) and row['valign']==0:
            row['insert']=row['align_point']
    return records


def native(source,out,reference,exe):
    import ezdxf
    from .native_cad import execute,lisp_string
    from .cad_intake import export_dwg
    from .cad_overlay import equivalent
    from .cad_sheet import plot
    out.mkdir(parents=True,exist_ok=False);copied=out/'input.dxf';shutil.copyfile(source,copied)
    dwg=out/'electrical-schematic.dwg';script=out/'save.scr'
    guard=f'(= (strcase (vl-string-translate (chr 92) "/" (strcat (getvar "DWGPREFIX") (getvar "DWGNAME")))) (strcase {lisp_string(copied)}))'
    script.write_text(f'(if {guard} (progn (setvar "FILEDIA" 0) (setvar "CMDDIA" 0) (command "_.SAVEAS" "2018" {lisp_string(dwg)})) (princ "BSA WRONG DOCUMENT"))\n_.QUIT\n_Y\n',encoding='ascii')
    execute(exe,copied,script,out/'save.log',120)
    if not dwg.is_file():raise ProjectError('native DWG not produced')
    reopened=export_dwg(dwg,out/'reopened',exe)
    expected=ezdxf.readfile(source);actual=ezdxf.readfile(reopened)
    if not equivalent(native_records(expected),native_records(actual)) or identities(expected)!=identities(actual):raise ProjectError('native diagram geometry, attributes or identities changed')
    settings=dict(source='Schematic paper layout in millimetres, not installation scale',window_drawing_units=[0,0,270,180],
        scale_denominator=1,reference_handle=reference,pdf_tolerance_mm=0.5)
    result=plot(dwg,source,settings,out/'sheet.pdf',exe)
    return dict(native_reopen_pass=True,dwg_sha256=digest(dwg),engine_sha256=digest(exe),plot=result,visual_review='pending')


def run(project,study_root,out,dot,autocad=None):
    import ezdxf
    from ezdxf.enums import TextEntityAlignment
    from ezdxf.math import Bezier4P,Vec2
    project,study_root,out,dot=[Path(v).resolve() for v in (project,study_root,out,dot)]
    p,study,before=context(project,study_root)
    if digest(dot)!=DOT_SHA256:raise ProjectError('requires evaluated Graphviz 13.1.2 executable hash')
    before[str(dot)]=digest(dot)
    before[str(Path(__file__).resolve())]=digest(Path(__file__))
    for plugin in sorted(dot.parent.glob('gvplugin_*.dll')):before[str(plugin.resolve())]=digest(plugin)
    if (dot.parent/'config6').is_file():before[str((dot.parent/'config6').resolve())]=digest(dot.parent/'config6')
    if autocad:before[str(Path(autocad).resolve())]=digest(Path(autocad).resolve())
    if not out.is_relative_to(ROOT) or any(out==Path(f) or out in Path(f).parents for f in before):raise ProjectError('separate repository output required')
    if out.exists():raise ProjectError('refusing to overwrite drawing')
    all_ids=[r['id'] for key in ('buses','lines','loads') for r in p[key]]
    if any(not id.isascii() or len(id)>40 or any(ord(c)<32 for c in id) for id in all_ids):raise ProjectError('diagram IDs currently require <=40 printable ASCII characters')
    node_names={r['id']:'n'+str(i) for i,r in enumerate(p['buses'])}
    text=['digraph G {','graph [rankdir=LR,nodesep=0.6,ranksep=0.8,pad=0];',
          'node [shape=box,fontname=Courier,fontsize=10];','edge [dir=none,fontname=Courier,fontsize=9];']
    labels={}
    for row in study['nodes']:
        label=row['id']+'\n'+'\n'.join(f'V{ph}={v:.2f} V' for ph,v in zip('ABC',row['phase_voltage_v']))
        labels[('bus',row['id'])]=label.splitlines()
        text.append(node_names[row['id']]+' [label='+json.dumps(label)+'];')
    for i,(line,row) in enumerate(zip(p['lines'],study['lines'])):
        label=line['id']+'\nL='+f"{line['length_m']:.2f}"+' m\n'+'\n'.join(f'I{ph}={v:.2f} A' for ph,v in zip('ABC',row['phase_current_a']))
        labels[('line',line['id'])]=label.splitlines()
        text.append(node_names[line['from']]+' -> '+node_names[line['to']]+' [id="e'+str(i)+'",label='+json.dumps(label)+'];')
    text.append('}');out.mkdir(parents=True)
    (out/'layout.dot').write_text('\n'.join(text),encoding='ascii')
    proc=subprocess.run([str(dot),'-Tjson',str(out/'layout.dot')],capture_output=True,timeout=60)
    (out/'graphviz.log').write_bytes(proc.stderr)
    if proc.returncode:raise ProjectError('Graphviz failed; inspect graphviz.log')
    layout=json.loads(proc.stdout);(out/'layout.json').write_bytes(proc.stdout)
    bounds=[float(v) for v in layout['bb'].split(',')];factor=25.4/72
    if len(bounds)!=4 or any(not math.isfinite(v) for v in bounds) or (bounds[2]-bounds[0])*factor>250 or (bounds[3]-bounds[1])*factor>100:
        raise ProjectError('layout exceeds supported sheet; larger-sheet/pagination work remains required')
    doc=ezdxf.new('R2010');doc.units=4;doc.appids.new(APP)
    for name in ('BSA_ELEC_BUS','BSA_ELEC_LINE','BSA_ELEC_TEXT','BSA_ELEC_META'):doc.layers.new(name)
    msp=doc.modelspace();study_hash=digest(study_root/'native/study.json')
    def tag(entity,kind,id):
        entity.set_xdata(APP,[(1000,kind),(1000,id),(1000,study_hash)]);return entity
    def point(pt):
        if len(pt)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in pt):raise ProjectError('finite two-coordinate layout points required')
        return (10+(float(pt[0])-bounds[0])*factor,65+(float(pt[1])-bounds[1])*factor)
    def line(a,b,kind,id):
        if math.dist(a,b)>1e-9:tag(msp.add_line(a,b,dxfattribs={'layer':'BSA_ELEC_BUS' if kind=='bus' else 'BSA_ELEC_LINE'}),kind,id)
    seen_text={}
    def draw(row,kind,id):
        for op in row.get('_draw_',[]):
            if op['op'] in ('p','P'):
                pts=[point(v) for v in op['points']]
                for a,b in zip(pts,pts[1:]+pts[:1]):line(a,b,kind,id)
            elif op['op'] in ('b','B'):
                pts=[point(v) for v in op['points']]
                if (len(pts)-1)%3:raise ProjectError('invalid upstream Bezier points')
                for start in range(0,len(pts)-1,3):
                    flattened=list(Bezier4P([Vec2(v) for v in pts[start:start+4]]).flattening(0.01))
                    for a,b in zip(flattened,flattened[1:]):line(a,b,kind,id)
            elif op['op'] not in ('c','C','S'):raise ProjectError('unsupported upstream diagram primitive')
        size=10
        for op in row.get('_ldraw_',[]):
            if op['op']=='F':size=float(op['size'])
            elif op['op']=='T':
                align={'c':TextEntityAlignment.CENTER,'l':TextEntityAlignment.LEFT,'r':TextEntityAlignment.RIGHT}[op['align']]
                tag(msp.add_text(op['text'],dxfattribs={'layer':'BSA_ELEC_TEXT','height':size*factor*0.75}).set_placement(point(op['pt']),align=align),kind,id)
                seen_text.setdefault((kind,id),[]).append(op['text'])
    objects=layout.get('objects',[]);edges=layout.get('edges',[])
    if len(objects)!=len(p['buses']) or len(edges)!=len(p['lines']):raise ProjectError('layout node/edge coverage differs')
    bus_by_name={v:k for k,v in node_names.items()}
    bus_by_gvid={obj['_gvid']:bus_by_name[obj['name']] for obj in objects}
    if len(bus_by_gvid)!=len(p['buses']) or set(bus_by_gvid.values())!=set(node_names):raise ProjectError('layout bus identities differ')
    for obj in objects:draw(obj,'bus',bus_by_name[obj['name']])
    for edge in edges:
        index=int(edge['id'][1:]);original=p['lines'][index]
        if bus_by_gvid[edge['tail']]!=original['from'] or bus_by_gvid[edge['head']]!=original['to']:raise ProjectError('layout line endpoint identity differs')
        draw(edge,'line',original['id'])
    if seen_text!=labels:raise ProjectError('layout text does not match source-bound diagram labels')
    notes=['THREE-PHASE NETWORK STUDY - SCHEMATIC ONLY',
        'Schematic positions / paper scale. Labelled L values are source route lengths.',
        'No cable / protection selection or physical neutral. Not an installation drawing.',
        'Numerical and declared study targets passed; full engineering / HK review pending.',
        'Phase order A / B / C. See loads.csv and lines.csv for the complete schedules.']
    for i,note in enumerate(notes):tag(msp.add_text(note,dxfattribs={'insert':(10,170-i*6),'height':3 if i else 4,'layer':'BSA_ELEC_META'}),'meta','scope')
    reference=tag(msp.add_line((10,15),(60,15),dxfattribs={'layer':'BSA_ELEC_META'}),'meta','paper-reference')
    tag(msp.add_text('50 mm paper reference - not a route length',dxfattribs={'insert':(10,20),'height':2.5,'layer':'BSA_ELEC_META'}),'meta','paper-reference')
    source=out/'schematic.dxf';doc.saveas(source)
    from ezdxf import bbox
    extents=bbox.extents(doc.modelspace(),fast=True)
    if not extents.has_data or extents.extmin.x<0 or extents.extmin.y<0 or extents.extmax.x>270 or extents.extmax.y>180:raise ProjectError('diagram or labels exceed sheet window')
    from .cad_overlay import snapshot,reconcile
    reconcile(snapshot(doc),source)
    if identities(doc)!=identities(ezdxf.readfile(source)):raise ProjectError('saved DXF electrical identities changed')
    with (out/'loads.csv').open('x',newline='',encoding='utf-8') as f:
        writer=csv.writer(f);writer.writerow(['load_id','bus','phase','electrical_kw','reactive_kvar','source_id'])
        for load in p['loads']:
            for ph,kw,kvar in zip('ABC',load['p_kw'],load['q_kvar']):writer.writerow([load['id'],load['bus'],ph,kw,kvar,load['source']])
    with (out/'lines.csv').open('x',newline='',encoding='utf-8') as f:
        writer=csv.writer(f);writer.writerow(['line_id','from_bus','to_bus','source_route_length_m','phase','current_a','study_current_limit_a','source_id','limit_source_id'])
        for line_row,result in zip(p['lines'],study['lines']):
            for ph,amps in zip('ABC',result['phase_current_a']):writer.writerow([line_row['id'],line_row['from'],line_row['to'],line_row['length_m'],ph,amps,line_row['max_current_a'],line_row['source'],line_row['current_limit_source']])
    generated_before={str(f):digest(f) for f in (source,out/'loads.csv',out/'lines.csv',out/'layout.dot',out/'layout.json')}
    native_result=native(source,out/'native',reference.dxf.handle,Path(autocad).resolve()) if autocad else None
    if any(digest(Path(f))!=h for f,h in generated_before.items()):raise ProjectError('generated source artifacts changed during native delivery')
    if any(not Path(f).is_file() or digest(Path(f))!=h for f,h in before.items()):raise ProjectError('inputs changed during drawing')
    result=dict(inputs=before,study_sha256=study_hash,graphviz_sha256=digest(dot),bus_count=len(p['buses']),line_count=len(p['lines']),
        load_phase_rows=3*len(p['loads']),line_phase_rows=3*len(p['lines']),dxf_identity_pass=True,native=native_result,
        design_accepted=False,scope='Source-linked calculation schematic and schedules only; full installation, protection and Hong Kong acceptance pending')
    result['artifacts']={f.relative_to(out).as_posix():digest(f) for f in out.rglob('*') if f.is_file()}
    (out/'drawing.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('project',type=Path);parser.add_argument('--study',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True);parser.add_argument('--dot',type=Path,required=True);parser.add_argument('--autocad',type=Path)
    a=parser.parse_args();r=run(a.project,a.study,a.out,a.dot,a.autocad)
    print(json.dumps(dict(output=str(a.out),dxf_identity_pass=r['dxf_identity_pass'],native_reopen_pass=bool(r['native']),design_accepted=False)))


if __name__=='__main__':main()

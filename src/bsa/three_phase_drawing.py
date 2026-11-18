"""Calculation-bound Graphviz/ezdxf schematic, not an installation design."""
import argparse
from collections import defaultdict
import csv
from hashlib import sha256
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
    project = Path(project).resolve()
    project_hash = digest(project)
    p,files=prepare(project);study_root=Path(study_root).resolve()
    bridge_path = study_root/'three-phase.json'
    bridge_bytes = bridge_path.read_bytes()
    bridge = json.loads(bridge_bytes)
    expected=study_inputs(project)
    recorded=bridge['inputs']
    if not expected.issubset({Path(f) for f in recorded}) or len(recorded)!=len(expected)+1:
        raise ProjectError('study source inventory differs')
    if recorded.get(str(project)) != project_hash or any(
        not Path(f).is_file() or digest(Path(f)) != h for f, h in recorded.items()
    ):raise ProjectError('study inputs changed')
    study_path=study_root/'native/study.json';network=study_root/'native/network.json'
    study_bytes = study_path.read_bytes()
    study = json.loads(study_bytes)
    study_hash, network_hash = sha256(study_bytes).hexdigest(), digest(network)
    if study_hash!=bridge['study_sha256'] or network_hash!=bridge['network_sha256'] or study['network_sha256']!=network_hash:raise ProjectError('study artifacts changed')
    if study['inputs']!={str(f):digest(f) for f in files} or study['source_records']!=p['sources'] or study['versions']!=VERSIONS:raise ProjectError('study/project correspondence differs')
    if study['verification_pass'] is not True or bridge['status']!=study['status'] or type(study['study_targets_pass']) is not bool or study['status']!=('pass' if study['study_targets_pass'] else 'fail'):
        raise ProjectError('a verified numerical study is required')
    if require_targets and (study['status']!='pass' or study['study_targets_pass'] is not True):
        raise ProjectError('a passing numerical and target study is required before drawing')
    if bridge['design_accepted'] is not False or study['design_accepted'] is not False:raise ProjectError('invalid study acceptance claim')
    before={f:h for f,h in recorded.items()}
    before.update({str(bridge_path): sha256(bridge_bytes).hexdigest(),
                   str(study_path): study_hash, str(network): network_hash})
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


def bus_contacts(doc, circuits):
    from ezdxf.math import Vec2, intersection_line_line_2d

    def segment_distance(point, a, b):
        axis = b - a
        if not axis.magnitude_square:
            return point.distance(a)
        t = min(1, max(0, (point - a).dot(axis) / axis.magnitude_square))
        return point.distance(a + t * axis)

    geometry = defaultdict(list)
    for entity in doc.modelspace().query('LINE'):
        if entity.has_xdata(APP):
            kind, name = (tag.value for tag in entity.get_xdata(APP)[:2])
            if kind in ('bus', 'line'):
                start, end = entity.dxf.start, entity.dxf.end
                if any(not all(math.isfinite(v) for v in point) or abs(point.z) > 1e-6
                       for point in (start, end)) or start == end:
                    raise ProjectError(f'Saved {kind} {name} has invalid planar geometry on handle {entity.dxf.handle}')
                geometry[kind, name].append((start, end, entity.dxf.handle))
    checks = []
    bus_geometry = {name: segments for (kind, name), segments in geometry.items() if kind == 'bus'}
    for circuit in circuits:
        name, tail, head = (circuit[key] for key in ('id', 'from', 'to'))
        neighbors = defaultdict(list)
        for start, end, _ in geometry['line', name]:
            neighbors[start].append(end)
            neighbors[end].append(start)
        ends = [point for point, adjacent in neighbors.items() if len(adjacent) == 1]
        boxes = [geometry['bus', bus] for bus in (tail, head)]
        if len(ends) != 2 or any(not box for box in boxes):
            raise ProjectError(f'Cannot establish both bus contacts for line {name}')
        if any(len(adjacent) > 2 for adjacent in neighbors.values()):
            raise ProjectError(f'Saved line {name} branches within the circuit')
        reached = set()
        pending = [ends[0]]
        while pending:
            point = pending.pop()
            if point not in reached:
                reached.add(point)
                pending.extend(neighbors[point])
        if len(reached) != len(neighbors):
            raise ProjectError(f'Saved line {name} contains disconnected geometry')
        pairings = [
            [min(segment_distance(point, a, b) for a, b, _ in box)
             for point, box in zip(order, boxes)]
            for order in (ends, ends[::-1])
        ]
        matches = [distances for distances in pairings if max(distances) <= 1e-6]
        if not matches:
            raise ProjectError(f'Saved line {name} does not meet its declared buses {tail} and {head}')
        if len(matches) != 1:
            raise ProjectError(f'Saved line {name} has ambiguous contacts at buses {tail} and {head}')
        distances = matches[0]
        for bus, segments in bus_geometry.items():
            if bus in (tail, head):
                continue
            for a, b, line_handle in geometry['line', name]:
                for c, d, bus_handle in segments:
                    if (intersection_line_line_2d((Vec2(a), Vec2(b)), (Vec2(c), Vec2(d)), virtual=False)
                            is not None or min(segment_distance(a, c, d), segment_distance(b, c, d),
                                               segment_distance(c, a, b), segment_distance(d, a, b)) <= 1e-6):
                        raise ProjectError(f'Saved line {name} touches undeclared bus {bus} '
                                           f'(line handle {line_handle}, bus handle {bus_handle})')
        checks.append(dict(line=name, from_bus=tail, to_bus=head,
                           from_gap_mm=distances[0], to_gap_mm=distances[1]))
    return checks


def native(source,out,reference,exe,project,study,study_hash):
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
    contacts = check_saved_schematic(actual, project, study, study_hash)
    settings=dict(source='Schematic paper layout in millimetres, not installation scale',window_drawing_units=[0,0,270,180],
        scale_denominator=1,reference_handle=reference,pdf_tolerance_mm=0.5)
    result=plot(dwg,source,settings,out/'sheet.pdf',exe)
    return dict(native_reopen_pass=True,dwg_sha256=digest(dwg),engine_sha256=digest(exe),
                bus_contacts=contacts,plot=result,visual_review='pending')


def schematic_labels(project, study):
    labels = {
        ('bus', row['id']): [row['id'], *(f'V{phase}={value:.2f} V'
                                        for phase, value in zip('ABC', row['phase_voltage_v']))]
        for row in study['nodes']
    }
    for line, row in zip(project['lines'], study['lines']):
        labels['line', line['id']] = [
            line['id'], f"L={line['length_m']:.2f} m",
            *(f'I{phase}={value:.2f} A' for phase, value in zip('ABC', row['phase_current_a'])),
        ]
    return labels


def verify_contacts(project, study, drawing):
    import ezdxf
    from . import workspace

    project, study, drawing = (Path(path).resolve() for path in (project, study, drawing))
    if not all(workspace.allowed(path) for path in (project, study, drawing)) or drawing.suffix.lower() != '.dxf':
        raise ProjectError('Select a saved DXF, project and study in the permitted workspace')
    prepared, study_result, pins = context(project, study)
    source_hash = digest(drawing)
    study_hash = pins[str(study/'native/study.json')]
    contacts = check_saved_schematic(ezdxf.readfile(drawing), prepared, study_result, study_hash)
    if digest(drawing) != source_hash or any(digest(Path(path)) != sha for path, sha in pins.items()):
        raise ProjectError('Schematic or study changed during contact verification')
    return dict(drawing_sha256=source_hash, study_sha256=study_hash, bus_contacts=contacts,
                design_accepted=False)


def check_saved_schematic(doc, prepared, study_result, study_hash):
    if doc.units != 4:
        raise ProjectError('Three-phase schematic requires drawing millimetres')
    expected = {('bus', row['id']) for row in prepared['buses']}
    expected.update(('line', row['id']) for row in prepared['lines'])
    observed = set()
    labels = defaultdict(list)
    bus_edges = defaultdict(list)
    kinds = {'BSA_ELEC_LINE': 'line', 'BSA_ELEC_BUS': 'bus'}
    for entity in doc.modelspace():
        kind = kinds.get(entity.dxf.layer)
        if kind:
            if entity.dxftype() != 'LINE' or not entity.has_xdata(APP):
                raise ProjectError(f'Missing electrical identity on handle {entity.dxf.handle}')
            tags = [tag.value for tag in entity.get_xdata(APP)]
            if len(tags) != 3 or tags[0] != kind or tags[2] != study_hash:
                raise ProjectError(f'Drawing study identity differs on handle {entity.dxf.handle}')
            observed.add(tuple(tags[:2]))
            if kind == 'bus':
                a, b = entity.dxf.start, entity.dxf.end
                bus_edges[tags[1]].append(frozenset(((a.x, a.y), (b.x, b.y))))
        elif entity.dxf.layer == 'BSA_ELEC_TEXT':
            tags = [tag.value for tag in entity.get_xdata(APP)] if entity.has_xdata(APP) else []
            if entity.dxftype() != 'TEXT' or len(tags) != 3 or tags[2] != study_hash or tuple(tags[:2]) not in expected:
                raise ProjectError(f'Drawing label study identity differs on handle {entity.dxf.handle}')
            labels[tuple(tags[:2])].append(entity)
        elif entity.dxftype() == 'LINE' and entity.has_xdata(APP):
            if entity.get_xdata(APP)[0].value in kinds.values():
                raise ProjectError(f'Electrical geometry outside scoped layers on handle {entity.dxf.handle}')
    if observed != expected:
        raise ProjectError('Saved schematic circuit or bus inventory differs from the study')
    for key, expected_text in schematic_labels(prepared, study_result).items():
        if sorted(entity.dxf.text for entity in labels[key]) != sorted(expected_text):
            raise ProjectError(f'Saved {key[0]} {key[1]} labels differ from the study')
    contacts = bus_contacts(doc, prepared['lines'])
    for bus, edges in bus_edges.items():
        if len(edges) != 4:
            raise ProjectError(f'Saved bus {bus} does not have a closed rectangular outline')
        corners = set().union(*edges)
        x_values, y_values = ({point[axis] for point in corners} for axis in (0, 1))
        sides = {frozenset((a, b)) for a in corners for b in corners
                 if a != b and (a[0] == b[0] or a[1] == b[1])}
        if len(x_values) != 2 or len(y_values) != 2 or len(corners) != 4 or set(edges) != sides:
            raise ProjectError(f'Saved bus {bus} does not have a closed rectangular outline')
        for label in labels['bus', bus]:
            _, anchor, _ = label.get_placement()
            if (tuple(label.dxf.extrusion) != (0, 0, 1) or not abs(anchor.z) <= 1e-6
                    or not min(x_values) < anchor.x < max(x_values)
                    or not min(y_values) < anchor.y < max(y_values)):
                raise ProjectError(f'Saved bus {bus} label anchor lies outside its box on handle {label.dxf.handle}')
    return contacts


def run(project,study_root,out,dot,autocad=None):
    import ezdxf
    from ezdxf.enums import TextEntityAlignment
    from ezdxf.math import Bezier4P,Vec2
    project,study_root,out,dot=[Path(v).resolve() for v in (project,study_root,out,dot)]
    p,study,before=context(project,study_root)
    graphviz_sha256 = digest(dot)
    if graphviz_sha256!=DOT_SHA256:raise ProjectError('requires evaluated Graphviz 13.1.2 executable hash')
    before[str(dot)]=graphviz_sha256
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
    labels=schematic_labels(p, study)
    for row in study['nodes']:
        label='\n'.join(labels['bus', row['id']])
        text.append(node_names[row['id']]+' [label='+json.dumps(label)+'];')
    for i,line in enumerate(p['lines']):
        label='\n'.join(labels['line', line['id']])
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
    msp=doc.modelspace();study_hash=before[str(study_root/'native/study.json')]
    def tag(entity,kind,id):
        entity.set_xdata(APP,[(1000,kind),(1000,id),(1000,study_hash)]);return entity
    def point(pt):
        if len(pt)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in pt):raise ProjectError('finite two-coordinate layout points required')
        return (10+(float(pt[0])-bounds[0])*factor,65+(float(pt[1])-bounds[1])*factor)
    def line(a,b,kind,id):
        if math.dist(a,b)>1e-9:tag(msp.add_line(a,b,dxfattribs={'layer':'BSA_ELEC_BUS' if kind=='bus' else 'BSA_ELEC_LINE'}),kind,id)
    seen_text={}
    bus_boxes = {}
    def join_bus(anchor, bus, circuit):
        (left, right), (bottom, top) = bus_boxes[bus]
        x, y = anchor
        on_box_x = min(max(x, left), right)
        on_box_y = min(max(y, bottom), top)
        sides = [(left, on_box_y), (right, on_box_y), (on_box_x, bottom), (on_box_x, top)]
        nearest = min(sides, key=lambda candidate: math.dist(anchor, candidate))
        # Graphviz rounds and clips spline endpoints just outside node boxes.
        if math.dist(anchor, nearest) > factor:
            raise ProjectError(f'Line {circuit} does not meet bus {bus} in the layout')
        return nearest

    def draw(row,kind,id,peers=None):
        bus_outline = []
        for op in row.get('_draw_',[]):
            if op['op'] in ('p','P'):
                pts=[point(v) for v in op['points']]
                if kind == 'bus':
                    bus_outline.extend(pts)
                for a,b in zip(pts,pts[1:]+pts[:1]):line(a,b,kind,id)
            elif op['op'] in ('b','B'):
                pts=[point(v) for v in op['points']]
                if len(pts)<4 or (len(pts)-1)%3:raise ProjectError('invalid upstream Bezier points')
                if peers:
                    pts[0] = join_bus(pts[0], peers[0], id)
                    pts[-1] = join_bus(pts[-1], peers[1], id)
                for start in range(0,len(pts)-1,3):
                    flattened=list(Bezier4P([Vec2(v) for v in pts[start:start+4]]).flattening(0.01))
                    for a,b in zip(flattened,flattened[1:]):line(a,b,kind,id)
            elif op['op'] not in ('c','C','S'):raise ProjectError('unsupported upstream diagram primitive')
        if kind == 'bus':
            if not bus_outline:
                raise ProjectError(f'Bus {id} has no layout box')
            bus_boxes[id] = [(min(axis), max(axis)) for axis in zip(*bus_outline)]
        size=10
        for op in row.get('_ldraw_',[]):
            if op['op']=='F':size=float(op['size'])
            elif op['op']=='T':
                align={'c':TextEntityAlignment.CENTER,'l':TextEntityAlignment.LEFT,'r':TextEntityAlignment.RIGHT}[op['align']]
                anchor = point(op['pt'])
                if kind == 'bus' and any(
                    not low < value < high for (low, high), value in zip(bus_boxes[id], anchor)
                ):
                    raise ProjectError(f'Bus {id} label anchor lies outside its box')
                tag(msp.add_text(op['text'],dxfattribs={'layer':'BSA_ELEC_TEXT','height':size*factor*0.75}).set_placement(anchor,align=align),kind,id)
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
        if sum(op['op'] in ('b','B') for op in edge.get('_draw_', [])) != 1:
            raise ProjectError(f"Line {original['id']} requires one layout spline")
        draw(edge,'line',original['id'],(original['from'],original['to']))
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
    saved = ezdxf.readfile(source)
    if identities(doc)!=identities(saved):raise ProjectError('saved DXF electrical identities changed')
    dxf_contacts = check_saved_schematic(saved, p, study, study_hash)
    with (out/'loads.csv').open('x',newline='',encoding='utf-8') as f:
        writer=csv.writer(f);writer.writerow(['load_id','bus','phase','electrical_kw','reactive_kvar','source_id'])
        for load in p['loads']:
            for ph,kw,kvar in zip('ABC',load['p_kw'],load['q_kvar']):writer.writerow([load['id'],load['bus'],ph,kw,kvar,load['source']])
    with (out/'lines.csv').open('x',newline='',encoding='utf-8') as f:
        writer=csv.writer(f);writer.writerow(['line_id','from_bus','to_bus','source_route_length_m','phase','current_a','study_current_limit_a','source_id','limit_source_id'])
        for line_row,result in zip(p['lines'],study['lines']):
            for ph,amps in zip('ABC',result['phase_current_a']):writer.writerow([line_row['id'],line_row['from'],line_row['to'],line_row['length_m'],ph,amps,line_row['max_current_a'],line_row['source'],line_row['current_limit_source']])
    generated_before={str(f):digest(f) for f in (source,out/'loads.csv',out/'lines.csv',out/'layout.dot',out/'layout.json')}
    native_result=native(source,out/'native',reference.dxf.handle,Path(autocad).resolve(),p,study,study_hash) if autocad else None
    if any(digest(Path(f))!=h for f,h in generated_before.items()):raise ProjectError('generated source artifacts changed during native delivery')
    if any(not Path(f).is_file() or digest(Path(f))!=h for f,h in before.items()):raise ProjectError('inputs changed during drawing')
    result=dict(inputs=before,study_sha256=study_hash,graphviz_sha256=graphviz_sha256,bus_count=len(p['buses']),line_count=len(p['lines']),
        load_phase_rows=3*len(p['loads']),line_phase_rows=3*len(p['lines']),dxf_identity_pass=True,
        dxf_bus_contacts=dxf_contacts,native=native_result,
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

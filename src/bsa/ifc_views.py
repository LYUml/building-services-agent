"""Source-linked orthographic IFC pipe views, including symbolic end-on segments."""
import argparse
import csv
import html
import json
import math
from pathlib import Path
import re
from .cli import digest
from .engine import ProjectError
from .ifc_drawing import AXES,extract
from .ifc_native import validate_settings as validate_sheet


def label_text(row,settings,mode):
    return f"{settings['labels'][row['guid']]}  ID {row['inner_diameter_m']*1000:g}/OD {row['outside_diameter_m']*1000:g} mm  L {row['length_m']:g} m"+(' END-ON' if mode=='end_on' else '')


def validate_settings(p):
    if not isinstance(p,dict) or set(p)!={'version','source','annotation_height_m','end_on_marker_half_size_m','labels','views'} or type(p['version']) is not int or p['version']!=1:
        raise ProjectError('versioned multiview settings, explicit labels and end-on symbol size required')
    if not isinstance(p['source'],str) or not p['source'].strip():raise ProjectError('multiview provenance required')
    for key in ('annotation_height_m','end_on_marker_half_size_m'):
        if type(p[key]) not in (int,float) or not math.isfinite(p[key]) or not .001<=p[key]<=1:raise ProjectError('annotation/symbol sizes must be 0.001..1 metre')
    labels=p['labels']
    if not isinstance(labels,dict) or not labels:raise ProjectError('complete explicit segment label map required')
    for guid,label in labels.items():
        if not isinstance(guid,str) or not re.fullmatch(r'[0-3][0-9A-Za-z_$]{21}',guid) or not isinstance(label,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,15}',label):raise ProjectError('GUIDs and unique short ASCII callouts required; full names remain in schedule')
    if len(set(labels.values()))!=len(labels):raise ProjectError('unique segment callouts required')
    if not isinstance(p['views'],list) or not 2<=len(p['views'])<=3:raise ProjectError('two or three distinct orthographic planes required')
    ids=set();planes=set()
    for view in p['views']:
        if not isinstance(view,dict) or set(view)!={'id','projection_axes','sheet'}:raise ProjectError('view ID, ordered axes and sourced sheet settings required')
        id=view['id'];axes=view['projection_axes']
        if not isinstance(id,str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,30}',id) or id in ids:raise ProjectError('unique path-safe view IDs required')
        if not isinstance(axes,list) or len(axes)!=2 or any(not isinstance(a,str) or a not in AXES for a in axes) or len(set(axes))!=2 or frozenset(axes) in planes:raise ProjectError('distinct orthographic planes required')
        ids.add(id);planes.add(frozenset(axes));validate_sheet(view['sheet'])
        if view['sheet']['reference_ifc_guid'] not in labels:raise ProjectError('sheet reference must be a declared segment')
    return p


def draw_view(rows,settings,view,out):
    import ezdxf
    h=settings['annotation_height_m'];radius=settings['end_on_marker_half_size_m'];axes=[AXES[a] for a in view['projection_axes']]
    doc=ezdxf.new('R2018');doc.header['$INSUNITS']=6;doc.appids.new('BSA_IFC')
    for name,color,weight in [('BSA_PIPE_AXIS',4,25),('BSA_END_ON',2,25),('BSA_LABEL',7,18),('BSA_LEADER',8,9)]:doc.layers.new(name,dxfattribs={'color':color,'lineweight':weight})
    ms=doc.modelspace();records=[];svg=[];projected=[]
    for row in rows:
        a,b=[[pt[i] for i in axes] for pt in (row['start_world_m'],row['end_world_m'])]
        projected.append((row,a,b,math.dist(a,b)))
    label_x=max(pt[0] for _,a,b,_ in projected for pt in (a,b))+4*h
    window=view['sheet']['window_drawing_units'];label_y=window[3]-2
    def line(a,b,layer,guid):
        e=ms.add_line(a,b,dxfattribs={'layer':layer});e.set_xdata('BSA_IFC',[(1000,guid)])
        svg.append(f'<line x1="{a[0]}" y1="{-a[1]}" x2="{b[0]}" y2="{-b[1]}" stroke="{"#888" if layer=="BSA_LEADER" else "black"}" stroke-width="{h/(25 if layer=="BSA_LEADER" else 12)}"/>');return e.dxf.handle
    def text(value,point,guid=None):
        e=ms.add_text(value,dxfattribs={'height':h,'insert':point,'layer':'BSA_LABEL'})
        if guid:e.set_xdata('BSA_IFC',[(1000,guid)])
        svg.append(f'<text x="{point[0]}" y="{-point[1]}" font-size="{h}">{html.escape(value)}</text>');return e.dxf.handle
    for row,a,b,length in sorted(projected,key=lambda r:(-(r[1][1]+r[2][1])/2,r[0]['guid'])):
        guid=row['guid'];middle=[(a[i]+b[i])/2 for i in (0,1)];handles=[];mode='axis' if length>1e-9 else 'end_on'
        if mode=='axis':handles.append(line(a,b,'BSA_PIPE_AXIS',guid))
        else:
            for sign in (-1,1):handles.append(line([middle[0]-radius,middle[1]-sign*radius],[middle[0]+radius,middle[1]+sign*radius],'BSA_END_ON',guid))
        label=label_text(row,settings,mode)
        handles.append(line(middle,[label_x-h,label_y],'BSA_LEADER',guid));handles.append(text(label,[label_x,label_y],guid))
        records.append(dict(guid=guid,label=settings['labels'][guid],mode=mode,projected_start_m=a,projected_end_m=b,projected_length_m=length,true_length_m=row['length_m'],handles=handles))
        label_y-=3*h
    titles=[f"{' / '.join(view['projection_axes'])} pipe projection; scale 1:{view['sheet']['scale_denominator']:g}; coordinates m",
            'Labels show true lengths; X marks a symbolic end-on pipe, not its diameter',
            'Pipes only; fittings, equipment and installation detail remain pending']
    for i,title in enumerate(titles):text(title,[window[0]+2*h,window[3]-(i+2)*1.6*h])
    # Conservative ASCII text allowance is a layout precheck; actual PDF review is separate.
    for e in ms:
        points=[e.dxf.start,e.dxf.end] if e.dxftype()=='LINE' else [e.dxf.insert,(e.dxf.insert.x+len(e.dxf.text)*h*.8,e.dxf.insert.y+1.3*h)]
        if any(not window[0]<=pt[0]<=window[2] or not window[1]<=pt[1]<=window[3] for pt in points):raise ProjectError('view geometry/annotation allowance falls outside declared sheet window')
    reference=next((r for r in records if r['guid']==view['sheet']['reference_ifc_guid']),None)
    if not reference or reference['mode']!='axis':raise ProjectError('sheet reference must have a nonzero projected axis in its own view')
    out.mkdir(parents=True,exist_ok=False);path=out/'segments.dxf';doc.saveas(path)
    from .cad_overlay import reconcile,snapshot
    from .ifc_native import identity
    reconcile(snapshot(doc),path)
    reopened=ezdxf.readfile(path)
    if identity(doc)!=identity(reopened):raise ProjectError('reopened multiview entity/GUID inventory mismatch')
    for record in records:
        for handle in record['handles']:
            e=reopened.entitydb[handle]
            if [(t.code,t.value) for t in e.get_xdata('BSA_IFC')]!=[(1000,record['guid'])]:raise ProjectError('reopened multiview GUID mismatch')
        e=reopened.entitydb[record['handles'][0]]
        if record['mode']=='axis' and (not e.dxf.start.isclose((*record['projected_start_m'],0),abs_tol=1e-9,rel_tol=0) or not e.dxf.end.isclose((*record['projected_end_m'],0),abs_tol=1e-9,rel_tol=0)):raise ProjectError('reopened multiview axis geometry mismatch')
    (out/'sheet.json').write_text(json.dumps(view['sheet'],indent=2),encoding='utf-8')
    (out/'preview.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" font-family="Arial,sans-serif" viewBox="{window[0]} {-window[3]} {window[2]-window[0]} {window[3]-window[1]}">'+''.join(svg)+'</svg>',encoding='utf-8')
    return dict(id=view['id'],projection_axes=view['projection_axes'],segments=records,dxf='views/'+view['id']+'/segments.dxf',sheet='views/'+view['id']+'/sheet.json')


def run(ifc,settings_path,out):
    ifc,settings_path,out=[Path(p).resolve() for p in (ifc,settings_path,out)]
    if any(out==p or out in p.parents for p in (ifc,settings_path)):raise ProjectError('output must not contain sources')
    before={str(p):digest(p) for p in (ifc,settings_path)};settings=validate_settings(json.loads(settings_path.read_text(encoding='utf-8-sig')))
    source=extract(ifc)
    if not source['calculated_checks_pass']:raise ProjectError('complete supported IFC segment coverage required: '+json.dumps(source['unsupported_segments']))
    rows=source['segments']
    if set(settings['labels'])!={r['guid'] for r in rows}:raise ProjectError('exact IFC segment/callout coverage required')
    out.mkdir(parents=True,exist_ok=False);views=[]
    for view in settings['views']:views.append(draw_view(rows,settings,view,out/'views'/view['id']))
    coverage={r['guid']:[v['id'] for v in views if any(s['guid']==r['guid'] and s['mode']=='axis' for s in v['segments'])] for r in rows}
    if any(not ids for ids in coverage.values()):raise ProjectError('each segment needs a nonzero axis in at least one view')
    with (out/'segments.csv').open('w',newline='',encoding='utf-8') as stream:
        fields=['label','guid','name','ifc_class','inner_diameter_m','outside_diameter_m','length_m','source'];writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore');writer.writeheader()
        writer.writerows(dict(row,label=settings['labels'][row['guid']]) for row in rows)
    if any(digest(Path(p))!=sha for p,sha in before.items()):raise ProjectError('source changed during multiview generation')
    result=dict(version=1,inputs=before,inputs_unchanged=True,settings=settings,source_geometry=source,views=views,axis_coverage=coverage,
                calculated_checks_pass=True,design_accepted=False,scope='orthographic pipe/duct centreline views with explicit symbolic end-on representation; projected and true lengths distinct',
                pending=['native DWG reopen and actual PDF visual review','hidden-line treatment, finite fittings/equipment and installation detail','full engineering acceptance'])
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'views.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


def verify_manifest(path):
    path=Path(path).resolve();p=json.loads(path.read_text(encoding='utf-8-sig'))
    if type(p.get('version')) is not int or p.get('version')!=1 or p.get('calculated_checks_pass') is not True or p.get('inputs_unchanged') is not True:raise ProjectError('passing multiview manifest required')
    validate_settings(p['settings'])
    if not isinstance(p.get('artifacts'),dict) or not p['artifacts']:raise ProjectError('multiview artifact inventory required')
    for name,sha in p['artifacts'].items():
        file=(path.parent/name).resolve()
        if not file.is_relative_to(path.parent) or not file.is_file() or digest(file)!=sha:raise ProjectError('multiview input artifact missing/changed/escaping its directory')
    expected={v['id']:v for v in p['settings']['views']}
    rows={r['guid']:r for r in p['source_geometry']['segments']}
    if p['source_geometry']['calculated_checks_pass'] is not True or set(rows)!=set(p['settings']['labels']):raise ProjectError('complete source geometry/callout coverage required')
    coverage={guid:[] for guid in rows}
    if len(p['views'])!=len(expected) or {v['id'] for v in p['views']}!=set(expected):raise ProjectError('manifest view coverage differs')
    for view in p['views']:
        id=view['id']
        if view['projection_axes']!=expected[id]['projection_axes'] or view['dxf']!='views/'+id+'/segments.dxf' or view['sheet']!='views/'+id+'/sheet.json':raise ProjectError('manifest view paths/axes differ')
        if view['dxf'] not in p['artifacts'] or view['sheet'] not in p['artifacts']:raise ProjectError('manifest omits required native inputs')
        if json.loads((path.parent/view['sheet']).read_text())!=expected[id]['sheet']:raise ProjectError('serialized sheet differs from manifest')
        import ezdxf
        doc=ezdxf.readfile(path.parent/view['dxf']);axes=[AXES[a] for a in view['projection_axes']]
        if doc.header.get('$INSUNITS')!=6 or len(view['segments'])!=len(rows) or {r['guid'] for r in view['segments']}!=set(rows):raise ProjectError('DXF units or per-view segment coverage differs')
        handles=[];h=p['settings']['annotation_height_m'];radius=p['settings']['end_on_marker_half_size_m']
        label_x=max(pt[axes[0]] for row in rows.values() for pt in (row['start_world_m'],row['end_world_m']))+4*h
        def close(a,b):return len(a)==len(b) and all(abs(x-y)<=1e-9 for x,y in zip(a,b))
        for index,record in enumerate(view['segments']):
            row=rows[record['guid']];a,b=[[pt[i] for i in axes] for pt in (row['start_world_m'],row['end_world_m'])]
            length=math.dist(a,b);mode='axis' if length>1e-9 else 'end_on';middle=[(a[i]+b[i])/2 for i in (0,1)]
            if record['mode']!=mode or not close(record['projected_start_m'],a) or not close(record['projected_end_m'],b) or abs(record['projected_length_m']-length)>1e-9 or abs(record['true_length_m']-row['length_m'])>1e-9:raise ProjectError('projection facts differ from saved source coordinates')
            entities=[doc.entitydb.get(handle) for handle in record['handles']];handles+=record['handles']
            if len(entities)!=(3 if mode=='axis' else 4) or any(e is None or not e.has_xdata('BSA_IFC') or [(t.code,t.value) for t in e.get_xdata('BSA_IFC')]!=[(1000,record['guid'])] for e in entities):raise ProjectError('view entity identity/coverage differs')
            segments=[(a,b)] if mode=='axis' else [([middle[0]-radius,middle[1]-sign*radius],[middle[0]+radius,middle[1]+sign*radius]) for sign in (-1,1)]
            for e,(start,end) in zip(entities,segments):
                if e.dxftype()!='LINE' or e.dxf.layer!=('BSA_PIPE_AXIS' if mode=='axis' else 'BSA_END_ON') or not close(list(e.dxf.start),start+[0]) or not close(list(e.dxf.end),end+[0]):raise ProjectError('projected axis/end-on glyph differs from source')
            if mode=='axis':coverage[row['guid']].append(id)
            text=entities[-1];leader=entities[-2];label_y=expected[id]['sheet']['window_drawing_units'][3]-2-index*3*h
            if text.dxftype()!='TEXT' or text.dxf.layer!='BSA_LABEL' or text.dxf.text!=label_text(row,p['settings'],mode) or abs(text.dxf.height-h)>1e-9 or not close(list(text.dxf.insert),[label_x,label_y,0]) or text.dxf.rotation!=0 or text.dxf.width!=1:raise ProjectError('multiview annotation differs')
            if leader.dxftype()!='LINE' or leader.dxf.layer!='BSA_LEADER' or not close(list(leader.dxf.start),middle+[0]) or not close(list(leader.dxf.end),[label_x-h,label_y,0]):raise ProjectError('multiview leader differs')
        linked={e.dxf.handle for e in doc.modelspace() if e.has_xdata('BSA_IFC')}
        if len(set(handles))!=len(handles) or set(handles)!=linked or len(doc.modelspace())!=len(handles)+3:raise ProjectError('unexpected/missing multiview model entities')
    if p['axis_coverage']!=coverage or any(not views for views in coverage.values()):raise ProjectError('combined nonzero projection coverage differs')
    return p


def run_native(manifest,out,exe):
    from .ifc_native import run as native
    from pypdf import PdfReader,PdfWriter
    manifest,out,exe=[Path(p).resolve() for p in (manifest,out,exe)];p=verify_manifest(manifest)
    inputs=[manifest]+[manifest.parent/name for name in p['artifacts']]
    if any(out==f or out in f.parents for f in inputs):raise ProjectError('native output must not contain multiview inputs')
    before={str(f):digest(f) for f in inputs};out.mkdir(parents=True,exist_ok=False);results=[];writer=PdfWriter();contents=[]
    for view in p['views']:
        folder=out/view['id'];r=native(manifest.parent/view['dxf'],manifest.parent/view['sheet'],folder,exe)
        results.append(dict(id=view['id'],native=r));reader=PdfReader(folder/'sheet.pdf');contents.append(reader.pages[0].get_contents().get_data());writer.append(reader)
    with (out/'drawing-set.pdf').open('wb') as stream:writer.write(stream)
    merged=PdfReader(out/'drawing-set.pdf')
    matching=len(merged.pages)==len(contents) and all(page.get_contents().get_data()==content for page,content in zip(merged.pages,contents))
    if not matching:raise ProjectError('merged PDF page content differs from verified source sheets')
    if any(digest(Path(f))!=sha for f,sha in before.items()):raise ProjectError('source multiview artifacts changed during native delivery')
    result=dict(inputs=before,inputs_unchanged=True,views=results,merged_page_content_match=matching,
                calculated_checks_pass=matching and all(v['native']['native_reopen_pass'] and v['native']['plot']['pdf_reference_pass'] for v in results),design_accepted=False,
                pending=['actual merged PDF visual review','hidden lines, fittings/equipment and installation-sheet detail','complete engineering acceptance'])
    result['artifacts']={f.relative_to(out).as_posix():digest(f) for f in out.rglob('*') if f.is_file()}
    (out/'native-views.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source',type=Path);parser.add_argument('--settings',type=Path);parser.add_argument('--out',required=True,type=Path);parser.add_argument('--autocad',type=Path);a=parser.parse_args()
    if a.autocad:r=run_native(a.source,a.out,a.autocad)
    elif a.settings:r=run(a.source,a.settings,a.out)
    else:parser.error('--settings for IFC views, or --autocad for a native views.json input')
    print(json.dumps({k:r[k] for k in ('calculated_checks_pass','design_accepted')}));return 0 if r['calculated_checks_pass'] else 2


if __name__=='__main__':raise SystemExit(main())

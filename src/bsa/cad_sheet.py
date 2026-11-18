"""Explicit-scale A4/A1 model-window plotting with independent PDF line measurement."""
import json
import math
from pathlib import Path
from .engine import ProjectError
from .cli import digest
from .cad_intake import METRES_PER_UNIT
from .native_cad import execute,lisp_string


def pdf_lines(path):
    from pypdf import PdfReader
    from pypdf.generic import ContentStream
    reader=PdfReader(path)
    if len(reader.pages)!=1:raise ProjectError('single sheet expected')
    page=reader.pages[0]
    if page.get('/Rotate',0) or page.get('/UserUnit',1)!=1:raise ProjectError('unsupported PDF page rotation/unit')
    matrix=[1.,0.,0.,1.,0.,0.];stack=[];paths=[];lines=[];current=None;start=None
    def point(x,y):
        a,b,c,d,e,f=matrix;return (a*x+c*y+e,b*x+d*y+f)
    for args,op in ContentStream(page.get_contents(),reader).operations:
        v=[float(x) for x in args] if op in (b'cm',b'm',b'l',b'c',b'v',b'y',b're') else []
        if op==b'q':stack.append(matrix[:])
        elif op==b'Q':matrix=stack.pop()
        elif op==b'cm':
            a,b,c,d,e,f=matrix;g,h,i,j,k,l=v
            matrix=[a*g+c*h,b*g+d*h,a*i+c*j,b*i+d*j,a*k+c*l+e,b*k+d*l+f]
        elif op==b'm':current=start=point(*v)
        elif op==b'l':
            target=point(*v)
            if current is not None:paths.append((current,target))
            current=target
        elif op in (b'c',b'v',b'y'):current=point(*v[-2:])
        elif op==b're':
            x,y,w,h=v;corners=[point(x,y),point(x+w,y),point(x+w,y+h),point(x,y+h)]
            paths.extend(zip(corners,corners[1:]+corners[:1]));current=start=corners[0]
        elif op in (b'h',b's',b'b',b'b*'):
            if current is not None and start is not None:paths.append((current,start))
            current=start
        if op in (b'S',b's',b'B',b'B*',b'b',b'b*'):lines.extend(paths);paths=[];current=start=None
        elif op in (b'n',b'f',b'f*',b'F'):paths=[];current=start=None
    factor=25.4/72
    return ([float(page.mediabox.width)*factor,float(page.mediabox.height)*factor],
            [([x*factor for x in a],[x*factor for x in b]) for a,b in lines])


def reference_points(doc,settings):
    ref=doc.entitydb.get(settings['reference_handle'])
    index=settings.get('reference_segment_index')
    if ref is None:raise ProjectError('Existing reference entity required')
    if ref.dxftype()=='LINE' and index is None:return ref.dxf.start,ref.dxf.end
    if ref.dxftype()!='LWPOLYLINE' or type(index) is not int:raise ProjectError('LINE or explicit straight polyline segment required')
    points=list(ref.vertices_in_wcs());count=len(points) if ref.closed else len(points)-1
    if not 0<=index<count or ref.get_points()[index][4]!=0:raise ProjectError('Existing straight polyline segment required')
    return points[index],points[(index+1)%len(points)]


def check_window_entities(doc, handles, window):
    from ezdxf import bbox

    if (not isinstance(window, list) or len(window) != 4
            or any(type(value) not in (int, float) or not math.isfinite(value) for value in window)
            or window[0] >= window[2] or window[1] >= window[3]):
        raise ProjectError('Required plot entities need a finite, ordered plot window')
    if (not isinstance(handles, list) or not handles
            or any(not isinstance(handle, str) or not handle for handle in handles)
            or len({handle.upper() for handle in handles}) != len(handles)):
        raise ProjectError('required_window_handles must contain distinct modelspace entity handles')
    entities = {entity.dxf.handle: entity for entity in doc.modelspace()}
    for handle in handles:
        entity = entities.get(handle.upper())
        if entity is None or entity.dxftype() not in ('LINE', 'CIRCLE', 'LWPOLYLINE', 'TEXT'):
            raise ProjectError(f'Plot window handle {handle} requires a supported modelspace entity')
        bounds = bbox.extents([entity])
        if (not bounds.has_data
                or not (window[0] <= bounds.extmin.x <= bounds.extmax.x <= window[2]
                        and window[1] <= bounds.extmin.y <= bounds.extmax.y <= window[3])):
            raise ProjectError(f'Estimated bounds of {entity.dxftype()} handle {handle} exceed the plot window')


def check_text_line_clearance(doc, settings):
    from .cad_text_layout import text_box
    from .route_drawing_qa import enters

    if not isinstance(settings, dict) or set(settings) != {'text_handles', 'line_layers'}:
        raise ProjectError('Text-line check requires explicit text handles and line layers')
    handles, layers = settings['text_handles'], settings['line_layers']
    for values in (handles, layers):
        if (not isinstance(values, list) or not values
                or any(not isinstance(value, str) or not value.strip() for value in values)
                or len({value.casefold() for value in values}) != len(values)):
            raise ProjectError('Text-line check requires distinct nonempty handles and layers')
    entities = {entity.dxf.handle: entity for entity in doc.modelspace()}
    layer_names = {name.casefold() for name in layers}
    lines = [entity for entity in entities.values()
             if entity.dxftype() == 'LINE' and entity.dxf.layer.casefold() in layer_names]
    if {entity.dxf.layer.casefold() for entity in lines} != layer_names:
        raise ProjectError('Every selected text-line obstacle layer needs a modelspace LINE')
    segments = [(line.dxf.handle, tuple(line.dxf.start)[:2], tuple(line.dxf.end)[:2]) for line in lines]
    findings = []
    for handle in handles:
        entity = entities.get(handle.upper())
        if entity is None or entity.dxftype() != 'TEXT':
            raise ProjectError(f'Text-line check handle {handle} requires modelspace TEXT')
        bounds = text_box(entity)
        hits = [line_handle for line_handle, start, end in segments if enters(start, end, bounds)]
        if hits:
            findings.append(f'TEXT {handle} ({entity.dxf.text}) crossed by LINE {", ".join(hits)}')
    if findings:
        raise ProjectError('Estimated text-line overlap: ' + '; '.join(findings))
    return dict(text_count=len(handles), obstacle_line_count=len(lines))


def plot(dwg,dxf,settings,output,exe):
    import ezdxf
    dwg,dxf,output=[Path(p).resolve() for p in (dwg,dxf,output)]
    if output.exists():raise ProjectError('refusing to overwrite PDF')
    if not isinstance(settings,dict) or set(settings)-{'paper','source','window_drawing_units','scale_denominator','reference_handle','pdf_tolerance_mm','reference_segment_index','required_window_handles','text_line_clearance'} or not {'source','window_drawing_units','scale_denominator','reference_handle','pdf_tolerance_mm'}<=set(settings):
        raise ProjectError('explicit sourced window, scale and PDF reference required')
    if not isinstance(settings['source'],str) or not settings['source'].strip():raise ProjectError('sheet source required')
    paper_name=settings.get('paper','A4')
    papers={'A4':(297,210,'ISO full bleed A4 (297.00 x 210.00 MM)'),
            'A1':(841,594,'ISO full bleed A1 (841.00 x 594.00 MM)')}
    if not isinstance(paper_name,str) or paper_name not in papers:raise ProjectError('Supported A4 or A1 paper required')
    paper_width,paper_height,media=papers[paper_name]
    window=settings['window_drawing_units'];den=settings['scale_denominator'];tol=settings['pdf_tolerance_mm']
    if not isinstance(window,list) or len(window)!=4 or any(type(v) not in (int,float) or not math.isfinite(v) for v in window+[den,tol]):
        raise ProjectError('finite plot parameters required')
    if den<=0 or tol<=0 or tol>1 or window[0]>=window[2] or window[1]>=window[3]:raise ProjectError('invalid scale, window or <=1 mm verification tolerance')
    doc=ezdxf.readfile(dxf);unit=METRES_PER_UNIT.get(int(doc.header['$INSUNITS']))
    if unit is None:raise ProjectError('known drawing units required')
    width=(window[2]-window[0])*unit*1000/den;height=(window[3]-window[1])*unit*1000/den
    if width>paper_width or height>paper_height:raise ProjectError('requested fixed-scale window exceeds selected landscape paper')
    ref_start,ref_end=reference_points(doc,settings)
    if abs(ref_start.z-ref_end.z)>1e-9:raise ProjectError('PDF reference must be horizontal in WCS XY plane')
    if math.dist(ref_start,ref_end)<=1e-9:raise ProjectError('Nonzero reference length required')
    for pt in (ref_start,ref_end):
        if not window[0]<=pt.x<=window[2] or not window[1]<=pt.y<=window[3]:raise ProjectError('reference lies outside plot window')
    if 'required_window_handles' in settings:
        check_window_entities(doc, settings['required_window_handles'], window)
    clearance = check_text_line_clearance(doc, settings['text_line_clearance']) if 'text_line_clearance' in settings else None
    condition=f'(= (strcase (vl-string-translate (chr 92) "/" (strcat (getvar "DWGPREFIX") (getvar "DWGNAME")))) (strcase {lisp_string(dwg)}))'
    args=['_.-PLOT','_Y','Model','DWG To PDF.pc3',media,'_M','_L','_N','_W',
          f'{window[0]},{window[1]}',f'{window[2]},{window[3]}',f'1={den*.001/unit:.12g}','_C','_Y','monochrome.ctb','_Y','_A',str(output),'_N','_Y']
    command='(command '+' '.join(lisp_string(v) for v in args)+')'
    script=output.with_suffix('.scr')
    script.write_text(f'(if {condition} (progn (setvar "FILEDIA" 0) (setvar "CMDDIA" 0) (setvar "BACKGROUNDPLOT" 0) (command "_.UCS" "_World") (command "_.PLAN" "_World") {command}))\n_.QUIT\n_Y\n',encoding='ascii')
    before=digest(dwg);execute(Path(exe),dwg,script,output.with_suffix('.log'),120)
    if not output.is_file():raise ProjectError('fixed-scale PDF missing')
    if digest(dwg)!=before:raise ProjectError('plot changed DWG source')
    paper,lines=pdf_lines(output)
    if any(abs(v-e)>.2 for v,e in zip(paper,[paper_width,paper_height])):raise ProjectError('PDF page size does not match selected landscape paper')
    def expected(pt):return [(paper[0]-width)/2+(pt.x-window[0])*unit*1000/den,(paper[1]-height)/2+(pt.y-window[1])*unit*1000/den]
    a,b=expected(ref_start),expected(ref_end)
    matches=[(x,y) for x,y in lines if min(max(math.dist(a,x),math.dist(b,y)),max(math.dist(a,y),math.dist(b,x)))<=tol]
    if not matches:raise ProjectError('PDF reference position/physical scale mismatch')
    length=math.dist(*matches[0]);expected_length=math.dist(a,b)
    result=dict(pdf_sha256=digest(output),dwg_unchanged=True,paper_mm=paper,scale_denominator=den,
                reference_handle=settings['reference_handle'],reference_expected_mm=expected_length,reference_measured_mm=length,
                pdf_reference_pass=True,visual_review='pending',design_accepted=False)
    if 'required_window_handles' in settings:
        result['estimated_window_bounds_checked_handles'] = settings['required_window_handles']
    if clearance is not None:
        result['estimated_text_line_clearance'] = clearance
    output.with_suffix('.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result

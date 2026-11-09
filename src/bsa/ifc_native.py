"""Isolated native AutoCAD delivery of GUID-linked IFC line/arc/text diagrams."""
import argparse
import json
import math
from pathlib import Path
import shutil
from .cli import digest
from .engine import ProjectError
from .native_cad import DEFAULT_EXE, execute, lisp_string
from .cad_overlay import snapshot, reconcile
from .cad_intake import export_dwg


def validate_settings(settings):
    fields={'source','window_drawing_units','scale_denominator','reference_ifc_guid','pdf_tolerance_mm'}
    if not isinstance(settings,dict) or not fields<=set(settings) or set(settings)-fields-{'reference_layer','drawing_name'}:
        raise ProjectError('explicit sourced sheet window, scale, IFC reference and PDF tolerance required')
    if not isinstance(settings['source'],str) or not settings['source'].strip():raise ProjectError('sheet source required')
    window=settings['window_drawing_units']
    if not isinstance(window,list) or len(window)!=4:raise ProjectError('four-coordinate sheet window required')
    values=window+[settings['scale_denominator'],settings['pdf_tolerance_mm']]
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in values):raise ProjectError('finite sheet values required')
    if window[0]>=window[2] or window[1]>=window[3] or settings['scale_denominator']<=0 or not 0<settings['pdf_tolerance_mm']<=1:
        raise ProjectError('valid window, positive scale and <=1 mm PDF tolerance required')
    if (window[2]-window[0])*1000/settings['scale_denominator']>297 or (window[3]-window[1])*1000/settings['scale_denominator']>210:
        raise ProjectError('fixed-scale window exceeds A4 landscape')
    if not isinstance(settings['reference_ifc_guid'],str) or not settings['reference_ifc_guid']:
        raise ProjectError('explicit IFC reference GUID required')
    if settings.get('reference_layer','BSA_PIPE_AXIS') not in ('BSA_PIPE_AXIS','BSA_EQUIPMENT_REFERENCE','BSA_CABLE_AXIS') or settings.get('drawing_name','segments') not in ('segments','equipment','cable-route'):raise ProjectError('supported native reference layer/drawing name required')
    return settings


def identity(doc):
    return {e.dxf.handle:([(tag.code,tag.value) for tag in e.get_xdata('BSA_IFC')] if e.has_xdata('BSA_IFC') else [])
            for e in doc.modelspace()}


def verify_dxf(source, exported):
    import ezdxf
    expected=ezdxf.readfile(source);actual=ezdxf.readfile(exported)
    reconcile(snapshot(expected),exported)
    if identity(expected)!=identity(actual):raise ProjectError('native model entity handles/counts or IFC XDATA changed')
    return dict(model_entity_count=len(identity(expected)),linked_entity_count=sum(bool(v) for v in identity(expected).values()),
                model_entities_and_ifc_xdata_match=True,geometry_layers_and_annotations_match=True,
                metre_units=actual.header['$INSUNITS']==6)


def run(source, settings_path, out, exe=DEFAULT_EXE):
    import ezdxf
    source,settings_path,out,exe=[Path(p).resolve() for p in (source,settings_path,out,exe)]
    if not exe.is_file() or not source.is_file() or source.suffix.lower()!='.dxf':
        raise ProjectError('existing AutoCAD executable and generated diagram DXF required')
    if any(out==p or out in p.parents for p in (source,settings_path)):raise ProjectError('output must not contain source inputs')
    settings=validate_settings(json.loads(settings_path.read_text(encoding='utf-8-sig')))
    before={str(p):digest(p) for p in (source,settings_path)}
    doc=ezdxf.readfile(source)
    if doc.header.get('$INSUNITS')!=6 or not list(doc.modelspace()):raise ProjectError('nonempty metre diagram required')
    if any(e.dxftype() not in ('LINE','ARC','TEXT') for e in doc.modelspace()):raise ProjectError('native IFC diagram supports LINE/ARC/TEXT only')
    for arc in doc.modelspace().query('ARC'):
        if any(not math.isfinite(v) for v in (*arc.dxf.center,arc.dxf.radius,arc.dxf.start_angle,arc.dxf.end_angle)) or arc.dxf.radius<=0 or (arc.dxf.end_angle-arc.dxf.start_angle)%360<=1e-9 or not arc.dxf.extrusion.isclose((0,0,1),rel_tol=0,abs_tol=1e-9) or abs(arc.dxf.center.z)>1e-9:
            raise ProjectError('finite nonzero positive-radius WCS XY arc required')
    if any(not math.isfinite(v) for e in doc.modelspace().query('LINE') for pt in (e.dxf.start,e.dxf.end) for v in pt):
        raise ProjectError('finite diagram geometry required')
    reference_layer=settings.get('reference_layer','BSA_PIPE_AXIS')
    references=[e for e in doc.modelspace().query(f'LINE[layer=="{reference_layer}"]')
                if e.has_xdata('BSA_IFC') and [(t.code,t.value) for t in e.get_xdata('BSA_IFC')]==[(1000,settings['reference_ifc_guid'])]]
    if len(references)!=1:raise ProjectError('one reference-layer LINE for supplied IFC GUID required')
    sheet={key:value for key,value in settings.items() if key not in ('reference_ifc_guid','reference_layer','drawing_name')}
    sheet['reference_handle']=references[0].dxf.handle
    # Reference geometry is checked before any AutoCAD writes.
    window=settings['window_drawing_units']
    ref=references[0]
    if ref.dxf.start.distance(ref.dxf.end)<=1e-9 or abs(ref.dxf.start.z-ref.dxf.end.z)>1e-9:
        raise ProjectError('nonzero reference in WCS XY required')
    if any(not window[0]<=pt.x<=window[2] or not window[1]<=pt.y<=window[3] for pt in (ref.dxf.start,ref.dxf.end)):
        raise ProjectError('reference outside sheet window')
    from ezdxf import bbox
    bounds=bbox.extents(doc.modelspace(),fast=True)
    if not bounds.has_data or bounds.extmin.x<window[0] or bounds.extmin.y<window[1] or bounds.extmax.x>window[2] or bounds.extmax.y>window[3]:raise ProjectError('geometry or annotation extents exceed sheet window')
    out.mkdir(parents=True,exist_ok=False);copied=out/'input.dxf';shutil.copyfile(source,copied)
    dwg=out/(settings.get('drawing_name','segments')+'.dwg');script=out/'save.scr'
    condition=f'(= (strcase (vl-string-translate (chr 92) "/" (strcat (getvar "DWGPREFIX") (getvar "DWGNAME")))) (strcase {lisp_string(copied)}))'
    script.write_text(f'(if {condition} (progn (setvar "FILEDIA" 0) (setvar "CMDDIA" 0) (command "_.SAVEAS" "2018" {lisp_string(dwg)})) (princ "BSA WRONG DOCUMENT"))\n_.QUIT\n_Y\n',encoding='ascii')
    execute(exe,copied,script,out/'save.log',120)
    if not dwg.is_file():raise ProjectError('native diagram DWG missing')
    exported=export_dwg(dwg,out/'native-reopen',exe)
    checks=verify_dxf(source,exported)
    from .cad_sheet import plot
    plotted=plot(dwg,source,sheet,out/'sheet.pdf',exe)
    if any(digest(Path(p))!=h for p,h in before.items()):raise ProjectError('source changed during native diagram delivery')
    result=dict(inputs=before,inputs_unchanged=True,engine=str(exe),engine_sha256=digest(exe),
                dwg_sha256=digest(dwg),native_reopen_pass=all(v for k,v in checks.items() if isinstance(v,bool)),
                checks=checks,plot=plotted,settings=settings,design_accepted=False,
                pending=['actual PDF visual review','equipment/fittings/insulation and installation drawing detail','complete engineering acceptance'])
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'native-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('dxf',type=Path)
    parser.add_argument('--settings',required=True,type=Path);parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--autocad',type=Path,default=DEFAULT_EXE);args=parser.parse_args()
    print(json.dumps(run(args.dxf,args.settings,args.out,args.autocad),indent=2))


if __name__=='__main__':main()

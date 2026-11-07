"""Versioned electrical overlays on unit-proven source drawings."""
import argparse
import json
import math
from pathlib import Path
from .cli import digest
from .engine import ProjectError,validate
from .cad_intake import run as intake,export_dwg,METRES_PER_UNIT
from .native_cad import execute,lisp_string

SUPPORTED={'LINE','LWPOLYLINE','CIRCLE','ARC','TEXT','MTEXT','INSERT','POINT'}


def snapshot(doc):
    """Supported geometry/render attributes, keyed by persistent entity handles."""
    def vec(value):return [float(v) for v in value]
    def record(e):
        kind=e.dxftype()
        if kind not in SUPPORTED:raise ProjectError('unsupported base entity for overlay preservation: '+kind)
        r=dict(type=kind,layer=e.dxf.layer,color=e.dxf.color,linetype=e.dxf.linetype,
               lineweight=e.dxf.lineweight,ltscale=e.dxf.ltscale,invisible=e.dxf.invisible)
        if kind=='LINE':r.update(start=vec(e.dxf.start),end=vec(e.dxf.end))
        elif kind=='LWPOLYLINE':r.update(points=[list(p) for p in e],closed=e.closed,elevation=e.dxf.elevation,extrusion=vec(e.dxf.extrusion),const_width=e.dxf.const_width)
        elif kind in ('CIRCLE','ARC'):
            r.update(centre=vec(e.dxf.center),radius=e.dxf.radius,extrusion=vec(e.dxf.extrusion))
            if kind=='ARC':r.update(start=e.dxf.start_angle,end=e.dxf.end_angle)
        elif kind=='POINT':r.update(location=vec(e.dxf.location))
        elif kind=='TEXT':
            r.update(text=e.dxf.text,insert=vec(e.dxf.insert),height=e.dxf.height,rotation=e.dxf.rotation,
                     width=e.dxf.width,oblique=e.dxf.oblique,style=e.dxf.style,halign=e.dxf.halign,valign=e.dxf.valign,
                     extrusion=vec(e.dxf.extrusion))
            if e.dxf.halign or e.dxf.valign:r['align_point']=vec(e.dxf.align_point)
        elif kind=='MTEXT':
            r.update(text=e.text,insert=vec(e.dxf.insert),height=e.dxf.char_height,width=e.dxf.width,
                     style=e.dxf.style,attachment=e.dxf.attachment_point,extrusion=vec(e.dxf.extrusion))
            r['text_direction']=vec(e.dxf.text_direction) if e.dxf.hasattr('text_direction') else [math.cos(math.radians(e.dxf.rotation)),math.sin(math.radians(e.dxf.rotation)),0.]
        elif kind=='INSERT':
            r.update(name=e.dxf.name,insert=vec(e.dxf.insert),scale=[e.dxf.xscale,e.dxf.yscale,e.dxf.zscale],
                     rotation=e.dxf.rotation,extrusion=vec(e.dxf.extrusion),rows=e.dxf.row_count,columns=e.dxf.column_count,
                     row_spacing=e.dxf.row_spacing,column_spacing=e.dxf.column_spacing,
                     attributes=[dict(tag=a.dxf.tag,text=a.dxf.text,insert=vec(a.dxf.insert)) for a in e.attribs])
        return r
    if any(b.block.dxf.flags&12 for b in doc.blocks):raise ProjectError('external references require separate packaging/review before overlay')
    records={'header:units':dict(insunits=int(doc.header.get('$INSUNITS',0)))}
    for layout in doc.layouts:
        for e in layout:records[e.dxf.handle]=dict(layout=layout.name,**record(e))
    for block in doc.blocks:
        if not block.is_any_layout:
            for e in block:records[e.dxf.handle]=dict(block=block.name,**record(e))
    for layer in doc.layers:
        records['layer:'+layer.dxf.name]=dict(name=layer.dxf.name,flags=layer.dxf.flags,color=layer.dxf.color,
                                             linetype=layer.dxf.linetype,lineweight=layer.dxf.lineweight,plot=layer.dxf.plot)
    return records


def equivalent(a,b):
    if isinstance(a,dict):return isinstance(b,dict) and a.keys()==b.keys() and all(equivalent(v,b[k]) for k,v in a.items())
    if isinstance(a,list):return isinstance(b,list) and len(a)==len(b) and all(equivalent(x,y) for x,y in zip(a,b))
    if type(a) in (int,float) and type(b) in (int,float):return math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-8)
    return a==b


def reconcile(expected,path):
    import ezdxf
    actual=snapshot(ezdxf.readfile(path))
    if any(handle not in actual or not equivalent(row,actual[handle]) for handle,row in expected.items()):
        raise ProjectError('preserved drawing entity geometry/attributes mismatch')
    return True


def validate_settings(settings):
    if not isinstance(settings,dict) or set(settings)!={'source','translation_m','rotation_deg','symbol_radius_m','text_height_m','label_offset_m'}:
        raise ProjectError('explicit sourced rigid transform and annotation dimensions required')
    if not isinstance(settings['source'],str) or not settings['source'].strip():raise ProjectError('overlay settings source required')
    for key in ('translation_m','label_offset_m'):
        if not isinstance(settings[key],list) or len(settings[key])!=2:raise ProjectError('two-dimensional overlay vectors required')
    values=settings['translation_m']+settings['label_offset_m']+[settings['rotation_deg'],settings['symbol_radius_m'],settings['text_height_m']]
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in values) or min(settings['symbol_radius_m'],settings['text_height_m'])<=0:
        raise ProjectError('finite transform and positive annotation dimensions required')


def run(project,drawing,selection,settings,out,exe=None,sheet=None):
    import ezdxf
    project,drawing,selection,settings,out=[Path(p).resolve() for p in (project,drawing,selection,settings,out)]
    sheet=Path(sheet).resolve() if sheet else None
    if sheet and not exe:raise ProjectError('AutoCAD required for fixed-scale sheet')
    inputs=[project,drawing,selection,settings]+([sheet] if sheet else [])
    if any(out==p or out in p.parents for p in inputs):raise ProjectError('output must not contain source inputs')
    before={str(p):digest(p) for p in inputs}
    electrical=validate(json.loads(project.read_text(encoding='utf-8-sig')))
    config=json.loads(settings.read_text(encoding='utf-8-sig'));validate_settings(config)
    out.mkdir(parents=True,exist_ok=False)
    intake(drawing,out/'intake',selection,exe)
    base=out/'intake/native/source-export.dxf' if drawing.suffix.lower()=='.dwg' else out/'intake/source-copy.dxf'
    doc=ezdxf.readfile(base);original=snapshot(doc);scale=METRES_PER_UNIT[int(doc.header['$INSUNITS'])]
    if any(name in doc.layers for name in ('BSA_DEVICES','BSA_LABELS')):raise ProjectError('reserved overlay layers already exist in base')
    doc.layers.new('BSA_DEVICES',dxfattribs={'color':2});doc.layers.new('BSA_LABELS',dxfattribs={'color':7})
    model=doc.modelspace();angle=math.radians(config['rotation_deg']);c,s=math.cos(angle),math.sin(angle)
    placement=[]
    for d in electrical['devices']:
        label=d['id']+' / '+d['circuit']
        if not label.isascii() or any(v in label for v in '\r\n'):raise ProjectError('overlay labels require ASCII without line breaks')
        x,y=d['x_m'],d['y_m'];tx,ty=config['translation_m']
        pt=((c*x-s*y+tx)/scale,(s*x+c*y+ty)/scale,0.)
        ox,oy=config['label_offset_m'];label_pt=(pt[0]+(c*ox-s*oy)/scale,pt[1]+(s*ox+c*oy)/scale,0.)
        circle=model.add_circle(pt,config['symbol_radius_m']/scale,dxfattribs={'layer':'BSA_DEVICES'})
        text=model.add_text(label,dxfattribs={'insert':label_pt,'height':config['text_height_m']/scale,'rotation':config['rotation_deg'],'layer':'BSA_LABELS'})
        placement.append(dict(id=d['id'],circle_handle=circle.dxf.handle,text_handle=text.dxf.handle,centre_drawing_units=list(pt)))
    output=out/'coordinated.dxf';doc.saveas(output)
    reconcile(original,output)
    combined=snapshot(ezdxf.readfile(output));native=False;plot_result=None
    if exe:
        dwg=out/'coordinated.dwg';script=out/'save.scr'
        condition=f'(= (strcase (vl-string-translate (chr 92) "/" (strcat (getvar "DWGPREFIX") (getvar "DWGNAME")))) (strcase {lisp_string(output)}))'
        script.write_text(f'(if {condition} (progn (setvar "FILEDIA" 0) (command "_.SAVEAS" "2018" {lisp_string(dwg)})))\n_.QUIT\n_Y\n',encoding='ascii')
        execute(Path(exe),output,script,out/'save.log',120)
        if not dwg.is_file():raise ProjectError('coordinated DWG missing')
        exported=export_dwg(dwg,out/'native-reopen',exe)
        reconcile(combined,exported);native=True
        if sheet:
            from .cad_sheet import plot
            plot_result=plot(dwg,output,json.loads(sheet.read_text(encoding='utf-8-sig')),out/'sheet.pdf',exe)
    if any(digest(Path(p))!=h for p,h in before.items()):raise ProjectError('source changed during overlay')
    result=dict(inputs=before,inputs_unchanged=True,base_entities_preserved=True,
                preserved_entity_count=sum(not key.startswith(('header:','layer:')) for key in original),
                preserved_layer_count=sum(key.startswith('layer:') for key in original),
                device_count=len(placement),placements=placement,native_reopen_pass=native,plot=plot_result,design_accepted=False,
                scope='Supported source entity geometry/render attributes and block contents retained; electrical rigid transform; native checks only when executed',
                pending=['font/style/table and arbitrary object fidelity','source and coordinated drawing visual review','device containment/clashes and full engineering acceptance'])
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'overlay-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project',type=Path)
    for name in ('drawing','selection','settings','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--autocad',type=Path);p.add_argument('--sheet',type=Path);a=p.parse_args()
    result=run(a.project,a.drawing,a.selection,a.settings,a.out,a.autocad,a.sheet)
    print(json.dumps({k:result[k] for k in ('inputs_unchanged','base_entities_preserved','device_count','native_reopen_pass','design_accepted')}))

if __name__=='__main__':main()

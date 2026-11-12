"""Native save/reopen and scaled plotting of a prepared single-line duct sheet."""
import json
import math
import shutil
from pathlib import Path
import ezdxf
from .cli import digest
from .native_cad import execute,lisp_string
from .cad_intake import export_dwg
from .cad_sheet import plot


def compare(source, reopened, layers):
    """Compare explicit generated layers, not uninspected base-building semantics."""
    if not isinstance(layers,list) or not layers or any(not isinstance(x,str) or not x for x in layers) or len(set(layers))!=len(layers):
        raise ValueError('Explicit unique layer inventory required')
    docs=[ezdxf.readfile(p) for p in (source,reopened)]
    if docs[0].units!=docs[1].units:raise ValueError('Native drawing units changed')
    inventories=[[e for e in d.modelspace() if e.dxf.layer in layers] for d in docs]
    if set(e.dxf.layer for e in inventories[0])!=set(layers):raise ValueError('Every reviewed layer must have entities')
    if len(inventories[0])!=len(inventories[1]):raise ValueError('Native entity count mismatch')
    def equal(a,b):
        if isinstance(a,(int,float)) and isinstance(b,(int,float)):
            return math.isclose(a,b,rel_tol=0,abs_tol=1e-7)
        if hasattr(a,'x') and hasattr(b,'x'):return all(equal(x,y) for x,y in zip(a,b))
        return a==b
    for a,b in zip(*inventories):
        if a.dxftype()!=b.dxftype() or a.dxftype() not in ('LINE','TEXT','CIRCLE','POINT','LWPOLYLINE'):
            raise ValueError('Native type/order differs or unsupported generated entity')
        keys=(set(a.dxf.all_existing_dxf_attribs())|set(b.dxf.all_existing_dxf_attribs()))-{'handle','owner'}
        if any(not equal(getattr(a.dxf,k),getattr(b.dxf,k)) for k in keys):
            raise ValueError('Native effective entity attributes differ')
        if a.dxftype()=='LWPOLYLINE':
            p,q=list(a.get_points()),list(b.get_points())
            if len(p)!=len(q) or any(not equal(x,y) for u,v in zip(p,q) for x,y in zip(u,v)):
                raise ValueError('Native polyline vertices differ')
    return dict(generated_entity_count=len(inventories[0]),layers=layers,
        comparison='Ordered effective DXF attributes and polyline vertices; handles/owners excluded; 1e-7 drawing-unit absolute tolerance',
        generated_native_correspondence=True)


def run(source,settings,output,exe,*,inherited_source_sha256=None):
    source,settings,output,exe=map(lambda p:Path(p).resolve(),(source,settings,output,exe))
    if output.exists() or any(output==p or output in p.parents for p in (source,settings,exe)):
        raise ValueError('New isolated output required')
    if source.suffix.lower()!='.dxf' or not exe.is_file():raise ValueError('Prepared DXF and explicit AutoCAD executable required')
    pins={str(p):digest(p) for p in (source,settings,exe)}
    spec=json.loads(settings.read_text(encoding='utf-8-sig'))
    if inherited_source_sha256 is not None:
        if 'source_sha256' in spec:raise ValueError('Inherited drawing hash cannot be overridden')
        if pins[str(source)]!=inherited_source_sha256:raise ValueError('Inherited drawing producer changed')
        spec['source_sha256']=inherited_source_sha256
    if set(spec)!={'source_sha256','layers','sheet'} or spec['source_sha256']!=pins[str(source)]:
        raise ValueError('Exact source hash, layers and sheet settings required')
    compare(source,source,spec['layers'])
    output.mkdir(parents=True);copied=output/'Supply Air Distribution.dxf';shutil.copyfile(source,copied)
    dwg=output/'Supply Air Distribution.dwg';script=output/'save.scr'
    condition=f'(= (strcase (vl-string-translate (chr 92) "/" (strcat (getvar "DWGPREFIX") (getvar "DWGNAME")))) (strcase {lisp_string(copied)}))'
    script.write_text(f'(if {condition} (progn (setvar "FILEDIA" 0) (setvar "CMDDIA" 0) (command "_.SAVEAS" "2018" {lisp_string(dwg)})))\n_.QUIT\n_Y\n',encoding='ascii')
    execute(exe,copied,script,output/'save.log',120)
    if not dwg.is_file():raise ValueError('Native DWG missing')
    exported=export_dwg(dwg,output/'reopened',exe)
    checked=compare(copied,exported,spec['layers'])
    plotted=plot(dwg,copied,spec['sheet'],output/'Supply Air Distribution.pdf',exe)
    if any(digest(Path(p))!=sha for p,sha in pins.items()) or digest(copied)!=pins[str(source)]:
        raise ValueError('Source, settings, runtime or copied DXF changed')
    result=dict(inputs=pins,native_reopen_pass=True,generated_geometry=checked,plot=plotted,
                scope='Explicit generated-layer native correspondence and physical plot reference; base-building semantic fidelity, routing and engineering acceptance separate',
                plot_visual_review='pending',design_accepted=False)
    (output/'native-sheet.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source');p.add_argument('settings');p.add_argument('--out',required=True);p.add_argument('--autocad',required=True)
    a=p.parse_args();run(a.source,a.settings,a.out,a.autocad)
    print('Native reopening and plot reference checked; actual visual/engineering review pending')

"""Run existing isolated native save/reopen/plot on a verified spatial schematic."""
import argparse
import json
from pathlib import Path
from . import spatial_terminal_drawing as drawing
from . import duct_sheet_native,cad_sheet,cad_intake,native_cad
from .cli import digest
from .workspace import allowed


def run(source,settings,out,exe):
    source,settings,out,exe=[Path(p).resolve() for p in (source,settings,out,exe)]
    if not all(allowed(p) for p in (source,settings,out)) or source.name!='drawing.json':raise ValueError('Selected verified spatial drawing and settings required')
    before=digest(source);report=drawing.verify(source.parent)
    spec=json.loads(settings.read_text(encoding='utf-8-sig'))
    if set(spec)!={'layers','sheet'} or set(spec['layers'])!={'BSA_ROOM','BSA_TERMINAL_CENTER','BSA_FLOW','BSA_ROOM_LABEL'}:raise ValueError('Exact inherited spatial drawing layers and sheet required')
    pins=dict(report['inputs']);pins[str(source)]=before;pins[str(settings)]=digest(settings)
    for module in (drawing,duct_sheet_native,cad_sheet,cad_intake,native_cad):pins[str(Path(module.__file__).resolve())]=digest(Path(module.__file__))
    pins[str(Path(__file__).resolve())]=digest(Path(__file__))
    if any(out==Path(p) or out in Path(p).parents for p in pins):raise ValueError('Native output overlaps sources')
    native=duct_sheet_native.run(source.parent/'Terminal Airflow Schematic.dxf',settings,out,exe,inherited_source_sha256=report['dxf_sha256'])
    drawing.verify(source.parent)
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Spatial native source or method changed')
    result=dict(source_drawing=str(source),inputs=pins,native=native,outputs={str(p):digest(p) for p in out.rglob('*') if p.is_file()},plot_visual_review='pending',design_accepted=False)
    (out/'spatial-native.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


def verify(folder):
    folder=Path(folder).resolve()
    if not allowed(folder):raise ValueError('Selected native workspace required')
    result=json.loads((folder/'spatial-native.json').read_text())
    if set(result)!={'source_drawing','inputs','native','outputs','plot_visual_review','design_accepted'} or result['design_accepted'] is not False or result['plot_visual_review']!='pending':raise ValueError('Exact unaccepted native evidence required')
    source=Path(result['source_drawing'])
    if not allowed(source) or source.name!='drawing.json':raise ValueError('Selected source drawing required')
    report=drawing.verify(source.parent);native=json.loads((folder/'native-sheet.json').read_text())
    if native!=result['native'] or native.get('native_reopen_pass') is not True or native.get('design_accepted') is not False:raise ValueError('Native report differs')
    pins=dict(report['inputs']);pins[str(source)]=digest(source)
    for module in (drawing,duct_sheet_native,cad_sheet,cad_intake,native_cad):pins[str(Path(module.__file__).resolve())]=digest(Path(module.__file__))
    pins[str(Path(__file__).resolve())]=digest(Path(__file__))
    original_dxf=source.parent/'Terminal Airflow Schematic.dxf'
    if native['inputs'].get(str(original_dxf))!=report['dxf_sha256']:raise ValueError('Native drawing replaced source')
    settings=[Path(p) for p in native['inputs'] if p!=str(original_dxf) and Path(p).suffix=='.json']
    if len(settings)!=1 or not allowed(settings[0]):raise ValueError('Exact native settings pin required')
    pins[str(settings[0])]=digest(settings[0])
    if pins!=result['inputs'] or any(digest(Path(p))!=sha for p,sha in {**pins,**native['inputs']}.items()):raise ValueError('Native source/method pins differ')
    if any(not Path(p).is_relative_to(folder) or not Path(p).is_file() or digest(Path(p))!=sha for p,sha in result['outputs'].items()):raise ValueError('Native output pins differ')
    required=['native-sheet.json','Supply Air Distribution.dwg','Supply Air Distribution.dxf','Supply Air Distribution.pdf','reopened/source-export.dxf']
    if not {str(folder/name) for name in required}<=set(result['outputs']):raise ValueError('Native output inventory incomplete')
    if digest(folder/'Supply Air Distribution.dxf')!=report['dxf_sha256'] or digest(folder/'Supply Air Distribution.pdf')!=native['plot']['pdf_sha256']:raise ValueError('Native source copy or PDF differs')
    spec=json.loads(settings[0].read_text());checked=duct_sheet_native.compare(original_dxf,folder/'reopened/source-export.dxf',spec['layers'])
    if checked!=native['generated_geometry']:raise ValueError('Native geometry replay differs')
    return result


def verify_workflow(tasks,root,plan_root,record):
    for task in tasks:
        if task['kind']!='spatial_terminal_native':continue
        folder=Path(root)/task['id']
        if not (folder/'spatial-native.json').is_file():
            if record[task['id']]['status']=='pass':raise ValueError('Passing native task lacks report')
            continue
        report=verify(folder)
        settings=(Path(plan_root)/task['settings']).resolve()
        if Path(report['source_drawing'])!=(Path(root)/task['depends_on']/'drawing.json').resolve() or str(settings) not in report['inputs']:raise ValueError('Native task replaced declared drawing/settings')
        if record[task['id']]['status']!='pass' or record[task['depends_on']]['status']!='pass':raise ValueError('Native task execution dependency differs')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source');parser.add_argument('--settings',required=True);parser.add_argument('--out',required=True);parser.add_argument('--autocad',required=True)
    args=parser.parse_args();run(args.source,args.settings,args.out,args.autocad)

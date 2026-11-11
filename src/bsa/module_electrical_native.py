"""Same-producer rule-gated native device schematic using existing AutoCAD tools."""
import csv
import json
from pathlib import Path
from .cli import digest
from .modules import ROOT,verify_result
from .module_contract import read_json
from .module_electrical_rules import verify as verify_rules
from .providers.electrical_circuits import verify_schematic


def rule_evidence(rule_folder):
    folder=Path(rule_folder)
    if (folder/'provider/result.json').is_file():
        return [folder/'provider/result.json',folder/'provider/rules/electrical-module-rules.json']
    return [folder/'electrical-module-rules.json']


def source_context(rule_folder):
    rule_folder=Path(rule_folder).resolve();rule=verify_rules(rule_folder)
    if rule['status']!='pass':raise ValueError('Passing exact electrical rule result required before native schematic')
    producer=Path(rule['producer_result']);module=verify_result(producer)
    source=(producer.parent/module['payload']['schematic_dxf']['path']).resolve()
    request_path=Path(module['request']['path']);request=read_json(request_path)
    project=read_json((request_path.parent/request['sources']['project']['path']).resolve())
    audit=verify_schematic(project,source)
    if audit['coincident_symbol_ids']:raise ValueError('Coincident device symbols require an explicit sourced presentation layout before native plotting')
    return rule,producer,source,audit


def native_readback(folder,source):
    """Compare recorded independent native CSV with source-checked DXF entities."""
    import ezdxf
    doc=ezdxf.readfile(source);lines=(Path(folder)/'native-entities.csv').read_text().splitlines()
    if not lines or lines[-1]!='UNITS,6':raise ValueError('Native electrical units differ')
    rows=list(csv.DictReader(lines[:-1]))
    expected_c=sorted((e.dxf.layer,round(e.dxf.center.x,8),round(e.dxf.center.y,8),round(e.dxf.radius,8)) for e in doc.modelspace().query('CIRCLE'))
    expected_t=sorted((e.dxf.layer,round(e.dxf.insert.x,8),round(e.dxf.insert.y,8),e.dxf.text) for e in doc.modelspace().query('TEXT'))
    actual_c=sorted((r['layer'],round(float(r['x']),8),round(float(r['y']),8),round(float(r['radius']),8)) for r in rows if r['type']=='CIRCLE')
    actual_t=sorted((r['layer'],round(float(r['x']),8),round(float(r['y']),8),r['text']) for r in rows if r['type']=='TEXT')
    if len(rows)!=len(expected_c)+len(expected_t) or actual_c!=expected_c or actual_t!=expected_t:raise ValueError('Native electrical recorded ID/coordinate/radius readback differs')


def run(rule_folder,out,exe):
    from .native_cad import convert,plot
    rule_folder,out,exe=[Path(p).resolve() for p in (rule_folder,out,exe)]
    rule,producer,source,audit=source_context(rule_folder)
    pins=dict(rule['inputs']);pins.update({str(p):digest(p) for p in (*rule_evidence(rule_folder),source,exe,Path(__file__),ROOT/'src/bsa/native_cad.py')})
    if not out.is_relative_to(ROOT) or out.exists() or any(out==Path(p) or out in Path(p).parents for p in pins):raise ValueError('New repository native output separate from sources required')
    native=convert(source,out,exe);native['plot']=plot(out/'devices.dwg',source,out/'devices.pdf',exe)
    (out/'native-verification.json').write_text(json.dumps(native,indent=2),encoding='utf-8');native_readback(out,source)
    if any(digest(Path(p))!=h for p,h in pins.items()):raise ValueError('Electrical native source changed during execution')
    source_context(rule_folder)
    report=dict(rule_run=str(rule_folder),producer_result=str(producer),schematic_source=str(source),inputs=pins,
        source_audit=audit,native_reopen_pass=native['native_reopen_pass'],plot_scale='fit-to-page schematic',
        visual_review='pending',geometry_bound=False,design_accepted=False,
        artifacts={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()},
        scope='Source-checked device symbols/IDs and recorded independent AutoCAD circle/text/unit readback;schematic only,not physical cable routes or complete engineering/visual acceptance')
    (out/'electrical-native.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


def verify(folder):
    folder=Path(folder).resolve();r=read_json(folder/'electrical-native.json')
    rule,producer,source,audit=source_context(r['rule_run'])
    exe=Path(read_json(folder/'native-verification.json')['engine']).resolve()
    pins=dict(rule['inputs']);pins.update({str(p):digest(p) for p in (*rule_evidence(r['rule_run']),source,exe,Path(__file__),ROOT/'src/bsa/native_cad.py')})
    if r['inputs']!=pins or r['producer_result']!=str(producer) or r['schematic_source']!=str(source) or r['source_audit']!=audit:raise ValueError('Electrical native source lineage differs')
    for name,sha in r['artifacts'].items():
        path=(folder/name).resolve()
        if not path.is_relative_to(folder) or digest(path)!=sha:raise ValueError('Electrical native artifact changed')
    actual={p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file() and p.name!='electrical-native.json'}
    if actual!=set(r['artifacts']):raise ValueError('Electrical native artifact inventory differs')
    n=read_json(folder/'native-verification.json');native_readback(folder,source)
    if n['source_sha256']!=digest(source) or n['dwg_sha256']!=digest(folder/'devices.dwg') or n['plot']['pdf_sha256']!=digest(folder/'devices.pdf') or n['native_reopen_pass'] is not True or not all(n['checks'].values()):raise ValueError('Electrical native saved/readback evidence differs')
    if r['native_reopen_pass'] is not True or r['plot_scale']!='fit-to-page schematic' or n['plot']['scale']!=r['plot_scale'] or r['visual_review']!='pending' or r['geometry_bound'] is not False or r['design_accepted'] is not False:raise ValueError('Electrical native acceptance/scope differs')
    return r


def verify_workflow(tasks,root,report_tasks):
    for task in tasks:
        if task['kind']!='module_electrical_native':continue
        folder=Path(root)/task['id']
        if not (folder/'electrical-native.json').is_file() and report_tasks[task['id']]['status']!='pass':continue
        r=verify(folder)
        if Path(r['rule_run']).resolve()!=(Path(root)/task['depends_on']).resolve():raise ValueError('Native electrical rule producer differs from declared task')
        if report_tasks[task['id']]['status']!='pass':raise ValueError('Native electrical task status contradicts retained result')

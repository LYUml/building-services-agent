"""Independently review saved network tags, ancestry and native AutoCAD output."""
import argparse
import json
from pathlib import Path
import ezdxf
from . import source_network_tags as tags,source_network_delivery as delivery
from . import source_network_schedule as schedule,ifc_native as native
from . import view_tags,route_annotations
from .cli import digest
from .workspace import allowed


def load(path):
    return json.loads(Path(path).read_text())


def graphic(study):
    study=Path(study).resolve();record=load(study/'placement.json')
    base=Path(record['source_delivery']).resolve();table=Path(record['source_schedule']).resolve()
    if not all(allowed(p) for p in (study,base,table)):raise ValueError('Host-selected annotation sources required')
    source=base/'layout/Supply Network Geometry.dxf';sheet_path=base/'layout/sheet.json';data_path=table/'Network Parameter Schedule.json'
    for p in (source,sheet_path,data_path):
        if record['source_hashes'].get(str(p))!=digest(p):raise ValueError('Annotation source changed')
    sheet=load(sheet_path);data=load(data_path);height=sheet['scale_denominator']*.0025
    if height!=record['text_height_m']:raise ValueError('Annotation plot text height differs')
    doc=ezdxf.readfile(source);geometry=tags.shapes(doc);names={r['guid']:r['tag'] for r in data['components']}
    if set(names)!=set(geometry):raise ValueError('Schedule/model identity differs')
    reserved=[view_tags.rectangle([e.dxf.insert.x,e.dxf.insert.y],e.dxf.text,e.dxf.height) for e in doc.modelspace().query('TEXT')]
    for e in doc.modelspace().query('LINE'):
        reserved.append(route_annotations.expand([min(e.dxf.start.x,e.dxf.end.x),min(e.dxf.start.y,e.dxf.end.y),max(e.dxf.start.x,e.dxf.end.x),max(e.dxf.start.y,e.dxf.end.y)],height*.15))
    checks=tags.audit_selection(geometry,names,reserved,sheet['window_drawing_units'],height,record['selected'])
    checks.update(tags.audit_saved(source,study/'Tagged Network Study.dxf',record['selected'],height))
    return record,base,table,sheet,checks


def native_stage(source,settings,sheet,native_out):
    proof=load(native_out/'native-verification.json')
    required={'input.dxf','section.dwg','sheet.pdf','sheet.json','native-reopen/source-export.dxf'}
    if not required<=set(proof['artifacts']):raise ValueError('Native artifact coverage missing')
    for name,sha in proof['artifacts'].items():
        p=(native_out/name).resolve()
        if not p.is_relative_to(native_out) or digest(p)!=sha:raise ValueError('Native artifact changed')
    if proof['inputs']!={str(p):digest(p) for p in (source,settings)}:raise ValueError('Native annotation source differs')
    exe=Path(proof['engine'])
    if digest(exe)!=proof['engine_sha256'] or digest(native_out/'section.dwg')!=proof['dwg_sha256'] or digest(native_out/'sheet.pdf')!=proof['plot']['pdf_sha256']:raise ValueError('Native runtime/DWG/PDF changed')
    if proof['settings']!=sheet:raise ValueError('Native settings differ')
    native.verify_dxf(source,native_out/'input.dxf')
    return dict(native_checks=native.verify_dxf(source,native_out/'native-reopen/source-export.dxf'),calibration=delivery.measure_pdf(native_out/'sheet.pdf',ezdxf.readfile(source),sheet)),exe


def evaluate(study,native_out):
    study,native_out=Path(study).resolve(),Path(native_out).resolve()
    if not allowed(study) or not allowed(native_out):raise ValueError('Host-selected annotation/native workspace required')
    record,base,table,sheet,checks=graphic(study)
    source=study/'Tagged Network Study.dxf';settings=base/'layout/sheet.json'
    preliminary=[study/'placement.json',source,base/'delivery.json',table/'schedule.json',native_out/'native-verification.json',native_out/'section.dwg',native_out/'sheet.pdf',native_out/'native-reopen/source-export.dxf']
    before={str(p):digest(p) for p in preliminary}
    delivery.verify(base);schedule.verify(table)
    source_analysis=Path(load(base/'delivery.json')['source_analysis']).resolve()
    fitting=Path(load(table/'schedule.json')['source_fitting_analysis']).resolve()
    if not allowed(fitting) or Path(load(fitting/'fitting-data.json')['source_analysis']).resolve()!=source_analysis:raise ValueError('Drawing and schedule analysis differ')
    stage,exe=native_stage(source,settings,sheet,native_out);checks.update(stage)
    if before!={str(p):digest(p) for p in preliminary}:raise ValueError('Tag review inputs changed during verification')
    paths=[study/'placement.json',source,base/'delivery.json',table/'schedule.json',native_out/'native-verification.json',native_out/'section.dwg',native_out/'sheet.pdf',native_out/'native-reopen/source-export.dxf',exe]
    paths += [Path(m.__file__).resolve() for m in (tags,delivery,schedule,native,view_tags,route_annotations)]+[Path(__file__).resolve()]
    return dict(study=str(study),native_output=str(native_out),checks=checks,inputs={str(p):digest(p) for p in paths},ancestry_verified=True,native_reopen_verified=True,plot_visual_review='pending',design_accepted=False)


def review(study,native_out,out):
    out=Path(out).resolve();sources=[Path(p).resolve() for p in (study,native_out)]
    if not allowed(out) or out.exists() or any(out.is_relative_to(p) or p.is_relative_to(out) for p in sources):raise ValueError('Fresh separate review directory required')
    result=evaluate(study,native_out);out.mkdir(parents=True);(out/'review.json').write_text(json.dumps(result,indent=2));return result


def verify(out):
    out=Path(out).resolve()
    if not allowed(out):raise ValueError('Host-selected review required')
    record=load(out/'review.json')
    if record!=evaluate(record['study'],record['native_output']):raise ValueError('Reconstructed tag review differs')
    return record


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    a=s.add_parser('review');a.add_argument('study');a.add_argument('native_output');a.add_argument('--out',required=True)
    s.add_parser('verify').add_argument('out');a=p.parse_args()
    r=review(a.study,a.native_output,a.out) if a.command=='review' else verify(a.out)
    print(json.dumps({k:r[k] for k in ('ancestry_verified','native_reopen_verified','plot_visual_review','design_accepted')},indent=2));raise SystemExit(2)

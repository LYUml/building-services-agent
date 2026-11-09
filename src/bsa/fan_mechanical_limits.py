"""Pinned TCF M300 BC-SW 122 speed-table check; not full fan selection."""
import argparse
import json
import math
from pathlib import Path
import re
from .cli import digest
from .engine import ProjectError
from .rectangular_fan import validate_curve

PDF_SHA256='a50f3202afc6fb0fc42af856d43493dc1079a529de36634d25bef9c9ebdcd18b'
CLASSES=('Class_I','Class_II','Class_III','Class_IV')


def speed_table(record,pdf):
    from pypdf import PdfReader
    pdf=Path(pdf)
    if not pdf.is_file() or digest(pdf)!=PDF_SHA256 or record.get('source',{}).get('sha256')!=PDF_SHA256:raise ProjectError('supported pinned manufacturer PDF required')
    if record.get('product',{}).get('manufacturer')!='Twin City Fan & Blower' or record['product'].get('designation')!='BC-SW 122':raise ProjectError('supported BC-SW 122 product record required')
    published=record.get('published_data',{}).get('maximum_speed_rpm',{})
    if published.get('printed_page')!=13 or published.get('row')!='BC SWSI 122':raise ProjectError('exact manufacturer speed-table locator required')
    text=PdfReader(pdf).pages[12].extract_text(extraction_mode='layout')
    if not all(label in text for label in ('Maximum RPM','CLASS I','CLASS II','CLASS III','CLASS IV')):raise ProjectError('speed-table headings missing')
    section=text.split('BC SWSI',1)[1].split('BC DWDI',1)[0]
    rows=re.findall(r'^\s*122\s+(.+)$',section,re.MULTILINE)
    if len(rows)!=1:raise ProjectError('unique source size-122 speed row required')
    values=rows[0].split()
    if len(values)!=12:raise ProjectError('four class speed/weight/inertia triples required')
    try:limits={name:int(values[i*3]) for i,name in enumerate(CLASSES)}
    except ValueError as exc:raise ProjectError('integer source speed limits required') from exc
    if any(type(published.get(k)) is not int or published[k]!=v for k,v in limits.items()):raise ProjectError('record speed limit differs from independently extracted PDF')
    return limits


def evaluate(record,pdf,speed,construction_class):
    if type(speed) not in (int,float) or not math.isfinite(speed) or speed<=0:raise ProjectError('positive finite fan speed required')
    if construction_class is not None and construction_class not in CLASSES:raise ProjectError('explicit supported construction class or null required')
    limits=speed_table(record,pdf)
    maximum=limits[construction_class] if construction_class else None
    comparison=speed<=maximum if maximum is not None else None
    return dict(status='pending' if comparison is None else 'pass' if comparison else 'fail',speed_rpm=speed,construction_class=construction_class,maximum_speed_rpm=maximum,speed_within_maximum=comparison,source_page=13,source_pdf_sha256=PDF_SHA256,independent_pdf_table_match=True,
        scope='BC-SW 122 declared construction-class maximum speed only; no interpolation, product authentication or design acceptance',
        design_accepted=False,pending=['Actual supplied construction-class identity and present product suitability','Validated numeric curve/digitization uncertainty and stable/installation applicability','Native fan geometry/ports, motor/transmission and drawn electrical input','Full Hong Kong and engineering acceptance'])


def run(record,pdf,curve,basis,out):
    import importlib.metadata
    paths=[Path(p).resolve() for p in (record,pdf,curve,basis)];out=Path(out).resolve()
    if out.exists() or any(out==p or out in p.parents for p in paths):raise ProjectError('new separate fan mechanical output required')
    before={str(p):digest(p) for p in paths}
    r,c,b=[json.loads(p.read_text(encoding='utf-8-sig')) for p in (paths[0],paths[2],paths[3])]
    validate_curve(c)
    if not isinstance(b,dict) or set(b)!={'product_reference','construction_class','source'} or b['product_reference']!=r.get('product',{}).get('designation') or not isinstance(b['source'],str) or not b['source'].strip():raise ProjectError('sourced exact product/class association required')
    result=evaluate(r,paths[1],c['speed_rpm'],b['construction_class'])
    if any(digest(Path(p))!=h for p,h in before.items()):raise ProjectError('fan mechanical inputs changed')
    result.update(inputs=before,inputs_unchanged=True,product_reference=b['product_reference'],association_source=b['source'],pypdf_version=importlib.metadata.version('pypdf'))
    out.mkdir(parents=True);(out/'fan-mechanical.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('record','pdf','curve','basis','out'):p.add_argument('--'+name,type=Path,required=True)
    r=run(**vars(p.parse_args()));print(json.dumps(r,indent=2));return 0 if r['status']=='pass' else 2

if __name__=='__main__':raise SystemExit(main())

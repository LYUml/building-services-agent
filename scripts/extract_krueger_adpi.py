"""Pinned Krueger Type 3 native-line chart extraction using unchanged pdf2plot."""
import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
SOURCE_SHA='f98aa9ded59150e157c83d5c5114faaa1a24c185928709ffe5d60c9b2f607988'


def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def extract(pdf,output):
    import fitz
    from extract_tcf_vectors import split_lines
    pdf,output=Path(pdf).resolve(),Path(output).resolve()
    project=Path(__import__('os').environ.get('BSA_PROJECT_ROOT',ROOT)).resolve()
    if not pdf.is_relative_to(project) or not output.is_relative_to(project) or output.exists() or output==pdf or output in pdf.parents:raise ValueError('Explicit selected project and fresh separate output required')
    lock=json.loads((ROOT/'adapters/pdf2plot/lock.json').read_text(encoding='utf-8'))
    helper=ROOT/'tools/pdf2plot-99a8ee1/pdf2plot_helper.py'
    if digest(pdf)!=SOURCE_SHA or digest(helper)!=lock['files']['pdf2plot_helper.py'] or importlib.metadata.version('PyMuPDF')!='1.26.7':raise ValueError('Exact source/helper/runtime required')
    with fitz.open(pdf) as source:
        page=source[10];drawings=page.get_drawings();text=page.get_text()
        if 'CIRCULAR CEILING PATTERN' not in text or '80 Btuh/ft' not in text:raise ValueError('Type 3 source/legend differs')
        left,right,top,bottom=90.52040100097656,288.6343994140625,548.2874145507812,638.8184204101562
        for idx,y in [(45,593.5635986328125),(49,top)]:
            item=drawings[idx]['items'][0]
            if item[0]!='l' or math.dist(item[1],(left,y))>1e-5 or math.dist(item[2],(right,y))>1e-5:raise ValueError('Pinned native axis grid differs')
        first=split_lines(drawings[62]['items']);second=split_lines(drawings[63]['items']);third=split_lines(drawings[64]['items'])
        fragments=[first[0],first[1],second[0],second[1],third[0]]
        if [len(f) for f in fragments]!=[117,38,65,74,71]:raise ValueError('Native chart fragments differ')
        if math.dist(fragments[1][-1],fragments[2][0])>.001:raise ValueError('Visually identified 40-load fragment seam differs')
        if any(any(a[0]>=b[0] for a,b in zip(f,f[1:])) for f in fragments):raise ValueError('Native X order differs')
        height=page.rect.height
    output.mkdir(parents=True)
    raw=dict(canvas=dict(height=height),paths=[dict(id=i,points=[dict(x=x,y=height-y) for x,y in f]) for i,f in enumerate(fragments)])
    raw_path=output/'native-paths.json';raw_path.write_text(json.dumps(raw),encoding='utf-8')
    command=[sys.executable,'-X','utf8',str(helper),'export',str(raw_path),'--x-left',f'@{left}:0','--x-right',f'@{right}:2.5','--y-bottom',f'@{bottom}:60','--y-top',f'@{top}:100','--data','0','1','2','3','4','--output',str(output/'calibrated.csv')]
    process=subprocess.run(command,capture_output=True,text=True,encoding='utf-8')
    (output/'export.log').write_text(process.stdout+process.stderr,encoding='utf-8')
    if process.returncode:raise ValueError('Unchanged upstream linear calibration failed')
    with (output/'calibrated.csv').open(encoding='utf-8') as f:csv_rows=list(csv.DictReader(f))
    reconstructed=[];maximum=0
    for index,(fragment,load) in enumerate(zip(fragments,[20,40,40,60,80]),1):
        values=[r for r in csv_rows if int(r['series'])==index]
        if len(values)!=len(fragment):raise ValueError('Upstream point coverage differs')
        points=[]
        for saved,(x,y) in zip(values,fragment):
            actual=[2.5*(x-left)/(right-left),60+40*(bottom-y)/(bottom-top)]
            maximum=max(maximum,abs(float(saved['x'])-actual[0]),abs(float(saved['y'])-actual[1]))
            if not math.isclose(float(saved['x']),actual[0],rel_tol=5e-6,abs_tol=1e-6) or not math.isclose(float(saved['y']),actual[1],rel_tol=5e-6,abs_tol=1e-6):raise ValueError('Upstream calibration differs from native coordinate reconstruction')
            points.append(actual)
        reconstructed.append(dict(load_Btuh_ft2=load,fragment=index,points=points))
    result=dict(source_pdf_sha256=SOURCE_SHA,pdf_page=11,printed_page='a1-11',pattern='Type 3 circular ceiling pattern',upstream=lock,
        fragments=reconstructed,fragment_count=5,point_count=len(csv_rows),native_stroke_width_pdf_points=.35,
        stroke_width_ADPI_points=.35*40/(bottom-top),stroke_width_ratio=.35*2.5/(right-left),
        maximum_upstream_csv_absolute_difference=maximum,fragment_seam='40 Btuh/ft2 has two native fragments separated by 0.0003 PDF pt; preserved separately, no invented join',
        scope='Source drawing representation only; not measured ADPI accuracy, actual load interpolation, installation applicability or design acceptance',ADPI_verified=False,design_accepted=False)
    (output/'curves.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('fragment_count','point_count','ADPI_verified')}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('pdf');p.add_argument('--out',required=True);a=p.parse_args();extract(a.pdf,a.out)

"""Extract disjoint native TCF curves and delegate log calibration to pinned pdf2plot."""
import argparse
import csv
from hashlib import sha256
import importlib.metadata
import json
import math
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
PDF_SHA='a50f3202afc6fb0fc42af856d43493dc1079a529de36634d25bef9c9ebdcd18b'
SPEEDS=(960,1450,2000,2500,2850,3500)


def digest(path):return sha256(Path(path).read_bytes()).hexdigest()


def split_lines(items,tolerance=1e-5):
    chains=[]
    for item in items:
        if item[0]!='l' or len(item)!=3:raise ValueError('source-specific extractor supports line primitives only')
        a,b=[tuple(float(v) for v in point) for point in item[1:]]
        if not all(math.isfinite(v) for point in (a,b) for v in point):raise ValueError('finite native path required')
        if not chains or math.dist(a,chains[-1][-1])>tolerance:chains.append([a])
        chains[-1].append(b)
    return chains


def run(pdf,helper,out):
    import fitz
    pdf,helper,out=[Path(p).resolve() for p in (pdf,helper,out)]
    if out.exists() or not out.is_relative_to(ROOT) or out==pdf or out in pdf.parents:raise ValueError('new separate repository output required')
    lock=json.loads((ROOT/'adapters/pdf2plot/lock.json').read_text())
    if digest(pdf)!=PDF_SHA or digest(helper)!=lock['files']['pdf2plot_helper.py'] or importlib.metadata.version('PyMuPDF')!='1.26.7':raise ValueError('pinned source/helper/runtime required')
    with fitz.open(pdf) as doc:
        page=doc[16];drawings=page.get_drawings();words=page.get_text('words')
        green=[d for d in drawings if d.get('color') and all(abs(a-b)<2/65535 for a,b in zip(d['color'],(.04,.666,.293))) and len(d['items'])==1200]
        if len(green)!=1:raise ValueError('unique native green performance path required')
        chains=split_lines(green[0]['items'])
        if len(chains)!=6 or any(len(c)!=201 for c in chains):raise ValueError('six separate 201-point native curves required')
        for speed,chain in zip(SPEEDS,chains):
            labels=[w for w in words if w[4]==str(speed) and 0<chain[0][0]-w[2]<40 and -1<chain[0][1]-w[3]<5]
            if len(labels)!=1:raise ValueError('native curve speed-label association unresolved')
            if any(a[0]>=b[0] or a[1]>=b[1] for a,b in zip(chain,chain[1:])):raise ValueError('strictly increasing native X/decreasing pressure path required')
        # Source-specific visually reviewed axis anchors; assert native grid lines.
        left,right=150.9062042236328,536.9342041015625
        bottom,top=459.9173583984375,174.693359375
        grid=drawings[153]['items']
        for y in (bottom,top):
            if not any(k=='l' and math.dist(tuple(a),(left,y))<1e-3 and math.dist(tuple(b),(right,y))<1e-3 for k,a,b in grid):raise ValueError('native calibration grid differs')
        for label,y in [('100',bottom),('1,000',top)]:
            if len([w for w in words if w[4]==label and left-30<w[0]<left and abs((w[1]+w[3])/2-y)<2])!=1:raise ValueError('source pressure tick label unresolved')
        for label,x in [('0.2',left),('2',right)]:
            if len([w for w in words if w[4]==label and abs((w[0]+w[2])/2-x)<2 and 573<w[1]<580])!=1:raise ValueError('source flow tick label unresolved')
        height=page.rect.height
    out.mkdir(parents=True)
    paths=dict(canvas=dict(height=height),paths=[dict(id=i,points=[dict(x=x,y=height-y) for x,y in c]) for i,c in enumerate(chains)])
    raw=out/'disjoint-paths.json';raw.write_text(json.dumps(paths))
    target=out/'calibrated.csv'
    command=[sys.executable,'-X','utf8',str(helper),'export',str(raw),'--x-left',f'@{left}:.2','--x-right',f'@{right}:2','--y-bottom',f'@{bottom}:100','--y-top',f'@{top}:1000','--x-log','--y-log','--data',*[str(i) for i in range(6)],'--output',str(target)]
    process=subprocess.run(command,capture_output=True,text=True,encoding='utf-8')
    (out/'export.log').write_text(process.stdout+process.stderr,encoding='utf-8')
    if process.returncode:raise ValueError('pinned upstream calibration failed')
    with target.open() as stream:rows=list(csv.DictReader(stream))
    if len(rows)!=1206:raise ValueError('calibrated point coverage differs')
    maximum=0.
    for i,chain in enumerate(chains,1):
        values=[r for r in rows if int(r['series'])==i]
        for row,(x,y) in zip(values,chain):
            expected=(.2*10**((x-left)/(right-left)),100*10**((bottom-y)/(bottom-top)))
            maximum=max(maximum,*(abs(float(row[k])/v-1) for k,v in zip(('x','y'),expected)))
    if maximum>5e-6:raise ValueError('upstream export differs from independent log-coordinate reconstruction')
    # A third source grid tick independently probes calibration, beyond anchors.
    tick_x=304.418212890625
    grid_residual=abs((.2*10**((tick_x-left)/(right-left)))/.5-1)
    result=dict(source_pdf_sha256=PDF_SHA,source_page=17,upstream=lock,curve_count=6,points_per_curve=201,speed_labels_rpm=SPEEDS,discontinuities_preserved=5,independent_log_export_relative_error=maximum,source_half_flow_grid_relative_residual=grid_residual,anchors=dict(x=[left,right],flow_m3_s=[.2,2],y_top_down=[bottom,top],total_pressure_pa=[100,1000]),solver_ready=False,design_accepted=False,pending=['Source graph rounding/interpolation and extraction uncertainty bounds','Stable interval and installation applicability','Viscosity and actual product/motor/port identity','No electrical-power inference from chart labels'])
    if digest(pdf)!=PDF_SHA or digest(helper)!=lock['files']['pdf2plot_helper.py']:raise ValueError('extraction inputs changed')
    result['artifacts']={p.name:digest(p) for p in out.iterdir() if p.is_file()}
    (out/'extraction.json').write_text(json.dumps(result,indent=2));return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('pdf','helper','out'):p.add_argument('--'+name,type=Path,required=True)
    r=run(**vars(p.parse_args()));print(json.dumps({k:r[k] for k in ('curve_count','points_per_curve','independent_log_export_relative_error','solver_ready')}))

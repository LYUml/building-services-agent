"""Recheck native source points then bound physical-linear versus log-log interpolation."""
import argparse
from hashlib import sha256
import importlib.metadata
import json
import math
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from bsa.curve_interpolation import curve_bound
from extract_tcf_vectors import split_lines,PDF_SHA,SPEEDS


def digest(path):return sha256(Path(path).read_bytes()).hexdigest()


def run(pdf,extraction,out):
    import fitz
    pdf,extraction,out=[Path(p).resolve() for p in (pdf,extraction,out)]
    if out.exists() or not out.is_relative_to(ROOT) or out==extraction or out in extraction.parents:raise ValueError('new separate repository output required')
    if digest(pdf)!=PDF_SHA or importlib.metadata.version('PyMuPDF')!='1.26.7':raise ValueError('pinned source/runtime required')
    report=extraction/'extraction.json';raw=extraction/'disjoint-paths.json'
    before={str(p):digest(p) for p in (pdf,report,raw)}
    r=json.loads(report.read_text());paths=json.loads(raw.read_text())
    for name,expected in r['artifacts'].items():
        p=(extraction/name).resolve()
        if not p.is_relative_to(extraction) or digest(p)!=expected:raise ValueError('extraction artifact mismatch')
    expected_anchors=dict(x=[150.9062042236328,536.9342041015625],flow_m3_s=[.2,2],y_top_down=[459.9173583984375,174.693359375],total_pressure_pa=[100,1000])
    if r['source_pdf_sha256']!=PDF_SHA or r['anchors']!=expected_anchors or r['source_page']!=17:raise ValueError('reviewed source calibration required')
    with fitz.open(pdf) as doc:
        page=doc[16];drawings=page.get_drawings();height=page.rect.height
        green=[d for d in drawings if d.get('color') and all(abs(a-b)<2/65535 for a,b in zip(d['color'],(.04,.666,.293))) and len(d['items'])==1200]
        if len(green)!=1:raise ValueError('native performance curves required')
        chains=split_lines(green[0]['items'])
    original=dict(canvas=dict(height=height),paths=[dict(id=i,points=[dict(x=x,y=height-y) for x,y in c]) for i,c in enumerate(chains)])
    if paths!=original:raise ValueError('saved points differ from independently reopened native PDF')
    left,right=r['anchors']['x'];bottom,top=r['anchors']['y_top_down']
    curves=[]
    for speed,chain in zip(SPEEDS,chains):
        values=[(.2*10**((x-left)/(right-left)),100*10**((bottom-y)/(bottom-top))) for x,y in chain]
        curves.append(dict(speed_rpm=speed,flow_domain_m3_s=[values[0][0],values[-1][0]],pressure_domain_pa=[values[-1][1],values[0][1]],**curve_bound(values)))
    if any(digest(Path(p))!=h for p,h in before.items()):raise ValueError('interpolation audit source changed')
    result=dict(inputs=before,native_source_points_match=True,curve_count=len(curves),curves=curves,
        scope='Analytic chord versus exact power-law image of each native log-log LINE segment; no extrapolation and no physical performance uncertainty bound',
        methods=['y/y0=(x/x0)^k; k=ln(y1/y0)/ln(x1/x0)','Differentiate chord/y for maximum relative error and chord-y for maximum absolute error'],
        source_grid_relative_residual=r['source_half_flow_grid_relative_residual'],solver_ready=False,design_accepted=False,
        pending=['Source graph/axis rounding and manufacturer performance tolerance','CSV endpoint rounding effects and operating-point sensitivity','Stable interval, installation, actual hardware/motor/ports'])
    out.mkdir(parents=True);(out/'interpolation.json').write_text(json.dumps(result,indent=2));return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('pdf','extraction','out'):p.add_argument('--'+name,type=Path,required=True)
    r=run(**vars(p.parse_args()));print(json.dumps(dict(curves=r['curve_count'],maximum_relative=max(c['maximum_relative_pressure_excess'] for c in r['curves']),solver_ready=False)))

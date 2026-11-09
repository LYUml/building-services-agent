"""Real graph coordinates on a synthetic native duct: interpolation sensitivity, no release."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from bsa.cli import digest
from bsa.rectangular_binding import run as bind,verified_study
from bsa.fan_interpolation_envelope import run as envelope,COVERAGE
from bsa.rectangular_fan import MODEL
ROOT=Path(__file__).resolve().parents[1]


def run(pdf,extraction,out):
    pdf,extraction,out=[Path(p).resolve() for p in (pdf,extraction,out)]
    if out.exists() or not out.is_relative_to(ROOT):raise ValueError('new repository-local output required')
    before={str(p):digest(p) for p in (pdf,extraction/'extraction.json',extraction/'disjoint-paths.json')}
    out.mkdir(parents=True)
    command=[str(ROOT/'tools/pdf2plot-runtime/Scripts/python.exe'),str(ROOT/'scripts/check_tcf_interpolation.py'),'--pdf',str(pdf),'--extraction',str(extraction),'--out',str(out/'source-audit')]
    worker=subprocess.run(command,capture_output=True,text=True)
    (out/'source-worker.log').write_text(worker.stdout+worker.stderr,encoding='utf-8')
    if worker.returncode:raise ValueError('native source interpolation audit did not pass')
    audit=json.loads((out/'source-audit/interpolation.json').read_text());row=next(r for r in audit['curves'] if r['speed_rpm']==1450)
    metadata=json.loads((extraction/'extraction.json').read_text());raw=json.loads((extraction/'disjoint-paths.json').read_text())
    chain=raw['paths'][1]['points'];height=raw['canvas']['height'];left,right=metadata['anchors']['x'];bottom,top=metadata['anchors']['y_top_down']
    points=[dict(flow_m3_s=.2*10**((p['x']-left)/(right-left)),total_pressure_rise_pa=100*10**((bottom-(height-p['y']))/(bottom-top))) for p in chain]
    curve=dict(model=MODEL,pressure_basis='fan total pressure rise',source='manufacturer_graph',sources=dict(manufacturer_graph='TCF BC-SW 122 M300 page 17, native 1450 rpm graph coordinates; PDF SHA256 '+digest(pdf),viscosity_assumption='1.8e-5 Pa.s is a synthetic study assumption, not a published manufacturer value'),speed_rpm=1450,fluid=dict(density_kg_m3=1.2,dynamic_viscosity_pa_s=1.8e-5),inlet_total_pressure_pa=0,efficiency_basis='not supplied',points=points,flow_bracket_m3_s=[points[0]['flow_m3_s'],points[-1]['flow_m3_s']],flow_tolerance_m3_s=1e-10,pressure_tolerance_pa=1e-6,max_iterations=100)
    curve_file=out/'research-curve.json';curve_file.write_text(json.dumps(curve,indent=2))
    basis=dict(source='Native-source interpolation audit SHA256 '+digest(out/'source-audit/interpolation.json')+'; graph/manufacturer uncertainty unresolved',coverage=COVERAGE,relative_pressure_excess=row['maximum_relative_pressure_excess'],manufacturer_performance_uncertainty=None)
    basis_file=out/'interpolation-basis.json';basis_file.write_text(json.dumps(basis,indent=2))
    ex=ROOT/'examples/rectangular-air';cases={}
    for label,target in [('within-domain',200),('outside-domain',30)]:
        root=out/label;root.mkdir()
        p=json.loads((ex/'elbow-chain-project.json').read_text());p['sources']['research_duty']='Explicit synthetic terminal total-pressure target for source-curve research; not measured building duty or regulation';p['nodes'][-1].update(required_total_pressure_pa=target,source='research_duty')
        project=root/'project.json';project.write_text(json.dumps(p,indent=2))
        native=root/'native';bind(project,ex/'elbow-chain-model.json',ex/'elbow-chain-binding.json',native)
        args=(native/'network-input.json',ex/'elbow-chain-model.json',ex/'elbow-chain-binding.json',native/'bim/model.ifc',native/'analysis/network.json')
        verified_study(*args)
        result=envelope(args[0],curve_file,basis_file,root/'sensitivity')
        verified_study(*args)
        cases[label]=dict(status=result['status'],interpolation_only_checks_pass=result['interpolation_only_checks_pass'],operating_flow_envelope_m3_s=result['operating_flow_envelope_m3_s'],endpoint_status={k:r['status'] for k,r in result['endpoints'].items()},native_path_correspondence_pass=True,report_sha256=digest(root/'sensitivity/interpolation-envelope.json'))
    if cases['within-domain']['status']!='pending' or not cases['within-domain']['interpolation_only_checks_pass'] or cases['outside-domain']['status']!='fail' or any(v!='not_bracketed' for v in cases['outside-domain']['endpoint_status'].values()):raise ValueError('unexpected source-domain sensitivity behavior')
    if any(digest(Path(p))!=h for p,h in before.items()):raise ValueError('source changed during research')
    result=dict(inputs=before,cases=cases,solver_ready=False,design_accepted=False,scope='Real graph representation on synthetic native duct/duty/K/viscosity; interpolation-only sensitivity; no manufacturer-performance or design release')
    (out/'research.json').write_text(json.dumps(result,indent=2));return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('pdf','extraction','out'):p.add_argument('--'+name,type=Path,required=True)
    print(json.dumps(run(**vars(p.parse_args()))))

"""Pending source-native fan research task; no replacement native producer inputs."""
import json
import math
from pathlib import Path
import subprocess
from .cli import digest
from .engine import ProjectError
from .rectangular_binding import verified_study
from .fan_interpolation_envelope import run as sensitivity,COVERAGE
from .rectangular_fan import MODEL
ROOT=Path(__file__).resolve().parents[2]


def sources(pdf,extraction,basis):
    pdf,extraction,basis=[Path(p).resolve() for p in (pdf,extraction,basis)]
    r=json.loads(extraction.read_text(encoding='utf-8-sig'))
    if set(r.get('artifacts',{}))!={'calibrated.csv','disjoint-paths.json','export.log'}:raise ProjectError('complete native extraction artifacts required')
    files={pdf,extraction,basis}
    for name,sha in r['artifacts'].items():
        path=(extraction.parent/name).resolve()
        if not path.is_relative_to(extraction.parent) or not path.is_file() or digest(path)!=sha:raise ProjectError('source extraction artifact changed')
        files.add(path)
    b=json.loads(basis.read_text(encoding='utf-8-sig'))
    if not isinstance(b,dict) or set(b)!={'source','speed_rpm','inlet_total_pressure_pa'} or not isinstance(b['source'],str) or not b['source'].strip() or type(b['speed_rpm']) not in (int,float) or b['speed_rpm'] not in r.get('speed_labels_rpm',[]):raise ProjectError('explicit reviewed speed and research basis required')
    if type(b['inlet_total_pressure_pa']) not in (int,float) or not math.isfinite(b['inlet_total_pressure_pa']) or b['inlet_total_pressure_pa']<0:raise ProjectError('explicit sourced nonnegative inlet total-pressure reference required')
    return files


def run(project,model,binding,ifc,analysis,pdf,extraction,basis,out,python):
    paths=[Path(p).resolve() for p in (project,model,binding,ifc,analysis,pdf,extraction,basis)]
    out,python=[Path(p).resolve() for p in (out,python)]
    tracked=set(paths)|sources(*paths[5:])
    if out.exists() or not out.is_relative_to(ROOT) or any(out==p or out in p.parents for p in tracked) or not python.is_file():raise ProjectError('new separate research output and explicit runtime required')
    before={str(p):digest(p) for p in tracked}
    verified_study(*paths[:5])
    data=json.loads(paths[0].read_text(encoding='utf-8-sig'));b=json.loads(paths[7].read_text(encoding='utf-8-sig'))
    if not math.isclose(data['fluid']['density_kg_m3'],1.2,rel_tol=1e-12):raise ProjectError('manufacturer reference density mismatch; no correction inferred')
    out.mkdir(parents=True)
    command=[str(python),str(ROOT/'scripts/check_tcf_interpolation.py'),'--pdf',str(paths[5]),'--extraction',str(paths[6].parent),'--out',str(out/'source-audit')]
    worker=subprocess.run(command,capture_output=True,text=True)
    (out/'source-worker.log').write_text(worker.stdout+worker.stderr,encoding='utf-8')
    if worker.returncode:raise ProjectError('source-native interpolation worker failed; inspect source-worker.log')
    audit=json.loads((out/'source-audit/interpolation.json').read_text());metadata=json.loads(paths[6].read_text());raw=json.loads((paths[6].parent/'disjoint-paths.json').read_text())
    if metadata['speed_labels_rpm']!=[r['speed_rpm'] for r in audit['curves']]:raise ProjectError('speed labels differ from native source reconstruction')
    speed=b['speed_rpm'];row=next(r for r in audit['curves'] if r['speed_rpm']==speed);index=metadata['speed_labels_rpm'].index(speed)
    if index>=len(raw['paths']) or len(raw['paths'])!=len(metadata['speed_labels_rpm']):raise ProjectError('speed/path coverage differs')
    chain=raw['paths'][index]['points'];height=raw['canvas']['height'];left,right=metadata['anchors']['x'];bottom,top=metadata['anchors']['y_top_down']
    points=[dict(flow_m3_s=.2*10**((p['x']-left)/(right-left)),total_pressure_rise_pa=100*10**((bottom-(height-p['y']))/(bottom-top))) for p in chain]
    curve=dict(model=MODEL,pressure_basis='fan total pressure rise',source='manufacturer_graph',sources=dict(manufacturer_graph='TCF M300 page17 native curve; PDF SHA256 '+digest(paths[5]),fluid_basis=data['sources'][data['fluid']['source']],research_scope=b['source']),speed_rpm=speed,fluid={k:data['fluid'][k] for k in ('density_kg_m3','dynamic_viscosity_pa_s')},inlet_total_pressure_pa=b['inlet_total_pressure_pa'],efficiency_basis='not supplied',points=points,flow_bracket_m3_s=[points[0]['flow_m3_s'],points[-1]['flow_m3_s']],flow_tolerance_m3_s=1e-10,pressure_tolerance_pa=1e-6,max_iterations=100)
    curve_path=out/'research-curve.json';curve_path.write_text(json.dumps(curve,indent=2))
    bounds=dict(source='Reopened native source audit SHA256 '+digest(out/'source-audit/interpolation.json'),relative_pressure_excess=row['maximum_relative_pressure_excess'],coverage=COVERAGE,manufacturer_performance_uncertainty=None)
    bound_path=out/'interpolation-basis.json';bound_path.write_text(json.dumps(bounds,indent=2))
    result=sensitivity(paths[0],curve_path,bound_path,out/'sensitivity')
    verified_study(*paths[:5])
    if any(not Path(p).is_file() or digest(Path(p))!=h for p,h in before.items()):raise ProjectError('native research inputs changed')
    result.update(inputs=before,inputs_unchanged=True,native_path_correspondence_pass=True,speed_rpm=speed,runtime_sha256=digest(python),scope='Source-reopened manufacturer graph on inherited native rectangular path; research only, no equipment/design release')
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'tcf-research.json').write_text(json.dumps(result,indent=2));return result

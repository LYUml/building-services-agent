"""Fresh thermal and scoped pipe rules on a reverified saved IFC circulation."""
import argparse
import json
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from .water_binding import reconcile
from .circulation_duty import run as thermal_run
from .epanet_pipe_regulations import run as rules_run
from .fluid_bindings import density_declarations,check_density_consistency


def verify_producer(producer,template,binding):
    producer=Path(producer).resolve();template=Path(template).resolve();binding=Path(binding).resolve()
    report=producer/'water-binding.json';report_hash=digest(report)
    data=json.loads(report.read_text(encoding='utf-8-sig'))
    for p in (template,binding):
        if data.get('inputs',{}).get(str(p))!=digest(p):raise ProjectError('producer source identity differs')
    required={'model.ifc','network-input.json','geometry-binding.json','analysis/water.json','analysis/network.inp','analysis/network.bin','analysis/network.rpt'}
    if not required<=set(data.get('artifacts',{})):raise ProjectError('missing native producer coverage')
    for name,sha in data['artifacts'].items():
        p=(producer/name).resolve()
        if not p.is_relative_to(producer) or not p.is_file() or digest(p)!=sha:raise ProjectError('producer artifact changed: '+name)
    for name,sha in data['inputs'].items():
        p=Path(name)
        if not p.is_file() or digest(p)!=sha:raise ProjectError('producer original input changed')
    reconcile(producer/'model.ifc',producer/'network-input.json',json.loads(template.read_text()),json.loads(binding.read_text()))
    return dict(producer_report_sha256=report_hash,ifc_sha256=digest(producer/'model.ifc'),network_sha256=digest(producer/'network-input.json'),saved_geometry_reconciled=True)


def run(producer,template,binding,thermal_basis,rule_basis,pack,sources,out):
    producer=Path(producer).resolve();out=Path(out).resolve()
    files=[Path(p).resolve() for p in (template,binding,thermal_basis,rule_basis,pack)]
    if out==producer or out in producer.parents or out.is_relative_to(producer) or any(out==p or out in p.parents for p in files):
        raise ProjectError('output must be separate from producer and input files')
    before={str(p):digest(p) for p in files}
    native=verify_producer(producer,*files[:2])
    declarations=[]
    for kind,p in [('circulation_duty',files[2]),('epanet_pipe_regulations',files[3])]:
        declarations.extend(density_declarations(dict(id=kind,kind=kind),p))
    check_density_consistency(declarations)
    out.mkdir(parents=True,exist_ok=False)
    # Both runs use the same rederived native network, never a caller replacement.
    thermal=thermal_run(producer/'network-input.json',files[2],out/'thermal')
    rules=rules_run(producer/'network-input.json',files[3],files[4],sources,out/'rules')
    if verify_producer(producer,*files[:2])!=native or any(digest(Path(p))!=h for p,h in before.items()):raise ProjectError('bound inputs changed during checks')
    result=dict(saved_ifc_binding=native,input_hashes=before,density_declarations=declarations,
                thermal_checks_pass=thermal['calculated_checks_pass'],pipe_rules_status=rules['status'],
                status='fail' if not thermal['calculated_checks_pass'] or rules['status']=='fail' else rules['status'],
                design_accepted=False,regulatory_compliance='not_established',
                pending=['actual product and fluid-temperature applicability','physical fittings, clash and viewer acceptance','heat transfer, controls, other regulations and complete engineering acceptance'])
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'ifc-circulation-checks.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('producer','template','binding','thermal-basis','rule-basis','pack','sources','out'):parser.add_argument('--'+name,required=True,type=Path)
    a=parser.parse_args();r=run(a.producer,a.template,a.binding,a.thermal_basis,a.rule_basis,a.pack,a.sources,a.out)
    print(json.dumps(r,indent=2));return 0 if r['status']=='pass' else 2


if __name__=='__main__':raise SystemExit(main())

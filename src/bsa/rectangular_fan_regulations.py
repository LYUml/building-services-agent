"""Bind the scoped HK fan-power denominator to fresh, saved-IFC-checked rectangular supply flow."""
import copy
import json
import math
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from .network_binding import _prepare
from .rectangular_binding import inspect_saved
from .rectangular_network import calculate
from .regulations import evaluate,source_paths,method_paths


def run(project,model,binding,ifc,analysis,basis,pack,sources,out):
    paths=[Path(p).resolve() for p in (project,model,binding,ifc,analysis,basis,pack)];project,model,binding,ifc,analysis,basis,pack=paths
    out=Path(out).resolve();root=Path(__file__).resolve().parents[2]
    if not out.is_relative_to(root) or out.exists() or any(out==p or out in p.parents for p in paths):raise ProjectError('new separate repository-local fan check output required')
    before={str(f):digest(f) for f in paths}
    data=[json.loads(p.read_text(encoding='utf-8-sig')) for p in (project,model,binding,analysis,basis,pack)];p,m,b,study,basis_data,rule_pack=data
    if set(basis_data)!={'jurisdiction','rule_pack','edition_decisions','facts'} or not isinstance(basis_data['facts'],dict):raise ProjectError('explicit fan basis without replacement project required')
    if 'supply_design_airflow' in basis_data['facts']:raise ProjectError('fan supply airflow is derived; override forbidden')
    if len(rule_pack.get('rules',[]))!=1 or rule_pack['rules'][0]['method']!='base_air_distribution_fan_power':raise ProjectError('one scoped base fan-power pack required')
    tracked=set(paths)|source_paths(rule_pack,sources)|method_paths(rule_pack)|{Path(__file__).resolve()}
    before.update({str(f):digest(f) if f.is_file() else None for f in tracked if str(f) not in before})
    from .rectangular_binding import verified_study
    fresh=verified_study(project,model,binding,ifc,analysis)
    derived=copy.deepcopy(basis_data)
    flow=fresh['supply_flow_m3_s']*1000
    derived['facts']['supply_design_airflow']=dict(value=flow,unit='L/s',source='Fresh source-native-bound rectangular supply flow; project SHA256 '+digest(project)+'; IFC SHA256 '+digest(ifc))
    result=evaluate(rule_pack,derived,sources)
    association=basis_data['facts'].get('network_represents_supply_design_flow',{})
    if not isinstance(association,dict) or association.get('value') is not True or not isinstance(association.get('source'),str) or not association['source'].strip():
        result['checks'][0]['status']='pending';result['checks'][0]['reasons'].append('source-backed whole-supply design-flow correspondence unresolved');result['supported_checks_pass']=False
    if any((digest(Path(f)) if Path(f).is_file() else None)!=sha for f,sha in before.items()):raise ProjectError('fan-check inputs changed during evaluation')
    statuses=[r['status'] for r in result['checks']]
    report=dict(status='fail' if 'review_required' in statuses else 'pass' if result['supported_checks_pass'] else 'pending',
        inputs=before,inputs_unchanged=True,project_sha256=digest(project),ifc_sha256=digest(ifc),native_geometry_correspondence_pass=True,
        fresh_supply_design_flow_l_s=flow,rule_result=result,derived_facts=derived['facts'],design_accepted=False,regulatory_compliance='not_established',
        scope='Verified native rectangular network/design-flow denominator only; fan motor power/inventory and whole-supply meaning are sourced assertions, not native fan selection or full HVAC acceptance')
    out.mkdir(parents=True);(out/'fan-regulations.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report

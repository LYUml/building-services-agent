"""Source-declared single-phase radial feeder paths; no inferred topology."""
import argparse
import copy
import json
import math
from pathlib import Path
from .cli import digest
from .engine import calculate, ProjectError

PHASE_METHOD='independent_single_phase_radials'
RETURN_BASIS='dedicated per-radial return paths; no shared-neutral coupling'


def calculate_phase_paths(project,topology):
    """Partition declared independent radials; reuse the original same-phase solver."""
    fields={'schema_version','method','source','installation_origin','return_path_basis','radials'}
    if set(topology)!=fields or type(topology['schema_version']) is not int or topology['schema_version']!=1 or topology['return_path_basis']!=RETURN_BASIS or not isinstance(topology['source'],str) or not topology['source'].strip() or not isinstance(topology['installation_origin'],str) or not topology['installation_origin'].strip():
        raise ProjectError('Explicit sourced independent radial return-path basis required')
    branch=calculate(project);phases={c['phase'] for c in project['circuits']};radials=topology['radials']
    if not isinstance(radials,dict) or set(radials)!=phases:raise ProjectError('Independent radial groups must cover every original phase exactly')
    feeders=[];paths=[];groups={};used_ids=set();used_nodes=set();pending=[]
    for phase,radial in radials.items():
        if not isinstance(radial,dict) or radial.get('method')!='single_phase_scalar_radial' or radial.get('installation_origin')!=topology['installation_origin']:
            raise ProjectError('Each group requires the original same-phase method and common declared installation origin')
        subset=copy.deepcopy(project);subset['circuits']=[c for c in subset['circuits'] if c['phase']==phase]
        ids={c['id'] for c in subset['circuits']};subset['devices']=[d for d in subset['devices'] if d['circuit'] in ids]
        result=calculate_paths(subset,radial)
        feeder_ids={f['id'] for f in result['feeders']}
        nodes={node for f in result['feeders'] for node in (f['from_node'],f['to_node']) if node!=topology['installation_origin']}
        if used_ids & feeder_ids or used_nodes & nodes:raise ProjectError('Cross-phase feeder identities or non-origin nodes cannot be shared by independent radials')
        used_ids.update(feeder_ids);used_nodes.update(nodes)
        feeders.extend(dict(f,phase=phase) for f in result['feeders'])
        paths.extend(dict(p,phase=phase) for p in result['paths'])
        groups[phase]=dict(circuit_ids=sorted(ids),feeder_ids=sorted(feeder_ids))
        pending.extend(result['pending'])
    if {p['circuit'] for p in paths}!={c['id'] for c in project['circuits']} or len(paths)!=len(project['circuits']):raise ProjectError('Complete once-only original circuit coverage required')
    return dict(branch_calculation=branch,feeders=feeders,paths=paths,installation_origin=topology['installation_origin'],
        topology_source=topology['source'],phase_groups=groups,return_path_basis=RETURN_BASIS,design_accepted=False,
        scope='Declared independent same-phase radial groups at nominal voltage; original phase labels and all loads preserved; no shared-neutral or multiphase load-flow solution',
        pending=list(dict.fromkeys(pending+['dedicated return-path applicability and actual source/topology completeness','shared-neutral/phase coupling not modelled'])))


def calculate_paths(project, topology):
    if isinstance(topology,dict) and topology.get('method')==PHASE_METHOD:return calculate_phase_paths(project,topology)
    branch=calculate(project)
    def text(value):
        return isinstance(value,str) and bool(value.strip())
    if topology.get('schema_version')!=1 or not text(topology.get('source')) or not text(topology.get('installation_origin')):
        raise ProjectError('versioned sourced installation origin required')
    if topology.get('method')!='single_phase_scalar_radial':
        raise ProjectError('explicit single_phase_scalar_radial method required')
    if len({c['phase'] for c in project['circuits']})!=1:
        raise ProjectError('all circuits must share one phase; three-phase/unbalanced calculation unsupported')
    origin=topology['installation_origin'];feeders=topology.get('feeders');attachments=topology.get('circuit_from_node')
    if not isinstance(feeders,list) or not isinstance(attachments,dict) or set(attachments)!={c['id'] for c in project['circuits']}:
        raise ProjectError('explicit feeders and exact circuit attachment coverage required')
    incoming={};ids=set()
    for feeder in feeders:
        if not isinstance(feeder,dict) or any(not text(feeder.get(k)) for k in ('id','from_node','to_node','source')):
            raise ProjectError('sourced feeder identity and endpoints required')
        if feeder['id'] in ids or feeder['to_node'] in incoming or feeder['to_node']==origin:
            raise ProjectError('unique feeder ids and one incoming edge per non-origin node required')
        ids.add(feeder['id']);incoming[feeder['to_node']]=feeder
        for key in ('route_length_m','vd_mv_a_m'):
            v=feeder.get(key)
            if type(v) not in (int,float) or not math.isfinite(v) or v<0:
                raise ProjectError('finite nonnegative feeder length and coefficient required')
    paths={};used=set()
    for circuit,node in attachments.items():
        if not text(node):raise ProjectError('circuit attachment node required')
        seen=set();path=[]
        while node!=origin:
            if node in seen or node not in incoming:raise ProjectError('cycle or disconnected circuit path')
            seen.add(node);f=incoming[node];path.append(f['id']);node=f['from_node']
        paths[circuit]=list(reversed(path));used.update(path)
    if used!=ids:raise ProjectError('unused or disconnected feeder; complete load coverage required')
    currents={c['id']:c['design_current_a'] for c in branch['circuits']}
    rows=[]
    for f in feeders:
        downstream=sorted(c for c,path in paths.items() if f['id'] in path)
        current=sum(currents[c] for c in downstream)
        drop=f['vd_mv_a_m']*current*f['route_length_m']/1000
        rows.append(dict(**f,downstream_circuits=downstream,design_current_a=current,voltage_drop_v=drop))
    drops={f['id']:f['voltage_drop_v'] for f in rows};results=[]
    for c in branch['circuits']:
        total=sum(drops[f] for f in paths[c['id']])+c['voltage_drop_v']
        percent=total/project['supply_voltage_v']*100
        if not all(math.isfinite(v) for v in (total,percent,c['design_current_a'])):
            raise ProjectError('nonfinite electrical path result')
        results.append(dict(circuit=c['id'],device_ids=c['device_ids'],feeder_ids=paths[c['id']],
                            branch_voltage_drop_v=c['voltage_drop_v'],total_voltage_drop_v=total,total_voltage_drop_percent=percent))
    return dict(branch_calculation=branch,feeders=rows,paths=results,installation_origin=origin,
                topology_source=topology['source'],design_accepted=False,
                scope='Sourced single-phase scalar radial path budget at nominal voltage; branch demand factors apply simultaneously, no extra feeder diversity',
                pending=['actual route lengths and coefficient applicability','load simultaneity and topology completeness','feeder protection/ampacity','three-phase, neutral and phasor effects','regulatory and engineering acceptance'])


def bind_facts(result, basis, evidence):
    """Replace the numeric metric; never invent applicability/edition decisions."""
    if not isinstance(basis.get('facts'),dict):raise ProjectError('explicit regulatory fact basis required')
    projects={}
    for row in result['paths']:
        p=copy.deepcopy(basis)
        p['facts']['installation_origin_to_fixed_equipment_voltage_drop']=dict(
            value=row['total_voltage_drop_percent'],unit='percent_of_nominal_supply_voltage',
            source=evidence+'; circuit '+row['circuit']+'; devices '+','.join(row['device_ids']))
        projects[row['circuit']]=p
    return projects


def run(project,topology,basis,out):
    paths=[Path(p).resolve() for p in (project,topology,basis)];out=Path(out).resolve()
    if any(out==p or out in p.parents for p in paths):raise ProjectError('output must not contain inputs')
    before={str(p):digest(p) for p in paths}
    values=[json.loads(p.read_text(encoding='utf-8-sig')) for p in paths]
    result=calculate_paths(*values[:2]);result.update(inputs=before,inputs_unchanged=True)
    if any(digest(Path(p))!=h for p,h in before.items()):raise ProjectError('electrical path source changed')
    out.mkdir(parents=True,exist_ok=False)
    report=out/'electrical-paths.json';report.write_text(json.dumps(result,indent=2),encoding='utf-8')
    bound=bind_facts(result,values[2],str(report)+' SHA256 '+digest(report))
    (out/'regulation-projects.json').write_text(json.dumps(bound,indent=2),encoding='utf-8')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project',type=Path)
    for k in ('topology','basis','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();run(a.project,a.topology,a.basis,a.out)


if __name__=='__main__':main()

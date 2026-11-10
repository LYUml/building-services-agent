"""Compare verified HVAC scenarios without selecting or approving a design."""
import argparse
import json
from pathlib import Path
from .workflow import verify
from .cli import digest


def capture(directory):
    directory=Path(directory).resolve()
    if not verify(directory)['integrity_pass']:raise ValueError('Scenario evidence changed')
    path=directory/'workflow.json';w=json.loads(path.read_text(encoding='utf-8'));data={}
    for kind,filename in [('air_allocation','allocation.json'),('duct_schedule','results.json')]:
        names=[n for n,t in w['tasks'].items() if t['kind']==kind]
        if len(names)!=1:raise ValueError('One allocation and schedule per scenario required')
        artifact=directory/names[0]/filename
        if not artifact.is_file():raise ValueError('Scenario did not produce required calculation evidence')
        data[kind]=json.loads(artifact.read_text(encoding='utf-8'))
    return directory,w,data


def run(baseline,candidate,output):
    baseline,candidate,output=(Path(p).resolve() for p in (baseline,candidate,output))
    if baseline==candidate or output.exists() or any(output==p or p in output.parents or output in p.parents for p in (baseline,candidate)):
        raise ValueError('Distinct scenarios and new output outside both runs required')
    captures=[capture(p) for p in (baseline,candidate)]
    first,second=[w for _,w,_ in captures]
    if {(r['id'],r['quote']) for r in first['requirements']}!={(r['id'],r['quote']) for r in second['requirements']}:
        raise ValueError('Scenarios must address the same source requirements')
    summaries=[]
    for directory,w,data in captures:
        a,d=data['air_allocation'],data['duct_schedule']
        summaries.append(dict(directory=str(directory),load_inputs=a['load']['inputs'],total_supply_L_s=a['load']['supply_flow_L_s'],
            terminals={t['id']:dict(center_m=t['center_m'],maximum_flow_L_s=t['maximum_flow_L_s']) for t in a['terminals']},
            sections={s['id']:dict(size_m=[s['inputs'].get('width_m'),s['inputs'].get('height_m')],calculated=s['calculation'] is not None,failures=s.get('failures',[])) for s in d['sections']},
            schedule_status=d['status'],unresolved_tasks=[n for n,t in w['tasks'].items() if t['status']!='pass']))
    a,b=summaries
    if set(a['terminals'])!=set(b['terminals']) or set(a['sections'])!=set(b['sections']):raise ValueError('Terminal/section identity coverage differs')
    changes={k:dict(baseline=a['load_inputs'][k],candidate=b['load_inputs'][k]) for k in a['load_inputs'] if a['load_inputs'][k]!=b['load_inputs'][k]}
    result=dict(scenarios=summaries,load_input_changes=changes,total_supply_change_L_s=b['total_supply_L_s']-a['total_supply_L_s'],
        section_changes={k:dict(baseline=a['sections'][k],candidate=b['sections'][k]) for k in a['sections'] if a['sections'][k]!=b['sections'][k]},
        candidate_uncomputed_sections=[k for k,s in b['sections'].items() if not s['calculated']],
        inputs={str(directory/'workflow.json'):digest(directory/'workflow.json') for directory,_,_ in captures},
        selected_scenario=None,design_accepted=False,scope='Scenario evidence comparison; no optimizer, applicability waiver or design selection')
    if any(not verify(directory)['integrity_pass'] for directory,_,_ in captures):raise ValueError('Scenario changed during comparison')
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2),encoding='utf-8');return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('baseline');p.add_argument('candidate');p.add_argument('--out',required=True)
    a=p.parse_args();r=run(a.baseline,a.candidate,a.out)
    print('Supply change L/s:',r['total_supply_change_L_s'],'candidate uncomputed sections:',r['candidate_uncomputed_sections'])

"""Source-bound numerical HVAC report from an executed workflow, not approval."""
import argparse
import html
import json
import math
from pathlib import Path
from .cli import digest
from .workflow import verify


def table(headers,rows):
    def cells(tag,row):return ''.join(f'<{tag}>{html.escape(str(x))}</{tag}>' for x in row)
    return '<table><thead><tr>'+cells('th',headers)+'</tr></thead><tbody>'+''.join('<tr>'+cells('td',r)+'</tr>' for r in rows)+'</tbody></table>'


def compose(workflow,allocation,lookup,ducts):
    expected={t['id']:t for t in allocation['terminals']}
    found={t['id']:t for t in lookup['terminals']}
    if len(expected)!=len(allocation['terminals']) or len(found)!=len(lookup['terminals']) or set(expected)!=set(found):
        raise ValueError('Report terminal identities differ')
    terminal=[]
    for name,t in found.items():
        for direction,r in t['directions'].items():
            mx,mn=r['cases']['maximum'],r['cases']['minimum']
            for case,key in [(mx,'maximum_flow_L_s'),(mn,'minimum_flow_L_s')]:
                if not math.isclose(case['flow_L_s'],expected[name][key],rel_tol=1e-10):raise ValueError('Report terminal flow differs from allocation')
            terminal.append([name,direction,f"{mx['flow_L_s']:.1f}",f"{mn['flow_L_s']:.1f}",f"{r['characteristic_length_m']:.3f}",*[f'{value:.3f}' if value is not None else 'outside catalogue' for value in (mx['T025_m'],mn['T025_m'],mx['ratio'],mn['ratio'])]])
    aggregation=ducts['flow_aggregation']
    if not math.isclose(aggregation['total_flow_L_s'],allocation['load']['supply_flow_L_s'],rel_tol=1e-10):raise ValueError('Report tree flow differs from allocation')
    sections=[]
    for r in ducts['sections']:
        i,c=r['inputs'],r['calculation']
        if not math.isclose(i['flow_m3_s']*1000,aggregation['section_flow_L_s'][r['id']],rel_tol=1e-10):raise ValueError('Report section flow differs from tree')
        sections.append([r['id'],f"{i['flow_m3_s']*1000:.1f}",f"{i['width_m']*1000:.0f} x {i['height_m']*1000:.0f}",f"{c['actual_velocity_m_s']:.2f}",f"{c['friction_Pa_m']:.3f}"])
    basis=[[k,str(v['value'])+' '+v['unit'],v['classification'],v['source']] for k,v in allocation['load']['inputs'].items()]
    groups=[[k,f'{q:.1f}',f"{q*allocation['turndown']:.1f}"] for k,q in sorted(aggregation['leaf_flow_L_s'].items())]
    requirements=[[r['id'],r['quote'],r['execution_status'],r['acceptance_status'],r['acceptance']] for r in workflow['requirements']]
    parts=['<!doctype html><html lang="en"><meta charset="utf-8"><title>HVAC System Design</title>',
        '<style>body{font:15px/1.5 Arial;max-width:1200px;margin:35px auto;color:#15333b}table{width:100%;border-collapse:collapse;margin:15px 0}th,td{padding:6px;border:1px solid #bbcbd0;text-align:left;overflow-wrap:anywhere}th{background:#e8f1f3}thead{display:table-header-group}tr{break-inside:avoid}h2{break-after:avoid}</style>',
        '<h1>HVAC System Design</h1><p>Design study. Numerical execution is not full engineering or regulatory acceptance. All requirement states below are retained from the verified workflow.</p>',
        '<h2>Source-classified load basis</h2>',table(['Input','Value','Classification','Source'],basis),
        '<p>'+html.escape(allocation['geometry_basis'])+'</p>',
        '<h2>Cooling and supply airflow</h2>',table(['Total thermal cooling kW','Trial sensible thermal kW','Trial supply L/s'],[[f"{allocation['load']['total_cooling_kW_thermal']:.3f}",f"{allocation['load']['sensible_trial_kW_thermal']:.3f}",f"{allocation['load']['supply_flow_L_s']:.1f}"]]),
        '<p>Displayed thermal loads use three decimal places in kW and airflow uses one decimal place in L/s. Calculations retain their original precision in the source artifacts.</p><p>A uniform allowance and sensible fraction do not establish the actual room sensible load for ADPI.</p>',
        '<h2>Maximum and minimum terminal lookup</h2><p>'+html.escape(lookup['basis'])+'</p><p>Listed L values remain input assumptions pending characteristic-length applicability review. No ADPI pass is inferred.</p>',
        table(['ID','Direction','Max L/s','Min L/s','Input L m','Max throw m','Min throw m','Max T/L','Min T/L'],terminal),
        '<h2>Leaf group flows</h2>',table(['Group','Max L/s','Min L/s'],groups),
        '<h2>Selected duct sections</h2><p>'+html.escape(ducts['basis'])+'</p>',table(['Section','L/s','Size mm','m/s','Pa/m'],sections),
        '<h2>Complete source requirement matrix</h2>',table(['ID','Source requirement','Execution','Acceptance state','Acceptance criterion'],requirements),
        '<p>Native files and plots are separate workflow artifacts. Their visual review, physical connections, source applicability and final delivery requirements remain distinct.</p></html>']
    return ''.join(parts),dict(terminal_direction_rows=len(terminal),leaf_groups=len(groups),duct_sections=len(sections),requirements=len(requirements))


def run(directory,output):
    directory,output=Path(directory).resolve(),Path(output).resolve()
    if output.exists() or output==directory or output in directory.parents or directory in output.parents:
        raise ValueError('New report directory outside immutable workflow required')
    if not verify(directory)['integrity_pass']:raise ValueError('Workflow evidence is stale or changed')
    workflow=json.loads((directory/'workflow.json').read_text(encoding='utf-8'))
    paths=[];data=[]
    for kind,filename in [('air_allocation','allocation.json'),('terminal_throw','terminal-results.json'),('duct_schedule','results.json')]:
        names=[name for name,t in workflow['tasks'].items() if t['kind']==kind]
        if len(names)!=1 or workflow['tasks'][names[0]]['status']!='pass':raise ValueError('One passing '+kind+' task required')
        p=directory/names[0]/filename;paths.append(p);data.append(json.loads(p.read_text(encoding='utf-8')))
    content,counts=compose(workflow,*data)
    pins={str(p):digest(p) for p in [directory/'workflow.json',*paths]}
    if not verify(directory)['integrity_pass']:raise ValueError('Workflow changed during report preparation')
    output.mkdir(parents=True);target=output/'HVAC System Design.html';target.write_text(content,encoding='utf-8')
    result=dict(inputs=pins,html_sha256=digest(target),counts=counts,scope='Single allocation/lookup/tree study; complete requirement states retained. No PDF or full design acceptance.',design_accepted=False)
    (output/'report.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run_directory');p.add_argument('--out',required=True)
    a=p.parse_args();print(run(a.run_directory,a.out)['counts'])

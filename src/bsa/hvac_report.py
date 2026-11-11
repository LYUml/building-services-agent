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


def connection_summary(directory,workflow,paths,review):
    """Recheck saved geometry instead of trusting review success/count assertions."""
    import ezdxf
    from .air_terminal_drawing import inspect
    record=json.loads(review.read_text(encoding='utf-8'))
    if record.get('workflow_sha256')!=digest(directory/'workflow.json') or record.get('schedule_sha256')!=digest(paths[2]):
        raise ValueError('Terminal review belongs to another workflow or schedule')
    inputs={Path(p).resolve():sha for p,sha in record['inputs'].items()}
    if len(inputs)!=4 or any(not p.is_file() or digest(p)!=sha for p,sha in inputs.items()):
        raise ValueError('Terminal review input evidence changed')
    lineage=record['lineage']
    if len(lineage)!=4 or any(workflow['tasks'].get(n,{}).get('kind')!=k or workflow['tasks'][n]['status']!='pass' for n,k in zip(lineage,('duct_sheet_native','duct_sheet','duct_schedule','air_allocation'))):
        raise ValueError('Passing terminal review ancestry required')
    drawing=directory/lineage[0]/'reopened/source-export.dxf'
    if paths[0]!=directory/lineage[3]/'allocation.json' or paths[2]!=directory/lineage[2]/'results.json' or drawing not in inputs or paths[0] not in inputs:
        raise ValueError('Terminal review source identities differ')
    sources=[p for p in inputs if p not in (drawing,paths[0])]
    if any(workflow['inputs'].get(str(p))!=inputs[p] for p in sources):
        raise ValueError('Terminal review uses sources outside workflow')
    schedule=json.loads(paths[2].read_text(encoding='utf-8'))
    projects=[p for p in sources if inputs[p]==schedule['input_sha256']]
    if len(projects)!=1:raise ValueError('Unique calculated duct project required')
    project=projects[0];binding=next(p for p in sources if p!=project)
    fresh=inspect(ezdxf.readfile(drawing),json.loads(paths[0].read_text(encoding='utf-8')),
        json.loads(project.read_text(encoding='utf-8'))['tree'],json.loads(binding.read_text(encoding='utf-8')),record['layers'])
    if any(record.get(k)!=v for k,v in fresh.items()):raise ValueError('Terminal review differs from saved geometry')
    return (f"Saved native drawing correspondence covers {fresh['terminal_count']} terminals, "
        f"{len(fresh['groups'])} groups and {fresh['rigid_section_count']} rigid sections. "
        f"The longest straight centre-to-centre planar flexible connection is {fresh['maximum_plan_length_m']:.3f} m. "
        'This does not verify physical ports, installed flexible lengths, labels, three-dimensional coordination or regulatory compliance.')


def adpi_summary(directory,lookup,review):
    """Reconstruct the screen from exact settings/source/lookup identities."""
    from . import adpi_review,adpi_screen
    review_hash=digest(review)
    record=json.loads(review.read_text(encoding='utf-8'))
    if not isinstance(record.get('settings_path'),str):raise ValueError('ADPI review settings identity missing;rerun its source review')
    settings=Path(record['settings_path']).resolve()
    spec,pins=adpi_review.settings_inputs(settings)
    for p in (Path(adpi_review.__file__),Path(adpi_screen.__file__),directory/'workflow.json',lookup):
        pins[str(p.resolve())]=digest(p)
    task=record.get('lookup_task')
    workflow=json.loads((directory/'workflow.json').read_text(encoding='utf-8'))
    if not isinstance(task,str) or workflow['tasks'].get(task,{}).get('kind')!='terminal_throw' or directory/task/'terminal-results.json'!=lookup:
        raise ValueError('ADPI review belongs to another terminal lookup')
    if record.get('inputs')!=pins or record.get('generator_sha256')!=digest(Path(adpi_review.__file__)):
        raise ValueError('ADPI review source/method/workflow identities differ')
    expected=adpi_screen.screen(json.loads(lookup.read_text(encoding='utf-8')),criterion=spec['criterion'],room_load_W_m2=spec['room_load_W_m2'],facts=spec['facts'])
    if any(record.get(k)!=v for k,v in expected.items() if k!='scope') or record.get('fact_evidence',{})!=spec.get('fact_evidence',{}):
        raise ValueError('ADPI review differs from fresh source-scoped screening')
    labels=dict(room_load_verified='Room sensible load',product_category_verified='Product category within selected criterion',
        lengths_verified='Characteristic lengths',installation_verified='Installation conditions',edition_selected='Criterion edition selection')
    state=lambda value:'Declared supported' if value is True else 'Declared rejected' if value is False else 'Unverified'
    criterion=expected['criterion']
    load='Unknown' if expected['room_load_W_m2'] is None else str(expected['room_load_W_m2'])+' W/m2'
    paragraphs=[
        'Applicability: '+expected['applicability']+'. '+str(len(expected['cases']))+' maximum/minimum directional cases. This is source-scoped ratio screening;no measured or predicted ADPI is claimed.',
        'Selected criterion: '+criterion['source']+'. Room sensible-load range: '+str(criterion['room_load_range_W_m2'][0])+' to '+str(criterion['room_load_range_W_m2'][1])+' W/m2. T0.25/L range: '+str(criterion['ratio_range'][0])+' to '+str(criterion['ratio_range'][1])+'.',
        'Supplied room-load value: '+load+'. Within source range: '+str(expected['load_in_source_range'])+'. An unverified preliminary value does not establish the actual room load or an ADPI failure.',
        'Missing applicability facts: '+(', '.join(labels[k] for k in expected['missing_facts']) or 'None declared')+'. Rejected facts: '+(', '.join(labels[k] for k in expected['rejected_facts']) or 'None declared')+'.']
    outcomes={key:sum(row['status']==key for row in expected['cases']) for key in ('not_evaluated','within_sourced_ratio_range','fail')}
    paragraphs.append('Screened outcomes: '+', '.join(key+'='+str(value) for key,value in outcomes.items())+'. All ratios within the selected applicable scope: '+str(expected['all_ratios_within_scope'])+'. Pending applicability is not a comfort pass or a measured failure.')
    paragraphs.extend(labels[k]+': '+state(value)+'.' for k,value in expected['facts'].items())
    for name,records in spec.get('fact_evidence',{}).items():
        for index,item in enumerate(records,1):
            paragraphs.append('Evidence for '+labels[name]+' '+str(index)+': '+Path(item['source']).name+'; '+item['locator']+'. '+item['note'])
    paragraphs.append('Source hashes and exact evidence notes are retained in the report manifest. Declarations and source-byte identity do not authenticate physical conditions or establish comfort/engineering acceptance.')
    pins[str(review)]=review_hash
    return paragraphs,pins


def run(directory,output,*,terminal_review=None,adpi_review=None):
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
    review_paragraphs=[];review_pins={}
    if adpi_review is not None:
        review=Path(adpi_review).resolve()
        review_paragraphs,review_pins=adpi_summary(directory,paths[1],review)
        if any(output==Path(p) or output in Path(p).parents for p in review_pins):raise ValueError('Report must not contain ADPI source evidence')
        section='<h2>ADPI applicability and evidence</h2>'+''.join('<p>'+html.escape(text)+'</p>' for text in review_paragraphs)
        content=content.replace('<h2>Maximum and minimum terminal lookup</h2>',section+'<h2>Maximum and minimum terminal lookup</h2>')
    if terminal_review is not None:
        review=Path(terminal_review).resolve()
        if output==review or output in review.parents:raise ValueError('Report must not contain review input')
        review_hash=digest(review)
        summary=connection_summary(directory,workflow,paths,review)
        if digest(review)!=review_hash:raise ValueError('Terminal review changed during reporting')
        content=content.replace('<h2>Complete source requirement matrix</h2>',
            '<h2>Saved terminal connections</h2><p>'+html.escape(summary)+'</p><h2>Complete source requirement matrix</h2>')
        paths.append(review)
    pins={str(p):digest(p) for p in [directory/'workflow.json',*paths]}
    pins.update(review_pins)
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Report review evidence changed during preparation')
    if not verify(directory)['integrity_pass']:raise ValueError('Workflow changed during report preparation')
    output.mkdir(parents=True);target=output/'HVAC System Design.html';target.write_text(content,encoding='utf-8')
    result=dict(inputs=pins,html_sha256=digest(target),counts=counts,scope='Single allocation/lookup/tree study; complete requirement states retained. No PDF or full design acceptance.',design_accepted=False)
    result['adpi_review_summary']=review_paragraphs
    (output/'report.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run_directory');p.add_argument('--out',required=True);p.add_argument('--terminal-review');p.add_argument('--adpi-review')
    a=p.parse_args();print(run(a.run_directory,a.out,terminal_review=a.terminal_review,adpi_review=a.adpi_review)['counts'])

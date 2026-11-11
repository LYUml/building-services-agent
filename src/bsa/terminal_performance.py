"""Source-bound diffuser catalogue pressures; NC rows retained without interpolation."""
import argparse
import html
import json
import math
from pathlib import Path
from fluids.numerics import interp
from .cli import digest
from .delivery import context
from .workflow import local_path,verify
from .terminal_throw import evaluate,positive


def calculate(rows,flow):
    flow=positive(flow)
    if len(rows)<2:raise ValueError('At least two performance rows required')
    flows=[positive(r['flow_L_s']) for r in rows]
    if any(b<=a for a,b in zip(flows,flows[1:])):raise ValueError('Strictly increasing catalogue flows required')
    for row in rows:
        positive(row['T025_m'])
        for key in ('static_pressure_Pa','total_pressure_Pa'):
            value=row[key]
            if type(value) not in (int,float) or not math.isfinite(value) or value<0:raise ValueError('Finite nonnegative catalogue pressure required')
        if row['total_pressure_Pa']<row['static_pressure_Pa']:raise ValueError('Catalogue total pressure is less than static pressure')
        nc=row['NC']
        if nc is not None and (type(nc) not in (int,float) or not math.isfinite(nc) or nc<0):raise ValueError('Numeric NC or explicitly qualified null required')
        if not isinstance(row['NC_qualifier'],str) or not row['NC_qualifier'].strip():raise ValueError('NC qualifier required;dash is not zero')
    if not flows[0]<=flow<=flows[-1]:
        return dict(flow_L_s=flow,status='outside_catalogue',static_pressure_Pa=None,total_pressure_Pa=None,NC=None,nc_catalogue_rows=[])
    exact=next((i for i,q in enumerate(flows) if q==flow),None)
    indices=[exact] if exact is not None else next([i,i+1] for i in range(len(flows)-1) if flows[i]<flow<flows[i+1])
    return dict(flow_L_s=flow,status='within_catalogue',
        static_pressure_Pa=interp(flow,flows,[r['static_pressure_Pa'] for r in rows]),
        total_pressure_Pa=interp(flow,flows,[r['total_pressure_Pa'] for r in rows]),
        NC=rows[exact]['NC'] if exact is not None else None,
        nc_status='exact_catalogue_row' if exact is not None else 'not_interpolated',
        nc_catalogue_rows=[dict(index=i,flow_L_s=flows[i],NC=rows[i]['NC'],qualifier=rows[i]['NC_qualifier']) for i in indices])


def run(plan,directory,lookup_task,settings,output):
    plan,directory,settings,output=[Path(p).resolve() for p in (plan,directory,settings,output)]
    source,workflow,integrity=context(plan,directory)
    if not integrity['integrity_pass']:raise ValueError('Current workflow integrity required')
    tasks={t['id']:t for t in source['tasks']}
    if lookup_task not in tasks or tasks[lookup_task]['kind']!='terminal_throw' or workflow['tasks'][lookup_task]['status']!='pass':
        raise ValueError('Exact passing terminal lookup task required')
    settings_hash=digest(settings)
    spec=json.loads(settings.read_text(encoding='utf-8-sig'))
    if set(spec)!={'source','source_sha256','catalogue','catalogue_sha256','conditions'} or not isinstance(spec['conditions'],str) or not spec['conditions'].strip():
        raise ValueError('Exact source/catalogue pins and explicit operating conditions required')
    document=local_path(settings.parent,spec['source']);catalogue=local_path(settings.parent,spec['catalogue'])
    if digest(document)!=spec['source_sha256'] or digest(catalogue)!=spec['catalogue_sha256']:raise ValueError('Performance source hash mismatch')
    project=local_path(plan.parent,tasks[lookup_task]['project'])
    original_project=json.loads(project.read_text(encoding='utf-8-sig'))
    original_catalogue=(project.parent/original_project['catalogue']).resolve()
    old=json.loads(original_catalogue.read_text(encoding='utf-8-sig'));new=json.loads(catalogue.read_text(encoding='utf-8-sig'))
    if old.get('source_sha256')!=spec['source_sha256'] or new.get('source_sha256')!=spec['source_sha256']:
        raise ValueError('Original lookup and pressure table must share the same source document')
    if len(old['rows'])!=len(new['rows']):raise ValueError('Exact original catalogue row coverage required')
    for a,b in zip(old['rows'],new['rows']):
        for key in ('flow_L_s','T025_m','static_pressure_Pa','total_pressure_Pa','NC','NC_qualifier'):
            if key in a and a[key]!=b.get(key):raise ValueError('Original lookup catalogue row differs from performance table')
    for key in ('model','locator','damper'):
        if key in old and new.get(key)!=old[key]:raise ValueError('Original product identity differs')
    lookup=directory/lookup_task/'terminal-results.json'
    pins={str(p):digest(p) for p in (plan,directory/'workflow.json',lookup,settings,document,catalogue,original_catalogue,Path(__file__))}
    pins.update({str(settings):settings_hash,str(document):spec['source_sha256'],str(catalogue):spec['catalogue_sha256'],str(original_catalogue):original_project['catalogue_sha256']})
    producer=tasks[lookup_task].get('depends_on')
    if producer:
        allocation=directory/producer/'allocation.json'
        pins[str(allocation)]=digest(allocation)
        allocated=json.loads(allocation.read_text(encoding='utf-8-sig'))
        turndown=allocated['turndown'];flow_rows=allocated['terminals']
    else:turndown=original_project['turndown'];flow_rows=original_project['terminals']
    flows={t['id']:t['maximum_flow_L_s'] for t in flow_rows}
    if len(flows)!=len(flow_rows):raise ValueError('Unique source flow inventory required')
    if output.exists() or any(output==Path(p) or output in Path(p).parents for p in pins) or output.is_relative_to(directory):
        raise ValueError('New output outside workflow and separate from all sources required')
    data=json.loads(lookup.read_text(encoding='utf-8-sig'));terminals=[]
    if len(data['terminals'])!=len(flows) or {t['id'] for t in data['terminals']}!=set(flows):
        raise ValueError('Exact source terminal flow inventory required')
    for terminal in data['terminals']:
        directions=list(terminal['directions'].values())
        if not directions:raise ValueError('Nonempty original directions required')
        maximum=flows[terminal['id']];minimum=maximum*turndown
        for direction in directions:
            expected=evaluate(old['rows'],maximum_flow_L_s=maximum,turndown=turndown,characteristic_length_m=direction['characteristic_length_m'])
            if direction!=expected:raise ValueError('Original directional lookup differs from replay or inherited flow')
        terminals.append(dict(id=terminal['id'],cases={name:calculate(new['rows'],q) for name,q in (('maximum',maximum),('minimum',minimum))}))
    if not terminals or len({r['id'] for r in terminals})!=len(terminals):raise ValueError('Unique nonempty terminal inventory required')
    result=dict(inputs=pins,lookup_task=lookup_task,conditions=spec['conditions'],terminals=terminals,
        pressure_method='Piecewise linear interpolation of original published pressure columns;design approximation,not a fitted physical loss model',
        acoustic_scope='NC retained only at exact catalogue flows;otherwise adjacent published rows are references,not bounds or an interpolated acoustic result. Room absorption and multiple-source room acoustics remain unverified.',
        scope='Catalogue terminal operating points only. Static and total pressures remain separate;do not add both or sum parallel terminals. VAV,flex,rigid ducts,fittings,installation,boundaries and full fan pressure remain unresolved.',
        fan_pressure_complete=False,ADPI_verified=False,design_accepted=False)
    if any(digest(Path(p))!=sha for p,sha in pins.items()) or not verify(directory)['integrity_pass']:
        raise ValueError('Terminal performance evidence changed during calculation')
    output.mkdir(parents=True)
    (output/'performance.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    rows=[]
    for t in terminals:
        for name,c in t['cases'].items():
            values=[t['id'],name,format(c['flow_L_s'],'.3f'),c['static_pressure_Pa'],c['total_pressure_Pa'],c.get('nc_status',c['status']),json.dumps(c['nc_catalogue_rows'])]
            rows.append('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in values)+'</tr>')
    text='<!doctype html><meta charset="utf-8"><title>Diffuser Operating Points</title><style>body{font:15px/1.5 Arial;margin:30px;color:#20343c}table{border-collapse:collapse}td,th{border:1px solid #bbcbd0;padding:7px}</style><h1>Diffuser Operating Points</h1>'
    text+=''.join('<p>'+html.escape(result[k])+'</p>' for k in ('conditions','pressure_method','acoustic_scope','scope'))
    text+='<table><tr>'+''.join('<th>'+h+'</th>' for h in ('Terminal','Condition','L/s','Static Pa','Total Pa','NC status','Published NC references'))+'</tr>'+''.join(rows)+'</table>'
    (output/'index.html').write_text(text,encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('plan','workflow','lookup_task','settings'):p.add_argument(name)
    p.add_argument('--out',required=True);a=p.parse_args()
    r=run(a.plan,a.workflow,a.lookup_task,a.settings,a.out)
    print(len(r['terminals']),'source-bound terminal pressure pairs;full fan/acoustic design pending')

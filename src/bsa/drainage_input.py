"""Prepare source-linked SWMM gravity-network input; does not execute the solver."""
import argparse
from datetime import datetime
import json
import math
from pathlib import Path
import re

from .cli import digest
from .engine import ProjectError


def compile_input(data):
    def exact(row, fields):
        if not isinstance(row, dict) or set(row) != set(fields.split()):
            raise ProjectError('unsupported or missing drainage input fields')
    exact(data, 'name sources simulation junctions outfall conduits')
    sources = data['sources']
    if not isinstance(sources, dict) or not sources or any(not isinstance(v, str) or not v.strip() for v in sources.values()):
        raise ProjectError('nonempty source descriptions required')
    def sourced(row):
        if not isinstance(row['source'], str) or row['source'] not in sources:
            raise ProjectError('known source required')
    def number(value, label, minimum=None, positive=False):
        if type(value) not in (int, float) or not math.isfinite(value) or (minimum is not None and value < minimum) or (positive and value <= 0):
            raise ProjectError('invalid ' + label)
        return value
    ids = set()
    def identity(row):
        value = row['id']
        if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,30}', value) or value.lower() in ids:
            raise ProjectError('unique simple drainage identity required')
        ids.add(value.lower())
    if not isinstance(data['name'], str) or not data['name'].strip() or any(c in data['name'] for c in '\r\n[];'):
        raise ProjectError('single-line drainage project name required')
    sim = data['simulation']
    exact(sim, 'start end routing_step_s report_step_s source'); sourced(sim)
    try:
        start, end = [datetime.strptime(sim[k], '%Y-%m-%dT%H:%M:%S') for k in ('start', 'end')]
    except (ValueError, TypeError) as exc:
        raise ProjectError('explicit local start/end timestamps required') from exc
    if end <= start:raise ProjectError('positive simulation interval required')
    for key in ('routing_step_s', 'report_step_s'):
        if type(sim[key]) is not int or not 1 <= sim[key] <= 86400:
            raise ProjectError('integer simulation step from 1 to 86400 seconds required')
    if sim['routing_step_s'] > sim['report_step_s']:raise ProjectError('routing step must not exceed report step')
    if (end-start).total_seconds() < sim['report_step_s']:raise ProjectError('at least one report interval required')
    nodes = data['junctions']
    if not isinstance(nodes, list) or not nodes:raise ProjectError('junctions required')
    by_id = {}
    for node in nodes:
        exact(node, 'id invert_m maximum_depth_m dry_weather_flow_lps source'); sourced(node); identity(node)
        number(node['invert_m'], 'invert');number(node['maximum_depth_m'], 'maximum depth', positive=True)
        number(node['dry_weather_flow_lps'], 'dry weather flow', 0)
        by_id[node['id']] = node
    outlet = data['outfall']
    exact(outlet, 'id invert_m boundary source'); sourced(outlet); identity(outlet)
    number(outlet['invert_m'], 'outfall invert')
    if outlet['boundary'] != 'FREE':raise ProjectError('only explicitly selected FREE outfall supported')
    by_id[outlet['id']] = outlet
    pipes = data['conduits']
    if not isinstance(pipes, list) or not pipes:raise ProjectError('conduits required')
    downstream = {}; slopes = []
    for pipe in pipes:
        exact(pipe, 'id from to length_m diameter_m manning_n inlet_offset_m outlet_offset_m source')
        sourced(pipe);identity(pipe)
        a,b=pipe['from'],pipe['to']
        if not isinstance(a,str) or not isinstance(b,str) or a not in by_id or b not in by_id or a==b or a==outlet['id'] or a in downstream:
            raise ProjectError('supported directed tree requires valid unique downstream connection')
        for key in ('length_m','diameter_m','manning_n'):number(pipe[key],key,positive=True)
        for key in ('inlet_offset_m','outlet_offset_m'):number(pipe[key],key,0)
        fall = by_id[a]['invert_m']+pipe['inlet_offset_m']-by_id[b]['invert_m']-pipe['outlet_offset_m']
        if fall <= 0:raise ProjectError('strictly falling gravity conduit required by this compiler scope')
        downstream[a]=b
        slopes.append(dict(id=pipe['id'],invert_fall_m=fall,slope=fall/pipe['length_m']))
    if sum(p['to']==outlet['id'] for p in pipes)!=1:raise ProjectError('single conduit at outfall required')
    for node in nodes:
        current=node['id'];seen=set()
        while current!=outlet['id']:
            if current in seen or current not in downstream:raise ProjectError('every junction must reach the outfall without a cycle')
            seen.add(current);current=downstream[current]
    def clock(seconds):return f'{seconds//3600:02}:{seconds//60%60:02}:{seconds%60:02}'
    lines=['[TITLE]',data['name'],'','[OPTIONS]','FLOW_UNITS LPS','FLOW_ROUTING DYNWAVE','LINK_OFFSETS DEPTH','ALLOW_PONDING NO',
           'START_DATE '+start.strftime('%m/%d/%Y'),'START_TIME '+start.strftime('%H:%M:%S'),
           'REPORT_START_DATE '+start.strftime('%m/%d/%Y'),'REPORT_START_TIME '+start.strftime('%H:%M:%S'),
           'END_DATE '+end.strftime('%m/%d/%Y'),'END_TIME '+end.strftime('%H:%M:%S'),
           'ROUTING_STEP '+str(sim['routing_step_s']),'REPORT_STEP '+clock(sim['report_step_s']), '', '[JUNCTIONS]']
    lines += [f"{n['id']} {n['invert_m']} {n['maximum_depth_m']} 0 0 0" for n in nodes]
    lines += ['', '[OUTFALLS]', f"{outlet['id']} {outlet['invert_m']} FREE NO",'', '[CONDUITS]']
    lines += [' '.join(str(p[k]) for k in ('id','from','to','length_m','manning_n','inlet_offset_m','outlet_offset_m'))+' 0 0' for p in pipes]
    lines += ['', '[XSECTIONS]']+[f"{p['id']} CIRCULAR {p['diameter_m']} 0 0 0 1" for p in pipes]
    lines += ['', '[DWF]']+[f"{n['id']} FLOW {n['dry_weather_flow_lps']}" for n in nodes]
    lines += ['', '[REPORT]', 'INPUT YES', 'CONTINUITY YES', 'FLOWSTATS YES', 'NODES ALL', 'LINKS ALL']
    return '\n'.join(lines)+'\n', slopes


def run(project, out):
    project,out=Path(project).resolve(),Path(out).resolve()
    if out.exists() or out==project or out in project.parents:raise ProjectError('new output directory outside inputs required')
    before=digest(project);data=json.loads(project.read_text(encoding='utf-8-sig'))
    text,slopes=compile_input(data)
    if digest(project)!=before:raise ProjectError('drainage input changed')
    out.mkdir(parents=True);inp=out/'network.inp';inp.write_text(text,encoding='utf-8')
    report=dict(inputs={str(project):before},artifacts={'network.inp':digest(inp)},
        conduit_geometry=slopes,source_references=data['sources'],preparation_pass=True,
        native_parse_verified=False,simulation_executed=False,design_accepted=False,
        assumptions=['initially dry nodes and conduits','zero extra surcharge depth and no surface ponding',
                     'one barrel per circular conduit','no flap gate, local losses, rainfall, infiltration or flow patterns',
                     'other engine numerical options remain upstream defaults; review before simulation'],
        scope='Prepared SI circular gravity-tree input with constant dry-weather inflows and FREE outfall; no hydraulic result or HK compliance')
    (out/'preparation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project',type=Path);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();print(json.dumps(run(a.project,a.out),indent=2))

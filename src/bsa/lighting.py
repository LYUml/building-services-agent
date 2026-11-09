"""IES-backed Radiance illuminance for an explicitly sourced rectangular room."""
import argparse
import csv
import json
import math
import os
from pathlib import Path
import subprocess
from .cli import digest
from .engine import ProjectError


def ies_metadata(path):
    text=path.read_text(encoding='utf-8-sig')
    lines=text.splitlines()
    if not lines or lines[0].strip()!='IESNA:LM-63-2002':raise ProjectError('this adapter currently accepts LM-63-2002 IES only')
    tilt=next((i for i,line in enumerate(lines) if line.strip().upper().startswith('TILT=')),None)
    if tilt is None or lines[tilt].strip().upper()!='TILT=NONE':raise ProjectError('IES TILT=NONE required; external/included tilt unsupported')
    try:values=[float(s) for s in ' '.join(lines[tilt+1:]).replace(',',' ').split()]
    except ValueError:raise ProjectError('unsupported nonnumeric IES payload, including embedded geometry')
    if len(values)<13 or not all(math.isfinite(v) for v in values):raise ProjectError('invalid IES numeric data')
    lamps,lumens,mult,nv,nh,kind,units,w,l,h,ballast,future,watts=values[:13]
    if any(v!=int(v) or v<1 for v in (lamps,nv,nh)) or nv<2 or kind!=1 or units not in (1,2):
        raise ProjectError('positive counts and Type C IES required')
    nv,nh=int(nv),int(nh)
    if len(values)!=13+nv+nh+nv*nh:raise ProjectError('IES angle/candela count mismatch')
    vertical=values[13:13+nv];horizontal=values[13+nv:13+nv+nh]
    if any(b<=a for a,b in zip(vertical,vertical[1:])) or any(b<=a for a,b in zip(horizontal,horizontal[1:])):
        raise ProjectError('strictly increasing IES angles required')
    if vertical[0]<0 or vertical[-1]>180 or horizontal[0]!=0 or horizontal[-1]>360:
        raise ProjectError('unsupported IES angle range')
    if mult<=0 or ballast<=0 or watts<0 or (lumens<=0 and lumens!=-1) or any(v<0 for v in values[13+nv+nh:]):raise ProjectError('invalid IES factors/intensities')
    return dict(photometric_type='C',format='LM-63-2002',input_watts=watts,candela_multiplier=mult,
                vertical_count=nv,horizontal_count=nh,sha256=digest(path))


def validate(p,root):
    if not isinstance(p,dict) or not isinstance(p.get('name'),str) or not p['name'].strip():raise ProjectError('named lighting project required')
    if set(p)!={'name','sources','room','luminaires','sensors','targets','simulation'}:
        raise ProjectError('unsupported/missing lighting fields; arbitrary scene geometry/daylight are not silently ignored')
    sources=p.get('sources')
    if not isinstance(sources,dict) or not sources or any(not isinstance(v,str) or not v.strip() for v in sources.values()):raise ProjectError('source descriptions required')
    def source(row):
        if not isinstance(row,dict) or not isinstance(row.get('source'),str) or row['source'] not in sources:raise ProjectError('known source required')
    def number(v,label,lo=None,hi=None):
        if type(v) not in (int,float) or not math.isfinite(v) or (lo is not None and v<lo) or (hi is not None and v>hi):raise ProjectError('invalid '+label)
    room=p.get('room');source(room)
    if set(room)!={'size_m','wall_reflectance','floor_reflectance','ceiling_reflectance','source'}:raise ProjectError('room supports only explicit rectangular dimensions and diffuse reflectance')
    size=room.get('size_m')
    if not isinstance(size,list) or len(size)!=3:raise ProjectError('room requires three dimensions')
    for v in size:number(v,'room size',0.01)
    for key in ('wall_reflectance','floor_reflectance','ceiling_reflectance'):number(room.get(key),key,0,0.95)
    sensors=p.get('sensors');fixtures=p.get('luminaires')
    if not isinstance(sensors,list) or not sensors or not isinstance(fixtures,list) or not fixtures:raise ProjectError('explicit sensors and luminaires required')
    ids=set();inputs=[]
    for row in sensors+fixtures:
        source(row)
        if not isinstance(row.get('id'),str) or not row['id'] or row['id'] in ids:raise ProjectError('unique sensor/luminaire IDs required')
        ids.add(row['id'])
        position=row.get('position_m')
        if not isinstance(position,list) or len(position)!=3:raise ProjectError('three position coordinates required')
        for v,limit in zip(position,size):number(v,'position',0.00001,limit-0.00001)
    if any(set(s)!={'id','position_m','source'} for s in sensors):raise ProjectError('sensors currently require horizontal upward normals; unsupported fields rejected')
    for fixture in fixtures:
        if set(fixture)!={'id','position_m','yaw_deg','maintenance_factor','ies','source'}:raise ProjectError('supported downlight fields only; tilt/detailed geometry unsupported')
        number(fixture.get('yaw_deg'),'yaw',-360,360)
        number(fixture.get('maintenance_factor'),'maintenance factor',0,1)
        relative=fixture.get('ies')
        if not isinstance(relative,str) or Path(relative).is_absolute():raise ProjectError('relative IES path required')
        path=(root/relative).resolve()
        if not path.is_relative_to(root) or not path.is_file():raise ProjectError('IES path missing or escapes project')
        inputs.append(path);ies_metadata(path)
    target=p.get('targets');source(target)
    if set(target)!={'average_lux','minimum_lux','minimum_over_average','source'}:raise ProjectError('unsupported lighting targets, including glare/daylight criteria')
    number(target.get('average_lux'),'average target',0)
    number(target.get('minimum_lux'),'minimum target',0)
    number(target.get('minimum_over_average'),'uniformity target',0,1)
    settings=p.get('simulation');source(settings)
    if set(settings)!={'ambient_bounces','ambient_divisions','verification_bounces','verification_divisions','relative_tolerance','source'}:raise ProjectError('unsupported simulation settings')
    for key,lo,hi in (('ambient_bounces',1,8),('ambient_divisions',64,65536)):
        v=settings.get(key)
        if type(v) is not int or not lo<=v<=hi:raise ProjectError('invalid '+key)
    for key,lo,hi in (('verification_bounces',settings['ambient_bounces']+1,9),('verification_divisions',settings['ambient_divisions']*2,131072)):
        value=settings.get(key)
        if type(value) is not int or not lo<=value<=hi:raise ProjectError('invalid '+key)
    number(settings.get('relative_tolerance'),'numerical stability tolerance',0.00001,0.5)
    if any(f['position_m'][2]<=s['position_m'][2] for f in fixtures for s in sensors):raise ProjectError('supported downlights must be above sensor plane')
    if len({s['position_m'][2] for s in sensors})!=1:raise ProjectError('one horizontal sensor plane required')
    return set(inputs)


def run(project,out,bin_dir):
    project,out,bin_dir=project.resolve(),out.resolve(),bin_dir.resolve()
    p=json.loads(project.read_text(encoding='utf-8-sig'));inputs=validate(p,project.parent);inputs.add(project)
    if any(out==f or out in f.parents for f in inputs):raise ProjectError('output must not contain inputs')
    suffix='.exe' if os.name=='nt' else ''
    executables={name:bin_dir/(name+suffix) for name in ('ies2rad','xform','oconv','rtrace')}
    if not all(path.is_file() for path in executables.values()):raise ProjectError('Radiance bin directory missing required executables')
    before={str(path):digest(path) for path in inputs}
    env=dict(os.environ,PATH=str(bin_dir)+os.pathsep+os.environ.get('PATH',''),RAYPATH='.'+os.pathsep+(bin_dir.parent/'lib').as_posix())
    out.mkdir(parents=True,exist_ok=False)
    calls=[]
    def call(name,args,input=None):
        command=[str(executables[name]),*args]
        try:
            proc=subprocess.run(command,cwd=out,env=env,input=input,capture_output=True,timeout=180)
        except OSError as exc:
            calls.append(dict(command=command,returncode=None,launch_error=str(exc),
                              winerror=getattr(exc,'winerror',None)))
            (out/'engine-calls.json').write_text(json.dumps(calls,indent=2),encoding='utf-8')
            raise ProjectError(f'{name} could not start; inspect engine-calls.json') from exc
        calls.append(dict(command=command,returncode=proc.returncode,stderr=proc.stderr.decode(errors='replace')))
        (out/'engine-calls.json').write_text(json.dumps(calls,indent=2),encoding='utf-8')
        if proc.returncode:raise ProjectError(f'{name} failed; inspect engine-calls.json')
        return proc.stdout
    scene=[];photometry={}
    for i,fixture in enumerate(p['luminaires']):
        prefix=f'fixture_{i:04}';path=project.parent/fixture['ies']
        photometry[fixture['id']]=ies_metadata(path)
        call('ies2rad',['-t','default','-m',str(fixture['maintenance_factor']),'-o',prefix,str(path)])
        x,y,z=fixture['position_m']
        scene.append(call('xform',['-rz',str(fixture['yaw_deg']),'-t',str(x),str(y),str(z),prefix+'.rad']).decode())
    def polygon(name,material,points):
        return f'{material} polygon {name}\n0\n0\n{len(points)*3} '+' '.join(str(c) for pt in points for c in pt)+'\n'
    room=p['room'];w,d,h=room['size_m']
    for kind in ('wall','floor','ceiling'):
        r=room[kind+'_reflectance'];scene.append(f'void plastic {kind}_mat\n0\n0\n5 {r} {r} {r} 0 0\n')
    for name,material,pts in (
        ('floor','floor_mat',[(0,0,0),(w,0,0),(w,d,0),(0,d,0)]),
        ('ceiling','ceiling_mat',[(0,d,h),(w,d,h),(w,0,h),(0,0,h)]),
        ('south','wall_mat',[(0,0,h),(w,0,h),(w,0,0),(0,0,0)]),
        ('north','wall_mat',[(0,d,0),(w,d,0),(w,d,h),(0,d,h)]),
        ('west','wall_mat',[(0,0,0),(0,d,0),(0,d,h),(0,0,h)]),
        ('east','wall_mat',[(w,0,h),(w,d,h),(w,d,0),(w,0,0)])):
        scene.append(polygon(name,material,pts))
    (out/'scene.rad').write_text('\n'.join(scene),encoding='utf-8')
    (out/'scene.oct').write_bytes(call('oconv',['scene.rad']))
    points=('\n'.join(' '.join(map(str,s['position_m']))+' 0 0 1' for s in p['sensors'])+'\n').encode()
    (out/'sensors.pts').write_bytes(points)
    settings=p['simulation'];results={}
    for name,bounces,divisions in (('direct',0,settings['ambient_divisions']),('initial',settings['ambient_bounces'],settings['ambient_divisions']),('total',settings['verification_bounces'],settings['verification_divisions'])):
        raw=call('rtrace',['-I+','-h-','-u-','-ab',str(bounces),'-ad',str(divisions),'-aa','0.1','-ar','64','-dj','0','-dt','0','-dc','1','scene.oct'],points)
        (out/(name+'-rgb.txt')).write_bytes(raw)
        values=[list(map(float,line.split())) for line in raw.decode().splitlines() if line.strip()]
        if len(values)!=len(p['sensors']) or any(len(v)!=3 or any(not math.isfinite(x) or x<0 for x in v) for v in values):raise ProjectError('invalid Radiance sensor results')
        results[name]=[179*(0.265*r+0.670*g+0.065*b) for r,g,b in values]
    lux=results['total'];average=sum(lux)/len(lux);minimum=min(lux);uniformity=minimum/average if average else 0
    stability=max(abs(a-b)/max(abs(a),abs(b),1.) for a,b in zip(results['initial'],results['total']))
    targets=p['targets'];checks=dict(average=average>=targets['average_lux'],minimum=minimum>=targets['minimum_lux'],uniformity=uniformity>=targets['minimum_over_average'],numerical_stability=stability<=settings['relative_tolerance'])
    records=[dict(id=s['id'],x_m=s['position_m'][0],y_m=s['position_m'][1],z_m=s['position_m'][2],direct_lux=results['direct'][i],total_lux=lux[i]) for i,s in enumerate(p['sensors'])]
    with (out/'illuminance.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    unchanged=all(digest(Path(path))==sha for path,sha in before.items())
    result=dict(inputs=before,inputs_unchanged=unchanged,photometry=photometry,sensors=records,
        average_lux=average,minimum_lux=minimum,maximum_lux=max(lux),minimum_over_average=uniformity,
        numerical_stability=dict(maximum_relative_change=stability,tolerance=settings['relative_tolerance'],denominator_floor_lux=1,
                                initial_bounces=settings['ambient_bounces'],verification_bounces=settings['verification_bounces'],
                                initial_divisions=settings['ambient_divisions'],verification_divisions=settings['verification_divisions']),
        checks=checks,calculated_checks_pass=unchanged and all(checks.values()),design_accepted=False,
        engine_version=call('rtrace',['-version']).decode(errors='replace'),executable_sha256={k:digest(v) for k,v in executables.items()},
        support_cal_sha256={f.name:digest(f) for f in (bin_dir.parent/'lib').glob('*.cal')},
        rgb_to_lux='179*(0.265R+0.670G+0.065B)',
        scope='Neutral-spectrum downlights in a closed rectangular diffuse room; maintained electric-light point illuminance at supplied sensor locations; arithmetic point mean, not an area-weighted regulatory average',
        pending=['manufacturer photometry and maintenance evidence','grid coverage and convergence review','furniture/obstruction and actual room geometry','glare/daylight/emergency lighting and code acceptance'])
    result['artifacts']={f.name:digest(f) for f in out.iterdir() if f.is_file()}
    (out/'lighting.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    if not unchanged:raise ProjectError('lighting input changed')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--radiance-bin',type=Path,required=True)
    a=p.parse_args();r=run(a.project,a.out,a.radiance_bin)
    print(json.dumps({k:r[k] for k in ('average_lux','minimum_lux','minimum_over_average','calculated_checks_pass','design_accepted')}))
    return 0 if r['calculated_checks_pass'] else 2

if __name__=='__main__':raise SystemExit(main())

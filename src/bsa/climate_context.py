"""Source-pinned candidate station context through isolated Ladybug, not site selection."""
import csv
import io
import json
import math
from pathlib import Path
import subprocess
from .annual_energy import read_weather,weather_bytes
from .cli import digest
from .engine import ProjectError
ROOT=Path(__file__).resolve().parents[2]


def prepare(weather,basis):
    weather,basis=Path(weather),Path(basis)
    b=json.loads(basis.read_text(encoding='utf-8-sig'))
    if not isinstance(b,dict) or set(b)!={'source','weather','calendar_year'} or not isinstance(b['source'],str) or not b['source'].strip() or type(b['calendar_year']) is not int or not 2000<=b['calendar_year']<=2100:raise ProjectError('explicit climate context source/weather/calendar required')
    meta=read_weather(weather,b['weather'],b['calendar_year'])
    return b,meta


def run(weather,basis,out,python):
    weather,basis,out,python=map(lambda p:Path(p).resolve(),(weather,basis,out,python))
    b,meta=prepare(weather,basis)
    worker=ROOT/'adapters/honeybee-scene/climate_worker.py';lock=worker.parent/'dependencies.json'
    pins={str(p):digest(p) for p in (weather,basis,python,worker,lock)}
    if any(out==Path(p) or out in Path(p).parents for p in pins):raise ProjectError('separate climate output required')
    raw=weather_bytes(weather);records=list(csv.reader(io.StringIO(raw.decode('utf-8-sig'))))[8:]
    out.mkdir(parents=True,exist_ok=False);epw=out/'source.epw';epw.write_bytes(raw);epw_sha=digest(epw)
    with (out/'worker.log').open('wb') as log:r=subprocess.run([str(python),str(worker),str(epw),str(b['calendar_year']),str(out/'ladybug')],stdout=log,stderr=subprocess.STDOUT,timeout=90)
    if r.returncode:raise ProjectError('Ladybug climate conversion failed; inspect worker.log')
    result=json.loads((out/'ladybug/climate.json').read_text(encoding='utf-8'))
    if result['source_record_count']!=meta['hours'] or len(result['monthly'])!=12:raise ProjectError('exact climate calendar coverage required')
    # Independent source-record sums; do not accept import-time missing-data zeroing.
    for row in result['monthly']:
        data=[r for r in records if int(r[1])==row['month']];temps=[float(r[6]) for r in data]
        expected=dict(dry_bulb_mean_c=math.fsum(temps)/len(temps),dry_bulb_min_c=min(temps),dry_bulb_max_c=max(temps),relative_humidity_mean_percent=math.fsum(float(r[8]) for r in data)/len(data),wind_speed_mean_m_s=math.fsum(float(r[21]) for r in data)/len(data),ghi_kwh_m2=math.fsum(float(r[13]) for r in data)/1000,dni_kwh_m2=math.fsum(float(r[14]) for r in data)/1000,dhi_kwh_m2=math.fsum(float(r[15]) for r in data)/1000)
        if row['hours']!=len(data) or any(not math.isclose(row[k],v,abs_tol=1e-9) for k,v in expected.items()):raise ProjectError('source climate monthly reconciliation failed')
    for k in ('ghi_kwh_m2','dni_kwh_m2','dhi_kwh_m2'):
        if not math.isclose(result['annual_irradiation_kwh_m2'][k],math.fsum(r[k] for r in result['monthly']),abs_tol=1e-9):raise ProjectError('annual irradiation reconciliation failed')
    with (out/'ladybug/sun-hourly.csv').open(encoding='utf-8') as file:sun=list(csv.DictReader(file))
    from datetime import datetime
    expected=[datetime(b['calendar_year'],int(r[1]),int(r[2]),int(r[3])-1,30).isoformat() for r in records]
    if [r['local_standard_interval_midpoint'] for r in sun]!=expected or any(not -90<=float(r['altitude_deg'])<=90 or not 0<=float(r['azimuth_deg'])<360 for r in sun):raise ProjectError('sun timestamp/angle coverage differs')
    if digest(epw)!=epw_sha or any(digest(Path(p))!=sha for p,sha in pins.items()):raise ProjectError('climate source changed during analysis')
    result.update(inputs=pins,weather_metadata=meta,scenario_source=b['source'],climate_checks_pass=True,pending=['confirm course city and project parcel','site coordinates/orientation and surrounding obstructions','actual shading/radiation/daylight and thermal performance','full project deliverables and acceptance'])
    plot(out,result)
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'climate-context.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


def plot(out,result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    months=np.arange(1,13);rows=result['monthly'];fig=plt.figure(figsize=(13,8));grid=fig.add_gridspec(2,2)
    axis=fig.add_subplot(grid[0,0]);axis.fill_between(months,[r['dry_bulb_min_c'] for r in rows],[r['dry_bulb_max_c'] for r in rows],alpha=.2,label='Source hourly minimum to maximum');axis.plot(months,[r['dry_bulb_mean_c'] for r in rows],marker='o',label='Source hourly mean');axis.set(xlabel='Source month',ylabel='Dry-bulb temperature (C)',xticks=months);axis.legend(fontsize=8);axis.grid(alpha=.25)
    axis=fig.add_subplot(grid[1,0])
    for i,(key,label) in enumerate((('ghi_kwh_m2','GHI'),('dni_kwh_m2','DNI'),('dhi_kwh_m2','DHI'))):axis.bar(months+(i-1)*.25,[r[key] for r in rows],width=.25,label=label)
    axis.set(xlabel='Source month',ylabel='Monthly irradiation (kWh/m2)',xticks=months);axis.legend();axis.grid(axis='y',alpha=.25)
    axis=fig.add_subplot(grid[:,1],projection='polar');axis.set_theta_zero_location('N');axis.set_theta_direction(-1)
    with (out/'ladybug/sun-seasonal.csv').open(encoding='utf-8') as file:solar=list(csv.DictReader(file))
    for month,label in ((3,'Mar 21'),(6,'Jun 21'),(9,'Sep 21'),(12,'Dec 21')):
        points=[r for r in solar if int(r['month'])==month and float(r['altitude_deg'])>=0]
        axis.plot([math.radians(float(r['azimuth_deg'])) for r in points],[90-float(r['altitude_deg']) for r in points],label=label)
    axis.set_ylim(0,90);axis.set_yticks([0,30,60,90],labels=['90 deg','60 deg','30 deg','0 deg']);axis.set_title('Station sun paths: altitude / azimuth',pad=25);axis.legend(loc='lower center',bbox_to_anchor=(.5,-.16),ncol=2)
    fig.suptitle(result['weather_metadata']['station_name']+' — candidate station context',fontsize=15)
    fig.text(.5,.015,'TMY3 source-month weather; solar calendar '+str(result['calendar_year'])+' in local standard time. No project parcel or shading result.',ha='center',fontsize=10)
    fig.tight_layout(rect=(0,.05,1,.95));fig.savefig(out/'climate-context.png',dpi=150);plt.close(fig)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('weather','basis','out','python'):parser.add_argument('--'+name,required=True,type=Path)
    a=parser.parse_args();r=run(a.weather,a.basis,a.out,a.python);print(json.dumps({k:r[k] for k in ('source_record_count','annual_irradiation_kwh_m2','climate_checks_pass','site_selected','shading_calculated','design_accepted')},indent=2))

# SPDX-License-Identifier: AGPL-3.0-only
"""Pinned Ladybug EPW and sun-path context, without site shading or thermal simulation."""
import csv
from datetime import datetime,timedelta
from importlib import metadata
import io
import json
import math
from pathlib import Path
import sys
from ladybug.epw import EPW
from ladybug.sunpath import Sunpath

FIELDS={'dry_bulb_temperature':(6,True),'relative_humidity':(8,True),'wind_speed':(21,True),'global_horizontal_radiation':(13,False),'direct_normal_radiation':(14,False),'diffuse_horizontal_radiation':(15,False)}


def run(epw_file,year,out):
    out=Path(out);text=Path(epw_file).read_text(encoding='utf-8-sig');rows=list(csv.reader(io.StringIO(text)))[8:]
    pins=json.loads((Path(__file__).parent/'dependencies.json').read_text(encoding='utf-8'))
    versions={r['name']:metadata.version(r['name']) for r in pins}
    if any(versions[r['name']]!=r['version'] for r in pins):raise ValueError('Ladybug environment differs from pins')
    epw=EPW.from_file_string(text);series={}
    for name,(column,point_field) in FIELDS.items():
        values=list(getattr(epw,name).values)
        # Undo only the documented point-in-time cyclic import shift, then prove
        # every value agrees with the original EPW source-record convention.
        if point_field:values=values[1:]+values[:1]
        if values!=[float(r[column]) for r in rows]:raise ValueError('Ladybug/source hourly alignment differs: '+name)
        series[name]=values
    monthly=[]
    for month in range(1,13):
        indices=[i for i,r in enumerate(rows) if int(r[1])==month]
        temp=[series['dry_bulb_temperature'][i] for i in indices]
        row=dict(month=month,hours=len(indices),dry_bulb_mean_c=math.fsum(temp)/len(temp),dry_bulb_min_c=min(temp),dry_bulb_max_c=max(temp),relative_humidity_mean_percent=math.fsum(series['relative_humidity'][i] for i in indices)/len(indices),wind_speed_mean_m_s=math.fsum(series['wind_speed'][i] for i in indices)/len(indices))
        for name,key in [('global_horizontal_radiation','ghi_kwh_m2'),('direct_normal_radiation','dni_kwh_m2'),('diffuse_horizontal_radiation','dhi_kwh_m2')]:row[key]=math.fsum(series[name][i] for i in indices)/1000
        monthly.append(row)
    path=Sunpath.from_location(epw.location);sun=[]
    for row in rows:
        time=datetime(year,int(row[1]),int(row[2]),int(row[3])-1,30)
        result=path.calculate_sun_from_date_time(time)
        sun.append(dict(local_standard_interval_midpoint=time.isoformat(),altitude_deg=result.altitude,azimuth_deg=result.azimuth,above_refracted_horizon=result.altitude>0))
    seasonal=[]
    for month,day in ((3,21),(6,21),(9,21),(12,21)):
        for minute in range(0,24*60,15):
            time=datetime(year,month,day)+timedelta(minutes=minute);result=path.calculate_sun_from_date_time(time)
            seasonal.append(dict(month=month,day=day,local_standard_time=time.isoformat(),altitude_deg=result.altitude,azimuth_deg=result.azimuth))
    out.mkdir(parents=True,exist_ok=False)
    for name,data in [('monthly.csv',monthly),('sun-hourly.csv',sun),('sun-seasonal.csv',seasonal)]:
        with (out/name).open('w',encoding='utf-8',newline='') as file:
            writer=csv.DictWriter(file,fieldnames=list(data[0]));writer.writeheader();writer.writerows(data)
    report=dict(runtime=versions,location=epw.location.to_dict(),calendar_year=year,source_record_count=len(rows),monthly=monthly,annual_irradiation_kwh_m2={k:math.fsum(r[k] for r in monthly) for k in ('ghi_kwh_m2','dni_kwh_m2','dhi_kwh_m2')},above_horizon_midpoint_count=sum(r['above_refracted_horizon'] for r in sun),hourly_alignment_pass=True,time_basis='EPW source-month hourly records retained; sun sampled at interval midpoint in local standard clock, no DST, true north. Analysis calendar year is not the observed weather year.',site_selected=False,shading_calculated=False,design_accepted=False)
    (out/'climate.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report

if __name__=='__main__':print(json.dumps(run(sys.argv[1],int(sys.argv[2]),sys.argv[3])))

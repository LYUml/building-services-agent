"""Verified hourly EPW annual ideal-load/lighting comparisons using actual EnergyPlus."""
import argparse
import calendar
import copy
import csv
import gzip
import hashlib
import io
from datetime import date,timedelta
import html
import json
import math
from pathlib import Path
import re
import sqlite3
import subprocess
from .cli import digest
from .engine import ProjectError
from .energy_completion import inspect as inspect_completion

MODEL='annual hourly EPW; two adjacent ideal-load zones'
RATES=('Zone Ideal Loads Supply Air Total Cooling Rate','Zone Ideal Loads Supply Air Total Heating Rate','Lights Electricity Rate')
UNMET=('Zone Heating Setpoint Not Met Time','Zone Cooling Setpoint Not Met Time')


def calendar_hours(year):
    current=date(year,1,1)
    while current.year==year:
        for hour in range(1,25):yield current.month,current.day,hour
        current+=timedelta(days=1)


def validate(p):
    if not isinstance(p,dict) or set(p)!={'model','source','building','weather','calendar_year','solver','targets'} or p['model']!=MODEL:raise ProjectError('explicit annual ideal-load EPW model required')
    if not isinstance(p['source'],str) or not p['source'].strip():raise ProjectError('annual model source required')
    if type(p['calendar_year']) is not int or not 1901<=p['calendar_year']<=2099:raise ProjectError('explicit Gregorian calendar year 1901..2099 required')
    building=p['building']
    building_fields={'name','source','zone_width_m','zone_depth_m','height_m','envelope_r_m2k_w','heating_setpoint_c','cooling_setpoint_c','baseline_lighting_w_m2','variant_lighting_w_m2'}
    if not isinstance(building,dict) or set(building)!=building_fields:raise ProjectError('exact building fields required; site comes from EPW and design days are omitted')
    weather=p['weather']
    if not isinstance(weather,dict) or set(weather)!={'source','sha256','station_id'} or not isinstance(weather['source'],str) or not weather['source'].strip() or not isinstance(weather['sha256'],str) or not re.fullmatch('[0-9a-f]{64}',weather['sha256']) or not isinstance(weather['station_id'],str) or not weather['station_id'].strip():raise ProjectError('weather source, exact SHA256 and station ID required')
    if not isinstance(p['solver'],dict) or set(p['solver'])!={'source','max_runtime_s','energy_tolerance_kwh','rate_tolerance_w'} or type(p['solver']['max_runtime_s']) is not int or not 1<=p['solver']['max_runtime_s']<=1800:raise ProjectError('sourced bounded annual solver budget required')
    if not isinstance(p['targets'],dict) or set(p['targets'])!={'source','maximum_zone_unmet_hours'}:raise ProjectError('explicit zone unmet-time target required')
    for group in (p['solver'],p['targets']):
        if not isinstance(group['source'],str) or not group['source'].strip():raise ProjectError('numerical/target provenance required')
    for value in (p['solver']['energy_tolerance_kwh'],p['solver']['rate_tolerance_w'],p['targets']['maximum_zone_unmet_hours']):
        if type(value) not in (int,float) or not math.isfinite(value) or value<0:raise ProjectError('finite nonnegative tolerances/target required')
    return p


def read_weather(path,config,year):
    path=Path(path)
    raw=weather_bytes(path)
    if hashlib.sha256(raw).hexdigest()!=config['sha256']:raise ProjectError('weather SHA256 differs from declared source')
    rows=list(csv.reader(io.StringIO(raw.decode('utf-8-sig'))))
    headers=['LOCATION','DESIGN CONDITIONS','TYPICAL/EXTREME PERIODS','GROUND TEMPERATURES','HOLIDAYS/DAYLIGHT SAVINGS','COMMENTS 1','COMMENTS 2','DATA PERIODS']
    if len(rows)<8 or any(not row or row[0]!=key for row,key in zip(rows[:8],headers)):raise ProjectError('eight standard EPW headers required')
    location=rows[0];period=rows[7]
    if len(location)!=10 or location[5]!=config['station_id']:raise ProjectError('weather station identity differs')
    if len(period)!=7 or period[1:3]!=['1','1'] or period[5].replace(' ','')!='1/1' or period[6].replace(' ','')!='12/31':raise ProjectError('one complete hourly Jan1..Dec31 EPW data period required')
    site={key:float(value) for key,value in zip(('latitude_deg','longitude_deg','timezone_h','elevation_m'),location[6:])}
    leap=calendar.isleap(year)
    if leap and rows[4][1].strip().lower()!='yes':raise ProjectError('leap-year simulation requires an EPW that allows leap data')
    expected=list(calendar_hours(year));data=rows[8:]
    if len(data)!=len(expected):raise ProjectError('weather record count does not cover the declared full calendar year')
    fields={6:('dry_bulb_c',-70,70),7:('dew_point_c',-70,70),8:('relative_humidity_percent',0,110),9:('station_pressure_pa',31000,120000),12:('horizontal_infrared_wh_m2',0,2000),13:('global_horizontal_wh_m2',0,2000),14:('direct_normal_wh_m2',0,2000),15:('diffuse_horizontal_wh_m2',0,2000),20:('wind_direction_deg',0,360),21:('wind_speed_m_s',0,40),22:('total_sky_cover_tenths',0,10),23:('opaque_sky_cover_tenths',0,10)}
    ranges={name:[math.inf,-math.inf] for name,_,_ in fields.values()};minutes=set();years=set();flags=set()
    for row,timestamp in zip(data,expected):
        if len(row)!=35:raise ProjectError('35 EPW data columns required')
        try:
            actual=tuple(int(row[i]) for i in (1,2,3));minute=int(row[4]);source_year=int(row[0])
            if actual!=timestamp or minute not in (0,60):raise ProjectError('weather calendar has missing/duplicate/out-of-order or subhourly records')
            minutes.add(minute);years.add(source_year);flags.add(row[5])
            for index,(name,low,high) in fields.items():
                value=float(row[index])
                if not math.isfinite(value) or not low<=value<=high:raise ProjectError('invalid/missing required EPW field: '+name)
                ranges[name][0]=min(ranges[name][0],value);ranges[name][1]=max(ranges[name][1],value)
        except (ValueError,IndexError) as exc:raise ProjectError('invalid EPW numeric/calendar data') from exc
    if len(minutes)!=1:raise ProjectError('one consistent EPW minute convention required')
    return dict(sha256=config['sha256'],asset_sha256=digest(path),source=config['source'],station_id=location[5],station_name=location[1],region=location[2],country=location[3],data_source=location[4],site=site,
                calendar_year=year,hours=len(expected),source_years=sorted(years),minute_field=next(iter(minutes)),required_field_ranges=ranges,distinct_uncertainty_flags=len(flags),
                scope='complete hourly calendar and required thermal/solar/wind fields; original uncertainty flags retained in source; not meteorological certification')


def weather_bytes(path):
    path=Path(path)
    if path.stat().st_size>20_000_000:raise ProjectError('hourly EPW asset exceeds 20 MB input budget')
    with (gzip.open(path,'rb') if path.suffix.lower()=='.gz' else path.open('rb')) as stream:raw=stream.read(20_000_001)
    if len(raw)>20_000_000:raise ProjectError('hourly EPW exceeds 20 MB decompressed input budget')
    return raw


def build(project,weather,weather_meta,lighting,out):
    import openstudio as os
    from .energy import build as base_build,validate as validate_building
    building=copy.deepcopy(project['building']);building.update(site=weather_meta['site'],design_days=[]);validate_building(building,require_design_days=False)
    metadata=base_build(building,lighting,out)
    model=os.model.Model.load(os.path(str(out/'model.osm'))).get();model.getYearDescription().setCalendarYear(project['calendar_year'])
    control=model.getSimulationControl();control.setRunSimulationforSizingPeriods(False);control.setRunSimulationforWeatherFileRunPeriods(True)
    control.setDoZoneSizingCalculation(False);control.setDoSystemSizingCalculation(False);control.setDoPlantSizingCalculation(False)
    for day in model.getDesignDays():day.remove()
    run=model.getRunPeriod();run.setName('Annual EPW');run.setBeginMonth(1);run.setBeginDayOfMonth(1);run.setEndMonth(12);run.setEndDayOfMonth(31)
    run.setUseWeatherFileDaylightSavings(False);run.setUseWeatherFileHolidays(False);run.setUseWeatherFileRainInd(False);run.setUseWeatherFileSnowInd(False)
    os.model.WeatherFile.setWeatherFile(model,os.EpwFile(os.path(str(weather))))
    for name in UNMET:
        variable=os.model.OutputVariable(name,model);variable.setReportingFrequency('Hourly');variable.setKeyValue('*')
    model.save(os.path(str(out/'model.osm')),True)
    ft=os.energyplus.ForwardTranslator();workspace=ft.translateModel(model);workspace.save(os.path(str(out/'model.idf')),True)
    if ft.errors():raise ProjectError('annual model translation errors')
    metadata.update(calendar_year=project['calendar_year'],design_day_count=len(model.getDesignDays()),weather_sha256=weather_meta['sha256'],translation_warnings=[str(v.logMessage()) for v in ft.warnings()])
    return metadata


def extract(sql,year,lighting_w_m2,area,solver,targets):
    con=sqlite3.connect(Path(sql).resolve().as_uri()+'?mode=ro',uri=True)
    try:
        completed=con.execute('SELECT Completed,CompletedSuccessfully FROM Simulations').fetchall()
        if len(completed)!=1:raise ProjectError('one SQL simulation record required')
        environments=con.execute('SELECT EnvironmentPeriodIndex,EnvironmentName,EnvironmentType FROM EnvironmentPeriods').fetchall()
        weather=[row for row in environments if row[2]==3]
        if len(weather)!=1 or len(environments)!=1:raise ProjectError('one weather run environment and no sizing/design-day environments required')
        records=con.execute('''SELECT d.Name,d.KeyValue,d.Units,d.ReportingFrequency,t.TimeIndex,t.Year,t.Month,t.Day,t.Hour,t.Minute,t.Interval,r.Value
          FROM ReportData r JOIN ReportDataDictionary d ON r.ReportDataDictionaryIndex=d.ReportDataDictionaryIndex
          JOIN Time t ON t.TimeIndex=r.TimeIndex WHERE t.EnvironmentPeriodIndex=? AND COALESCE(t.WarmupFlag,0)=0
          ORDER BY d.Name,d.KeyValue,t.TimeIndex''',(weather[0][0],)).fetchall()
    finally:con.close()
    series={};expected=list(calendar_hours(year))
    for name,key,units,freq,ti,actual_year,month,day,hour,minute,interval,value in records:
        if name not in RATES+UNMET:continue
        if units!=('W' if name in RATES else 'hr') or freq!='Hourly' or interval!=60 or actual_year!=year or minute!=0 or not math.isfinite(value) or value<0 or name in UNMET and value>1:raise ProjectError('invalid annual reporting units/frequency/interval/year/value')
        series.setdefault((name,key),[]).append(dict(time_index=ti,month=month,day=day,hour=hour,value=value))
    for name in RATES+UNMET:
        selected=[rows for (variable,key),rows in series.items() if variable==name]
        if len(selected)!=2 or any([(r['month'],r['day'],r['hour']) for r in rows]!=expected for rows in selected):raise ProjectError('each annual variable requires two complete unique hourly series')
    hours=[];monthly=[];totals=[]
    for index,(month,day,hour) in enumerate(expected):
        values={name:sum(rows[index]['value'] for (variable,key),rows in series.items() if variable==name) for name in RATES}
        hours.append(dict(month=month,day=day,hour=hour,**values))
    for name in RATES:
        values=[r[name] for r in hours];annual=math.fsum(values)/1000
        totals.append(dict(variable=name,quantity='lighting electricity' if name==RATES[2] else 'ideal supplied cooling thermal' if name==RATES[0] else 'ideal supplied heating thermal',annual_kwh=annual,coincident_peak_kw=max(values)/1000,hours=len(values)))
        for month in range(1,13):
            values=[r[name] for r in hours if r['month']==month]
            monthly.append(dict(month=month,variable=name,kwh=math.fsum(values)/1000,coincident_peak_kw=max(values)/1000,hours=len(values)))
    unmet=[dict(variable=name,zone=key,zone_hours=math.fsum(r['value'] for r in rows)) for (name,key),rows in series.items() if name in UNMET]
    expected_w=lighting_w_m2*area;actual=next(t for t in totals if t['variable']==RATES[2]);expected_kwh=expected_w*len(expected)/1000
    checks=dict(full_weather_calendar=True,complete_hourly_variable_coverage=True,
                lighting_analytic_energy=abs(actual['annual_kwh']-expected_kwh)<=solver['energy_tolerance_kwh'],
                lighting_constant_power=all(abs(r[RATES[2]]-expected_w)<=solver['rate_tolerance_w'] for r in hours),
                monthly_annual_reconciliation=all(abs(math.fsum(r['kwh'] for r in monthly if r['variable']==t['variable'])-t['annual_kwh'])<=solver['energy_tolerance_kwh'] for t in totals),
                zone_unmet_time_target=all(r['zone_hours']<=targets['maximum_zone_unmet_hours'] for r in unmet))
    return dict(checks=checks,calculated_checks_pass=all(checks.values()),environments=environments,annual=totals,monthly=monthly,zone_unmet=unmet,analytic_lighting_kwh=expected_kwh,
                sql_completion_flags=[list(row) for row in completed],sql_completion_flags_true=all(v in (1,'TRUE') for v in completed[0])),hours


def run(project,weather,out,exe):
    project,weather,out,exe=[Path(v).resolve() for v in (project,weather,out,exe)]
    if not exe.is_file() or any(out==p or out in p.parents for p in (project,weather)):raise ProjectError('existing engine and separate annual output required')
    before={str(v):digest(v) for v in (project,weather)}
    p=validate(json.loads(project.read_text(encoding='utf-8-sig')));weather_meta=read_weather(weather,p['weather'],p['calendar_year'])
    import openstudio
    if openstudio.openStudioVersion()!='3.11.0' or openstudio.energyPlusVersion()!='25.2.0':raise ProjectError('pinned OpenStudio 3.11.0 / EnergyPlus 25.2.0 required')
    version=subprocess.check_output([str(exe),'--version'],text=True).strip()
    if openstudio.energyPlusVersion() not in version:raise ProjectError('OpenStudio/EnergyPlus version mismatch')
    out.mkdir(parents=True,exist_ok=False);results={}
    engine_weather=out/'weather.epw';engine_weather.write_bytes(weather_bytes(weather))
    if digest(engine_weather)!=p['weather']['sha256']:raise ProjectError('prepared EPW differs from declared weather hash')
    (out/'weather-input.json').write_text(json.dumps(weather_meta,indent=2),encoding='utf-8')
    for kind,key in (('baseline','baseline_lighting_w_m2'),('variant','variant_lighting_w_m2')):
        folder=out/kind;folder.mkdir();meta=build(p,engine_weather,weather_meta,p['building'][key],folder)
        with (folder/'engine.log').open('wb') as stream:proc=subprocess.run([str(exe),'-x','-w',str(engine_weather),'-d',str(folder),str(folder/'model.idf')],cwd=folder,stdout=stream,stderr=subprocess.STDOUT,timeout=p['solver']['max_runtime_s'])
        completion=inspect_completion(folder,proc.returncode,version,digest(exe))
        (folder/'completion.json').write_text(json.dumps(completion,indent=2),encoding='utf-8')
        if not completion['completion_verified']:raise ProjectError('annual native completion evidence is unverified; inspect completion.json')
        diagnostics=(folder/'eplusout.err').read_text(errors='replace');end=(folder/'eplusout.end').read_text(errors='replace')
        summary,hourly=extract(folder/'eplusout.sql',p['calendar_year'],p['building'][key],meta['floor_area_m2'],p['solver'],p['targets'])
        with (folder/'hourly-building-rates.csv').open('w',newline='',encoding='utf-8') as stream:
            writer=csv.DictWriter(stream,fieldnames=['month','day','hour']+list(RATES));writer.writeheader();writer.writerows(hourly)
        (folder/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');results[kind]=dict(metadata=meta,summary=summary,diagnostics=diagnostics,completion=completion,sql_sha256=digest(folder/'eplusout.sql'),engine_success_evidence=dict(returncode=proc.returncode,end_report=end,end_report_sha256=digest(folder/'eplusout.end'),stdout_success_marker=True))
    comparison=[]
    for base,variant in zip(results['baseline']['summary']['annual'],results['variant']['summary']['annual']):comparison.append(dict(variable=base['variable'],quantity=base['quantity'],change_kwh=variant['annual_kwh']-base['annual_kwh'],change_coincident_peak_kw=variant['coincident_peak_kw']-base['coincident_peak_kw']))
    if any(digest(Path(v))!=sha for v,sha in before.items()):raise ProjectError('annual source input changed')
    result=dict(inputs=before,inputs_unchanged=True,source_data=p,weather=weather_meta,engine=version,engine_sha256=digest(exe),results=results,comparison=comparison,
                calculated_checks_pass=all(v['summary']['calculated_checks_pass'] for v in results.values()),design_accepted=False,
                scope='Full-calendar hourly EPW simulation of two adjacent ideal-load zones; heating/cooling thermal demand and lighting electricity reported separately',
                assumptions=['No windows, people, equipment, ventilation/infiltration; adiabatic floors; always-on lights and constant setpoints','Ideal air loads are supplied thermal demand, not HVAC electricity; no plant/COP or whole-building EUI inferred','Uniform R layer plus source-declared fixed 0.1 m mass layer: conductivity 0.5 W/mK, density 800 kg/m3, specific heat 1000 J/kgK','Weather calendar remapped to declared simulation year; DST/holidays/rain/snow indicators disabled; no design-day/sizing runs'],
                pending=['actual building geometry/construction/gain/schedule and meteorological applicability','detailed HVAC, ventilation/moisture, plant electricity and code acceptance','real-project calibration and full engineering acceptance'])
    result['completion_limitations']=[dict(case=kind,status=v['completion']['status'],native_sql_flags_preserved=True,source_commit=v['completion']['source_inference']['commit']) for kind,v in results.items() if v['completion']['known_unwritten_initial_flags']]
    (out/'report.html').write_text('<!doctype html><meta charset="utf-8"><h1>Annual ideal-load and lighting comparison</h1><p>'+html.escape(result['scope'])+'</p><pre>'+html.escape(json.dumps(dict(comparison=comparison,results=results),indent=2))+'</pre><p>'+html.escape('; '.join(result['pending']))+'</p>',encoding='utf-8')
    result['artifacts']={v.relative_to(out).as_posix():digest(v) for v in out.rglob('*') if v.is_file()}
    (out/'annual.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project',type=Path);p.add_argument('--weather',required=True,type=Path);p.add_argument('--energyplus',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();r=run(a.project,a.weather,a.out,a.energyplus);print(json.dumps({k:r[k] for k in ('calculated_checks_pass','comparison','design_accepted')},indent=2));return 0 if r['calculated_checks_pass'] else 2


if __name__=='__main__':raise SystemExit(main())

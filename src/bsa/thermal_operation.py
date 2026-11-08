"""Sourced weekly gains and fixed scheduled simple outdoor air for annual runs."""
from datetime import date
import math
import sqlite3
from pathlib import Path
from .engine import ProjectError

DAYS=('monday','tuesday','wednesday','thursday','friday','saturday','sunday')
MODEL='fixed scheduled design flow; no wind/stack'
VARIABLES={'Electric Equipment Electricity Rate':'W','Zone People Occupant Count':'','Zone Ventilation Fan Electricity Energy':'J','Zone Infiltration Mass Flow Rate':'kg/s','Zone Ventilation Mass Flow Rate':'kg/s'}


def validate(p):
    if not isinstance(p,dict) or set(p)!={'source','outdoor_air_model','lighting','equipment','people','infiltration','ventilation'} or p['outdoor_air_model']!=MODEL:raise ProjectError('explicit fixed-flow weekly operation model required')
    if not isinstance(p['source'],str) or not p['source'].strip():raise ProjectError('operation source required')
    fields={'lighting':{'fraction_radiant','fraction_visible'},'equipment':{'watts_per_m2','fraction_radiant','fraction_latent','fraction_lost'},'people':{'people_per_m2','activity_w_per_person','fraction_radiant','sensible_heat_fraction'},'infiltration':{'air_changes_per_hour'},'ventilation':{'flow_m3_s_per_m2','type','fan_pressure_rise_pa','fan_total_efficiency'}}
    for name,keys in fields.items():
        group=p[name]
        if not isinstance(group,dict) or set(group)!=keys|{'source','weekly_fraction'} or not isinstance(group['source'],str) or not group['source'].strip():raise ProjectError('exact sourced operation fields required: '+name)
        weekly=group['weekly_fraction']
        if not isinstance(weekly,dict) or set(weekly)!=set(DAYS):raise ProjectError('all seven named weekdays required')
        for values in weekly.values():
            if not isinstance(values,list) or len(values)!=24 or any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1 for v in values):raise ProjectError('24 finite hourly fractions required for each weekday')
        for key in keys-{'type'}:
            v=group[key]
            if type(v) not in (int,float) or not math.isfinite(v) or v<0 or ('fraction' in key or key=='fan_total_efficiency') and v>1:raise ProjectError('invalid operation physical value: '+key)
        if sum(group[k] for k in keys if k.startswith('fraction_'))>1:raise ProjectError('heat fractions exceed unity')
    if p['people']['activity_w_per_person']<=0 or p['ventilation']['fan_total_efficiency']<=0:raise ProjectError('positive activity and fan efficiency required')
    if p['ventilation']['type'] not in ('Natural','Intake','Exhaust','Balanced'):raise ProjectError('explicit simple ventilation type required')
    if p['ventilation']['type']=='Natural' and p['ventilation']['fan_pressure_rise_pa']!=0:raise ProjectError('natural ventilation cannot claim fan power')
    return p


def fractions(weekly,year):
    from .annual_energy import calendar_hours
    return [weekly[DAYS[date(year,m,d).weekday()]][h-1] for m,d,h in calendar_hours(year)]


def weekly_schedule(model,name,weekly):
    import openstudio as os
    schedule=os.model.ScheduleRuleset(model);schedule.setName('BSA '+name+' weekly')
    for i,day in enumerate(DAYS):
        rule=os.model.ScheduleRule(schedule);rule.setName(name+' '+day)
        rule.setApplyAllDays(False);getattr(rule,'setApply'+day.capitalize())(True)
        profile=rule.daySchedule();profile.setInterpolatetoTimestep("No")
        for hour,value in enumerate(weekly[day],1):profile.addValue(os.Time(0,hour,0,0),value)
    schedule.defaultDaySchedule().addValue(os.Time(0,24,0,0),0)
    return schedule


def author(model,p,spaces):
    import openstudio as os
    validate(p);schedules={name:weekly_schedule(model,name,p[name]['weekly_fraction']) for name in ('lighting','equipment','people','infiltration','ventilation')}
    activity=os.model.ScheduleConstant(model);activity.setName('BSA person activity');activity.setValue(p['people']['activity_w_per_person'])
    for space in spaces:
        name=space.thermalZone().get().nameString()
        for light in space.lights():
            light.setSchedule(schedules['lighting']);definition=light.lightsDefinition()
            definition.setReturnAirFraction(0)
            definition.setFractionRadiant(p['lighting']['fraction_radiant']);definition.setFractionVisible(p['lighting']['fraction_visible'])
        g=p['equipment'];definition=os.model.ElectricEquipmentDefinition(model);definition.setWattsperSpaceFloorArea(g['watts_per_m2'])
        for field,suffix in (('fraction_radiant','Radiant'),('fraction_latent','Latent'),('fraction_lost','Lost')):getattr(definition,'setFraction'+suffix)(g[field])
        equipment=os.model.ElectricEquipment(definition);equipment.setName(name+' equipment');equipment.setSpace(space);equipment.setSchedule(schedules['equipment'])
        g=p['people'];definition=os.model.PeopleDefinition(model);definition.setPeopleperSpaceFloorArea(g['people_per_m2']);definition.setFractionRadiant(g['fraction_radiant']);definition.setSensibleHeatFraction(g['sensible_heat_fraction'])
        people=os.model.People(definition);people.setName(name+' people');people.setSpace(space);people.setNumberofPeopleSchedule(schedules['people']);people.setActivityLevelSchedule(activity)
        infiltration=os.model.SpaceInfiltrationDesignFlowRate(model);infiltration.setName(name+' infiltration');infiltration.setSpace(space);infiltration.setSchedule(schedules['infiltration']);infiltration.setAirChangesperHour(p['infiltration']['air_changes_per_hour'])
        ventilation=os.model.ZoneVentilationDesignFlowRate(model);ventilation.setName(name+' ventilation');ventilation.setSchedule(schedules['ventilation']);ventilation.setFlowRateperZoneFloorArea(p['ventilation']['flow_m3_s_per_m2']);ventilation.setVentilationType(p['ventilation']['type']);ventilation.setFanPressureRise(p['ventilation']['fan_pressure_rise_pa']);ventilation.setFanTotalEfficiency(p['ventilation']['fan_total_efficiency']);ventilation.setDensityBasis('Outdoor');ventilation.addToThermalZone(space.thermalZone().get())
        # Deliberately simple scheduled flow: no empirical weather coefficients.
        for obj in (infiltration,ventilation):
            for suffix,value in (('ConstantTermCoefficient',1),('TemperatureTermCoefficient',0),('VelocityTermCoefficient',0),('VelocitySquaredTermCoefficient',0)):getattr(obj,'set'+suffix)(value)
        for suffix,value in (('MinimumIndoorTemperature',-100),('MaximumIndoorTemperature',100),('MinimumOutdoorTemperature',-100),('MaximumOutdoorTemperature',100),('DeltaTemperature',-100),('MaximumWindSpeed',40)):getattr(ventilation,'set'+suffix)(value)
        for obj,group in [(light,'lighting') for light in space.lights()]+[(equipment,'equipment'),(people,'people'),(infiltration,'infiltration'),(ventilation,'ventilation')]:obj.additionalProperties().setFeature('Source',p[group]['source'])
    for name in VARIABLES:
        output=os.model.OutputVariable(name,model);output.setReportingFrequency('Hourly');output.setKeyValue('*')


def audit(model,p):
    """Reconcile saved links, physical settings and all seven daily profiles."""
    import openstudio as os
    validate(p);records=[]
    def value(x):
        if hasattr(x,'empty'):
            if x.empty():raise ProjectError('saved operation property missing')
            return x.get()
        return x
    def compare(actual,expected):
        actual=value(actual)
        if isinstance(expected,str):good=actual==expected
        else:good=math.isclose(actual,expected,rel_tol=1e-9,abs_tol=1e-10)
        if not good:raise ProjectError('saved operation property differs from source')
    def schedule(actual,weekly):
        actual=value(actual).to_ScheduleRuleset()
        if actual.empty():raise ProjectError('saved weekly schedule missing')
        actual=actual.get();year=value(model.getYearDescription().calendarYear())
        for day in range(1,8):
            date_os=os.Date(os.MonthOfYear(1),day,year)
            profiles=actual.getDaySchedules(date_os,date_os)
            if len(profiles)!=1:raise ProjectError('one saved daily operation profile required')
            compare(profiles[0].interpolatetoTimestep(),'No')
            expected=weekly[DAYS[date(year,1,day).weekday()]]
            for h,v in enumerate(expected):compare(profiles[0].getValue(os.Time(0,h,30,0)),v)
    zones={z.handle():z.nameString() for z in model.getThermalZones()}
    for space in model.getSpaces():
        zone=space.thermalZone()
        if zone.empty() or zone.get().handle() not in zones:raise ProjectError('operation space zone missing')
        name=zone.get().nameString()
        for objects,group in ((space.lights(),'lighting'),(space.electricEquipment(),'equipment'),(space.people(),'people'),(space.spaceInfiltrationDesignFlowRates(),'infiltration')):
            if len(objects)!=1:raise ProjectError('one saved operation object per space and category required')
            obj=objects[0];g=p[group]
            compare(obj.additionalProperties().getFeatureAsString('Source'),g['source'])
            schedule(obj.numberofPeopleSchedule() if group=='people' else obj.schedule(),g['weekly_fraction'])
            if group=='lighting':
                definition=obj.lightsDefinition();compare(definition.fractionRadiant(),g['fraction_radiant']);compare(definition.fractionVisible(),g['fraction_visible']);compare(definition.returnAirFraction(),0)
            elif group=='equipment':
                definition=obj.electricEquipmentDefinition();compare(definition.wattsperSpaceFloorArea(),g['watts_per_m2'])
                for key,suffix in (('fraction_radiant','Radiant'),('fraction_latent','Latent'),('fraction_lost','Lost')):compare(getattr(definition,'fraction'+suffix)(),g[key])
            elif group=='people':
                definition=obj.peopleDefinition();compare(definition.peopleperSpaceFloorArea(),g['people_per_m2']);compare(definition.fractionRadiant(),g['fraction_radiant']);compare(definition.sensibleHeatFraction(),g['sensible_heat_fraction']);compare(value(obj.activityLevelSchedule()).to_ScheduleConstant().get().value(),g['activity_w_per_person'])
            else:
                compare(obj.airChangesperHour(),g['air_changes_per_hour'])
                for suffix,v in (('constantTermCoefficient',1),('temperatureTermCoefficient',0),('velocityTermCoefficient',0),('velocitySquaredTermCoefficient',0)):compare(getattr(obj,suffix)(),v)
            records.append(dict(zone=name,category=group,object=obj.nameString(),source=g['source'],weekly_profile_match=True))
    ventilation=model.getZoneVentilationDesignFlowRates()
    if len(ventilation)!=len(zones) or {value(v.thermalZone()).handle() for v in ventilation}!=set(zones):raise ProjectError('saved ventilation zone coverage differs')
    for v in ventilation:
        g=p['ventilation'];schedule(v.schedule(),g['weekly_fraction'])
        compare(v.additionalProperties().getFeatureAsString('Source'),g['source'])
        for getter,expected in (('flowRateperZoneFloorArea',g['flow_m3_s_per_m2']),('fanPressureRise',g['fan_pressure_rise_pa']),('fanTotalEfficiency',g['fan_total_efficiency']),('ventilationType',g['type']),('densityBasis','Outdoor'),('constantTermCoefficient',1),('temperatureTermCoefficient',0),('velocityTermCoefficient',0),('velocitySquaredTermCoefficient',0),('minimumIndoorTemperature',-100),('maximumIndoorTemperature',100),('minimumOutdoorTemperature',-100),('maximumOutdoorTemperature',100),('deltaTemperature',-100),('maximumWindSpeed',40)):compare(getattr(v,getter)(),expected)
        records.append(dict(zone=value(v.thermalZone()).nameString(),category='ventilation',object=v.nameString(),source=g['source'],weekly_profile_match=True))
    return dict(saved_operation_matches=True,records=records,scope='all seven weekdays and saved physical settings; fixed simple airflow, no duct network/heat recovery/plant')


def extract(sql,p,geometry,year,solver):
    """Independent full-calendar equipment/count/fan balance from native SQL."""
    from .annual_energy import calendar_hours
    validate(p);expected=list(calendar_hours(year));series={}
    with_sql=sqlite3.connect(Path(sql).resolve().as_uri()+'?mode=ro',uri=True)
    try:
        rows=with_sql.execute('''SELECT d.Name,d.KeyValue,d.Units,d.ReportingFrequency,t.Year,t.Month,t.Day,t.Hour,t.Minute,t.Interval,r.Value
          FROM ReportData r JOIN ReportDataDictionary d ON d.ReportDataDictionaryIndex=r.ReportDataDictionaryIndex
          JOIN Time t ON t.TimeIndex=r.TimeIndex JOIN EnvironmentPeriods e ON e.EnvironmentPeriodIndex=t.EnvironmentPeriodIndex
          WHERE COALESCE(t.WarmupFlag,0)=0 AND e.EnvironmentType=3 ORDER BY d.Name,d.KeyValue,t.TimeIndex''').fetchall()
    finally:with_sql.close()
    for name,key,units,freq,y,m,d,h,minute,interval,value in rows:
        if name not in VARIABLES:continue
        if units!=VARIABLES[name] or freq!='Hourly' or y!=year or minute!=0 or interval!=60 or not math.isfinite(value) or value<0:raise ProjectError('invalid operation hourly units/calendar/value')
        series.setdefault((name,key),[]).append(((m,d,h),value))
    summaries=[];checks={};hourly=[]
    for name in VARIABLES:
        keys={(s['id']+' equipment').upper() if name=='Electric Equipment Electricity Rate' else s['id'].upper() for s in geometry['spaces']}
        selected={key:values for (variable,key),values in series.items() if variable==name}
        if set(selected)!=keys or any([t for t,v in values]!=expected for values in selected.values()):raise ProjectError('operation series do not cover exact saved zones and calendar')
        actual=[sum(values[i][1] for values in selected.values()) for i in range(len(expected))]
        group='equipment' if name=='Electric Equipment Electricity Rate' else 'people' if name=='Zone People Occupant Count' else 'ventilation'
        if name=='Zone Infiltration Mass Flow Rate':group='infiltration'
        profile=fractions(p[group]['weekly_fraction'],year)
        area=geometry['floor_area_m2']
        if VARIABLES[name]=='kg/s':
            design=p[group]['air_changes_per_hour'] if group=='infiltration' else p[group]['flow_m3_s_per_m2']
            checks[group+'_scheduled_mass_flow']=all((value>0 if f>0 and design>0 else abs(value)<1e-10) for values in selected.values() for (_,value),f in zip(values,profile))
            summaries.append(dict(variable=name,units='kg/s',quantity=group+' outdoor-air mass kg',annual_integral=math.fsum(actual)*3600,analytic_integral=None,hours=len(actual),scope='scheduled on/off checked; mass depends on engine air density, no fixed-density equality asserted'))
            for (m,d,h),value in zip(expected,actual):hourly.append(dict(variable=name,month=m,day=d,hour=h,value=value,analytic=None,units='kg/s'))
            continue
        if group=='equipment':peak=area*p[group]['watts_per_m2'];scale=1/1000;quantity='equipment electricity kWh';tolerance=solver['rate_tolerance_w']
        elif group=='people':peak=area*p[group]['people_per_m2'];scale=1;quantity='person-hours';tolerance=1e-6
        else:
            v=p[group];multiplier=0 if v['type']=='Natural' else 2 if v['type']=='Balanced' else 1
            peak=area*v['flow_m3_s_per_m2']*v['fan_pressure_rise_pa']/v['fan_total_efficiency']*multiplier*3600
            scale=1/3600000;quantity='simple ventilation fan electricity kWh';tolerance=solver['rate_tolerance_w']*3600
        checks[group+'_hourly_balance']=all(abs(v-peak*f)<=tolerance for v,f in zip(actual,profile))
        checks[group+'_per_zone_hourly_balance']=all(abs(value-peak*(s['size_m'][0]*s['size_m'][1]/area)*f)<=tolerance for s in geometry['spaces'] for (_,value),f in zip(selected[(s['id']+' equipment').upper() if group=='equipment' else s['id'].upper()],profile))
        checks[group+'_annual_integral']=abs(math.fsum(actual)*scale-peak*math.fsum(profile)*scale)<=(1e-6 if group=='people' else solver['energy_tolerance_kwh'])
        summaries.append(dict(variable=name,units=VARIABLES[name],quantity=quantity,annual_integral=math.fsum(actual)*scale,analytic_integral=peak*math.fsum(profile)*scale,hours=len(actual)))
        for i,((m,d,h),value) in enumerate(zip(expected,actual)):hourly.append(dict(variable=name,month=m,day=d,hour=h,value=value,analytic=peak*profile[i],units=VARIABLES[name]))
    return dict(checks=checks,calculated_checks_pass=all(checks.values()),annual=summaries),hourly

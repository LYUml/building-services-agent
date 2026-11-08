"""Explicit fixed-size single-speed DX PTACs; electric heat and cycling fans."""
import math
from .engine import ProjectError

MODEL='single-speed DX PTAC; electric heat; cycling fixed-speed fan'
RATES=('Zone Packaged Terminal Air Conditioner Total Cooling Rate','Zone Packaged Terminal Air Conditioner Total Heating Rate','Lights Electricity Rate','Zone Packaged Terminal Air Conditioner Electricity Rate')
COMPONENTS={'Cooling Coil Electricity Rate':' PTAC DX','Heating Coil Electricity Rate':' PTAC heat','Fan Electricity Rate':' PTAC fan','Heating Coil Heating Rate':' PTAC heat','Cooling Coil Total Cooling Rate':' PTAC DX','Zone Packaged Terminal Air Conditioner Fan Part Load Ratio':' PTAC'}
CURVES={'capacity_temperature':6,'capacity_flow':3,'eir_temperature':6,'eir_flow':3,'part_load':3}
FIELDS={'cooling_capacity_w':'setRatedTotalCoolingCapacity','cooling_cop':'setRatedCOP','cooling_shr':'setRatedSensibleHeatRatio','supply_flow_m3_s':'setRatedAirFlowRate','heating_capacity_w':'setNominalCapacity','heating_efficiency':'setEfficiency','fan_pressure_pa':'setPressureRise','fan_efficiency':'setFanTotalEfficiency','motor_efficiency':'setMotorEfficiency','motor_in_air_fraction':'setMotorInAirstreamFraction'}


def extrema(c,x,y=None):
    def f(a,b=0):return c[0]+c[1]*a+c[2]*a*a+(c[3]*b+c[4]*b*b+c[5]*a*b if len(c)==6 else 0)
    points=[(a,b) for a in x for b in (y or [0])]
    if c[2]:
        for b in y or [0]:
            a=-(c[1]+(c[5]*b if y else 0))/(2*c[2])
            if x[0]<=a<=x[1]:points.append((a,b))
    if y:
        if c[4]:
            for a in x:
                b=-(c[3]+c[5]*a)/(2*c[4])
                if y[0]<=b<=y[1]:points.append((a,b))
        scale=max(abs(c[2]),abs(c[4]),abs(c[5])) or 1
        a11,a22,a12=2*c[2]/scale,2*c[4]/scale,c[5]/scale
        det=a11*a22-a12*a12
        if det:
            b1,b2=-c[1]/scale,-c[3]/scale
            a=(a22*b1-a12*b2)/det;b=(a11*b2-a12*b1)/det
            if x[0]<=a<=x[1] and y[0]<=b<=y[1]:points.append((a,b))
    values=[f(*point) for point in points]
    return min(values),max(values)


def validate(p,spaces):
    if not isinstance(p,dict) or set(p)!={'model','source','curves','zones'} or p['model']!=MODEL or not isinstance(p['source'],str) or not p['source'].strip():raise ProjectError('sourced explicit PTAC model required')
    curves=p['curves']
    if not isinstance(curves,dict) or set(curves)!=set(CURVES):raise ProjectError('five explicit DX performance curves required')
    for name,count in CURVES.items():
        curve=curves[name];keys={'source','coefficients','x_range','output_range'}|({'y_range'} if count==6 else set())
        if not isinstance(curve,dict) or set(curve)!=keys or not isinstance(curve['source'],str) or not curve['source'].strip():raise ProjectError('exact sourced DX curve fields required')
        for key in keys-{'source'}:
            values=curve[key];length=count if key=='coefficients' else 2
            if not isinstance(values,list) or len(values)!=length or any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>1e6 for v in values):raise ProjectError('finite bounded DX curve coefficients/ranges required')
            if key!='coefficients' and values[0]>=values[1]:raise ProjectError('ordered DX curve ranges required')
        low,high=extrema(curve['coefficients'],curve['x_range'],curve.get('y_range'))
        if not math.isfinite(low) or not math.isfinite(high) or low<=0 or low<curve['output_range'][0]-1e-10 or high>curve['output_range'][1]+1e-10 or curve['output_range'][0]<=0:raise ProjectError('DX curve must remain positive within declared output limits over its full input domain')
        if count==3 and not curve['x_range'][0]<=1<=curve['x_range'][1]:raise ProjectError('flow/part-load curves must include rated fraction one')
        if name=='part_load' and (curve['x_range']!=[0,1] or low<.7 or high>1):raise ProjectError('part-load fraction curve must cover 0..1 and remain within 0.7..1')
        if name=='part_load':
            c=curve['coefficients']
            if extrema([c[0],c[1]-1,c[2]],[0,1])[0]<-1e-10 or abs(sum(c)-1)>1e-6:raise ProjectError('part-load fraction must be at least load ratio and equal one at full load')
    zones=p['zones']
    if not isinstance(zones,list) or len(zones)!=len(spaces):raise ProjectError('one PTAC specification per thermal zone required')
    names=[]
    for zone in zones:
        if not isinstance(zone,dict) or set(zone)!={'id','source'}|set(FIELDS) or not isinstance(zone['source'],str) or not zone['source'].strip() or not isinstance(zone['id'],str):raise ProjectError('exact sourced PTAC zone inputs required')
        names.append(zone['id'])
        for key in FIELDS:
            v=zone[key]
            if type(v) not in (int,float) or not math.isfinite(v) or v<0 or key!='motor_in_air_fraction' and v==0 or key in ('cooling_shr','heating_efficiency','fan_efficiency','motor_efficiency','motor_in_air_fraction') and v>1:raise ProjectError('invalid explicit PTAC rating: '+key)
        if zone['cooling_shr']<.5:raise ProjectError('DX rated sensible heat ratio must be at least 0.5')
    if len(set(names))!=len(names) or set(names)!={s['id'] for s in spaces}:raise ProjectError('PTAC IDs must cover exact thermal zones')
    return p


def curve(model,name,spec):
    import openstudio as os
    obj=os.model.CurveBiquadratic(model) if len(spec['coefficients'])==6 else os.model.CurveQuadratic(model)
    obj.setName('BSA DX '+name);obj.additionalProperties().setFeature('Source',spec['source'])
    setters=('setCoefficient1Constant','setCoefficient2x','setCoefficient3xPOW2','setCoefficient4y','setCoefficient5yPOW2','setCoefficient6xTIMESY')
    for setter,value in zip(setters,spec['coefficients']):
        if not getattr(obj,setter)(value):raise ProjectError('SDK rejected DX curve coefficient')
    for axis in ('x','y'):
        if axis+'_range' in spec:
            lo,hi=spec[axis+'_range'];getattr(obj,'setMinimumValueof'+axis)(lo);getattr(obj,'setMaximumValueof'+axis)(hi)
    obj.setMinimumCurveOutput(spec['output_range'][0]);obj.setMaximumCurveOutput(spec['output_range'][1])
    obj.setInputUnitTypeforX('Temperature' if len(spec['coefficients'])==6 else 'Dimensionless')
    if len(spec['coefficients'])==6:obj.setInputUnitTypeforY('Temperature')
    obj.setOutputUnitType('Dimensionless')
    return obj


def author(model,p):
    import openstudio as os
    curves={name:curve(model,name,spec) for name,spec in p['curves'].items()}
    on=model.alwaysOnDiscreteSchedule();off=os.model.ScheduleConstant(model);off.setName('BSA PTAC cycling mode');off.setValue(0)
    for spec in p['zones']:
        name=spec['id'];zone=model.getThermalZoneByName(name).get();zone.setUseIdealAirLoads(False)
        fan=os.model.FanOnOff(model);fan.setName(name+' PTAC fan');fan.setMaximumFlowRate(spec['supply_flow_m3_s'])
        heat=os.model.CoilHeatingElectric(model,on);heat.setName(name+' PTAC heat')
        cool=os.model.CoilCoolingDXSingleSpeed(model,on,*[curves[k] for k in CURVES]);cool.setName(name+' PTAC DX')
        for key,setter in FIELDS.items():
            obj=cool if key.startswith('cooling_') or key=='supply_flow_m3_s' else heat if key.startswith('heating_') else fan
            if not getattr(obj,setter)(spec[key]):raise ProjectError('SDK rejected PTAC rating: '+key)
        cool.setCondenserType('AirCooled');cool.setCrankcaseHeaterCapacity(0);cool.setMinimumOutdoorDryBulbTemperatureforCompressorOperation(-100)
        # Fixed-speed on/off operation; speed modifiers are explicit unity curves.
        unity=curve(model,name+' fixed speed',dict(source=p['source'],coefficients=[1,0,0],x_range=[0,1],output_range=[.01,2]))
        fan.setFanPowerRatioFunctionofSpeedRatioCurve(unity);fan.setFanEfficiencyRatioFunctionofSpeedRatioCurve(unity)
        ptac=os.model.ZoneHVACPackagedTerminalAirConditioner(model,on,fan,heat,cool);ptac.setName(name+' PTAC');ptac.setFanPlacement('DrawThrough');ptac.setSupplyAirFanOperatingModeSchedule(off)
        for suffix in ('CoolingOperation','HeatingOperation'):getattr(ptac,'setSupplyAirFlowRateDuring'+suffix)(spec['supply_flow_m3_s'])
        ptac.setSupplyAirFlowRateWhenNoCoolingorHeatingisNeeded(0)
        for method in ('setOutdoorAirFlowRateDuringCoolingOperation','setOutdoorAirFlowRateDuringHeatingOperation','setOutdoorAirFlowRateWhenNoCoolingorHeatingisNeeded'):getattr(ptac,method)(0)
        if not ptac.addToThermalZone(zone):raise ProjectError('SDK rejected PTAC zone link')
        for obj in (ptac,fan,heat,cool):obj.additionalProperties().setFeature('Source',spec['source'])
    limits=os.model.ScheduleTypeLimits(model);limits.setName('BSA PTAC mode limits');limits.setLowerLimitValue(0);limits.setUpperLimitValue(1);limits.setNumericType('Discrete');limits.setUnitType('Dimensionless');off.setScheduleTypeLimits(limits)
    for name in COMPONENTS:
        v=os.model.OutputVariable(name,model);v.setReportingFrequency('Hourly');v.setKeyValue('*')


def audit(model,p):
    """Reopen-proof sizing, topology, mode, sources and explicit curve links."""
    def unwrap(x):
        if hasattr(x,'empty'):
            if x.empty():raise ProjectError('saved PTAC property missing')
            return x.get()
        return x
    def same(x,y):
        x=unwrap(x)
        if (x!=y if isinstance(y,str) else not math.isclose(x,y,rel_tol=1e-9,abs_tol=1e-10)):raise ProjectError('saved PTAC property/source differs from input')
    units=model.getZoneHVACPackagedTerminalAirConditioners();specs={s['id']:s for s in p['zones']}
    if len(units)!=len(specs) or len(model.getThermalZones())!=len(specs):raise ProjectError('saved PTAC count differs')
    records=[]
    for unit in units:
        zone=unwrap(unit.thermalZone());name=zone.nameString()
        equipment=[q for q in zone.equipment() if q.to_ZoneVentilationDesignFlowRate().empty()]
        if name not in specs or zone.useIdealAirLoads() or len(equipment)!=1 or equipment[0].handle()!=unit.handle():raise ProjectError('saved PTAC zone equipment topology differs')
        spec=specs[name];same(unit.nameString(),name+' PTAC')
        fan=unit.supplyAirFan().to_FanOnOff();heat=unit.heatingCoil().to_CoilHeatingElectric();cool=unit.coolingCoil().to_CoilCoolingDXSingleSpeed()
        if any(obj.empty() for obj in (fan,heat,cool)):raise ProjectError('saved PTAC component class differs')
        fan,heat,cool=[obj.get() for obj in (fan,heat,cool)]
        for obj in (unit,fan,heat,cool):
            same(obj.additionalProperties().getFeatureAsString('Source'),spec['source'])
            available=unwrap(obj.availabilitySchedule()).to_ScheduleConstant()
            if available.empty():raise ProjectError('saved PTAC availability schedule differs')
            same(available.get().value(),1)
        same(fan.nameString(),name+' PTAC fan');same(heat.nameString(),name+' PTAC heat');same(cool.nameString(),name+' PTAC DX')
        for key,setter in FIELDS.items():
            obj=cool if key.startswith('cooling_') or key=='supply_flow_m3_s' else heat if key.startswith('heating_') else fan
            getter=setter[3:];getter=getter[0].lower()+getter[1:];same(getattr(obj,getter)(),spec[key])
        same(fan.maximumFlowRate(),spec['supply_flow_m3_s']);same(unit.fanPlacement(),'DrawThrough')
        mode=unwrap(unit.supplyAirFanOperatingModeSchedule()).to_ScheduleConstant()
        if mode.empty():raise ProjectError('saved PTAC cycling schedule missing')
        same(mode.get().value(),0)
        limits=unwrap(mode.get().scheduleTypeLimits());same(limits.lowerLimitValue(),0);same(limits.upperLimitValue(),1);same(limits.numericType(),'Discrete');same(limits.unitType(),'Dimensionless')
        for getter in ('supplyAirFlowRateDuringCoolingOperation','supplyAirFlowRateDuringHeatingOperation'):same(getattr(unit,getter)(),spec['supply_flow_m3_s'])
        for getter in ('supplyAirFlowRateWhenNoCoolingorHeatingisNeeded','outdoorAirFlowRateDuringCoolingOperation','outdoorAirFlowRateDuringHeatingOperation','outdoorAirFlowRateWhenNoCoolingorHeatingisNeeded'):same(getattr(unit,getter)(),0)
        same(cool.condenserType(),'AirCooled');same(cool.crankcaseHeaterCapacity(),0);same(cool.minimumOutdoorDryBulbTemperatureforCompressorOperation(),-100)
        getters=('totalCoolingCapacityFunctionOfTemperatureCurve','totalCoolingCapacityFunctionOfFlowFractionCurve','energyInputRatioFunctionOfTemperatureCurve','energyInputRatioFunctionOfFlowFractionCurve','partLoadFractionCorrelationCurve')
        for curve_name,getter in zip(CURVES,getters):
            saved=getattr(cool,getter)();spec_curve=p['curves'][curve_name]
            actual=saved.to_CurveBiquadratic() if len(spec_curve['coefficients'])==6 else saved.to_CurveQuadratic()
            if actual.empty():raise ProjectError('saved DX curve type differs')
            actual=actual.get();same(actual.nameString(),'BSA DX '+curve_name);same(actual.additionalProperties().getFeatureAsString('Source'),spec_curve['source'])
            for suffix,v in zip(('1Constant','2x','3xPOW2','4y','5yPOW2','6xTIMESY'),spec_curve['coefficients']):same(getattr(actual,'coefficient'+suffix)(),v)
            for axis in ('x','y'):
                if axis+'_range' in spec_curve:
                    same(getattr(actual,'minimumValueof'+axis)(),spec_curve[axis+'_range'][0]);same(getattr(actual,'maximumValueof'+axis)(),spec_curve[axis+'_range'][1])
            same(actual.minimumCurveOutput(),spec_curve['output_range'][0]);same(actual.maximumCurveOutput(),spec_curve['output_range'][1])
            same(actual.inputUnitTypeforX(),'Temperature' if len(spec_curve['coefficients'])==6 else 'Dimensionless');same(actual.outputUnitType(),'Dimensionless')
            if len(spec_curve['coefficients'])==6:same(actual.inputUnitTypeforY(),'Temperature')
        for getter in ('fanPowerRatioFunctionofSpeedRatioCurve','fanEfficiencyRatioFunctionofSpeedRatioCurve'):
            actual=unwrap(getattr(fan,getter)()).to_CurveQuadratic()
            if actual.empty():raise ProjectError('saved fixed-speed fan curve differs')
            actual=actual.get()
            for getter,v in (('coefficient1Constant',1),('coefficient2x',0),('coefficient3xPOW2',0),('minimumValueofx',0),('maximumValueofx',1),('minimumCurveOutput',.01),('maximumCurveOutput',2),('inputUnitTypeforX','Dimensionless'),('outputUnitType','Dimensionless')):same(getattr(actual,getter)(),v)
            same(actual.additionalProperties().getFeatureAsString('Source'),p['source'])
        records.append(dict(zone=name,ptac=unit.nameString(),source=spec['source'],cooling_capacity_w=spec['cooling_capacity_w'],heating_capacity_w=spec['heating_capacity_w'],supply_flow_m3_s=spec['supply_flow_m3_s']))
    return dict(saved_hvac_matches=True,records=records,curve_extrema={k:extrema(c['coefficients'],c['x_range'],c.get('y_range')) for k,c in p['curves'].items()},pending=['real product, rated normalization and operating-domain applicability','native ancillary/rating defaults; no SEER/EER acceptance','detailed routed HVAC/controls/plant and engineering acceptance'])


def extract(sql,p,geometry,year,solver):
    import sqlite3
    from pathlib import Path
    from .annual_energy import calendar_hours
    con=sqlite3.connect(Path(sql).resolve().as_uri()+'?mode=ro',uri=True)
    try:
        rows=con.execute('''SELECT d.Name,d.KeyValue,d.Units,d.ReportingFrequency,t.Year,t.Month,t.Day,t.Hour,t.Minute,t.Interval,r.Value FROM ReportData r JOIN ReportDataDictionary d ON d.ReportDataDictionaryIndex=r.ReportDataDictionaryIndex JOIN Time t ON t.TimeIndex=r.TimeIndex JOIN EnvironmentPeriods e ON e.EnvironmentPeriodIndex=t.EnvironmentPeriodIndex WHERE COALESCE(t.WarmupFlag,0)=0 AND e.EnvironmentType=3 ORDER BY d.Name,d.KeyValue,t.TimeIndex''').fetchall()
    finally:con.close()
    variables={**COMPONENTS,RATES[3]:' PTAC'};series={};expected=list(calendar_hours(year))
    for name,key,units,freq,y,m,d,h,minute,interval,v in rows:
        if name not in variables:continue
        if units!=('' if name.endswith('Ratio') else 'W') or freq!='Hourly' or y!=year or minute!=0 or interval!=60 or not math.isfinite(v) or v<0:raise ProjectError('invalid native PTAC component series')
        series.setdefault((name,key),[]).append(((m,d,h),v))
    for name,suffix in variables.items():
        keys={(s['id']+suffix).upper() for s in p['zones']}
        selected={key:values for (var,key),values in series.items() if var==name}
        if set(selected)!=keys or any([t for t,v in values]!=expected for values in selected.values()):raise ProjectError('exact complete PTAC component keys/calendar required')
    checks=dict(component_coverage=True);records=[]
    checks['hourly_electricity_sum']=True;checks['annual_electricity_sum']=True;checks['electric_heater_efficiency']=True;checks['cycling_fan_power']=True
    for spec in p['zones']:
        zone=spec['id']
        def values(name):return [v for t,v in series[(name,(zone+variables[name]).upper())]]
        coil,heat,fan=[values(n) for n in list(COMPONENTS)[:3]];total=values(RATES[3])
        checks['hourly_electricity_sum'] &= all(abs(t-c-h-f)<=solver['rate_tolerance_w'] for t,c,h,f in zip(total,coil,heat,fan))
        checks['annual_electricity_sum'] &= abs(math.fsum(total)-math.fsum(coil)-math.fsum(heat)-math.fsum(fan))/1000<=solver['energy_tolerance_kwh']
        checks['electric_heater_efficiency'] &= all(abs(q-w*spec['heating_efficiency'])<=solver['rate_tolerance_w'] for q,w in zip(values('Heating Coil Heating Rate'),heat))
        nominal=spec['supply_flow_m3_s']*spec['fan_pressure_pa']/spec['fan_efficiency']
        checks['cycling_fan_power'] &= all(abs(w-nominal*f)<=solver['rate_tolerance_w'] for w,f in zip(fan,values('Zone Packaged Terminal Air Conditioner Fan Part Load Ratio')))
        records.append(dict(zone=zone,cooling_electricity_kwh=math.fsum(coil)/1000,heating_electricity_kwh=math.fsum(heat)/1000,fan_electricity_kwh=math.fsum(fan)/1000,ptac_electricity_kwh=math.fsum(total)/1000))
    return dict(checks=checks,calculated_checks_pass=all(checks.values()),zones=records,scope='component accounting; PTAC total already includes these coils/fan; simple ventilation fan is separate; gross coil cooling and net zone delivery differ')

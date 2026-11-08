"""Read supported saved IDF sizing controls into source-bound jurisdiction facts."""
import argparse
import copy
import json
import math
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from .regulations import evaluate,source_paths
from .sizing_humidity import METHOD


def extract(path,bases):
    import openstudio as os
    loaded=os.Workspace.load(os.path(str(path)))
    if loaded.empty():raise ProjectError('saved IDF could not be loaded')
    w=loaded.get()
    for obj in w.objects():
        kind=obj.iddObject().name()
        if kind.startswith(('EnergyManagementSystem:','ExternalInterface','PythonPlugin:')) or kind.startswith('ZoneControl:') and kind!='ZoneControl:Thermostat':
            raise ProjectError('unsupported native control override: '+kind)
        if kind.startswith('SizingPeriod:') and kind!='SizingPeriod:DesignDay':
            raise ProjectError('unsupported native sizing period: '+kind)
    def objects(kind):return w.getObjectsByType(os.IddObjectType(kind))
    def fields(obj):
        result={}
        for i in range(obj.numFields()):
            f=obj.iddObject().getField(i);v=obj.getString(i)
            if not f.empty():result[f.get().name()]='' if v.empty() else v.get()
        return result
    def indexed(kind,key='Name'):
        rows=[fields(o) for o in objects(kind)];names=[r[key] for r in rows]
        if len(names)!=len(set(n.casefold() for n in names)):raise ProjectError('duplicate native identities: '+kind)
        return {r[key]:r for r in rows}
    def number(value):
        try:v=float(value)
        except (TypeError,ValueError):raise ProjectError('explicit native numeric field required')
        if not math.isfinite(v):raise ProjectError('finite native field required')
        return v
    zones=indexed('Zone');sizing=indexed('Sizing:Zone','Zone or ZoneList Name')
    controls=indexed('ZoneControl:Thermostat','Zone or ZoneList Name')
    if not zones or set(zones)!=set(sizing) or set(zones)!=set(controls) or not isinstance(bases,dict) or set(bases)!=set(zones):
        raise ProjectError('exact zone/sizing/thermostat/regulatory basis coverage required')
    for kind in ['ZoneControl:Humidistat','ZoneControl:Thermostat:OperativeTemperature','ZoneControl:Thermostat:TemperatureAndHumidity']:
        if objects(kind):raise ProjectError('unsupported overriding zone control: '+kind)
    sim=objects('SimulationControl')
    if len(sim)!=1 or fields(sim[0]).get('Do Zone Sizing Calculation')!='Yes':raise ProjectError('zone sizing must be enabled')
    constants=indexed('Schedule:Constant');indexed('Schedule:Compact')
    compact={fields(o)['Name']:[o.getString(i).get() for i in range(2,o.numFields())] for o in objects('Schedule:Compact')}
    schedule_names=[fields(o).get('Name','').casefold() for o in w.objects() if o.iddObject().name().startswith('Schedule:')]
    if len(schedule_names)!=len(set(schedule_names)):raise ProjectError('duplicate native schedule identities')
    dual=indexed('ThermostatSetpoint:DualSetpoint')
    def constant(name):
        if name not in constants:raise ProjectError('constant native setpoint schedule required')
        return number(constants[name]['Hourly Value'])
    days=indexed('SizingPeriod:DesignDay')
    if not days:raise ProjectError('explicit native design days required')
    results={};origin='Saved IDF '+str(path)+' SHA256 '+digest(Path(path))
    def q(value,unit=None):return dict(value=value,source=origin,**({'unit':unit} if unit else {}))
    for zone in zones:
        basis=bases[zone]
        if not isinstance(basis,dict) or set(basis.get('load_design_conditions',{}))!={'application'}:
            raise ProjectError('basis supplies only sourced application; native design values cannot be overridden')
        s=sizing[zone];c=controls[zone]
        if s['Zone Load Sizing Method']!=METHOD:raise ProjectError('explicit sensible and latent sizing required')
        if c.get('Control 1 Object Type')!='ThermostatSetpoint:DualSetpoint' or any(c.get('Control '+str(i)+' Object Type') for i in (2,3,4)):
            raise ProjectError('single dual-setpoint thermostat required')
        if number(c.get('Temperature Difference Between Cutout And Setpoint','0'))!=0:raise ProjectError('thermostat cutout offset unsupported')
        schedule=c['Control Type Schedule Name']
        if schedule in constants:
            enabled=constant(schedule)==4
        else:
            enabled=compact.get(schedule)==['Through: 12/31','For: AllDays','Until: 24:00','4']
        if not enabled:raise ProjectError('constant dual-setpoint control type required')
        thermostat=dual.get(c['Control 1 Name'])
        if thermostat is None:raise ProjectError('native thermostat link missing')
        heating=constant(thermostat['Heating Setpoint Temperature Schedule Name']);cooling=constant(thermostat['Cooling Setpoint Temperature Schedule Name'])
        low=constant(s['Zone Humidistat Humidification Set Point Schedule Name']);high=constant(s['Zone Humidistat Dehumidification Set Point Schedule Name'])
        if not heating<cooling or not 0<low<=high<100:raise ProjectError('invalid native temperature or humidity deadband')
        for name,day in days.items():
            if day['Day Type'] not in ('SummerDesignDay','WinterDesignDay') or day['Dry-Bulb Temperature Range Modifier Type']!='DefaultMultipliers' or day['Humidity Condition Type']!='WetBulb':
                raise ProjectError('unsupported design-day type/profile/humidity representation')
            if day.get('Dry-Bulb Temperature Range Modifier Day Schedule Name') or day.get('Humidity Condition Day Schedule Name'):raise ProjectError('custom design-day profiles unsupported')
            summer=day['Day Type']=='SummerDesignDay'
            maximum=number(day['Maximum Dry-Bulb Temperature']);span=number(day['Daily Dry-Bulb Temperature Range']);wet=number(day['Wetbulb or DewPoint at Maximum Dry-Bulb'])
            if span<0 or wet>maximum:raise ProjectError('inconsistent native design-day conditions')
            p=copy.deepcopy(basis);data=p['load_design_conditions']
            data.update(season=q('summer' if summer else 'winter'),indoor_dry_bulb=q(cooling if summer else heating,'degC'),
                        indoor_relative_humidity=q(low if summer else high,'percent'),outdoor_dry_bulb=q(maximum if summer else maximum-span,'degC'))
            if summer:data['outdoor_wet_bulb']=q(wet,'degC')
            results.setdefault(zone,{})[name]=p
    return results


def run(idf,basis,pack,sources,out):
    files=[Path(p).resolve() for p in (idf,basis,pack)];out=Path(out).resolve()
    before={str(p):digest(p) for p in files};bases,data=[json.loads(p.read_text(encoding='utf-8-sig')) for p in files[1:]]
    official=source_paths(data,sources)
    if any(out==p or out in p.parents for p in set(files)|official):raise ProjectError('output must not contain source inputs')
    cached={str(p):digest(p) if p.is_file() else None for p in official}
    projects=extract(files[0],bases)
    checks={z:{day:evaluate(data,p,sources) for day,p in days.items()} for z,days in projects.items()}
    if any(digest(Path(p))!=h for p,h in before.items()) or any((digest(Path(p)) if Path(p).is_file() else None)!=h for p,h in cached.items()):raise ProjectError('native HVAC rule inputs changed')
    before.update({p:h for p,h in cached.items() if h is not None})
    result=dict(inputs=before,missing_sources=[p for p,h in cached.items() if h is None],inputs_unchanged=True,zone_design_day_checks=checks,supported_checks_pass=all(c['supported_checks_pass'] for days in checks.values() for c in days.values()),design_accepted=False,regulatory_compliance='not_established',
        scope='Saved supported IDF controls and design-day input limits; entire RH band checked conservatively, winter minimum equals maximum minus daily range; no maintained-state or full HVAC acceptance')
    out.mkdir(parents=True,exist_ok=False)
    (out/'bound-design-projects.json').write_text(json.dumps(projects,indent=2),encoding='utf-8')
    (out/'hvac-idf-checks.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('idf',type=Path)
    for k in ('basis','pack','sources','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();r=run(a.idf,a.basis,a.pack,a.sources,a.out)
    return 0 if r['supported_checks_pass'] else 2


if __name__=='__main__':raise SystemExit(main())

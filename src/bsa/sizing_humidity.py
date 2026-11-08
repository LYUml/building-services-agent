"""Explicit sizing-only humidity schedules with saved-model verification."""
import math
from .engine import ProjectError

METHOD='Sensible And Latent Load'


def validate(data):
    if not isinstance(data,dict) or set(data)!={'source','humidification_rh_percent','dehumidification_rh_percent'}:
        raise ProjectError('explicit sizing humidity source and both RH limits required')
    if not isinstance(data['source'],str) or not data['source'].strip():raise ProjectError('sizing humidity source required')
    for k in ('humidification_rh_percent','dehumidification_rh_percent'):
        v=data[k]
        if type(v) not in (int,float) or not math.isfinite(v) or not 0<v<100:raise ProjectError('sizing RH must be finite and strictly between 0 and 100 percent')
    if data['humidification_rh_percent']>data['dehumidification_rh_percent']:raise ProjectError('sizing humidity deadband inverted')
    return data


def author(model,data):
    import openstudio as os
    validate(data)
    for zone in model.getThermalZones():
        if not zone.zoneControlHumidistat().empty():raise ProjectError('operating humidistat would override sizing-only schedules')
        sizing=zone.sizingZone()
        if not sizing.setZoneLoadSizingMethod(METHOD):raise ProjectError('native SDK rejected latent sizing method')
        sizing.additionalProperties().setFeature('BSA_SizingHumiditySource',data['source'])
        for key,method in [('humidification_rh_percent','setZoneHumidistatHumidificationSetPointSchedule'),('dehumidification_rh_percent','setZoneHumidistatDehumidificationSetPointSchedule')]:
            schedule=os.model.ScheduleConstant(model);schedule.setName(zone.nameString()+' sizing '+key)
            if not schedule.setValue(data[key]) or not getattr(sizing,method)(schedule):raise ProjectError('native SDK rejected sizing humidity schedule')


def audit(model,data):
    validate(data);rows=[]
    for zone in model.getThermalZones():
        sizing=zone.sizingZone()
        if sizing.zoneLoadSizingMethod()!=METHOD or not zone.zoneControlHumidistat().empty():raise ProjectError('saved sizing humidity method or overriding control differs')
        source=sizing.additionalProperties().getFeatureAsString('BSA_SizingHumiditySource')
        if source.empty() or source.get()!=data['source']:raise ProjectError('saved sizing humidity provenance differs')
        row=dict(zone=zone.nameString(),method=sizing.zoneLoadSizingMethod())
        for key,getter in [('humidification_rh_percent','zoneHumidistatHumidificationSetPointSchedule'),('dehumidification_rh_percent','zoneHumidistatDehumidificationSetPointSchedule')]:
            item=getattr(sizing,getter)()
            if item.empty() or item.get().to_ScheduleConstant().empty():raise ProjectError('saved sizing humidity requires constant schedule')
            schedule=item.get().to_ScheduleConstant().get()
            if not math.isclose(schedule.value(),data[key],rel_tol=0,abs_tol=1e-10):raise ProjectError('saved sizing RH differs from source')
            row[key]=schedule.value();row[key+'_schedule']=schedule.nameString()
        rows.append(row)
    if not rows:raise ProjectError('no zones for sizing humidity audit')
    return dict(zones=rows,saved_osm_checks_pass=True,scope='Sizing-only RH schedules and sensible/latent sizing mode; operating humidistat and equipment performance not established')


def audit_idf(path,rows,data):
    import openstudio as os
    loaded=os.Workspace.load(os.path(str(path)))
    if loaded.empty():raise ProjectError('saved IDF could not be loaded')
    workspace=loaded.get()
    def objects(kind):return workspace.getObjectsByType(os.IddObjectType(kind))
    def field(obj,name):
        for i in range(obj.numFields()):
            f=obj.iddObject().getField(i)
            if not f.empty() and f.get().name()==name:
                value=obj.getString(i)
                if not value.empty():return value.get()
        raise ProjectError('missing native sizing field: '+name)
    if objects('ZoneControl:Humidistat'):raise ProjectError('native operating humidistat overrides sizing schedules')
    native=objects('Sizing:Zone');expected={r['zone']:r for r in rows}
    names=[field(o,'Zone or ZoneList Name') for o in native]
    if len(names)!=len(set(names)) or set(names)!=set(expected):raise ProjectError('native sizing zone coverage differs')
    constants=objects('Schedule:Constant');schedules={field(o,'Name'):o for o in constants}
    if len(schedules)!=len(constants):raise ProjectError('duplicate native constant schedule name')
    for obj in native:
        row=expected[field(obj,'Zone or ZoneList Name')]
        if field(obj,'Zone Load Sizing Method')!=METHOD:raise ProjectError('native latent sizing method differs')
        for key,label in [('humidification_rh_percent','Humidification'),('dehumidification_rh_percent','Dehumidification')]:
            name=field(obj,'Zone Humidistat '+label+' Set Point Schedule Name')
            if name!=row[key+'_schedule'] or name not in schedules:raise ProjectError('native sizing schedule linkage differs')
            if not math.isclose(float(field(schedules[name],'Hourly Value')),data[key],rel_tol=0,abs_tol=1e-10):raise ProjectError('native sizing RH differs')
    return dict(saved_idf_checks_pass=True,zone_count=len(native))

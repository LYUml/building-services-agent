"""Saved IFC PTAC identity/rating binding and property-only result revision."""
import math
from pathlib import Path
from .cli import digest
from .engine import ProjectError

PSET='BSA_PTACSimulation'
PROPERTIES={'cooling_capacity_w':'PTAC_CoolingCapacity_thermal_W','cooling_cop':'PTAC_GrossCoolingCOP','cooling_shr':'PTAC_GrossCoolingSHR','supply_flow_m3_s':'PTAC_SupplyFlow_m3_s','heating_capacity_w':'PTAC_HeatingCapacity_thermal_W','heating_efficiency':'PTAC_HeatingEfficiency','fan_pressure_pa':'PTAC_FanPressure_Pa','fan_efficiency':'PTAC_FanTotalEfficiency','motor_efficiency':'PTAC_MotorEfficiency','motor_in_air_fraction':'PTAC_MotorInAirFraction'}


def validate(project,binding):
    if 'hvac_devices' not in binding:return
    rows=binding['hvac_devices'];hvac=project.get('building',{}).get('hvac')
    if not hvac or not isinstance(rows,list) or len(rows)!=len(hvac['zones']):raise ProjectError('one saved IFC device mapping per PTAC zone required')
    zones=set();devices=set()
    for r in rows:
        if not isinstance(r,dict) or set(r)!={'zone_id','device_guid','system_guid','source'} or any(not isinstance(v,str) or not v.strip() for v in r.values()):raise ProjectError('exact sourced HVAC device/zone/system mapping required')
        if r['zone_id'] in zones or r['device_guid'] in devices:raise ProjectError('duplicate HVAC device/zone mapping')
        zones.add(r['zone_id']);devices.add(r['device_guid'])
    if zones!={z['id'] for z in hvac['zones']} or zones!={s['id'] for s in binding['spaces']}:raise ProjectError('HVAC device mappings must cover exact thermal spaces')


def bind(path,project,binding,geometry):
    import ifcopenshell
    import ifcopenshell.geom
    import ifcopenshell.util.element as element
    import ifcopenshell.util.system as system
    import numpy as np
    validate(project,binding);model=ifcopenshell.open(str(path));source_hash=digest(Path(path))
    if geometry['ifc_sha256']!=source_hash:raise ProjectError('HVAC space audit is from a different saved IFC')
    spaces={s['thermal_id']:s for s in geometry['spaces']};specs={s['id']:s for s in project['building']['hvac']['zones']};records=[]
    settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True)
    mapped={r['device_guid'] for r in binding['hvac_devices']}
    selected=set()
    for row in binding['hvac_devices']:
        try:device=model.by_guid(row['device_guid']);group=model.by_guid(row['system_guid'])
        except RuntimeError as exc:raise ProjectError('HVAC device/system GUID missing from saved IFC') from exc
        if not device.is_a('IfcUnitaryEquipment') or not group.is_a('IfcDistributionSystem') or group.PredefinedType!='AIRCONDITIONING':raise ProjectError('mapped HVAC unit/system class or type differs')
        groups=system.get_element_systems(device)
        if len(groups)!=1 or groups[0].GlobalId!=group.GlobalId:raise ProjectError('saved HVAC system membership differs from mapping')
        selected.update(o.GlobalId for o in system.get_system_elements(group) if o.is_a('IfcUnitaryEquipment'))
        space=spaces[row['zone_id']];container=element.get_container(device)
        if not container or container.GlobalId!=space['guid']:raise ProjectError('saved HVAC equipment is not in mapped thermal space')
        props=element.get_psets(device)
        if PSET in props:raise ProjectError('reserved HVAC simulation properties exist; preserve prior revision')
        design=props.get('BSA_DesignInputs',{})
        if not isinstance(design.get('Source'),str) or not design['Source'].strip():raise ProjectError('saved HVAC equipment source required')
        for key,property_name in PROPERTIES.items():
            actual=design.get(property_name);expected=specs[row['zone_id']][key]
            if type(actual) not in (int,float) or not math.isfinite(actual) or not math.isclose(actual,expected,rel_tol=1e-9,abs_tol=1e-9):raise ProjectError('saved HVAC rating differs from simulation input: '+property_name)
        try:shape=ifcopenshell.geom.create_shape(settings,device)
        except Exception as exc:raise ProjectError('saved HVAC device geometry unavailable') from exc
        vertices=np.asarray(shape.geometry.verts).reshape(-1,3)
        lo=np.asarray(space['origin_m']);hi=lo+np.asarray(space['size_m'])
        if not len(vertices) or not np.isfinite(vertices).all() or np.any(vertices.min(axis=0)<lo-1e-7) or np.any(vertices.max(axis=0)>hi+1e-7) or np.any(vertices.max(axis=0)-vertices.min(axis=0)<=0):raise ProjectError('saved HVAC device body lies outside mapped space or is degenerate')
        specs[row['zone_id']]['ifc_device_guid']=device.GlobalId;specs[row['zone_id']]['ifc_space_guid']=space['guid']
        records.append(dict(zone_id=row['zone_id'],device_guid=device.GlobalId,space_guid=space['guid'],system_guid=group.GlobalId,device_name=device.Name,source=row['source'],saved_source=design['Source'],body_bounds_m=[vertices.min(axis=0).tolist(),vertices.max(axis=0).tolist()],ratings_match=True))
    if selected!=mapped:raise ProjectError('selected HVAC systems contain unmapped unitary equipment')
    if digest(Path(path))!=source_hash:raise ProjectError('HVAC source IFC changed during binding')
    return dict(source_ifc_sha256=source_hash,devices=records,complete_selected_unitary_equipment_coverage=True,scope='identity, ratings, containment and bounds; no product, clash, duct/port or visual acceptance')


def append_results(source,out,annual,annual_path,binding_audit):
    import ifcopenshell
    import ifcopenshell.api as api
    import ifcopenshell.util.element as element
    import ifcopenshell.validate
    source,out=Path(source).resolve(),Path(out).resolve()
    if out.exists() or out==source:raise ProjectError('new separate HVAC result IFC required')
    model=ifcopenshell.open(str(source));original={e.id():str(e) for e in model};records=[]
    for row in binding_audit['devices']:
        obj=model.by_guid(row['device_guid'])
        if PSET in element.get_psets(obj):raise ProjectError('reserved HVAC simulation properties already exist')
        values=dict(ThermalZoneID=row['zone_id'],SourceDeviceGUID=row['device_guid'],SourceSpaceGUID=row['space_guid'],SourceIFCSHA256=binding_audit['source_ifc_sha256'],AnnualReportSHA256=digest(Path(annual_path)),Engine=annual['engine'],CalculatedChecksPass=annual['calculated_checks_pass'],DesignAccepted=False,Scope='Simulated annual operating quantities; not nameplate/feeder design values')
        for case in ('baseline','variant'):
            summaries=annual['results'][case]['summary']['hvac']['zones']
            match=next((r for r in summaries if r['zone']==row['zone_id']),None)
            if match is None:raise ProjectError('native HVAC zone result missing')
            prefix=case.capitalize()
            values[prefix+'AnnualElectricity_kWh']=match['ptac_electricity_kwh']
            values[prefix+'PeakElectricity_kW']=match['ptac_peak_electricity_kw']
        pset=api.run('pset.add_pset',model,product=obj,name=PSET);api.run('pset.edit_pset',model,pset=pset,properties=values)
        records.append(dict(device_guid=obj.GlobalId,properties=values))
    model.write(str(out));saved=ifcopenshell.open(str(out))
    if any(str(saved.by_id(key))!=value for key,value in original.items()):raise ProjectError('original IFC entity changed during HVAC result append')
    for row in records:
        actual=element.get_psets(saved.by_guid(row['device_guid'])).get(PSET,{})
        for k,v in row['properties'].items():
            saved_value=actual.get(k)
            equal=(type(saved_value) in (int,float) and math.isclose(saved_value,v,rel_tol=1e-12,abs_tol=1e-12)) if type(v) is float else saved_value==v
            if type(v) is bool:equal=type(saved_value) is bool and saved_value==v
            if not equal:raise ProjectError('saved HVAC result property differs')
    logger=ifcopenshell.validate.json_logger();ifcopenshell.validate.validate(saved,logger,express_rules=True)
    if logger.statements:raise ProjectError('annotated HVAC IFC schema validation failed')
    if digest(Path(source))!=binding_audit['source_ifc_sha256']:raise ProjectError('original HVAC IFC changed')
    return dict(path=Path(out).name,sha256=digest(Path(out)),original_entities_unchanged=True,original_entity_count=len(original),schema_issues=0,devices=records,design_accepted=False)

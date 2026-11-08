"""Source-backed synthetic two-zone OpenStudio/EnergyPlus design-day workflow."""
import argparse
import json
import math
import sqlite3
import subprocess
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from .energy_completion import inspect as inspect_completion


def build(p, lighting, out):
    import openstudio as os
    m=os.model.Model()
    m.getBuilding().setName(p["name"])
    m.getYearDescription().setCalendarYear(2025)
    site=m.getSite()
    for method,key in (("setLatitude","latitude_deg"),("setLongitude","longitude_deg"),("setTimeZone","timezone_h"),("setElevation","elevation_m")):
        getattr(site,method)(p["site"][key])
    control=m.getSimulationControl()
    control.setRunSimulationforSizingPeriods(True)
    control.setRunSimulationforWeatherFileRunPeriods(False)
    control.setDoZoneSizingCalculation(True)
    m.getTimestep().setNumberOfTimestepsPerHour(4)
    material=os.model.MasslessOpaqueMaterial(m)
    material.setName("Synthetic uniform insulation")
    material.setThermalResistance(p["envelope_r_m2k_w"])
    material.setRoughness("MediumRough")
    construction=os.model.Construction(m)
    mass=os.model.StandardOpaqueMaterial(m)
    mass.setName("Synthetic thermal mass")
    mass.setThickness(0.1);mass.setConductivity(0.5)
    mass.setDensity(800);mass.setSpecificHeat(1000)
    layers=os.model.MaterialVector();layers.append(mass);layers.append(material)
    construction.setLayers(layers)
    on=os.model.ScheduleConstant(m);on.setValue(1)
    heat=os.model.ScheduleConstant(m);heat.setValue(p["heating_setpoint_c"])
    cool=os.model.ScheduleConstant(m);cool.setValue(p["cooling_setpoint_c"])
    spaces=[]
    for i in range(2):
        x=i*p["zone_width_m"];w=p["zone_width_m"];d=p["zone_depth_m"]
        points=os.Point3dVector()
        for a,b in ((x,0),(x,d),(x+w,d),(x+w,0)):
            points.append(os.Point3d(a,b,0))
        space=os.model.Space.fromFloorPrint(points,p["height_m"],m).get()
        space.setName(f"Zone {i+1} space");spaces.append(space)
        zone=os.model.ThermalZone(m);zone.setName(f"Zone {i+1}")
        space.setThermalZone(zone)
        thermostat=os.model.ThermostatSetpointDualSetpoint(m)
        thermostat.setHeatingSetpointTemperatureSchedule(heat)
        thermostat.setCoolingSetpointTemperatureSchedule(cool)
        zone.setThermostatSetpointDualSetpoint(thermostat)
        zone.setUseIdealAirLoads(True)
        definition=os.model.LightsDefinition(m)
        definition.setWattsperSpaceFloorArea(lighting)
        lights=os.model.Lights(definition);lights.setSpace(space);lights.setSchedule(on)
        for surface in space.surfaces():
            surface.setConstruction(construction)
            if surface.surfaceType()=="Floor":surface.setOutsideBoundaryCondition("Adiabatic")
    sv=os.model.SpaceVector()
    for space in spaces:sv.append(space)
    os.model.matchSurfaces(sv)
    for dd in p["design_days"]:
        day=os.model.DesignDay(m);day.setName(dd["name"]);day.setMonth(dd["month"])
        day.setDayOfMonth(dd["day"]);day.setDayType(dd["type"])
        day.setMaximumDryBulbTemperature(dd["max_dry_bulb_c"])
        day.setDailyDryBulbTemperatureRange(dd["range_c"])
        day.setHumidityConditionType("WetBulb")
        day.setWetBulbOrDewPointAtMaximumDryBulb(dd["wet_bulb_c"])
        day.setBarometricPressure(101325);day.setWindSpeed(3);day.setWindDirection(0)
        day.setSolarModelIndicator("ASHRAEClearSky");day.setSkyClearness(1)
    for variable in ("Zone Ideal Loads Supply Air Total Cooling Rate","Zone Ideal Loads Supply Air Total Heating Rate","Lights Electricity Rate"):
        v=os.model.OutputVariable(variable,m);v.setReportingFrequency("Hourly");v.setKeyValue("*")
    m.getOutputSQLite().setOptionType("SimpleAndTabular")
    osm=out/"model.osm";m.save(os.path(str(osm)),True)
    ft=os.energyplus.ForwardTranslator();workspace=ft.translateModel(m)
    workspace.save(os.path(str(out/"model.idf")),True)
    errors=[str(x.logMessage()) for x in ft.errors()]
    if errors:raise ProjectError("translation errors: "+str(errors))
    area=sum(s.floorArea() for s in spaces)
    matched=sum(s.outsideBoundaryCondition()=="Surface" for s in m.getSurfaces())
    if not math.isclose(area,2*w*d) or matched!=2:
        raise ProjectError(f"geometry mismatch: area={area}, matched surfaces={matched}")
    return dict(openstudio_version=os.openStudioVersion(),energyplus_version=os.energyPlusVersion(),
        floor_area_m2=area,thermal_zones=len(m.getThermalZones()),matched_surface_count=matched,
        lighting_w_m2=lighting,translation_warnings=[str(x.logMessage()) for x in ft.warnings()])


def extract(sql):
    con=sqlite3.connect(Path(sql).resolve().as_uri()+'?mode=ro',uri=True)
    try:
        rows=con.execute("""SELECT d.Name,d.KeyValue,d.Units, MAX(r.Value),SUM(r.Value*t.Interval*60),COUNT(*)
          FROM ReportData r JOIN ReportDataDictionary d ON r.ReportDataDictionaryIndex=d.ReportDataDictionaryIndex
          JOIN Time t ON r.TimeIndex=t.TimeIndex WHERE COALESCE(t.WarmupFlag,0)=0
          GROUP BY d.ReportDataDictionaryIndex""").fetchall()
        return [dict(variable=n,key=k,units=u,peak=v,integral_j=energy if u=="W" else None,samples=count)
                for n,k,u,v,energy,count in rows]
    finally:con.close()


def totals(sql):
    """Coincident whole-building peaks, grouped by simulated environment."""
    con=sqlite3.connect(Path(sql).resolve().as_uri()+'?mode=ro',uri=True)
    try:
        rows=con.execute("""WITH whole_building AS (
          SELECT e.EnvironmentName AS environment, d.Name AS variable,d.Units AS units,
          t.TimeIndex AS ti,t.Interval AS minutes,SUM(r.Value) AS rate
          FROM ReportData r JOIN ReportDataDictionary d ON r.ReportDataDictionaryIndex=d.ReportDataDictionaryIndex
          JOIN Time t ON r.TimeIndex=t.TimeIndex
          JOIN EnvironmentPeriods e ON t.EnvironmentPeriodIndex=e.EnvironmentPeriodIndex
          WHERE COALESCE(t.WarmupFlag,0)=0 AND d.Units='W'
          GROUP BY e.EnvironmentPeriodIndex,d.Name,t.TimeIndex)
          SELECT environment,variable,MAX(rate),SUM(rate*minutes*60)/3600000.0,COUNT(*)
          FROM whole_building GROUP BY environment,variable""").fetchall()
        return [dict(environment=e,variable=v,coincident_peak_kw=peak/1000,
                     simulated_period_kwh=energy,samples=n) for e,v,peak,energy,n in rows]
    finally:con.close()


def validate(p,require_design_days=True):
    if not isinstance(p,dict) or not isinstance(p.get("source"),str) or not p["source"].strip():
        raise ProjectError("source statement required")
    def number(value,label,low=None,high=None):
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
            raise ProjectError(f"finite number required: {label}")
        if (low is not None and value<low) or (high is not None and value>high):
            raise ProjectError(f"out of range: {label}")
    for key in ("zone_width_m","zone_depth_m","height_m","envelope_r_m2k_w"):
        number(p.get(key),key,0.001)
    for key in ("baseline_lighting_w_m2","variant_lighting_w_m2"):
        number(p.get(key),key,0)
    for key in ("heating_setpoint_c","cooling_setpoint_c"):
        number(p.get(key),key,-50,60)
    if p["heating_setpoint_c"]>=p["cooling_setpoint_c"]:raise ProjectError("setpoint deadband required")
    if not isinstance(p.get("name"),str) or not p["name"].strip():raise ProjectError("name required")
    site=p.get("site")
    if not isinstance(site,dict):raise ProjectError("site required")
    for key,lo,hi in (("latitude_deg",-90,90),("longitude_deg",-180,180),("timezone_h",-12,14),("elevation_m",-500,9000)):
        number(site.get(key),key,lo,hi)
    days=p.get("design_days")
    if not isinstance(days,list) or require_design_days and not days:raise ProjectError("design days required")
    names=set()
    import datetime
    for d in days:
        if not isinstance(d,dict) or d.get("type") not in ("SummerDesignDay","WinterDesignDay"):
            raise ProjectError("unsupported design day")
        if not isinstance(d.get("name"),str) or not d["name"].strip() or d["name"] in names:
            raise ProjectError("unique design day names required")
        names.add(d["name"])
        try:datetime.date(2025,d["month"],d["day"])
        except (KeyError,ValueError,TypeError):raise ProjectError("invalid design day date")
        number(d.get("max_dry_bulb_c"),"dry bulb",-60,70)
        number(d.get("range_c"),"daily range",0,50)
        number(d.get("wet_bulb_c"),"wet bulb",-60,70)
        if d["wet_bulb_c"]>d["max_dry_bulb_c"]:raise ProjectError("wet bulb exceeds dry bulb")
    return p


def run(project,out,exe):
    project,out,exe=project.resolve(),out.resolve(),exe.resolve()
    if not exe.is_file():raise ProjectError("EnergyPlus executable not found")
    if out in project.parents:raise ProjectError("output cannot contain project")
    p=validate(json.loads(project.read_text(encoding="utf-8-sig")))
    before=digest(project)
    version=subprocess.check_output([str(exe),"--version"],text=True).strip()
    import openstudio
    if openstudio.energyPlusVersion() not in version:raise ProjectError("SDK/engine version mismatch")
    out.mkdir(parents=True,exist_ok=False)
    results={}
    for variant,field in (("baseline","baseline_lighting_w_m2"),("variant","variant_lighting_w_m2")):
        folder=out/variant;folder.mkdir()
        metadata=build(p,p[field],folder)
        with (folder/"engine.log").open("wb") as log:
            process=subprocess.run([str(exe),"-x","-D","-d",str(folder),str(folder/"model.idf")],
                cwd=folder,stdout=log,stderr=subprocess.STDOUT,timeout=180)
        completion=inspect_completion(folder,process.returncode,version,digest(exe))
        (folder/'completion.json').write_text(json.dumps(completion,indent=2),encoding='utf-8')
        if not completion['completion_verified']:raise ProjectError('design-day native completion evidence unverified; inspect completion.json')
        err=(folder/"eplusout.err").read_text(errors="replace")
        (folder/"diagnostics.txt").write_text(err,encoding="utf-8")
        metrics=extract(folder/"eplusout.sql")
        if not any("Total Cooling Rate" in r["variable"] and r["peak"]>0 for r in metrics):
            raise ProjectError("missing cooling output")
        results[variant]=dict(metadata=metadata,metrics=metrics,completion=completion,whole_building=totals(folder/"eplusout.sql"),error_log_sha256=digest(folder/"eplusout.err"),
            warnings=err,artifacts={f.name:digest(f) for f in folder.iterdir() if f.suffix in (".osm",".idf",".sql")})
    if digest(project)!=before:raise ProjectError("input changed")
    base={(r["environment"],r["variable"]):r for r in results["baseline"]["whole_building"]}
    comparison=[]
    for r in results["variant"]["whole_building"]:
        b=base[(r["environment"],r["variable"])]
        comparison.append(dict(environment=r["environment"],variable=r["variable"],
            peak_change_kw=r["coincident_peak_kw"]-b["coincident_peak_kw"],
            period_change_kwh=r["simulated_period_kwh"]-b["simulated_period_kwh"]))
    result=dict(comparison=comparison,engine=version,engine_sha256=digest(exe),input_sha256=before,input_unchanged=True,
        analysis_scope="Two synthetic design days, not annual energy; ideal loads are thermal demand, not plant electricity",
        assumptions=[p["source"],"No windows, occupants, equipment, ventilation or infiltration; adiabatic floors; always-on lights; 101325 Pa, wind 3 m/s, clear sky; added 0.1 m mass layer k=0.5 W/mK, rho=800 kg/m3, cp=1000 J/kgK"],
        design_accepted=False,results=results)
    (out/"analysis.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("project",type=Path);p.add_argument("--out",required=True,type=Path)
    p.add_argument("--energyplus",required=True,type=Path)
    a=p.parse_args();r=run(a.project,a.out,a.energyplus)
    print(json.dumps({"engine":r["engine"],"scope":r["analysis_scope"],"output":str(a.out)},indent=2))

if __name__=="__main__":main()

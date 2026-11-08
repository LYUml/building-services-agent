"""Sourced rectangular exterior-wall windows with explicit simple glazing."""
import math
import re
from .engine import ProjectError

FACES={'X-':(0,-1,1),'X+':(0,1,1),'Y-':(1,-1,0),'Y+':(1,1,0)}
VARIABLES={'Surface Window Transmitted Solar Radiation Energy':'J','Surface Window Heat Gain Energy':'J','Surface Window Heat Loss Energy':'J','Surface Outside Face Incident Solar Radiation Rate per Area':'W/m2'}
VALIDATION_BASIS=dict(engine='EnergyPlus 25.2.0-cf7368216c',file='Energy+.idd',sha256='5f71380fdeb7d2456dbfb71913b90c40f87e109051c62c44f08577451974f44f',object='WindowMaterial:SimpleGlazingSystem',scope='input syntax/ranges; not product/code applicability')


def validate(rows,spaces=None,zone_ids=None):
    if not isinstance(rows,list) or not 1<=len(rows)<=200:raise ProjectError('one to 200 explicit sourced windows required')
    ids=set();known={s['id']:s for s in spaces} if spaces is not None else None
    zones=set(known) if known is not None else set(zone_ids or [])
    for row in rows:
        if not isinstance(row,dict) or set(row)!={'id','zone','source','face','offset_m','sill_m','width_m','height_m','glazing'}:raise ProjectError('exact exterior-window geometry/glazing fields required')
        if not isinstance(row['id'],str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}',row['id']) or row['id'].upper() in ids:raise ProjectError('unique ASCII window IDs required')
        ids.add(row['id'].upper())
        if not isinstance(row['zone'],str) or row['zone'] not in zones or not isinstance(row['face'],str) or row['face'] not in FACES:raise ProjectError('known thermal zone and Cartesian exterior face required')
        if not isinstance(row['source'],str) or not row['source'].strip():raise ProjectError('window geometry source required')
        for key in ('offset_m','sill_m','width_m','height_m'):
            if type(row[key]) not in (int,float) or not math.isfinite(row[key]) or row[key]<=0:raise ProjectError('positive finite window dimensions/edge offsets required')
        g=row['glazing']
        if not isinstance(g,dict) or set(g)!={'source','u_factor_w_m2k','shgc','visible_transmittance'} or not isinstance(g['source'],str) or not g['source'].strip():raise ProjectError('sourced simple glazing U/SHGC/visible transmittance required')
        for key in ('u_factor_w_m2k','shgc','visible_transmittance'):
            value=g[key]
            if type(value) not in (int,float) or not math.isfinite(value) or value<=0 or key!='u_factor_w_m2k' and value>=1:raise ProjectError('invalid simple glazing property: '+key)
        if known is not None:
            axis,sign,horizontal=FACES[row['face']];space=known[row['zone']];origin=space['origin_m'];size=space['size_m']
            if row['offset_m']+row['width_m']>=size[horizontal]-1e-7 or row['sill_m']+row['height_m']>=size[2]-1e-7:raise ProjectError('window must fit strictly inside source wall')
            plane=origin[axis]+(size[axis] if sign>0 else 0)
            for other in spaces:
                if other['id']==space['id']:continue
                peer_plane=other['origin_m'][axis]+(0 if sign>0 else other['size_m'][axis])
                overlap=all(min(origin[k]+size[k],other['origin_m'][k]+other['size_m'][k])-max(origin[k],other['origin_m'][k])>1e-7 for k in (horizontal,2))
                if abs(plane-peer_plane)<=1e-7 and overlap:raise ProjectError('window requested on interzone wall')
    for i,a in enumerate(rows):
        for b in rows[i+1:]:
            if a['zone']==b['zone'] and a['face']==b['face'] and min(a['offset_m']+a['width_m'],b['offset_m']+b['width_m'])-max(a['offset_m'],b['offset_m'])>1e-7 and min(a['sill_m']+a['height_m'],b['sill_m']+b['height_m'])-max(a['sill_m'],b['sill_m'])>1e-7:raise ProjectError('overlapping source windows')
    return rows


def rectangle(row,space):
    axis,sign,h=FACES[row['face']];origin=space['origin_m'];size=space['size_m']
    plane=origin[axis]+(size[axis] if sign>0 else 0);u=origin[h]+row['offset_m'];z=origin[2]+row['sill_m']
    points=[]
    for a,b in ((u,z),(u+row['width_m'],z),(u+row['width_m'],z+row['height_m']),(u,z+row['height_m'])):
        point=[0.,0.,b];point[axis]=plane;point[h]=a;points.append(point)
    # u cross +Z is +X for X faces and -Y for Y faces.
    if sign!=(1 if axis==0 else -1):points.reverse()
    return points


def author(model,rows,spaces):
    import openstudio as os
    validate(rows,spaces);known={s['id']:s for s in spaces}
    for row in rows:
        space=model.getSpaceByName(row['zone']+' space').get();transform=space.transformation();axis,sign,h=FACES[row['face']]
        plane=known[row['zone']]['origin_m'][axis]+(known[row['zone']]['size_m'][axis] if sign>0 else 0)
        parents=[s for s in space.surfaces() if s.surfaceType()=='Wall' and s.outsideBoundaryCondition()=='Outdoors' and all(abs((transform*v).x()-plane)<1e-7 if axis==0 else abs((transform*v).y()-plane)<1e-7 for v in s.vertices())]
        if len(parents)!=1:raise ProjectError('one actual exterior parent wall required')
        points=os.Point3dVector()
        for xyz in rectangle(row,known[row['zone']]):points.append(transform.inverse()*os.Point3d(*xyz))
        window=os.model.SubSurface(points,model);window.setName('WIN '+row['id']);window.setSubSurfaceType('FixedWindow');window.setMultiplier(1)
        if not window.setSurface(parents[0]):raise ProjectError('SDK rejected exterior window parent')
        g=row['glazing'];material=os.model.SimpleGlazing(model);material.setName('BSA glazing '+row['id']);material.additionalProperties().setFeature('Source',g['source'])
        for key,setter in (('u_factor_w_m2k','setUFactor'),('shgc','setSolarHeatGainCoefficient'),('visible_transmittance','setVisibleTransmittance')):
            if not getattr(material,setter)(g[key]):raise ProjectError('SDK rejected glazing property: '+key)
        construction=os.model.Construction(model);construction.setName('BSA window '+row['id']);layers=os.model.MaterialVector();layers.append(material)
        if not construction.setLayers(layers) or not window.setConstruction(construction):raise ProjectError('SDK rejected glazing construction')
        for feature,value in (('Source',row['source']),('InputID',row['id']),('ZoneID',row['zone']),('Face',row['face'])):window.additionalProperties().setFeature(feature,value)
        for name in VARIABLES:
            output=os.model.OutputVariable(name,model);output.setKeyValue(window.nameString());output.setReportingFrequency('Hourly')


def audit(model,rows,spaces):
    import numpy as np
    validate(rows,spaces);known={s['id']:s for s in spaces};windows=model.getSubSurfaces()
    if {w.nameString() for w in windows}!={'WIN '+r['id'] for r in rows} or len(windows)!=len(rows):raise ProjectError('saved window identity/count differs')
    records=[]
    for row in rows:
        window=model.getSubSurfaceByName('WIN '+row['id']).get();parent=window.surface()
        if not window.windowPropertyFrameAndDivider().empty() or window.shadingControls() or window.isConstructionDefaulted():raise ProjectError('explicit unshaded frameless window construction required')
        if parent.empty() or parent.get().outsideBoundaryCondition()!='Outdoors' or parent.get().surfaceType()!='Wall' or window.subSurfaceType()!='FixedWindow' or window.multiplier()!=1:raise ProjectError('saved window parent/type/multiplier differs')
        if window.space().empty() or window.space().get().thermalZone().get().nameString()!=row['zone']:raise ProjectError('saved window zone differs')
        transform=window.space().get().transformation();world=[transform*p for p in window.vertices()];actual=[[p.x(),p.y(),p.z()] for p in world]
        expected=rectangle(row,known[row['zone']])
        if len(actual)!=4 or not np.allclose(sorted(actual),sorted(expected),atol=1e-7,rtol=0):raise ProjectError('saved window world vertices differ')
        normal=transform*window.outwardNormal();axis,sign,h=FACES[row['face']];target=[0,0,0];target[axis]=sign
        if not np.allclose([normal.x(),normal.y(),normal.z()],target,atol=1e-7,rtol=0):raise ProjectError('saved window face orientation differs')
        for key,value in (('Source',row['source']),('InputID',row['id']),('ZoneID',row['zone']),('Face',row['face'])):
            feature=window.additionalProperties().getFeatureAsString(key)
            if feature.empty() or feature.get()!=value:raise ProjectError('saved window provenance differs')
        if window.construction().empty() or window.construction().get().to_Construction().empty():raise ProjectError('saved glazing construction missing')
        construction=window.construction().get().to_Construction().get()
        if construction.numLayers()!=1 or construction.layers()[0].to_SimpleGlazing().empty():raise ProjectError('one saved simple glazing layer required')
        material=construction.layers()[0].to_SimpleGlazing().get();g=row['glazing']
        for key,getter in (('u_factor_w_m2k','uFactor'),('shgc','solarHeatGainCoefficient'),('visible_transmittance','visibleTransmittance')):
            value=getattr(material,getter)()
            if hasattr(value,'get'):
                if value.empty():raise ProjectError('saved glazing property missing')
                value=value.get()
            if not math.isclose(value,g[key],rel_tol=1e-9,abs_tol=1e-10):raise ProjectError('saved glazing property differs')
        source=material.additionalProperties().getFeatureAsString('Source')
        if source.empty() or source.get()!=g['source']:raise ProjectError('saved glazing source differs')
        area=row['width_m']*row['height_m']
        if not math.isclose(window.grossArea(),area,rel_tol=1e-9,abs_tol=1e-9):raise ProjectError('saved window area differs')
        records.append(dict(id=row['id'],key=window.nameString().upper(),zone=row['zone'],face=row['face'],parent=parent.get().nameString(),vertices_m=actual,area_m2=area,u_factor_w_m2k=g['u_factor_w_m2k'],shgc=g['shgc'],visible_transmittance=g['visible_transmittance']))
    parents={w.surface().get().handle():w.surface().get() for w in windows}
    for parent in parents.values():
        if not math.isclose(parent.grossArea()-parent.netArea(),sum(w.grossArea() for w in parent.subSurfaces()),rel_tol=1e-9,abs_tol=1e-8):raise ProjectError('parent opaque/window area reconciliation failed')
    return dict(validation_basis=VALIDATION_BASIS,saved_windows_match=True,window_area_m2=sum(r['area_m2'] for r in records),windows=records,scope='vertical thermal-model windows; simple glazing indices include films; no IFC window/product/daylighting acceptance')


def extract(sql,audit,year,solver):
    import sqlite3
    from pathlib import Path
    from .annual_energy import calendar_hours
    con=sqlite3.connect(Path(sql).resolve().as_uri()+'?mode=ro',uri=True)
    try:
        environments=con.execute('SELECT EnvironmentType FROM EnvironmentPeriods').fetchall()
        if environments!=[(3,)]:raise ProjectError('one annual window weather environment required')
        rows=con.execute('''SELECT d.Name,d.KeyValue,d.Units,d.ReportingFrequency,t.Year,t.Month,t.Day,t.Hour,t.Minute,t.Interval,r.Value FROM ReportData r JOIN ReportDataDictionary d ON d.ReportDataDictionaryIndex=r.ReportDataDictionaryIndex JOIN Time t ON t.TimeIndex=r.TimeIndex WHERE COALESCE(t.WarmupFlag,0)=0 ORDER BY d.Name,d.KeyValue,t.TimeIndex''').fetchall()
    finally:con.close()
    expected=list(calendar_hours(year));series={};windows={r['key']:r for r in audit['windows']}
    for name,key,units,freq,y,m,d,h,minute,interval,value in rows:
        if name not in VARIABLES:continue
        if units!=VARIABLES[name] or freq!='Hourly' or y!=year or minute!=0 or interval!=60 or not math.isfinite(value) or value<0:raise ProjectError('invalid native hourly window units/calendar/value')
        series.setdefault((name,key),[]).append(((m,d,h),value))
    for name in VARIABLES:
        keys={key for variable,key in series if variable==name}
        if keys!=set(windows) or any([t for t,value in series[(name,key)]]!=expected for key in keys):raise ProjectError('complete unique window identities and hourly coverage required')
    annual=[];monthly=[];hourly=[];bound=True;reconciled=True
    transmitted='Surface Window Transmitted Solar Radiation Energy';incident='Surface Outside Face Incident Solar Radiation Rate per Area'
    for key,window in windows.items():
        solar=[v for t,v in series[(transmitted,key)]];sun=[v for t,v in series[(incident,key)]]
        bound &= all(a<=b*window['area_m2']*3600+solver['rate_tolerance_w']*3600 for a,b in zip(solar,sun))
        for name,units in VARIABLES.items():
            values=series[(name,key)];scale=1/3600000 if units=='J' else window['area_m2']/1000
            total=math.fsum(v for t,v in values)*scale
            annual.append(dict(window=window['id'],key=key,variable=name,kwh=total,quantity='incident solar on window' if units!='J' else 'transmitted solar' if name==transmitted else 'window heat gain' if 'Gain' in name else 'window heat loss',hours=len(values)))
            amounts=[]
            for month in range(1,13):
                amount=math.fsum(v for (m,d,h),v in values if m==month)*scale;amounts.append(amount)
                monthly.append(dict(window=window['id'],variable=name,month=month,kwh=amount))
            reconciled &= abs(math.fsum(amounts)-total)<=solver['energy_tolerance_kwh']
            for (m,d,h),v in values:hourly.append(dict(window=window['id'],key=key,variable=name,month=m,day=d,hour=h,value=v,units=units))
    checks=dict(window_hourly_coverage=True,transmitted_solar_incident_bound=bound,window_monthly_annual_reconciliation=reconciled)
    return dict(checks=checks,calculated_checks_pass=all(checks.values()),annual=annual,monthly=monthly,scope='window solar and net-gain/loss terms; not HVAC electricity or daylight illuminance'),hourly

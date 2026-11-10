"""Bounded official 2D source snapshot and thin GIS projection; no inferred heights/site."""
import argparse
from datetime import datetime,timezone
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from bsa.cli import digest
from bsa.engine import ProjectError
ROOT=Path(__file__).resolve().parents[1]


def run(out,python,cache=None):
    from shapely.geometry import shape,box
    from importlib import metadata
    out,python=Path(out).resolve(),Path(python).resolve();decision=ROOT/'benchmarks/mit-4401-2018/gis-decisions.json'
    if out.exists() or not out.is_relative_to(ROOT):raise ProjectError('new repository-local GIS output required')
    d=json.loads(decision.read_text(encoding='utf-8'));west,south,east,north=d['bbox_wgs84'];limit=d['maximum_records']
    wkt=f'POLYGON(({west} {south},{east} {south},{east} {north},{west} {north},{west} {south}))'
    where="intersects(the_geom, '"+wkt+"')";api='https://data.cityofchicago.org/resource/syp8-uezg.json'
    count=api+'?'+urllib.parse.urlencode({'$where':where,'$select':'count(*)'})
    urls={'metadata.json':'https://data.cityofchicago.org/api/views/syp8-uezg.json','count.json':count,'features.json':api+'?'+urllib.parse.urlencode({'$where':where,'$limit':str(limit),'$select':'bldg_id,the_geom,stories,no_stories,z_coord'}),'count-after.json':count,'county-item.json':'https://www.arcgis.com/sharing/rest/content/items/7c4f47a3b32944e58c5f18652880fc05?f=json','county-metadata.xml':'https://www.arcgis.com/sharing/rest/content/items/7c4f47a3b32944e58c5f18652880fc05/info/metadata/metadata.xml'}
    out.mkdir(parents=True);sources=out/'sources';sources.mkdir();hashes={}
    if cache:
        cache=Path(cache).resolve();manifest=json.loads((cache/'snapshot.json').read_text(encoding='utf-8'))
        if manifest['urls']!=urls or set(manifest['sha256'])!=set(urls):raise ProjectError('GIS cache query identity differs')
        for name in urls:
            path=cache/'sources'/name
            if digest(path)!=manifest['sha256'][name]:raise ProjectError('GIS cache source changed')
            shutil.copyfile(path,sources/name);hashes[name]=digest(sources/name)
            if hashes[name]!=manifest['sha256'][name]:raise ProjectError('GIS cache source changed during copy')
        acquired=manifest['acquired_utc']
    else:
        acquired=datetime.now(timezone.utc).isoformat()
        for name,url in urls.items():
            with urllib.request.urlopen(url,timeout=45) as response:data=response.read(2_000_001)
            if len(data)>2_000_000:raise ProjectError('bounded GIS source exceeded byte budget')
            (sources/name).write_bytes(data);hashes[name]=digest(sources/name)
    (out/'snapshot.json').write_text(json.dumps(dict(urls=urls,sha256=hashes,acquired_utc=acquired),indent=2),encoding='utf-8')
    source=json.loads((sources/'features.json').read_text(encoding='utf-8'));meta=json.loads((sources/'metadata.json').read_text(encoding='utf-8'))
    expected=int(json.loads((sources/'count.json').read_text(encoding='utf-8'))[0]['count']);after=int(json.loads((sources/'count-after.json').read_text(encoding='utf-8'))[0]['count'])
    if meta['id']!='syp8-uezg' or expected!=after or not 0<expected<=limit or len(source)!=expected or len({r['bldg_id'] for r in source})!=expected:raise ProjectError('exact bounded source count/identity without truncation required')
    query=box(west,south,east,north)
    for row in source:
        geometry=shape(row['the_geom'])
        if geometry.geom_type!='MultiPolygon' or not geometry.is_valid or geometry.area<=0 or not geometry.intersects(query):raise ProjectError('invalid/nonintersecting source footprint; no geometry auto-repair allowed')
    worker=ROOT/'adapters/gis-context/worker.py';lock=worker.parent/'dependencies.json';pins={str(p):digest(p) for p in (decision,worker,lock,python)}
    packet=out/'packet.json';packet.write_text(json.dumps(dict(latitude=d['latitude'],longitude=d['longitude'],features=source),indent=2),encoding='utf-8')
    packet_sha=digest(packet)
    with (out/'worker.log').open('wb') as log:process=subprocess.run([str(python),str(worker),str(packet),str(out/'local-footprints.json')],stdout=log,stderr=subprocess.STDOUT,timeout=60)
    if process.returncode:raise ProjectError('pinned GIS projection failed; inspect worker.log')
    result=json.loads((out/'local-footprints.json').read_text(encoding='utf-8'))
    if len(result['features'])!=expected or result['maximum_roundtrip_error_deg']>1e-9 or any(abs(v)>1e-8 for v in result['reference_xy_m']) or abs(result['north_probe_xy_m'][0])>1e-6 or result['north_probe_xy_m'][1]<=0:raise ProjectError('GIS coverage/axis order/roundtrip differs')
    ids={r['bldg_id'] for r in source}
    if {r['id'] for r in result['features']}!=ids:raise ProjectError('projected source IDs differ')
    for row in result['features']:
        geometry=shape(row['geometry']);area=geometry.area
        if not geometry.is_valid or not math.isfinite(area) or area<=0 or abs(area/row['geodesic_area_m2']-1)>1e-4 or row['height_m'] is not None:raise ProjectError('projected geometry/area/unknown height differs')
        row['projected_area_m2']=area
    if digest(packet)!=packet_sha or any(digest(sources/name)!=sha for name,sha in hashes.items()) or any(digest(Path(p))!=sha for p,sha in pins.items()):raise ProjectError('GIS source changed during conversion')
    result.update(source='City of Chicago Building Footprints syp8-uezg; full intersecting polygons retained, no clipping',source_time_period=meta.get('metadata',{}).get('custom_fields',{}).get('Metadata',{}).get('Time Period','unspecified'),source_rows_updated_at=meta['rowsUpdatedAt'],license_id=meta.get('licenseId'),query_bbox_wgs84=d['bbox_wgs84'],query_source=d['source'],feature_count=expected,geometry_checks_pass=True,base_geometry_runtime=dict(shapely=metadata.version('shapely')),inputs=pins,unknown_height_count=expected,pending=['Cook County 2022 height geometry download (direct host TLS failure recorded separately)','height datum/units/ground and current completeness verification','actual parcel/site, orientation and IFC placement','trees/other obstructions and real shading/daylight acceptance'])
    plot(out,result)
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'gis-context.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


def plot(out,result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axis=plt.subplots(figsize=(9,9))
    for row in result['features']:
        for poly in row['geometry']['coordinates']:
            for ring in poly:axis.plot([p[0] for p in ring],[p[1] for p in ring],color='#42576b',linewidth=1)
    axis.scatter([0],[0],marker='+',s=100,color='#c45918',label='Query reference only, not project site')
    axis.set_aspect('equal');axis.set(xlabel='Local azimuthal-equidistant X (m)',ylabel='Local azimuthal-equidistant Y (m)',title=f"{result['feature_count']} historical building footprints; all heights unknown")
    axis.annotate('N at reference',xy=(0,95),xytext=(0,55),ha='center',arrowprops=dict(arrowstyle='->'));axis.grid(alpha=.2);axis.legend(loc='lower left',fontsize=8)
    fig.suptitle('City of Chicago source: August 2015 candidate area',fontsize=14)
    fig.text(.5,.025,'Source: data.cityofchicago.org / syp8-uezg. Modified coordinate presentation; no City endorsement.\nNot a parcel boundary, current survey, 3D context or shading result.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.07,1,.95));fig.savefig(out/'footprints.png',dpi=150);plt.close(fig)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--gis-python',type=Path,required=True);p.add_argument('--cache',type=Path)
    a=p.parse_args();r=run(a.out,a.gis_python,a.cache);print(json.dumps({k:r[k] for k in ('feature_count','source_time_period','unknown_height_count','geometry_checks_pass','three_dimensional_context_ready','site_selected','design_accepted')},indent=2))

"""Original thin pyproj composition; no footprint extraction or height inference."""
from importlib import metadata
import json
import math
from pathlib import Path
import sys
from pyproj import CRS,Transformer,Geod,__proj_version__


def run(packet,out):
    p=json.loads(Path(packet).read_text(encoding='utf-8'));lat=p['latitude'];lon=p['longitude']
    pins=json.loads((Path(__file__).parent/'dependencies.json').read_text(encoding='utf-8'))
    if any(metadata.version(r['name'])!=r['version'] for r in pins):raise ValueError('GIS runtime differs from pins')
    local=CRS.from_proj4(f'+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m +no_defs')
    forward=Transformer.from_crs('EPSG:4326',local,always_xy=True);back=Transformer.from_crs(local,'EPSG:4326',always_xy=True);geod=Geod(ellps='WGS84')
    output=[];error=0
    for row in p['features']:
        parts=[];area=0
        for polygon in row['the_geom']['coordinates']:
            rings=[]
            for index,ring in enumerate(polygon):
                transformed=[]
                for x,y in ring:
                    a,b=forward.transform(x,y,errcheck=True);rx,ry=back.transform(a,b,errcheck=True)
                    error=max(error,abs(rx-x),abs(ry-y));transformed.append([a,b])
                signed,_=geod.polygon_area_perimeter([v[0] for v in ring],[v[1] for v in ring]);area+=abs(signed) if index==0 else -abs(signed)
                rings.append(transformed)
            parts.append(rings)
        output.append(dict(id=row['bldg_id'],geometry=dict(type='MultiPolygon',coordinates=parts),geodesic_area_m2=area,height_m=None,source_attributes={k:row.get(k) for k in ('stories','no_stories','z_coord')}))
    north=forward.transform(lon,lat+.001,errcheck=True)
    result=dict(runtime={r['name']:metadata.version(r['name']) for r in pins},proj_version=__proj_version__,crs_wkt=local.to_wkt(),reference=dict(latitude=lat,longitude=lon,meaning='Candidate query reference, not surveyed project/site position'),reference_xy_m=forward.transform(lon,lat,errcheck=True),north_probe_xy_m=north,maximum_roundtrip_error_deg=error,features=output,site_selected=False,three_dimensional_context_ready=False,design_accepted=False)
    Path(out).write_text(json.dumps(result,indent=2),encoding='utf-8');return result

if __name__=='__main__':print(json.dumps({'features':len(run(sys.argv[1],sys.argv[2])['features'])}))

"""Source-bound manual raster points using pinned upstream axis calibration."""
import argparse
import csv
import importlib.util
import json
import math
from importlib.metadata import version
from pathlib import Path

from PIL import Image
from .cli import digest
from .workspace import allowed

ROOT=Path(__file__).resolve().parents[2]
UPSTREAM=ROOT/'third_party/scientific-plot-digitizer/digitize_plot.py'
UPSTREAM_SHA256='04c988d25acf72c127d9b575a44df22c8823a1d8d4f02b5c3c4f96405050834c'


def upstream():
    if digest(UPSTREAM)!=UPSTREAM_SHA256:raise ValueError('Pinned upstream digitizer changed')
    spec=importlib.util.spec_from_file_location('bsa_pinned_raster_digitizer',UPSTREAM)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.pixel_to_data


def number(value):
    if type(value) not in (int,float) or not math.isfinite(value):raise ValueError('Finite numerical values required')
    return value


def run(project,out):
    project,out=Path(project).resolve(),Path(out).resolve()
    if not allowed(project) or not allowed(out):raise ValueError('Explicit selected workspace required')
    if out.exists():raise ValueError('New output directory required')
    before=digest(project);data=json.loads(project.read_text(encoding='utf-8-sig'))
    if set(data)!={'source','image','axes','calibration','pixel_uncertainty','checks','points'}:raise ValueError('Exact raster point project fields required')
    axes=data['axes']
    if not isinstance(axes,dict) or set(axes)!={'x','y'}:raise ValueError('Explicit axis quantities and units required')
    for axis in axes.values():
        if not isinstance(axis,dict) or set(axis)!={'quantity','unit'} or any(not isinstance(v,str) or not v.strip() for v in axis.values()):raise ValueError('Nonempty axis quantity/unit required')
    pins={str(project):before,str(Path(__file__)):digest(Path(__file__)),str(UPSTREAM):UPSTREAM_SHA256,
          str(ROOT/'src/bsa/workspace.py'):digest(ROOT/'src/bsa/workspace.py')}
    for name in ('source','image'):
        entry=data[name]
        if set(entry)!=({'path','sha256','locator'} if name=='source' else {'path','sha256'}):raise ValueError('Exact source/image identity required')
        if not isinstance(entry['path'],str) or Path(entry['path']).is_absolute():raise ValueError('Relative source/image path required')
        path=(project.parent/entry['path']).resolve()
        if not allowed(path) or not path.is_file() or digest(path)!=entry['sha256']:raise ValueError('Source/image missing, changed or outside workspace')
        if name=='source' and (not isinstance(entry['locator'],str) or not entry['locator'].strip()):raise ValueError('Source locator required')
        if out==path or out in path.parents:raise ValueError('Output must preserve source inputs')
        pins[str(path)]=entry['sha256']
        if name=='image':image_path=path
    if out==project or out in project.parents:raise ValueError('Output must preserve project')
    with Image.open(image_path) as image:width,height=image.size
    def pixel(value):
        if not isinstance(value,list) or len(value)!=2:raise ValueError('Pixel pair required')
        x,y=map(number,value)
        if not (0<=x<width and 0<=y<height):raise ValueError('Pixel outside original image')
        return x,y
    cal=data['calibration']
    if set(cal)!={'x1','x2','y1','y2','x_scale','y_scale'}:raise ValueError('Exact axis calibration required')
    for key in ('x1','x2','y1','y2'):
        if set(cal[key])!={'pixel','value'}:raise ValueError('Calibration pixel/value required')
        pixel(cal[key]['pixel']);number(cal[key]['value'])
    for axis in ('x','y'):
        a,b=cal[axis+'1'],cal[axis+'2'];index=0 if axis=='x' else 1
        if cal[axis+'_scale'] not in ('linear','log10') or a['value']==b['value'] or a['pixel'][index]==b['pixel'][index]:raise ValueError('Distinct supported axis calibration required')
        if a['pixel'][1-index]!=b['pixel'][1-index]:raise ValueError('Axis-aligned calibration only; rectify rotated/skewed images separately')
    uncertainty=number(data['pixel_uncertainty'])
    if uncertainty<=0:raise ValueError('Positive declared pixel uncertainty required')
    convert=upstream()
    xmin,xmax=sorted([cal['x1']['pixel'][0],cal['x2']['pixel'][0]])
    ymin,ymax=sorted([cal['y1']['pixel'][1],cal['y2']['pixel'][1]])
    if uncertainty>=min(xmax-xmin,ymax-ymin)/2:raise ValueError('Pixel uncertainty overwhelms calibrated domain')
    def read(value):
        x,y=pixel(value)
        if not (xmin<=x<=xmax and ymin<=y<=ymax):raise ValueError('Point outside calibrated domain; no extrapolation')
        center=convert(x,y,cal)
        corners=[convert(px,py,cal) for px in (max(xmin,x-uncertainty),min(xmax,x+uncertainty)) for py in (max(ymin,y-uncertainty),min(ymax,y+uncertainty))]
        for pair in [center,*corners]:
            if any(not math.isfinite(v) for v in pair):raise ValueError('Nonfinite converted value')
        return dict(pixel=value,x=center[0],y=center[1],x_range=[min(v[0] for v in corners),max(v[0] for v in corners)],y_range=[min(v[1] for v in corners),max(v[1] for v in corners)])
    checks=data['checks']
    if not isinstance(checks,list) or len(checks)<2:raise ValueError('At least two held-out tick checks required')
    rows=[];held_x=False;held_y=False
    for check in checks:
        if set(check)!={'pixel','expected'} or not isinstance(check['expected'],list) or len(check['expected'])!=2:raise ValueError('Held-out pixel/expected pair required')
        row=read(check['pixel']);expected=list(map(number,check['expected']))
        held_x |= check['pixel'][0] not in (xmin,xmax)
        held_y |= check['pixel'][1] not in (ymin,ymax)
        if any(not row[axis+'_range'][0]<=v<=row[axis+'_range'][1] for axis,v in zip(('x','y'),expected)):raise ValueError('Held-out tick differs beyond declared pixel uncertainty')
        rows.append(dict(**row,expected=expected))
    if not held_x or not held_y:raise ValueError('Both axes need held-out interior ticks')
    points=data['points']
    if not isinstance(points,list) or not points:raise ValueError('Nonempty explicitly selected points required')
    result_points=[];ids=set()
    for point in points:
        if set(point)!={'id','pixel','series','interpretation'}:raise ValueError('Explicit point identity, series and interpretation required')
        if any(not isinstance(point[k],str) or not point[k].strip() for k in ('id','series','interpretation')) or point['id'] in ids:raise ValueError('Unique nonempty point metadata required')
        ids.add(point['id']);result_points.append(dict(**read(point['pixel']),id=point['id'],series=point['series'],interpretation=point['interpretation']))
    if any(not Path(p).is_file() or digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Source or method changed during reading')
    result=dict(inputs=pins,axes=axes,calibration=cal,pixel_uncertainty=uncertainty,checks=rows,points=result_points,
        runtime_dependencies={name:version(name) for name in ('numpy','Pillow')},
        source_locator=data['source']['locator'],axis_tick_checks_pass=True,source_image_derivation_verified=False,curve_identity_verified=False,design_accepted=False,
        scope='Declared manual pixels converted by pinned upstream axes; uncertainty covers declared pixel displacement only, not curve identification, scan distortion, source authenticity or engineering acceptance')
    out.mkdir(parents=True)
    (out/'points.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    with (out/'points.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.writer(stream);writer.writerow(['ID','Series',axes['x']['quantity']+' ['+axes['x']['unit']+']',axes['y']['quantity']+' ['+axes['y']['unit']+']','x low','x high','y low','y high'])
        for row in result_points:writer.writerow([row['id'],row['series'],row['x'],row['y'],*row['x_range'],*row['y_range']])
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('project');parser.add_argument('--out',required=True)
    args=parser.parse_args();result=run(args.project,args.out)
    print(len(result['points']),'declared pixels converted; curve identity and engineering acceptance remain unverified')
    return 0


if __name__=='__main__':raise SystemExit(main())

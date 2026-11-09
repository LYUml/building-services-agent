"""Record a screened curve on a new IFC copy and rebind its hydraulic template."""
import argparse
import copy
import json
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from .ifc_circulation_checks import verify_producer
from .circulation_pump_design import selected_input
from .water_binding import run as bind

PSET='BSA_ScreenedPumpCurve'


def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def physical(data):
    data=copy.deepcopy(data);data.pop('sources',None)
    for group in ('reservoirs','junctions','pipes','pumps'):
        for row in data[group]:row.pop('source',None)
    return data


def run(producer,screening,template,binding,catalogue,out):
    import ifcopenshell
    import ifcopenshell.api as api
    import ifcopenshell.util.element as element
    producer,screening,out=(Path(p).resolve() for p in (producer,screening,out))
    files=[Path(p).resolve() for p in (template,binding,catalogue)]
    if any(out==p or out in p.parents or out.is_relative_to(p) for p in (producer,screening)) or any(out==p or out in p.parents for p in files):raise ProjectError('output must be separate from producers and source files')
    hashes={str(p):digest(p) for p in files}
    native=verify_producer(producer,*files[:2])
    selected=selected_input(screening,producer/'network-input.json',files[2]);screen_hash=digest(screening/'pump-screening.json')
    target=read(selected);base=read(files[0]);links=read(files[1]);selection=read(screening/'pump-screening.json')['selected']
    if len(target['pumps'])!=1 or len(base['pumps'])!=1 or target['pumps'][0]['id']!=base['pumps'][0]['id']:raise ProjectError('single identical bound pump required')
    pump=target['pumps'][0];source=pump['source']
    if source in base['sources']:raise ProjectError('selected source collides with original template')
    revised=copy.deepcopy(base);revised['sources'][source]=target['sources'][source]
    revised['pumps'][0].update(head_curve=pump['head_curve'],source=source)
    guid=links['pumps'][pump['id']]['element_guid']
    model=ifcopenshell.open(str(producer/'model.ifc'));obj=model.by_guid(guid)
    if not obj.is_a('IfcPump') or PSET in element.get_psets(obj):raise ProjectError('unambiguous pump without reserved selection metadata required')
    properties=dict(CandidateId=selection['id'],HeadCurve_m3_s_m=json.dumps(pump['head_curve'],separators=(',',':')),
                    Source=target['sources'][source],ScreeningReportSHA256=screen_hash,
                    Scope='Screened hydraulic curve only; physical product, motor, efficiency and NPSH not established')
    out.mkdir(parents=True,exist_ok=False);new_template=out/'selected-template.json';new_template.write_text(json.dumps(revised,indent=2),encoding='utf-8')
    pset=api.run('pset.add_pset',model,product=obj,name=PSET);api.run('pset.edit_pset',model,pset=pset,properties=properties)
    new_ifc=out/'selected-model.ifc';model.write(str(new_ifc))
    saved=element.get_psets(ifcopenshell.open(str(new_ifc)).by_guid(guid)).get(PSET,{})
    if any(saved.get(k)!=v for k,v in properties.items()):raise ProjectError('saved selected curve metadata differs')
    rebound=bind(new_template,new_ifc,files[1],out/'rebound')
    if physical(read(out/'rebound/network-input.json'))!=physical(target):raise ProjectError('rebound selected network differs from screened physical scenario')
    if verify_producer(producer,*files[:2])!=native or selected_input(screening,producer/'network-input.json',files[2])!=selected or digest(screening/'pump-screening.json')!=screen_hash or any(digest(Path(p))!=h for p,h in hashes.items()):raise ProjectError('selection inputs changed')
    result=dict(inputs=hashes,upstream_binding=native,screening_report_sha256=screen_hash,candidate_id=selection['id'],pump_guid=guid,
                saved_curve_properties_match=True,screened_physical_input_match=True,calculated_checks_pass=rebound['calculated_checks_pass'],design_accepted=False,
                pending=['manufacturer pump shape, speed, efficiency, motor and NPSH','physical fitting/clash/visual acceptance','fresh combined thermal/regulatory delivery checks and full engineering acceptance'])
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'selected-pump-ifc.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('producer','screening','template','binding','catalogue','out'):parser.add_argument('--'+name,required=True,type=Path)
    a=parser.parse_args();r=run(a.producer,a.screening,a.template,a.binding,a.catalogue,a.out)
    print(json.dumps({k:r[k] for k in ('candidate_id','calculated_checks_pass','design_accepted')}));return 0 if r['calculated_checks_pass'] else 2


if __name__=='__main__':raise SystemExit(main())

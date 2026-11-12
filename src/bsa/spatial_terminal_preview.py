"""Source-bound multi-view preview of terminal envelopes against retained IFC context."""
import argparse
import json
from pathlib import Path
import numpy as np
import ifcopenshell
from . import spatial_terminal_ifc as author,ifc_preview
from .cli import digest
from .module_contract import read_json
from .workspace import allowed


def selection(source):
    report=author.verify(source.parent)
    if source.name!='terminal-ifc.json':raise ValueError('Exact verified terminal model report required')
    model=ifcopenshell.open(str(source.parent/'Terminal Envelope Study.ifc'))
    terminals=sorted(report['terminals'],key=lambda r:r['id']);foreground=[r['guid'] for r in terminals]
    context=[o.GlobalId for o in [*model.by_type('IfcSpace'),*model.by_type('IfcElement')] if o.GlobalId not in foreground and o.Representation]
    labels={r['guid']:f'T{i:02}' for i,r in enumerate(terminals,1)}
    bindings={labels[r['guid']]:dict(terminal_id=r['id'],guid=r['guid'],space_guid=r['space_guid']) for r in terminals}
    pins=dict(report['inputs']);pins[str(source)]=digest(source);target=source.parent/'Terminal Envelope Study.ifc';pins[str(target)]=digest(target)
    for module in (author,ifc_preview):pins[str(Path(module.__file__).resolve())]=digest(Path(module.__file__))
    pins[str(Path(__file__).resolve())]=digest(Path(__file__))
    return target,foreground,context,labels,bindings,pins


def run(source,out):
    source,out=[Path(p).resolve() for p in (source,out)]
    if not allowed(source) or not allowed(out) or out.exists():raise ValueError('Selected verified source and fresh preview output required')
    before=digest(source);target,foreground,context,labels,bindings,pins=selection(source)
    if pins[str(source)]!=before or any(out==Path(p) or out in Path(p).parents for p in pins):raise ValueError('Preview source changed or output overlaps sources')
    preview=ifc_preview.run(target,foreground[0],out/'overview',foreground[1:],context_guids=context,element_labels=labels)
    author.verify(source.parent)
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Preview source/method changed')
    result=dict(terminal_ifc=str(source),inputs=pins,bindings=bindings,preview=preview,preview_report_sha256=digest(out/'overview/preview.json'),visual_review='pending',design_accepted=False,
        scope='Native saved terminal envelopes in solid blue against transparent retained represented IFC context;short labels bind to source terminal IDs. No physical installation or complete engineering acceptance')
    (out/'terminal-preview.json').write_text(json.dumps(result,indent=2),encoding='utf-8');verify(out);return result


def verify(folder):
    folder=Path(folder).resolve()
    if not allowed(folder):raise ValueError('Selected preview workspace required')
    result=read_json(folder/'terminal-preview.json')
    if set(result)!={'terminal_ifc','inputs','bindings','preview','preview_report_sha256','visual_review','design_accepted','scope'} or result['design_accepted'] is not False or result['visual_review']!='pending':raise ValueError('Exact unaccepted preview evidence required')
    source=Path(result['terminal_ifc'])
    if not allowed(source):raise ValueError('Selected original model required')
    target,foreground,context,labels,bindings,pins=selection(source);preview=read_json(folder/'overview/preview.json')
    if result['inputs']!=pins or result['bindings']!=bindings or any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Preview source/method/identity bindings differ')
    if result['preview_report_sha256']!=digest(folder/'overview/preview.json') or result['preview']!=preview or preview['preview_sha256']!=digest(folder/'overview/preview.png'):raise ValueError('Preview output pins differ')
    if preview['ifc']!=str(target) or preview['ifc_sha256']!=digest(target) or preview['included_element_guids']!=foreground+context or preview['context_element_guids']!=context or preview['element_labels']!=labels:raise ValueError('Preview replaced selected source/roles')
    vertices=[];triangles=0;ports=[];context_ports=[];omitted=None
    for guid in foreground+context:
        v,f,p,missing=ifc_preview.extract(target,guid);vertices.append(v);triangles+=len(f)
        if omitted is None:omitted=[g for g in missing if g not in foreground+context]
        if guid in context:context_ports+=p
        else:ports+=p
    cloud=np.concatenate(vertices)
    if preview['vertices']!=len(cloud) or preview['triangles']!=triangles or preview['world_bounds_m']!=[cloud.min(axis=0).tolist(),cloud.max(axis=0).tolist()]:raise ValueError('Preview mesh inventory differs from saved native geometry')
    if preview['ports']!=ports or preview['context_ports_not_drawn']!=context_ports or preview['omitted_element_guids']!=omitted or preview['display_origin_m']!=((cloud.min(axis=0)+cloud.max(axis=0))/2).tolist():raise ValueError('Preview port/context/origin replay differs')
    versions={n:ifc_preview.importlib.metadata.version(n) for n in ('ifcopenshell','matplotlib','numpy')}
    if preview['runtime']!=versions or preview['design_accepted'] is not False or preview['visual_review']!='pending':raise ValueError('Preview runtime/acceptance differs')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source');parser.add_argument('--out',required=True)
    args=parser.parse_args();run(args.source,args.out)

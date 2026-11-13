"""Compose existing native network projection, review layout and AutoCAD delivery."""
import argparse
import json
import math
from pathlib import Path
import numpy as np
import ezdxf
from . import source_network_drawing as drawing,source_network_analysis as analysis,ifc_native as native
from . import cad_overlay,cad_sheet,cad_intake,native_cad
from . import circular_geometry
from .cli import digest
from .workspace import allowed


def checked_projection(folder):
    folder=Path(folder).resolve()
    if not allowed(folder):raise ValueError('Host-selected projection workspace required')
    data=json.loads((folder/'drawing.json').read_text())
    if set(data['artifacts'])!={'Supply Network Plan.dxf','sheet.json'}:
        raise ValueError('Exact native projection artifacts required')
    for name,sha in data['artifacts'].items():
        if digest(folder/name)!=sha:raise ValueError('Projection artifact changed')
    for name,sha in data['inputs'].items():
        if not allowed(name) or digest(Path(name))!=sha:raise ValueError('Projection source/method changed')
    return data


def compose(folder,scale=None):
    """Deterministic annotation-only composition; no source geometry replacement."""
    folder=Path(folder);data=checked_projection(folder)
    lo=np.min([r['bounds_xy_m'][0] for r in data['products']],axis=0)
    hi=np.max([r['bounds_xy_m'][1] for r in data['products']],axis=0)
    if scale is None:scale=25*math.ceil(max((hi[0]-lo[0]+2)*1000/277,(hi[1]-lo[1]+2)*1000/165)/25)
    if type(scale) not in (int,float) or not math.isfinite(scale) or scale<=0:
        raise ValueError('Finite positive review-sheet scale required')
    doc=ezdxf.readfile(folder/'Supply Network Plan.dxf');msp=doc.modelspace()
    for e in list(msp.query('TEXT')):msp.delete_entity(e)
    for name,font in [('BSA_REVIEW_TITLE','arialbd.ttf'),('BSA_REVIEW_NOTES','arial.ttf')]:
        if name in doc.styles:raise ValueError('Unexpected prior review style')
        doc.styles.new(name,dxfattribs={'font':font})
    notes=[('Supply Network Geometry',.026667,.004,'BSA_REVIEW_TITLE'),
        (f'Source-model projection | 1:{scale:g} | metres',.021,.002333,'BSA_REVIEW_NOTES'),
        ('Scale, elevation and wall gauge follow recorded study assumptions.',.017,.002333,'BSA_REVIEW_NOTES'),
        ('Pressure, product selection and installation details: review pending.',.013,.002333,'BSA_REVIEW_NOTES')]
    for text,y,height,style in notes:
        msp.add_text(text,dxfattribs={'height':height*scale,'insert':(lo[0],hi[1]+y*scale),'style':style})
    msp.add_text('1 m model reference',dxfattribs={'height':.001667*scale,'insert':(lo[0]+1.3,lo[1]-1.1),'style':'BSA_REVIEW_NOTES'})
    sheet=json.loads((folder/'sheet.json').read_text());sheet.update(scale_denominator=float(scale),
        window_drawing_units=[float(lo[0]-1),float(lo[1]-2),float(hi[0]+1),float(hi[1]+.033*scale)],
        source='Automatic review composition from unchanged source-native contours; physical source scale remains unconfirmed')
    native.validate_settings(sheet)
    from ezdxf import bbox
    b=bbox.extents(msp,fast=True);w=sheet['window_drawing_units']
    if not (w[0]<=b.extmin.x<=b.extmax.x<=w[2] and w[1]<=b.extmin.y<=b.extmax.y<=w[3]):
        raise ValueError('Review annotations exceed declared fixed-scale window')
    return doc,sheet,data


def methods():
    return [Path(m.__file__).resolve() for m in (drawing,analysis,native,cad_overlay,cad_sheet,cad_intake,native_cad,circular_geometry)]+[Path(__file__).resolve()]


def audit_projection(folder,source):
    """Reconstruct projected material from the original saved IFC, not output hashes."""
    import ifcopenshell
    import ifcopenshell.geom
    from shapely import Polygon,union_all
    from .circular_geometry import configure
    data=checked_projection(folder);case=json.loads((Path(source)/'analysis.json').read_text())
    model=ifcopenshell.open(str(Path(case['source'])/'Supply Network.ifc'))
    objects=model.by_type('IfcDistributionElement');guids={o.GlobalId for o in objects}
    if guids!={r['guid'] for r in data['products']} or data['product_count']!=len(objects):
        raise ValueError('Projection product/source coverage differs')
    doc=ezdxf.readfile(Path(folder)/'Supply Network Plan.dxf');native.validate_contours(doc);groups={}
    for e in doc.modelspace().query('LWPOLYLINE'):
        guid=e.get_xdata('BSA_IFC')[0].value;groups.setdefault(guid,[]).append(Polygon(list(e.get_points('xy'))))
    if set(groups)!=guids:raise ValueError('Projected contour identities differ')
    settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True);configure(settings)
    for obj in objects:
        shape=ifcopenshell.geom.create_shape(settings,obj)
        expected=union_all(drawing.project(np.array(shape.geometry.verts).reshape(-1,3),np.array(shape.geometry.faces).reshape(-1,3)))
        actual=Polygon()
        for ring in groups[obj.GlobalId]:actual=actual.symmetric_difference(ring)
        g=drawing.GRID_M
        if actual.is_empty or not actual.is_valid or not actual.buffer(2*g).covers(expected) or not expected.buffer(2*g).covers(actual) or abs(actual.area-expected.area)>2*expected.length*g+4*g*g:
            raise ValueError('Saved projected contours differ from original native material')
    if data['original_requirement_ids']!=case['original_requirement_ids']:
        raise ValueError('Original requirement identities differ')


def measure_pdf(path,doc,sheet):
    paper,lines=cad_sheet.pdf_lines(path);w=sheet['window_drawing_units'];den=sheet['scale_denominator']
    if any(abs(a-b)>.2 for a,b in zip(paper,[297,210])):raise ValueError('Expected A4 landscape PDF')
    refs=[e for e in doc.modelspace().query('LINE[layer=="BSA_SECTION_REFERENCE"]') if e.has_xdata('BSA_IFC') and e.get_xdata('BSA_IFC')[0].value==sheet['reference_ifc_guid']]
    if len(refs)!=1:raise ValueError('Unique model reference required')
    width=(w[2]-w[0])*1000/den;height=(w[3]-w[1])*1000/den
    def point(p):return [(paper[0]-width)/2+(p.x-w[0])*1000/den,(paper[1]-height)/2+(p.y-w[1])*1000/den]
    a,b=point(refs[0].dxf.start),point(refs[0].dxf.end)
    matches=[(x,y) for x,y in lines if min(max(math.dist(a,x),math.dist(b,y)),max(math.dist(a,y),math.dist(b,x)))<=sheet['pdf_tolerance_mm']]
    if not matches:raise ValueError('Saved PDF reference scale/position differs')
    return dict(reference_expected_mm=math.dist(a,b),reference_measured_mm=math.dist(*matches[0]))


def run(source,out,autocad,scale=None):
    source,out,autocad=map(lambda p:Path(p).resolve(),(source,out,autocad))
    if not allowed(source) or not allowed(out) or out.exists() or out.is_relative_to(source) or source.is_relative_to(out) or not autocad.is_file():
        raise ValueError('Fresh selected delivery workspace and explicit existing AutoCAD required')
    pins={str(p):digest(p) for p in [source/'analysis.json',autocad,*methods()]}
    drawing.run(source,out/'projection')
    doc,sheet,project=compose(out/'projection',scale);layout=out/'layout';layout.mkdir()
    doc.saveas(layout/'Supply Network Geometry.dxf');(layout/'sheet.json').write_text(json.dumps(sheet,indent=2))
    result=native.run(layout/'Supply Network Geometry.dxf',layout/'sheet.json',out/'native',autocad)
    calibration=measure_pdf(out/'native/sheet.pdf',doc,sheet)
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Delivery source/runtime/method changed')
    record=dict(inputs=pins,source_analysis=str(source),autocad=str(autocad),scale_denominator=sheet['scale_denominator'],
        original_requirement_ids=project['original_requirement_ids'],product_count=project['product_count'],
        native_reopen_pass=result['native_reopen_pass'],pdf_reference_pass=result['plot']['pdf_reference_pass'],
        calibration=calibration,
        plot_visual_review='pending',pressure_budget_complete=False,design_accepted=False,
        scope='Composed source-native geometry-study delivery only; actual visual review, physical scale, products, installation and complete engineering acceptance remain separate')
    record['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'delivery.json').write_text(json.dumps(record,indent=2));return record


def verify(out):
    out=Path(out).resolve()
    if not allowed(out):raise ValueError('Host-selected delivery required')
    record=json.loads((out/'delivery.json').read_text());source=Path(record['source_analysis'])
    if not allowed(source):raise ValueError('Host-selected source analysis required')
    expected={str(p):digest(p) for p in [source/'analysis.json',Path(record['autocad']),*methods()]}
    if expected!=record['inputs']:raise ValueError('Delivery inputs/methods changed')
    required={'projection/drawing.json','projection/Supply Network Plan.dxf','projection/sheet.json',
        'layout/Supply Network Geometry.dxf','layout/sheet.json','native/section.dwg',
        'native/native-verification.json','native/native-reopen/source-export.dxf','native/sheet.pdf'}
    if not required<=set(record['artifacts']):raise ValueError('Required delivery artifact coverage missing')
    for name,sha in record['artifacts'].items():
        path=(out/name).resolve()
        if not path.is_relative_to(out) or digest(path)!=sha:raise ValueError('Delivery artifact changed')
    analysis.verify(source)
    audit_projection(out/'projection',source)
    doc,sheet,project=compose(out/'projection',record['scale_denominator'])
    def plain(v):
        if isinstance(v,dict):return {k:plain(x) for k,x in v.items()}
        if isinstance(v,list):return [plain(x) for x in v]
        return v.item() if isinstance(v,np.generic) else v
    if not cad_overlay.equivalent(plain(cad_overlay.snapshot(doc)),plain(cad_overlay.snapshot(ezdxf.readfile(out/'layout/Supply Network Geometry.dxf')))) or sheet!=json.loads((out/'layout/sheet.json').read_text()):
        raise ValueError('Source-reconstructed layout differs')
    checks=native.verify_dxf(out/'layout/Supply Network Geometry.dxf',out/'native/native-reopen/source-export.dxf')
    proof=json.loads((out/'native/native-verification.json').read_text())
    stage_required={'section.dwg','sheet.pdf','input.dxf','sheet.json','native-reopen/source-export.dxf'}
    if not stage_required<=set(proof['artifacts']):raise ValueError('Required native stage artifacts missing')
    for name,sha in proof['artifacts'].items():
        path=(out/'native'/name).resolve()
        if not path.is_relative_to(out/'native') or digest(path)!=sha:raise ValueError('Native stage artifact differs')
    if proof['inputs']!={str(p):digest(p) for p in [out/'layout/Supply Network Geometry.dxf',out/'layout/sheet.json']} or proof['checks']!=checks or proof['engine']!=record['autocad'] or proof['engine_sha256']!=digest(Path(record['autocad'])) or proof['dwg_sha256']!=digest(out/'native/section.dwg') or proof['plot']['pdf_sha256']!=digest(out/'native/sheet.pdf') or proof['native_reopen_pass'] is not True or proof['inputs_unchanged'] is not True or proof['plot']['dwg_unchanged'] is not True:
        raise ValueError('Native producer/runtime/input correspondence differs')
    if measure_pdf(out/'native/sheet.pdf',doc,sheet)!=record['calibration']:
        raise ValueError('PDF calibration replay differs')
    if not all(v for v in checks.values() if isinstance(v,bool)) or project['original_requirement_ids']!=record['original_requirement_ids'] or project['product_count']!=record['product_count'] or not record['native_reopen_pass'] or not record['pdf_reference_pass'] or record['design_accepted'] is not False or record['pressure_budget_complete'] is not False or record['plot_visual_review']!='pending':
        raise ValueError('Native/requirement or acceptance correspondence differs')
    return dict(integrity_pass=True,product_count=project['product_count'],requirements=len(record['original_requirement_ids']),native_reopen_pass=True,plot_visual_review='pending',design_accepted=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    a=s.add_parser('run');a.add_argument('source');a.add_argument('--out',required=True);a.add_argument('--autocad',required=True);a.add_argument('--scale',type=float)
    s.add_parser('verify').add_argument('out');a=p.parse_args()
    r=run(a.source,a.out,a.autocad,a.scale) if a.command=='run' else verify(a.out)
    print(json.dumps({k:r[k] for k in ('product_count','native_reopen_pass','plot_visual_review','design_accepted')},indent=2));raise SystemExit(2)

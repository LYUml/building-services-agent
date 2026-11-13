"""GUID-linked XY silhouettes of a verified source-native network, not installation drawings."""
import argparse
import importlib.metadata as metadata
import json
import math
from pathlib import Path
import numpy as np
from shapely import Polygon,union_all
from .cli import digest
from .workspace import allowed
from . import source_network_analysis as analysis

GRID_M=1e-8

def project(vertices,faces):
    v=np.asarray(vertices,dtype=float);f=np.asarray(faces)
    if v.ndim!=2 or v.shape[1]!=3 or not np.isfinite(v).all() or f.ndim!=2 or f.shape[1]!=3 or not np.issubdtype(f.dtype,np.integer) or np.any(f<0) or np.any(f>=len(v)):
        raise ValueError('Finite native vertices and triangular index faces required')
    pieces=[Polygon(v[row,:2]) for row in f]
    pieces=[p for p in pieces if p.area>0]
    raw=union_all(pieces,grid_size=0)
    shape=union_all(pieces,grid_size=GRID_M)
    if shape.is_empty or not shape.is_valid or shape.geom_type not in ('Polygon','MultiPolygon'):
        raise ValueError('Valid positive polygonal XY silhouette required')
    # GEOS discrete Hausdorff compares polygon ring vertices, including spurious
    # internal seam boundaries. Bound the filled sets by mutual offset coverage.
    if not raw.buffer(2*GRID_M).covers(shape) or not shape.buffer(2*GRID_M).covers(raw) or abs(shape.area-raw.area)>2*raw.length*GRID_M+4*GRID_M**2:
        raise ValueError('Projection cleanup exceeds numerical displacement/area bound')
    return list(shape.geoms) if shape.geom_type=='MultiPolygon' else [shape]


def run(source,out):
    import ifcopenshell
    import ifcopenshell.geom
    import ifcopenshell.util.unit
    import ezdxf
    from .circular_geometry import configure
    source,out=Path(source).resolve(),Path(out).resolve()
    if not allowed(source) or not allowed(out) or out.exists() or out.is_relative_to(source) or source.is_relative_to(out):
        raise ValueError('Fresh selected workspace outside source analysis required')
    if metadata.version('shapely')!='2.2.0':raise ValueError('Pinned Shapely2.2.0 required')
    analysis.verify(source);data=json.loads((source/'analysis.json').read_text())
    model_path=Path(data['source'])/'Supply Network.ifc'
    pins={str(p):digest(p) for p in (model_path,source/'analysis.json',Path(__file__))}
    model=ifcopenshell.open(str(model_path))
    if ifcopenshell.util.unit.calculate_unit_scale(model)!=1:raise ValueError('Verified metre model required')
    objects=sorted(model.by_type('IfcDistributionElement'),key=lambda o:o.GlobalId)
    if {o.GlobalId for o in objects}!={r['guid'] for r in data['products']}:
        raise ValueError('Complete analysed/native product identity required')
    settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True);configure(settings)
    doc=ezdxf.new('R2018');doc.units=6;doc.appids.new('BSA_IFC');doc.layers.new('BSA_NETWORK_OUTLINE');doc.layers.new('BSA_SECTION_REFERENCE');msp=doc.modelspace();rows=[]
    for obj in objects:
        shape=ifcopenshell.geom.create_shape(settings,obj);mesh=shape.geometry
        vertices=np.asarray(mesh.verts).reshape(-1,3);faces=np.asarray(mesh.faces).reshape(-1,3)
        polygons=project(vertices,faces);handles=[]
        for p in polygons:
            for ring in [p.exterior,*p.interiors]:
                entity=msp.add_lwpolyline(list(ring.coords)[:-1],close=True,dxfattribs={'layer':'BSA_NETWORK_OUTLINE'})
                entity.set_xdata('BSA_IFC',[(1000,obj.GlobalId)]);handles.append(entity.dxf.handle)
        rows.append(dict(guid=obj.GlobalId,name=obj.Name,ifc_class=obj.is_a(),handles=handles,
            projected_area_m2=sum(p.area for p in polygons),bounds_xy_m=[vertices[:,:2].min(axis=0).tolist(),vertices[:,:2].max(axis=0).tolist()]))
    lo=np.min([r['bounds_xy_m'][0] for r in rows],axis=0);hi=np.max([r['bounds_xy_m'][1] for r in rows],axis=0)
    scale=50*math.ceil(max((hi[0]-lo[0]+4)/.25,(hi[1]-lo[1]+8)/.16)/50)
    reference=msp.add_line((lo[0],lo[1]-1),(lo[0]+1,lo[1]-1),dxfattribs={'layer':'BSA_SECTION_REFERENCE'})
    reference.set_xdata('BSA_IFC',[(1000,objects[0].GlobalId)])
    for i,text in enumerate(['Supply Network - Geometry Study','XY silhouette; source scale/elevation/gauge assumptions retained','Not an installation layout; pressure, products and engineering review pending']):
        msp.add_text(text,dxfattribs={'height':scale*.0025,'insert':(lo[0],hi[1]+2+i*scale*.0035)})
    out.mkdir(parents=True);drawing=out/'Supply Network Plan.dxf';doc.saveas(drawing)
    loaded=ezdxf.readfile(drawing)
    linked={tag.value for e in loaded.modelspace() if e.has_xdata('BSA_IFC') for tag in e.get_xdata('BSA_IFC') if tag.code==1000}
    if linked!={o.GlobalId for o in objects}:raise ValueError('Saved DXF source identity coverage differs')
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Source changed during projection')
    sheet=dict(source='Host-chosen A4 review composition; model-based scale, not surveyed physical scale',window_drawing_units=[float(lo[0]-1),float(lo[1]-2),float(hi[0]+1),float(hi[1]+5+scale*.007)],scale_denominator=scale,reference_ifc_guid=objects[0].GlobalId,reference_layer='BSA_SECTION_REFERENCE',drawing_name='section',pdf_tolerance_mm=.3)
    (out/'sheet.json').write_text(json.dumps(sheet,indent=2))
    record=dict(inputs=pins,products=rows,product_count=len(rows),original_requirement_ids=data['original_requirement_ids'],
        artifacts={p.name:digest(p) for p in (drawing,out/'sheet.json')},runtime={k:metadata.version(k) for k in ('shapely','ifcopenshell','ezdxf')},
        projection_grid_m=GRID_M,maximum_allowed_cleanup_displacement_m=2*GRID_M,
        native_reopen_pass=False,plot_visual_review='pending',design_accepted=False,
        scope='Tessellated native-material XY silhouette only; no hidden-line removal between products, architectural context, insulation/joints, supports, installation dimensions or engineering acceptance.')
    (out/'drawing.json').write_text(json.dumps(record,indent=2));return record


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source');parser.add_argument('--out',required=True);a=parser.parse_args();r=run(a.source,a.out);print(json.dumps(dict(product_count=r['product_count'],design_accepted=False)))

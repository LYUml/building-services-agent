"""Saved source-checked rectangular duct/equipment outer-envelope orthographic sheet."""
import json
import math
from pathlib import Path
from .cli import digest
from .engine import ProjectError


def run(ifc,model,settings,out):
    import ifcopenshell
    import ifcopenshell.geom
    import ifcopenshell.util.element as element
    import numpy as np
    import ezdxf
    from .bim import validate
    from .rectangular_geometry import WALL,specification,verify
    from .circular_geometry import configure
    from .box_geometry import box_mesh
    from .cad_overlay import snapshot,reconcile
    from .ifc_native import identity
    paths=[Path(p).resolve() for p in (ifc,model,settings)];out=Path(out).resolve()
    if out.exists() or any(out==p or out in p.parents for p in paths):raise ProjectError('new separate rectangular drawing output required')
    before={str(p):digest(p) for p in paths}
    source=validate(json.loads(paths[1].read_text(encoding='utf-8-sig')));s=json.loads(paths[2].read_text(encoding='utf-8-sig'))
    if set(s)!={'source','axes','annotation_height_m'} or not isinstance(s['source'],str) or not s['source'].strip() or s['axes'] not in ('XY','XZ','YZ'):raise ProjectError('explicit sourced orthographic axes required')
    height=s['annotation_height_m']
    if type(height) not in (int,float) or not math.isfinite(height) or not .001<=height<=1:raise ProjectError('explicit finite annotation height required')
    axes={'XY':(0,1),'XZ':(0,2),'YZ':(1,2)}[s['axes']]
    saved=ifcopenshell.open(str(paths[0]));physical=saved.by_type('IfcElement')
    if len(physical)!=len(source['devices']):raise ProjectError('complete source/device drawing coverage required')
    native=ifcopenshell.geom.settings();native.set(native.USE_WORLD_COORDS,True);configure(native)
    doc=ezdxf.new('R2018');doc.units=6;doc.appids.new('BSA_IFC');msp=doc.modelspace();rows=[]
    for layer in ('BSA_PIPE_AXIS','BSA_DUCT_OUTLINE','BSA_CONTEXT_OUTLINE','BSA_DUCT_TEXT'):doc.layers.new(layer)
    def link(entity,guid):entity.set_xdata('BSA_IFC',[(1000,guid)])
    for index,d in enumerate(source['devices']):
        objects=[o for o in physical if o.Name==d['id'] and o.is_a(d['ifc_class'])]
        if len(objects)!=1:raise ProjectError('unique native/source element required')
        obj=objects[0];shape=ifcopenshell.geom.create_shape(native,obj);v=np.array(shape.geometry.verts).reshape(-1,3)
        lo,hi=v.min(axis=0),v.max(axis=0)
        if not np.allclose([lo,hi],[d['origin_m'],np.array(d['origin_m'])+d['size_m']],atol=2e-5,rtol=0):raise ProjectError('saved drawing bounds differ from source')
        metadata=element.get_psets(obj).get('BSA_DesignInputs',{})
        if metadata.get('InputID')!=d['id'] or metadata.get('Source')!=source['sources'][d['source']]:raise ProjectError('saved drawing source metadata differs')
        row=dict(guid=obj.GlobalId,name=d['id'],ifc_class=obj.is_a(),bounds_m=[lo.tolist(),hi.tolist()])
        if d.get('body_shape')==WALL:
            verify(obj,d,shape);spec=specification(d);a=spec['matrix'][:3,3];b=a+spec['matrix'][:3,2]*spec['length']
            if math.dist(a[list(axes)],b[list(axes)])<1e-8:raise ProjectError('end-on rectangular duct view unsupported; choose another orthographic plane')
            line=msp.add_line(tuple(a[list(axes)]),tuple(b[list(axes)]),dxfattribs={'layer':'BSA_PIPE_AXIS'});link(line,obj.GlobalId)
            text=f"{d['id']} {spec['width']*1000:g}x{spec['height']*1000:g} mm INSIDE; L {spec['length']:g} m"
            row.update(internal_width_m=spec['width'],internal_height_m=spec['height'],length_m=spec['length'],wall_thickness_m=spec['thickness'],axis_start_m=a.tolist(),axis_end_m=b.tolist())
            layer='BSA_DUCT_OUTLINE'
        elif d.get('body_shape','bounding envelope')=='bounding envelope' and d['ifc_class']=='IfcFan':
            box_mesh(v,np.array(shape.geometry.faces).reshape(-1,3));text=d['id']+' ENVELOPE ONLY';layer='BSA_CONTEXT_OUTLINE'
        else:raise ProjectError('unsupported represented element; do not omit it from rectangular drawing')
        points=[(lo[axes[0]],lo[axes[1]]),(hi[axes[0]],lo[axes[1]]),(hi[axes[0]],hi[axes[1]]),(lo[axes[0]],hi[axes[1]])]
        for a,b in zip(points,points[1:]+points[:1]):link(msp.add_line(a,b,dxfattribs={'layer':layer}),obj.GlobalId)
        if not text.isascii() or any(c in text for c in '\r\n'):raise ProjectError('rectangular drawing requires ASCII single-line IDs')
        # Dedicated note rows avoid representing these as associative dimensions.
        link(msp.add_text(text,dxfattribs={'layer':'BSA_DUCT_TEXT','height':height,'insert':(.5,.5-index*height*1.8)}),obj.GlobalId)
        rows.append(row)
    out.mkdir(parents=True);path=out/'segments.dxf';doc.saveas(path)
    reconcile(snapshot(doc),path)
    if identity(doc)!=identity(ezdxf.readfile(path)):raise ProjectError('saved rectangular DXF GUID inventory differs')
    from .rectangular_drawing_audit import audit
    independent=audit(path,rows,s['axes'],height)
    if any(digest(Path(p))!=sha for p,sha in before.items()):raise ProjectError('rectangular drawing sources changed')
    result=dict(inputs=before,inputs_unchanged=True,elements=rows,independent_saved_audit=independent,complete_represented_coverage=True,axes=s['axes'],annotation_height_m=height,design_accepted=False,
        scope='Source-checked orthographic outer-envelope outlines, centreline and nonassociative text notes only; not hidden-line, fabrication, insulation or installation drawings')
    result['artifacts']={path.name:digest(path)};(out/'drawing.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result

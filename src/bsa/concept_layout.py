"""Concept saved-space layout composition; no thermal simulation or native openings."""
import json
from pathlib import Path
from .cli import digest
from .engine import ProjectError

def geometry_handoff(ifc,source,wwr):
    """Reuse saved-solid extraction and adjacency; do not infer thermal boundaries."""
    import ifcopenshell
    from .concept_spaces import inspect_spaces
    from .thermal_binding import extract
    from .thermal_geometry import boxes,adjacency
    if not isinstance(wwr,(int,float)) or isinstance(wwr,bool) or not 0<wwr<1:
        raise ValueError('explicit fractional concept WWR target required')
    before=digest(ifc)
    inspected=inspect_spaces(ifcopenshell.open(str(ifc)),source)
    binding=dict(spaces=[dict(guid=r['guid'],id=r['id'],source='Concept geometry only; not established thermal boundary') for r in inspected])
    rows,audit=extract(ifc,binding)
    boxes(dict(spaces=rows));pairs=adjacency(rows)
    total_walls=sum(2*(r['size_m'][0]+r['size_m'][1])*r['size_m'][2] for r in rows)
    exterior_walls=total_walls-2*sum(r['area_m2'] for r in pairs if r['axis']!=2)
    horizontal=sum(r['size_m'][0]*r['size_m'][1] for r in rows)
    horizontal_contacts=sum(r['area_m2'] for r in pairs if r['axis']==2)
    from .thermal_windows import FACES,validate as validate_windows,rectangle
    # Explicit design choice: one centred rectangle on each vertical face,
    # equal width/height scale sqrt(WWR). No glazing properties are implied.
    windows=[]
    for row in rows:
        for face,(axis,sign,face_axis) in FACES.items():
            width=row['size_m'][face_axis]*wwr**.5;height=row['size_m'][2]*wwr**.5
            windows.append(dict(id=row['id']+'_'+face.replace('-','Minus').replace('+','Plus'),zone=row['id'],face=face,
                source='Unapproved design decision: one centered rectangle per concept vertical face; equal fractional width/height sqrt(course WWR). Not surveyed windows or IFC opening geometry.',
                offset_m=(row['size_m'][face_axis]-width)/2,sill_m=(row['size_m'][2]-height)/2,width_m=width,height_m=height))
    validate_windows(windows,rows,require_glazing=False)
    window_geometry=[dict(**w,vertices_m=rectangle(w,next(r for r in rows if r['id']==w['zone']))) for w in windows]
    if digest(ifc)!=before:raise ValueError('concept source changed during handoff')
    return dict(ifc_sha256=before,geometry=audit,adjacency=pairs,
        exterior_vertical_face_area_m2=exterior_walls,
        exposed_top_face_area_m2=horizontal-horizontal_contacts,
        exposed_bottom_face_area_m2=horizontal-horizontal_contacts,
        course_wwr_target=wwr,target_glazed_area_m2=exterior_walls*wwr,
        draft_window_rectangles=window_geometry,draft_window_area_m2=sum(w['width_m']*w['height_m'] for w in windows),
        glazing_selected=False,
        modeled_window_area_m2=0,thermal_model_ready=False,design_accepted=False,
        scope='Geometric exterior faces only; not surveyed facade or validated thermal boundaries. Window rectangles are an unapproved layout without glazing, walls or native openings.',
        pending=['site/weather and explicit orientation','actual thermal boundary and clear-height interpretation','window positions and sourced glazing','construction, gains, schedules and HVAC','native annual simulation and deliverable acceptance'])


def validate_settings(settings):
    if not isinstance(settings,dict) or set(settings)!={'source','window_wall_ratio','layout'} or not isinstance(settings['source'],str) or not settings['source'].strip() or settings['layout']!='centered-equal-fraction':
        raise ProjectError('explicit sourced centered concept layout settings required')
    value=settings['window_wall_ratio']
    if type(value) not in (float,int) or not 0<value<1:
        raise ProjectError('concept window wall ratio must be a finite fraction')
    return settings


def run(ifc,project,settings,out):
    ifc,project,settings,out=map(Path,(ifc,project,settings,out))
    pins={str(p):digest(p) for p in (ifc,project,settings)}
    basis=validate_settings(json.loads(settings.read_text(encoding='utf-8-sig')))
    result=geometry_handoff(ifc,json.loads(project.read_text(encoding='utf-8-sig')),basis['window_wall_ratio'])
    result.update(layout_source=basis['source'],layout=basis['layout'],inputs=pins)
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ProjectError('concept layout inputs changed')
    out.mkdir(parents=True,exist_ok=False)
    (out/'geometry-handoff.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result

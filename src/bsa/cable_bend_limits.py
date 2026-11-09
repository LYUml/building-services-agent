"""Source-bound declared cable bend limits; not complete cable selection."""
import argparse
import json
import math
from pathlib import Path

from .cli import digest
from .engine import ProjectError
from .three_phase import fields,ROOT
from .three_phase_ifc import inspect as inspect_geometry


def prepare(basis):
    basis=Path(basis).resolve();p=json.loads(basis.read_text(encoding='utf-8-sig'))
    fields(p,'version sources bends')
    if type(p['version']) is not int or p['version']!=1 or not isinstance(p['sources'],dict) or not p['sources'] or not isinstance(p['bends'],dict):raise ProjectError('version 1, sources and explicit bend map required')
    files={basis,Path(__file__).resolve()}
    for source in p['sources'].values():
        fields(source,'path sha256 locator kind')
        if not isinstance(source['path'],str) or Path(source['path']).is_absolute():raise ProjectError('relative bend-limit source required')
        path=(basis.parent/source['path']).resolve()
        if not path.is_relative_to(basis.parent) or not path.is_file() or digest(path)!=source['sha256']:raise ProjectError('bend-limit source path/hash mismatch')
        if source['kind'] not in ('assumption','manufacturer','course_given','measured','design_target') or not isinstance(source['locator'],str) or not source['locator'].strip():raise ProjectError('explicit bend-limit source kind/locator required')
        files.add(path)
    for row in p['bends'].values():
        fields(row,'product_reference diameter_m diameter_basis condition radius_reference minimum_radius_m source')
        if not isinstance(row['product_reference'],str) or not row['product_reference'].strip() or row['source'] not in p['sources']:raise ProjectError('product reference and known limit source required')
        for key in ('diameter_m','minimum_radius_m'):
            if row[key] is not None and (type(row[key]) not in (int,float) or not math.isfinite(row[key]) or row[key]<=0):raise ProjectError('positive finite SI dimensional value or null required')
        if row['diameter_basis'] not in ('nominal','maximum','unknown') or row['condition'] not in ('installed','during_installation_under_tension','unknown') or row['radius_reference'] not in ('inside','centreline','unknown'):raise ProjectError('explicit diameter, condition and radius-reference enums required')
    return p,files


def evaluate(observed,row,metadata,source):
    """Compare only declared scope; unknown radius datum never implies centreline."""
    radius=observed['bend_radius_m'];envelope=observed['envelope_radius_m']
    diameter=2*envelope;pending=[];failures=[]
    if not metadata.get('ProductReference') or not metadata.get('SourceSHA256'):pending.append('native product/source identity absent')
    else:
        if metadata['ProductReference']!=row['product_reference']:failures.append('native product reference differs from declared product')
        if metadata['SourceSHA256']!=source['sha256']:failures.append('native product source differs from declared source bytes')
    dimension_pass=None
    if row['diameter_m'] is None or row['diameter_basis']=='unknown':pending.append('outside diameter or its basis unresolved')
    else:
        dimension_pass=(math.isclose(diameter,row['diameter_m'],rel_tol=0,abs_tol=1e-6) if row['diameter_basis']=='nominal' else diameter>=row['diameter_m'])
        if not dimension_pass:failures.append('native envelope does not correspond to declared product diameter')
    if row['condition']=='unknown':pending.append('installation condition unresolved')
    elif not metadata.get('InstallationCondition'):pending.append('native installation condition absent')
    elif metadata['InstallationCondition']!=row['condition']:failures.append('native installation condition differs from declared limit condition')
    metric=radius-envelope if row['radius_reference']=='inside' else radius if row['radius_reference']=='centreline' else None
    if metric is None:pending.append('minimum-radius measurement reference unresolved')
    if row['minimum_radius_m'] is None:pending.append('minimum radius unresolved')
    radius_pass=None if metric is None or row['minimum_radius_m'] is None else metric>=row['minimum_radius_m']
    if not pending and radius_pass is False:failures.append('saved bend radius is below the declared minimum')
    status='fail' if failures else 'pending' if pending else 'pass'
    return dict(status=status,product_reference=row['product_reference'],diameter_basis=row['diameter_basis'],condition=row['condition'],
                radius_reference=row['radius_reference'],centreline_radius_m=radius,inside_radius_m=radius-envelope,
                observed_envelope_diameter_m=diameter,declared_diameter_m=row['diameter_m'],diameter_correspondence_pass=dimension_pass,
                evaluated_radius_m=metric,minimum_radius_m=row['minimum_radius_m'],numeric_radius_comparison=radius_pass,
                source_kind=source['kind'],source_record=source,failures=failures,pending=pending)


def run(project,ifc,binding,basis,out):
    import ifcopenshell
    import ifcopenshell.util.element as element
    basis,out=Path(basis).resolve(),Path(out).resolve()
    p,files=prepare(basis)
    geometry=inspect_geometry(project,ifc,binding)
    before={**geometry['inputs'],**{str(f):digest(f) for f in files}}
    if not out.is_relative_to(ROOT) or out.exists() or any(out==Path(f) or out in Path(f).parents for f in before):raise ProjectError('new separate repository output required')
    bends={row['id']:row for row in geometry['lines'] if row['route_geometry'] in ('quarter circle','quarter plus tangent straight','straight plus quarter plus straight')}
    if set(p['bends'])!=set(bends):raise ProjectError('exact selected-system supported-bend coverage required')
    model=ifcopenshell.open(str(ifc));rows=[]
    for name,observed in bends.items():
        row=p['bends'][name]
        metadata=element.get_psets(model.by_guid(observed['element_guid'])).get('BSA_CableSelection',{})
        rows.append(dict(id=name,element_guid=observed['element_guid'],**evaluate(observed,row,metadata,p['sources'][row['source']])))
    status='fail' if any(r['status']=='fail' for r in rows) else 'pending' if not rows or any(r['status']=='pending' for r in rows) else 'pass'
    if any(not Path(f).is_file() or digest(Path(f))!=sha for f,sha in before.items()):raise ProjectError('inputs changed during bend-limit check')
    result=dict(status=status,inputs=before,input_unchanged=True,geometry_correspondence_pass=True,bends=rows,design_accepted=False,
                manufacturer_selection_verified=False,regulatory_compliance='not established',
                scope='Supported saved bends versus declared product diameter/condition/radius-reference limits only; source interpretation, cable selection, ratings, pulling forces, joints and full engineering/regulatory acceptance remain unverified')
    out.mkdir(parents=True);(out/'bend-limits.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('project',type=Path)
    for key in ('ifc','binding','basis','out'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();r=run(a.project,a.ifc,a.binding,a.basis,a.out)
    print(json.dumps({k:r[k] for k in ('status','manufacturer_selection_verified','design_accepted')}))
    raise SystemExit(0 if r['status']=='pass' else 2)

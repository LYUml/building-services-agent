"""Bind checked saved cable radius to the selected HK table; no whole-code acceptance."""
import argparse
import json
import math
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from .three_phase import ROOT,fields
from .three_phase_ifc import inspect
from .regulations import evaluate,source_paths


def prepare(path):
    path=Path(path).resolve();basis=json.loads(path.read_text(encoding='utf-8-sig'))
    fields(basis,'version sources jurisdiction rule_pack edition_decision bends')
    if type(basis['version']) is not int or basis['version']!=1 or not isinstance(basis['sources'],dict) or not basis['sources'] or not isinstance(basis['bends'],dict):raise ProjectError('version 1 sourced cable-rule basis required')
    files={path,Path(__file__).resolve()}
    for record in basis['sources'].values():
        fields(record,'path sha256 locator kind')
        if not isinstance(record['path'],str) or Path(record['path']).is_absolute():raise ProjectError('relative cable-rule source required')
        source=(path.parent/record['path']).resolve()
        if not source.is_relative_to(path.parent) or not source.is_file() or digest(source)!=record['sha256']:raise ProjectError('cable-rule source path/hash mismatch')
        if record['kind'] not in ('assumption','course_given','manufacturer','measured','design_target') or not isinstance(record['locator'],str) or not record['locator'].strip():raise ProjectError('source kind/locator required')
        files.add(source)
    decision=basis['edition_decision'];fields(decision,'edition source')
    if decision['source'] not in basis['sources']:raise ProjectError('known edition-decision source required')
    for row in basis['bends'].values():
        fields(row,'source product_reference overall_diameter_mm overall_diameter_is_actual wiring_scope_confirmed low_voltage pvc_insulated stranded_copper armoured')
        if row['source'] not in basis['sources']:raise ProjectError('known cable-classification source required')
        if row['product_reference'] is not None and (not isinstance(row['product_reference'],str) or not row['product_reference'].strip()):raise ProjectError('product reference or null required')
        for key in ('overall_diameter_is_actual','wiring_scope_confirmed','low_voltage','pvc_insulated','stranded_copper','armoured'):
            if row[key] is not None and type(row[key]) is not bool:raise ProjectError('explicit Boolean classification or null required')
        value=row['overall_diameter_mm']
        if value is not None and (type(value) not in (int,float) or not math.isfinite(value) or value<=0):raise ProjectError('positive sourced overall diameter or null required')
    return basis,files


def run(project,ifc,binding,basis,pack,sources,out):
    import ifcopenshell
    import ifcopenshell.util.element as element
    from . import regulations,cable_bend_rules
    project,ifc,binding,basis,pack,out=[Path(p).resolve() for p in (project,ifc,binding,basis,pack,out)]
    data,files=prepare(basis);rule_pack=json.loads(pack.read_text(encoding='utf-8-sig'))
    if rule_pack.get('jurisdiction')!='HK' or len(rule_pack.get('rules',[]))!=1 or rule_pack['rules'][0].get('method')!='pvc_stranded_copper_bend':raise ProjectError('one scoped Hong Kong cable-bend table pack required')
    geometry=inspect(project,ifc,binding)
    before=dict(geometry['inputs'])
    extras={str(p):digest(p) for p in files|{pack,Path(regulations.__file__).resolve(),Path(cable_bend_rules.__file__).resolve()}}
    if any(p in before and before[p]!=sha for p,sha in extras.items()):raise ProjectError('shared geometry/classification inputs changed between checks')
    before.update(extras)
    official={str(p):digest(p) if p.is_file() else None for p in source_paths(rule_pack,sources)}
    if any(p in before and before[p]!=sha for p,sha in official.items()):raise ProjectError('conflicting official/input source identity')
    before.update(official)
    if not out.is_relative_to(ROOT) or out.exists() or any(out==Path(p) or out in Path(p).parents for p in before):raise ProjectError('new separate repository output required')
    bends={row['id']:row for row in geometry['lines'] if row['bend_radius_m'] is not None}
    if set(data['bends'])!=set(bends):raise ProjectError('exact saved bend/classification coverage required')
    model=ifcopenshell.open(str(ifc));reports={};derived={}
    rule=rule_pack['rules'][0];source_id=rule['source_id']
    def citation(name):return json.dumps(data['sources'][name],sort_keys=True)
    for name,observed in bends.items():
        row=data['bends'][name];pending=[];proof=citation(row['source'])
        diameter=row['overall_diameter_mm'];native_diameter=2*observed['envelope_radius_m']*1000
        if row['overall_diameter_is_actual'] is not True:pending.append('actual overall-diameter representation unresolved; nominal/unknown envelope cannot silently select a table band')
        if diameter is not None and row['overall_diameter_is_actual'] is True and not math.isclose(diameter,native_diameter,rel_tol=0,abs_tol=1e-9):raise ProjectError('saved envelope differs from sourced actual overall diameter')
        metadata=element.get_psets(model.by_guid(observed['element_guid'])).get('BSA_CableSelection',{})
        if not row['product_reference'] or not metadata.get('ProductReference') or not metadata.get('SourceSHA256'):pending.append('native product/source correspondence unresolved')
        elif metadata['ProductReference']!=row['product_reference'] or metadata['SourceSHA256']!=data['sources'][row['source']]['sha256']:raise ProjectError('native product/classification source identity differs')
        facts={key:dict(value=row[key],source=proof) for key in ('wiring_scope_confirmed','low_voltage','pvc_insulated','stranded_copper','armoured')}
        facts['overall_diameter']=dict(value=diameter,unit='mm',source=proof)
        facts['internal_bend_radius']=dict(value=(observed['bend_radius_m']-observed['envelope_radius_m'])*1000,unit='mm',source='Saved native-checked centreline radius minus verified circular envelope radius; IFC SHA256 '+digest(ifc))
        decision=data['edition_decision']
        derived[name]=dict(jurisdiction=data['jurisdiction'],rule_pack=data['rule_pack'],edition_decisions={source_id:dict(edition=decision['edition'],basis=citation(decision['source']))},facts=facts)
        report=evaluate(rule_pack,derived[name],sources)
        if pending:
            report['checks'][0]['reasons']+=pending;report['checks'][0]['status']='pending';report['supported_checks_pass']=False
        reports[name]=report
    statuses=[report['checks'][0]['status'] for report in reports.values()]
    status='fail' if 'review_required' in statuses else 'pass' if statuses and all(value=='pass' for value in statuses) else 'pending'
    if any((digest(Path(p)) if Path(p).is_file() else None)!=sha for p,sha in before.items()):raise ProjectError('cable regulation inputs changed during evaluation')
    result=dict(status=status,inputs=before,inputs_unchanged=True,geometry_correspondence_pass=True,reports=reports,derived_inputs=derived,
        manufacturer_selection_verified=False,regulatory_compliance='not_established',design_accepted=False,
        scope='Saved single-quarter cable geometry versus selected HK table with explicitly sourced classifications; evidence assertions, manufacturer/no-damage, numerical-study revision, workflow gates and full installation acceptance remain separate')
    out.mkdir(parents=True);(out/'cable-regulations.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('project',type=Path)
    for key in ('ifc','binding','basis','pack','sources','out'):parser.add_argument('--'+key,type=Path,required=True)
    result=run(**vars(parser.parse_args()));print(json.dumps({key:result[key] for key in ('status','geometry_correspondence_pass','design_accepted')}))
    raise SystemExit(0 if result['status']=='pass' else 2)

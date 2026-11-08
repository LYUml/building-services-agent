"""Versioned jurisdiction rule packs; scoped checks never imply full compliance."""
import argparse
import json
import math
from pathlib import Path

from .cli import digest
from .engine import ProjectError


def evaluate(pack,project,source_directory):
    if pack.get('schema_version')!=1 or not isinstance(pack.get('rules'),list):raise ProjectError('supported versioned rule pack required')
    if project.get('jurisdiction')!=pack.get('jurisdiction') or project.get('rule_pack')!=pack.get('id'):raise ProjectError('explicit matching jurisdiction and pinned rule pack required')
    facts=project.get('facts',{});decisions=project.get('edition_decisions',{})
    if not isinstance(facts,dict) or not isinstance(decisions,dict):raise ProjectError('fact and edition-decision mappings required')
    sources=pack['sources'];checks=[];seen=set();root=Path(source_directory).resolve()
    def fact(name):
        value=facts.get(name)
        if not isinstance(value,dict) or not isinstance(value.get('source'),str) or not value['source'].strip():return None
        return value
    for rule in pack['rules']:
        if rule['id'] in seen:raise ProjectError('unique rule ids required')
        seen.add(rule['id'])
        if rule['method']=='hvac_load_design_conditions':
            from .hvac_rules import design_conditions_check
            checks.append(design_conditions_check(pack,rule,project,root));continue
        if rule['method']=='office_lighting_power_density':
            from .lighting_rules import office_check
            checks.append(office_check(pack,rule,project,root));continue
        if rule['method'] not in ('deemed_to_satisfy_maximum','prescriptive_maximum'):raise ProjectError('unsupported rule method')
        if type(rule.get('maximum')) not in (int,float) or not math.isfinite(rule['maximum']) or rule['maximum']<0:raise ProjectError('finite nonnegative rule maximum required')
        if not isinstance(rule.get('applicability'),list) or not rule['applicability'] or any(type(c.get('equals')) is not bool for c in rule['applicability']):raise ProjectError('explicit Boolean applicability conditions required')
        source=sources[rule['source_id']]
        if not rule.get('clause') or not rule.get('pdf_page_1_based'):raise ProjectError('rule clause and page required')
        row=dict(id=rule['id'],status='pending',scope=rule['scope'],source_url=source['url'],source_sha256=source['sha256'],edition=source['edition'],clause=rule['clause'],pdf_page_1_based=rule['pdf_page_1_based'])
        reasons=[]
        decision=decisions.get(rule['source_id'])
        if not isinstance(decision,dict) or decision.get('edition')!=source['edition'] or not isinstance(decision.get('basis'),str) or not decision['basis'].strip():
            reasons.append('edition applicability decision missing or mismatched')
        path=(root/source['cache_filename']).resolve()
        if not path.is_relative_to(root):raise ProjectError('source cache path escapes root')
        if not path.is_file() or digest(path)!=source['sha256']:reasons.append('pinned official source unavailable or changed')
        applicable=True
        for condition in rule['applicability']:
            item=fact(condition['fact'])
            if item is None or type(item.get('value')) is not bool:
                reasons.append('missing sourced applicability fact: '+condition['fact'])
            elif item['value'] is not condition['equals']:applicable=False
        value=fact(rule['metric'])
        if value is None or type(value.get('value')) not in (int,float) or not math.isfinite(value['value']) or value['value']<0 or value.get('unit')!=rule['unit']:
            reasons.append('missing or invalid sourced metric/unit: '+rule['metric'])
        if reasons:row['reasons']=reasons
        elif not applicable:row.update(status='not_applicable',reasons=['outside this explicitly supported rule path; other requirements remain unresolved'])
        else:
            passed=value['value']<=rule['maximum']
            row.update(status='pass' if passed else 'review_required',value=value['value'],unit=rule['unit'],maximum=rule['maximum'],evidence=value['source'],
                       reasons=['selected '+('prescriptive limit' if rule['method']=='prescriptive_maximum' else 'deemed-to-satisfy path')+' met'] if passed else [rule['alternative_path_note']])
        checks.append(row)
    applicable=[r for r in checks if r['status']!='not_applicable']
    return dict(rule_pack=pack['id'],jurisdiction=pack['jurisdiction'],checks=checks,
                supported_checks_pass=bool(applicable) and all(r['status']=='pass' for r in applicable),
                coverage=pack['coverage'],regulatory_compliance='not_established',design_accepted=False,
                scope='Selected sourced checks only; applicability assertions remain project evidence, not an independent legal determination')


def source_paths(pack, directory):
    """Only sources used by executable rules; catalog entries need no cached PDF."""
    root=Path(directory).resolve();paths=set()
    for rule in pack['rules']:
        path=(root/pack['sources'][rule['source_id']]['cache_filename']).resolve()
        if not path.is_relative_to(root):raise ProjectError('source cache path escapes root')
        paths.add(path)
    return paths


def run(pack,project,sources,out):
    pack,project,out=Path(pack).resolve(),Path(project).resolve(),Path(out).resolve()
    if any(out==p or out in p.parents for p in (pack,project)):raise ProjectError('output must not contain inputs')
    before={str(p):digest(p) for p in (pack,project)}
    data=json.loads(pack.read_text(encoding='utf-8-sig'))
    official=source_paths(data,sources)
    if any(out==p or out in p.parents for p in official):raise ProjectError('output must not contain official sources')
    source_before={str(p):digest(p) if p.is_file() else None for p in official}
    result=evaluate(data,json.loads(project.read_text(encoding='utf-8-sig')),sources)
    if any((digest(Path(p)) if Path(p).is_file() else None)!=h for p,h in source_before.items()):raise ProjectError('official source changed during evaluation')
    before.update({p:h for p,h in source_before.items() if h is not None})
    if any(digest(Path(p))!=h for p,h in before.items()):raise ProjectError('regulation evaluation input changed')
    result.update(inputs=before,inputs_unchanged=True,missing_sources=[p for p,h in source_before.items() if h is None])
    out.mkdir(parents=True,exist_ok=False);(out/'regulation-checks.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('project',type=Path)
    for key in ('pack','sources','out'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();result=run(a.pack,a.project,a.sources,a.out);print(json.dumps(result,indent=2))
    return 0 if result['supported_checks_pass'] else 2


if __name__=='__main__':raise SystemExit(main())

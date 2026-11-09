"""Declared source-linked missing/conflicting inputs; no semantic inference."""
import re
from .engine import ProjectError


def validate(plan, passages, task_ids):
    issues=plan.get('unresolved_inputs',[])
    if not isinstance(issues,list):raise ProjectError('unresolved_inputs must be a list')
    seen=set()
    for issue in issues:
        if not isinstance(issue,dict) or set(issue)!={'id','kind','description','sources','blocks_tasks'}:
            raise ProjectError('unresolved input requires id/kind/description/sources/blocks_tasks')
        id=issue['id']
        if not isinstance(id,str) or not re.fullmatch(r'[A-Za-z0-9_-]+',id) or id in seen:
            raise ProjectError('unresolved input IDs must be unique path-safe strings')
        seen.add(id)
        if issue['kind'] not in ('missing','conflict') or not isinstance(issue['description'],str) or not issue['description'].strip():
            raise ProjectError('unresolved input requires missing/conflict kind and description')
        targets=issue['blocks_tasks']
        if not isinstance(targets,list) or not targets or any(not isinstance(t,str) or t not in task_ids for t in targets) or len(set(targets))!=len(targets):
            raise ProjectError('unresolved input must block unique known tasks')
        sources=issue['sources']
        if not isinstance(sources,list) or not sources:raise ProjectError('unresolved input requires source citations')
        cited=set()
        for source in sources:
            if not isinstance(source,dict) or set(source)!={'passage','quote'}:
                raise ProjectError('input issue source requires passage/quote')
            passage,quote=source['passage'],source['quote']
            if not isinstance(passage,str) or passage not in passages or not isinstance(quote,str) or not quote.strip() or quote not in passages[passage]['text']:
                raise ProjectError('input issue citation does not match source')
            if (passage,quote) in cited:raise ProjectError('duplicate input issue citation')
            cited.add((passage,quote))
        if issue['kind']=='conflict' and len(cited)<2:raise ProjectError('conflict needs at least two distinct source citations')
    return issues


def blockers(plan, task_id):
    return [issue for issue in plan.get('unresolved_inputs',[]) if task_id in issue['blocks_tasks']]

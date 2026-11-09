"""Bootstrap a source-linked, blocked interpretation plan; never infer engineering inputs."""
import argparse
import json
from pathlib import Path

from .cli import digest
from .engine import ProjectError
from .workflow import plan_documents

ROOT=Path(__file__).resolve().parents[2]


def draft(brief,out,supplements=None,ocr=None):
    brief,out=Path(brief).resolve(),Path(out).resolve()
    if not out.is_relative_to(ROOT) or out.exists():raise ProjectError('new repository-local plan file required')
    def source(path):
        path=Path(path).resolve()
        if not path.is_relative_to(out.parent) or not path.is_file():raise ProjectError('sources must be files under the plan directory')
        return dict(brief=path.relative_to(out.parent).as_posix(),brief_sha256=digest(path))
    spec=source(brief)
    if ocr:
        path=Path(ocr).resolve()
        if not path.is_relative_to(out.parent) or not path.is_file():raise ProjectError('OCR must be under the plan directory')
        spec.update(ocr=path.relative_to(out.parent).as_posix(),ocr_sha256=digest(path))
    if supplements:spec['supplemental_briefs']=[source(path) for path in supplements]
    document=plan_documents(out.parent,spec)
    if not document['passages']:raise ProjectError('no extracted passages; resolve document extraction before drafting')
    plan=dict(version=1,**spec,document_review={},passage_dispositions={},tasks=[],requirements=[],unresolved_inputs=[])
    for index,row in enumerate(document['passages'],1):
        task=f'interpret-{index:03}'
        plan['passage_dispositions'][row['id']]='requirement'
        plan['tasks'].append(dict(id=task,kind='manual',description='Uninterpreted source passage: inspect original, identify every requirement, replace with sourced engineering tasks and acceptance criteria.'))
        plan['requirements'].append(dict(id=f'R{index:03}',passage=row['id'],quote=row['text'],task=task,
            acceptance='Pending interpretation: cover the complete source passage, split requirements and establish actual deliverables and verification before execution.'))
        plan['unresolved_inputs'].append(dict(id=f'interpretation-{index:03}',kind='missing',description='Source meaning, design inputs and acceptance criteria have not been interpreted.',
            sources=[dict(passage=row['id'],quote=row['text'])],blocks_tasks=[task]))
    # No extraction issues are acknowledged on the user's behalf.
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x',encoding='utf-8') as stream:json.dump(plan,stream,ensure_ascii=False,indent=2)
    return dict(plan=str(out),passages=len(document['passages']),extraction_issues=document['issues'],
        interpretation_status='pending',design_accepted=False,
        scope='Conservative all-passage scaffold only; no semantic requirement extraction, adapter selection or engineering design')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('brief',type=Path);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--supplement',type=Path,action='append');parser.add_argument('--ocr',type=Path)
    args=parser.parse_args()
    try:result=draft(args.brief,args.out,args.supplement,args.ocr)
    except (ProjectError,OSError,ValueError) as exc:parser.exit(2,str(exc)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 2


if __name__=='__main__':raise SystemExit(main())

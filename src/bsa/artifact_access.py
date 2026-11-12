"""Read recorded workflow artifacts after existing source-bound delivery audit."""
import base64
import hashlib
from pathlib import Path
from . import delivery,workspace
from .cli import digest

LIMIT=2*1024*1024


def audited(plan,out):
    plan,out=Path(plan).resolve(),Path(out).resolve()
    root=(workspace.project_root() or workspace.ROOT/'runs').resolve()
    if not plan.is_relative_to(root) or not out.is_relative_to(root):
        raise ValueError('Plan and workflow must belong to selected project')
    before=digest(out/'workflow.json')
    source,report,integrity=delivery.context(plan,out)
    if not integrity['integrity_pass']:raise ValueError('Stale workflow evidence; rerun or repair first')
    if digest(out/'workflow.json')!=before:raise ValueError('Workflow changed during audit')
    return out,source,report,before


def index(plan,out):
    folder,source,report,receipt=audited(plan,out)
    rows=[]
    for name,sha in sorted(report['artifact_hashes'].items()):
        path=delivery.relative_file(folder,name)
        rows.append(dict(path=name,sha256=sha,size=path.stat().st_size,suffix=path.suffix.lower(),readable=path.stat().st_size<=LIMIT))
    return dict(workflow_sha256=receipt,artifacts=rows,tasks=report['tasks'],requirements=report['requirements'],requirement_count=len(source['requirements']),unresolved_inputs=source.get('unresolved_inputs',[]),design_accepted=False)


def read(plan,out,artifact,workflow_sha256):
    folder,_,report,receipt=audited(plan,out)
    if receipt!=workflow_sha256:raise ValueError('Workflow differs from inspected index')
    if artifact not in report['artifact_hashes']:raise ValueError('Only recorded workflow artifacts may be read')
    path=delivery.relative_file(folder,artifact)
    with path.open('rb') as stream:data=stream.read(LIMIT+1)
    if len(data)>LIMIT:raise ValueError('Artifact exceeds bounded read limit')
    sha=hashlib.sha256(data).hexdigest()
    if sha!=report['artifact_hashes'][artifact] or digest(folder/'workflow.json')!=receipt:
        raise ValueError('Artifact or workflow changed during reading')
    try:content=data.decode('utf-8');encoding='utf-8'
    except UnicodeDecodeError:content=base64.b64encode(data).decode('ascii');encoding='base64'
    return dict(path=artifact,sha256=sha,size=len(data),workflow_sha256=receipt,encoding=encoding,content=content,design_accepted=False)


def render_page(plan,out,artifact,workflow_sha256,page,target,*,renderer=None,max_side=2048):
    from . import source_page
    import json
    folder,_,report,receipt=audited(plan,out)
    if receipt!=workflow_sha256:raise ValueError('Workflow differs from inspected index')
    if artifact not in report['artifact_hashes']:raise ValueError('Recorded PDF artifact required')
    pdf=delivery.relative_file(folder,artifact)
    target=Path(target).resolve()
    root=(workspace.project_root() or workspace.ROOT/'runs').resolve()
    if not target.is_relative_to(root):raise ValueError('Preview must belong to selected project')
    if pdf.suffix.lower()!='.pdf':raise ValueError('Recorded PDF artifact required')
    result=source_page.run(pdf,page,target,renderer=renderer,max_side=max_side)
    _,_,after,after_receipt=audited(plan,out)
    if after_receipt!=receipt or result['source_sha256']!=after['artifact_hashes'][artifact]:
        raise ValueError('Workflow or artifact changed during rendering')
    result=dict(result,workflow_sha256=receipt,artifact=artifact,artifact_sha256=report['artifact_hashes'][artifact],engineering_acceptance='not_established')
    (target/'artifact-page.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result

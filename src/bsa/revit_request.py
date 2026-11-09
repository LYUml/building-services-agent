"""Prepare a source-bound native pipe request; never invokes Revit."""
import argparse
import json
import math
from pathlib import Path
from .cli import digest
from .engine import ProjectError


def prepare(inventory, model, basis, out):
    root=Path(__file__).resolve().parents[2]
    inventory,model,basis,out=[Path(p).resolve() for p in (inventory,model,basis,out)]
    if any(not p.is_relative_to(root) for p in (inventory,model,basis,out)) or out.exists():
        raise ProjectError('Use repository-local inputs and a new output directory')
    before={str(p):digest(p) for p in (inventory,model,basis)}
    data=json.loads(inventory.read_text(encoding='utf-8-sig'))
    spec=json.loads(basis.read_text(encoding='utf-8-sig'))
    if data.get('units')!='metres' or not isinstance(data.get('document_path'),str):
        raise ProjectError('Expected metre-valued native inventory')
    if Path(data['document_path']).resolve()!=model or data.get('saved_rvt_sha256')!=before[str(model)]:
        raise ProjectError('Inventory does not match saved model')
    if set(spec)!={'source','pipe'} or not isinstance(spec['source'],dict) or not isinstance(spec['pipe'],dict):
        raise ProjectError('Basis requires source and pipe objects only')
    source=spec['source'];pipe=spec['pipe']
    if set(source)!={'path','sha256','locator'} or not isinstance(source['path'],str):
        raise ProjectError('Source requires path, SHA256 and locator')
    source_path=(basis.parent/source['path']).resolve()
    if not source_path.is_relative_to(root) or not isinstance(source['locator'],str) or not source['locator'].strip():
        raise ProjectError('Source must be repository-local with explicit locator')
    source_hash=digest(source_path)
    if source_hash!=source['sha256']:raise ProjectError('Source document changed')
    before[str(source_path)]=source_hash
    fields={'PipeTypeUniqueId','SystemTypeUniqueId','LevelUniqueId','StartMetres','EndMetres','DiameterMetres'}
    if set(pipe)!=fields:raise ProjectError('Explicit type/system/level/endpoints/diameter required; no defaults')
    for field,collection in (('PipeTypeUniqueId','pipe_types'),('SystemTypeUniqueId','system_types'),('LevelUniqueId','levels')):
        rows=data.get(collection)
        if not isinstance(rows,list):raise ProjectError('Missing native selection inventory')
        ids=[row.get('unique_id') for row in rows]
        if any(not isinstance(uid,str) or not uid for uid in ids) or len(ids)!=len(set(ids)):
            raise ProjectError('Invalid or duplicate native selection identities')
        if pipe[field] not in ids:raise ProjectError('Requested selection not in model: '+field)
    for field in ('StartMetres','EndMetres'):
        value=pipe[field]
        if not isinstance(value,list) or len(value)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in value):
            raise ProjectError('Three finite metre coordinates required')
    d=pipe['DiameterMetres']
    if type(d) not in (int,float) or not math.isfinite(d) or d<=0 or math.dist(pipe['StartMetres'],pipe['EndMetres'])<=0:
        raise ProjectError('Positive diameter and nonzero segment required')
    if any(out==Path(p) or out in Path(p).parents for p in before):
        raise ProjectError('Output may not contain source inputs')
    source_text=json.dumps(dict(path=str(source_path),sha256=source_hash,locator=source['locator'],
                               basis_sha256=before[str(basis)]),sort_keys=True)
    request=dict(DocumentPath=str(model),Source=source_text,**pipe)
    if any(digest(Path(p))!=h for p,h in before.items()):raise ProjectError('Input changed during preparation')
    out.mkdir(parents=True)
    (out/'pipe-request.json').write_text(json.dumps(request,indent=2),encoding='utf-8')
    result=dict(scope='Source and native-selection binding only; no native execution or semantic source validation',
                inputs=before,request_sha256=digest(out/'pipe-request.json'),native_executed=False,
                source_interpretation_verified=False,design_accepted=False)
    (out/'preparation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('inventory','model','basis','out'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(prepare(args.inventory,args.model,args.basis,args.out),indent=2))


if __name__=='__main__':main()

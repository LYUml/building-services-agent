"""Source-pinned post-run ratio screening from a verified terminal lookup task."""
import argparse
import json
from pathlib import Path
from .cli import digest
from .workflow import verify
from .adpi_screen import screen


def run(directory,settings,output):
    directory,settings,output=(Path(p).resolve() for p in (directory,settings,output))
    if output.exists() or output==directory or directory in output.parents or output in directory.parents or output==settings or output in settings.parents:
        raise ValueError('New review output outside sources and immutable workflow required')
    settings_hash=digest(settings)
    spec=json.loads(settings.read_text(encoding='utf-8'))
    if set(spec)!={'criterion','room_load_W_m2','facts','source','source_sha256'}:
        raise ValueError('Exact sourced criterion, room load and applicability settings required')
    if not isinstance(spec['source'],str) or Path(spec['source']).is_absolute():raise ValueError('Relative criterion source required')
    source=(settings.parent/spec['source']).resolve()
    if not source.is_file() or digest(source)!=spec['source_sha256']:raise ValueError('ADPI criterion source hash mismatch')
    if output==source or output in source.parents:raise ValueError('Output must not contain criterion source')
    if not verify(directory)['integrity_pass']:raise ValueError('Workflow source or artifact evidence changed')
    manifest=directory/'workflow.json';manifest_hash=digest(manifest)
    workflow=json.loads(manifest.read_text(encoding='utf-8'))
    names=[name for name,t in workflow['tasks'].items() if t['kind']=='terminal_throw']
    if len(names)!=1 or workflow['tasks'][names[0]]['status']!='pass':raise ValueError('One passing terminal lookup required')
    lookup=directory/names[0]/'terminal-results.json';lookup_hash=digest(lookup)
    result=screen(json.loads(lookup.read_text(encoding='utf-8')),criterion=spec['criterion'],room_load_W_m2=spec['room_load_W_m2'],facts=spec['facts'])
    pins={str(settings):settings_hash,str(source):spec['source_sha256'],str(manifest):manifest_hash,str(lookup):lookup_hash}
    if any(digest(Path(p))!=sha for p,sha in pins.items()) or not verify(directory)['integrity_pass']:
        raise ValueError('ADPI review inputs changed during execution')
    result.update(inputs=pins,lookup_task=names[0],generator_sha256=digest(Path(__file__)),scope=result['scope']+'; source bytes pinned, transcription and declared facts require independent review')
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('workflow');p.add_argument('settings');p.add_argument('--out',required=True)
    a=p.parse_args();r=run(a.workflow,a.settings,a.out)
    print(r['applicability'],len(r['cases']),'screened cases; ADPI acceptance not established')
    raise SystemExit(2)

"""Source-pinned post-run ratio screening from a verified terminal lookup task."""
import argparse
import json
from pathlib import Path
from .cli import digest
from .workflow import verify
from .adpi_screen import screen


def settings_inputs(settings):
    """Pin criterion and optional per-fact review documents without inferring facts."""
    settings=Path(settings).resolve();settings_hash=digest(settings)
    spec=json.loads(settings.read_text(encoding='utf-8-sig'))
    required={'criterion','room_load_W_m2','facts','source','source_sha256'}
    if not isinstance(spec,dict) or not required<=set(spec) or set(spec)-required-{'fact_evidence'}:
        raise ValueError('Exact sourced criterion, room load and applicability settings required')
    pins={str(settings):settings_hash}
    def document(value,sha):
        if not isinstance(value,str) or not value.strip() or Path(value).is_absolute():raise ValueError('Relative ADPI evidence source required')
        path=(settings.parent/value).resolve()
        if not path.is_file() or digest(path)!=sha:raise ValueError('ADPI source hash mismatch (criterion or fact evidence)')
        if str(path) in pins and pins[str(path)]!=sha:raise ValueError('Conflicting ADPI evidence pins')
        pins[str(path)]=sha
    document(spec['source'],spec['source_sha256'])
    evidence=spec.get('fact_evidence',{})
    facts={'room_load_verified','product_category_verified','lengths_verified','installation_verified','edition_selected'}
    if not isinstance(evidence,dict) or set(evidence)-facts:raise ValueError('Known ADPI fact evidence mapping required')
    for name,records in evidence.items():
        if not isinstance(records,list) or not 1<=len(records)<=20:raise ValueError('One to twenty source records per reviewed fact required')
        for record in records:
            if not isinstance(record,dict) or set(record)!={'source','sha256','locator','note'} or any(not isinstance(record[k],str) or not record[k].strip() for k in record):
                raise ValueError('Exact fact document,hash,locator and review note required')
            document(record['source'],record['sha256'])
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('ADPI settings or evidence changed during validation')
    return spec,pins


def run(directory,settings,output):
    directory,settings,output=(Path(p).resolve() for p in (directory,settings,output))
    if output.exists() or output==directory or directory in output.parents or output in directory.parents or output==settings or output in settings.parents:
        raise ValueError('New review output outside sources and immutable workflow required')
    spec,pins=settings_inputs(settings)
    if any(output==Path(p) or output in Path(p).parents for p in pins):raise ValueError('Output must not contain criterion or fact evidence source')
    from . import adpi_screen
    for method in (Path(__file__),Path(adpi_screen.__file__)):
        pins[str(method.resolve())]=digest(method)
    if not verify(directory)['integrity_pass']:raise ValueError('Workflow source or artifact evidence changed')
    manifest=directory/'workflow.json';manifest_hash=digest(manifest)
    workflow=json.loads(manifest.read_text(encoding='utf-8'))
    names=[name for name,t in workflow['tasks'].items() if t['kind']=='terminal_throw']
    if len(names)!=1 or workflow['tasks'][names[0]]['status']!='pass':raise ValueError('One passing terminal lookup required')
    lookup=directory/names[0]/'terminal-results.json';lookup_hash=digest(lookup)
    result=screen(json.loads(lookup.read_text(encoding='utf-8')),criterion=spec['criterion'],room_load_W_m2=spec['room_load_W_m2'],facts=spec['facts'])
    pins.update({str(manifest):manifest_hash,str(lookup):lookup_hash})
    if any(digest(Path(p))!=sha for p,sha in pins.items()) or not verify(directory)['integrity_pass']:
        raise ValueError('ADPI review inputs changed during execution')
    result.update(inputs=pins,lookup_task=names[0],fact_evidence=spec.get('fact_evidence',{}),generator_sha256=digest(Path(__file__)),scope=result['scope']+'; source bytes pinned, transcription and declared facts require independent review; evidence records do not set applicability facts automatically')
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('workflow');p.add_argument('settings');p.add_argument('--out',required=True)
    a=p.parse_args();r=run(a.workflow,a.settings,a.out)
    print(r['applicability'],len(r['cases']),'screened cases; ADPI acceptance not established')
    raise SystemExit(2)

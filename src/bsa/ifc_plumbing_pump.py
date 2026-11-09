"""Fresh plumbing capacity checks from rederived saved network-coordination IFC."""
import json
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from .network_binding import prepare, reconcile
from .plumbing_pump_binding import run as check


def verify_producer(producer, project, model, binding):
    producer = Path(producer).resolve()
    paths = [Path(p).resolve() for p in (project, model, binding)]
    def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
    report = producer/'network-binding.json'; data = read(report)
    if set(data.get('inputs', {})) != {str(p) for p in paths}:
        raise ProjectError('exact original network/model/binding identities required')
    for p in paths:
        if digest(p) != data['inputs'][str(p)]:raise ProjectError('producer original source changed')
    required = {'bim/model.ifc', 'bim/bim-verification.json', 'network-input.json', 'analysis/network.json'}
    if not required <= set(data.get('artifacts', {})):raise ProjectError('missing producer native artifact coverage')
    for name, sha in data['artifacts'].items():
        p = (producer/name).resolve()
        if not p.is_relative_to(producer) or not p.is_file() or digest(p) != sha:
            raise ProjectError('producer artifact changed: '+name)
    if data.get('inputs_unchanged') is not True or data.get('saved_ifc_geometry_match') is not True:
        raise ProjectError('producer geometry/source checks incomplete')
    template, original, links = [read(p) for p in paths]
    expected, _ = prepare(template, original, links)
    if expected != read(producer/'network-input.json'):
        raise ProjectError('derived network differs from original source reconstruction')
    reconcile(producer/'bim/model.ifc', producer/'network-input.json', links, original)
    return dict(report_sha256=digest(report), ifc_sha256=digest(producer/'bim/model.ifc'),
                network_sha256=digest(producer/'network-input.json'), source_reconstruction_match=True,
                saved_geometry_reconciled=True)


def run(producer, project, model, binding, curve, basis, pack, sources, out):
    producer, out = Path(producer).resolve(), Path(out).resolve()
    paths = [Path(p).resolve() for p in (project, model, binding)]
    if out == producer or producer in out.parents or out in producer.parents or any(out == p or out in p.parents for p in paths):
        raise ProjectError('new output must be separate from producer and sources')
    before = verify_producer(producer, *paths)
    result = check(producer/'network-input.json', curve, basis, pack, sources, out)
    if verify_producer(producer, *paths) != before:raise ProjectError('saved IFC producer changed during checks')
    result['saved_ifc_binding'] = before
    result['inputs'].update({str(p):digest(p) for p in paths})
    result['pending'].append('IFC route binding does not prove physical pump/tank identity, duplicate equipment or controls')
    (out/'plumbing-pump-checks.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result

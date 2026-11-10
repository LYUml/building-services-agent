"""Bounded catalogue throw interpolation using pinned fluids, not ADPI prediction."""
import math
from fluids.numerics import interp


def run(project_path, output, *, allocation_path=None, allocation_sha256=None):
    """Execute source-pinned terminal lookups; input facts remain caller-reviewed."""
    import json
    import hashlib
    from pathlib import Path
    project_path=Path(project_path).resolve(); output=Path(output).resolve()
    raw=project_path.read_bytes(); project=json.loads(raw.decode('utf-8-sig'))
    catalogue=(project_path.parent/project['catalogue']).resolve()
    data=catalogue.read_bytes(); actual=hashlib.sha256(data).hexdigest()
    if actual!=project['catalogue_sha256']:
        raise ValueError('Catalogue source hash mismatch')
    source=json.loads(data.decode('utf-8-sig'))
    if output.exists() or any(output==p or output in p.parents for p in (project_path,catalogue)):
        raise ValueError('New output directory separate from inputs required')
    if not isinstance(project.get('basis'),str) or not project['basis'].strip():
        raise ValueError('Explicit project basis and limitations required')
    inherited = None
    if allocation_path is not None:
        allocation_path=Path(allocation_path).resolve()
        inherited=allocation_path.read_bytes()
        if hashlib.sha256(inherited).hexdigest()!=allocation_sha256:
            raise ValueError('Allocation producer hash mismatch')
        if output==allocation_path or output in allocation_path.parents:
            raise ValueError('Output must not contain allocation producer')
        if 'turndown' in project or any('maximum_flow_L_s' in t for t in project['terminals']):
            raise ValueError('Inherited flow and turndown cannot be overridden')
        allocation=json.loads(inherited.decode('utf-8-sig'))
        rows=allocation['terminals']
        flows={t['id']:t['maximum_flow_L_s'] for t in rows}
        if len(flows)!=len(rows) or set(flows)!={t['id'] for t in project['terminals']}:
            raise ValueError('Allocation and lookup terminal identities must match exactly')
        project['turndown']=allocation['turndown']
        for terminal in project['terminals']:
            terminal['maximum_flow_L_s']=flows[terminal['id']]
    elif allocation_sha256 is not None:
        raise ValueError('Allocation path required with producer hash')
    results=[]; ids=set()
    for terminal in project['terminals']:
        name=terminal['id']
        if not isinstance(name,str) or not name.strip() or name in ids:
            raise ValueError('Unique nonempty terminal IDs required')
        ids.add(name)
        lengths = terminal['characteristic_lengths_m']
        if not isinstance(lengths, dict) or not lengths or any(
                not isinstance(key, str) or not key.strip() for key in lengths):
            raise ValueError('Characteristic-length evidence required')
        results.append(dict(id=name,directions={direction:evaluate(source['rows'],
            maximum_flow_L_s=terminal['maximum_flow_L_s'],turndown=project['turndown'],
            characteristic_length_m=length)
            for direction,length in terminal['characteristic_lengths_m'].items()}))
    if not results:raise ValueError('Nonempty terminal inventory required')
    if project_path.read_bytes()!=raw or catalogue.read_bytes()!=data:
        raise ValueError('Inputs changed during calculation')
    unresolved = sum(case['status'] != 'within_catalogue'
                     for terminal in results for direction in terminal['directions'].values()
                     for case in direction['cases'].values())
    result=dict(inputs={str(project_path):hashlib.sha256(raw).hexdigest(),str(catalogue):actual},
                lookup_status='outside_catalogue' if unresolved else 'within_catalogue',
                outside_catalogue_cases=unresolved,
                source_scope='Pins reviewed catalogue JSON; original manufacturer document and transcription require separate review',
                basis=project['basis'],terminals=results,ADPI_verified=False,design_accepted=False)
    if inherited is not None:
        if allocation_path.read_bytes()!=inherited:
            raise ValueError('Allocation producer changed during lookup')
        result['inputs'][str(allocation_path)]=allocation_sha256
        result['flow_basis']='Exact inherited air allocation; no replacement flow or turndown'
    output.mkdir(parents=True)
    (output/'terminal-results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def positive(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ValueError('Finite positive numeric value required')
    return value


def evaluate(rows, *, maximum_flow_L_s, turndown, characteristic_length_m):
    q = positive(maximum_flow_L_s)
    length = positive(characteristic_length_m)
    if positive(turndown) > 1:
        raise ValueError('Turndown must be <=1')
    if len(rows) < 2:
        raise ValueError('At least two catalogue rows required')
    flows = [positive(r['flow_L_s']) for r in rows]
    throws = [positive(r['T025_m']) for r in rows]
    if any(b <= a for a,b in zip(flows,flows[1:])):
        raise ValueError('Catalogue flows must be strictly increasing')
    cases = {}
    for name, flow in [('maximum',q), ('minimum',q*turndown)]:
        if not flows[0] <= flow <= flows[-1]:
            cases[name] = dict(flow_L_s=flow,status='outside_catalogue',T025_m=None,ratio=None)
            continue
        throw = interp(flow, flows, throws)
        bracket = next((i for i in range(len(flows)-1) if flows[i] <= flow <= flows[i+1]))
        cases[name] = dict(flow_L_s=flow,status='within_catalogue',T025_m=throw,
                           ratio=throw/length,bracketing_rows=[bracket,bracket+1])
    return dict(characteristic_length_m=length,cases=cases,method='Piecewise linear interpolation; explicit design approximation',
                ADPI_verified=False,design_accepted=False,
                pending=['Catalogue condition and characteristic-length applicability',
                         'ADPI classification, thermal load and criterion applicability'])


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project'); parser.add_argument('--out',required=True)
    args=parser.parse_args(); result=run(args.project,args.out)
    print('Terminal inventories calculated:',len(result['terminals']),'; ADPI acceptance remains pending')
    raise SystemExit(2 if result['outside_catalogue_cases'] else 0)

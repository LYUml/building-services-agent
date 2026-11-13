"""Host-only pinned Core Console read probe; project records stay private."""
import argparse
from dataclasses import asdict
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import traceback

VERSIONS={'dcc-mcp-autocad':'0.1.3','dcc-mcp-core':'0.20.36','dcc-mcp-server':'0.20.53'}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(source,out,autocad):
    root=Path(os.environ['BSA_PROJECT_ROOT']).resolve()
    source,out,autocad=[Path(p).resolve() for p in (source,out,autocad)]
    if not root.is_dir() or root==Path(root.anchor) or not source.is_relative_to(root) or not out.is_relative_to(root) or out.exists() or out==source or out in source.parents or not source.is_file() or not autocad.is_file():raise ValueError('Explicit project source, fresh output and host engine required')
    out.mkdir(parents=True);before=sha(source)
    record=dict(scope='Pinned upstream Core Console read probe only; no drawing writes or plot acceptance',source=str(source),source_sha256=before,engine=str(autocad),engine_sha256=sha(autocad),design_accepted=False,calls=[])
    try:
        versions={name:importlib.metadata.version(name) for name in VERSIONS}
        if versions!=VERSIONS:raise ValueError('Exact reviewed dependency versions required')
        record['versions']=versions
        from dcc_mcp_autocad.transports.core_console import CoreConsoleTransport
        from dcc_mcp_autocad.compat import host_verdict
        import dcc_mcp_autocad.transports.core_console as implementation
        record['upstream_transport_sha256']=sha(implementation.__file__)
        class Logged(CoreConsoleTransport):
            def _run_script(self,*args,**kwargs):
                result=super()._run_script(*args,**kwargs);record['calls'].append(result)
                if result['returncode']!=0:raise ValueError('Upstream native process did not exit successfully')
                return result
        transport=Logged(str(autocad),timeout_secs=90)
        record['status']=transport.status()
        record['host_verdict']=host_verdict(record['status'].get('version'))
        record['inventory']=asdict(transport.inspect_drawing(str(source)))
        record['probe_completed']=True
    except Exception as exc:
        record.update(probe_completed=False,error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc())
    record['source_unchanged']=source.is_file() and sha(source)==before
    if not record['source_unchanged']:record['probe_completed']=False
    (out/'probe.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps({k:record[k] for k in ['probe_completed','source_unchanged','design_accepted']}|dict(error=record.get('error')),indent=2))
    return 0 if record['probe_completed'] else 2

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['source','out','autocad']:parser.add_argument('--'+key,required=True)
    a=parser.parse_args();raise SystemExit(run(a.source,a.out,a.autocad))

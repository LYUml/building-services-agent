"""Bounded-memory inspection of retained worker diagnostics; no engine execution."""
from pathlib import Path

CHUNK_BYTES=65536
POLICY_MARKER=b'application control policy'


def inspect_log(path,*,tail_limit=8192):
    if type(tail_limit) is not int or not 1<=tail_limit<=CHUNK_BYTES:
        raise ValueError('Diagnostic tail budget must be 1..65536 bytes')
    tail=b'';overlap=b'';total=0;policy=False
    with Path(path).open('rb') as stream:
        while chunk:=stream.read(CHUNK_BYTES):
            window=(overlap+chunk).lower()
            policy=policy or POLICY_MARKER in window
            overlap=window[-(len(POLICY_MARKER)-1):]
            total+=len(chunk);tail=(tail+chunk)[-tail_limit:]
    return dict(tail=tail.decode('utf-8',errors='replace'),bytes=total,
        truncated=total>tail_limit,application_control_policy=policy)

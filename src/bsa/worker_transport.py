"""Fixed worker IPC with bounded-memory diagnostic forwarding, independent of MCP."""
import codecs
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from .mcp_worker import OPERATIONS

LOG_CHUNK_BYTES=65536


def _forward_logs(source,sink):
    decoder=codecs.getincrementaldecoder('utf-8')(errors='replace')
    while chunk:=source.read(LOG_CHUNK_BYTES):
        sink.write(decoder.decode(chunk))
    sink.write(decoder.decode(b'',final=True))


def invoke(operation,args,kwargs,*,cwd):
    if operation not in OPERATIONS:raise ValueError('Fixed engineering operation required')
    request=json.dumps(dict(operation=operation,args=args,kwargs=kwargs),default=str,allow_nan=False)
    with tempfile.TemporaryDirectory(prefix='bsa-mcp-response-') as directory, tempfile.TemporaryFile() as diagnostics:
        response=Path(directory)/'response.json'
        # Native diagnostics can be much larger than the structured response.
        # Preserve both streams without buffering their entire bytes in RAM.
        completed=subprocess.run([sys.executable,'-X','utf8','-m','bsa.mcp_worker','--response-file',str(response)],
            input=request.encode('utf-8'),stdout=diagnostics,stderr=subprocess.STDOUT,cwd=cwd)
        diagnostics.seek(0);_forward_logs(diagnostics,sys.stderr)
        try:result=json.loads(response.read_text(encoding='utf-8'))
        except (OSError,ValueError) as exc:raise ValueError(f'Engineering worker produced no valid response (exit {completed.returncode}); inspect server stderr') from exc
    if not isinstance(result,dict) or type(result.get('ok')) is not bool or (result['ok'] and 'value' not in result):
        raise ValueError('Engineering worker response envelope is invalid')
    if completed.returncode or result['ok'] is not True:raise ValueError(result.get('error','Engineering worker failed'))
    return result['value']

"""Windows fresh-process baseline for import/startup and synthetic worker log pressure.

Uses existing SDK/worker/reference operations and Win32 process counters; it adds
no dependency or engineering benchmark claim. Output stays in repository runs.
"""
from pathlib import Path
import argparse
import subprocess,sys,os,json,statistics,time
from windows_memory_probe import MEMORY_CODE
ROOT=Path(__file__).resolve().parents[1]
CODE=r"""
import sys,os,time,json,ctypes,asyncio,subprocess
from unittest.mock import patch
"""+MEMORY_CODE+r"""
probe=sys.argv[1];before=memory();start=time.perf_counter()
if probe=='pump_import':import bsa.pump_catalogue_iteration
elif probe=='cli_import':import bsa.cli
elif probe=='workflow_import':import bsa.workflow
else:
 from bsa.mcp_server import create_server
 server=create_server()
 if probe!='mcp_create':
  real_run=subprocess.run;count=32 if probe=='transport_32mib' else 0
  child="import os,sys; from bsa import mcp_worker; chunk=b'x'*1048576; [os.write(1,chunk) for _ in range("+str(count)+")]; raise SystemExit(mcp_worker.main(sys.argv[1]))"
  def worker(args,**kwargs):
   response=args[args.index('--response-file')+1]
   return real_run([sys.executable,'-X','utf8','-c',child,response],**kwargs)
  with patch('subprocess.run',side_effect=worker):
   asyncio.run(server.call_tool('bsa_reference_catalogue',dict(kind='all',limit=1)))
print(json.dumps(dict(probe=probe,seconds=time.perf_counter()-start,before=before,after=memory())))
"""
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out',type=Path,required=True)
parser.add_argument('--trials',type=int,default=3)
args=parser.parse_args()
if sys.platform!='win32':parser.error('Windows process-memory counters required for this profiler')
if not 1<=args.trials<=10:parser.error('trials must be between 1 and 10')
out=args.out.resolve()
if not out.is_relative_to(ROOT/'runs') or out.exists():parser.error('Fresh repository runs directory required')
out.mkdir(parents=True);rows=[]
for probe in ['cli_import','workflow_import','pump_import','mcp_create','transport_quiet','transport_32mib']:
 for trial in range(args.trials):
  env=dict(os.environ);env.pop('BSA_PROJECT_ROOT',None)
  p=subprocess.run([sys.executable,'-X','utf8','-c',CODE,probe],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8');assert p.returncode==0,(probe,p.stdout)
  row=json.loads(p.stdout);row['trial']=trial+1;rows.append(row)
summary={probe:dict(median_seconds=statistics.median(r['seconds'] for r in rows if r['probe']==probe),median_peak_bytes=statistics.median(r['after']['peak_bytes'] for r in rows if r['probe']==probe)) for probe in {r['probe'] for r in rows}}
(out/'measurements.json').write_text(json.dumps(dict(rows=rows,summary=summary,scope='Fresh process Windows working-set probes; 32MiB diagnostic stress is synthetic transport load, not engineering simulation performance'),indent=2),encoding='utf-8');print(json.dumps(summary,indent=2))

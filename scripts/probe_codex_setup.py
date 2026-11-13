"""Probe installed project-scoped BSA tools through an ephemeral Codex backend.

No model turn is sent. This does not establish current desktop-chat hot reload.
"""
import argparse,json,os,queue,shutil,subprocess,threading,time
from pathlib import Path
from bsa import workspace
from bsa.cli import digest
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True);p.add_argument('--ledger');a=p.parse_args()
project=(workspace.project_root() or workspace.ROOT).resolve();output=Path(a.out).resolve()
if project==workspace.ROOT.parent/'polyu_bse3124':raise ValueError('Completed historical project is read-only')
if not workspace.allowed(output) or output.exists() or not (output.is_relative_to(workspace.ROOT/'runs') or (workspace.project_root() is not None and output.is_relative_to(project))):raise ValueError('Fresh host-selected diagnostic output required')
cli=shutil.which('codex')
if not cli:raise ValueError('Installed Codex CLI required')
effective=json.loads(subprocess.run([cli,'mcp','get','building_services','--json'],cwd=project,capture_output=True,text=True,encoding='utf-8',check=True).stdout)
import tomllib
config_path=project/'.codex/config.toml';local=tomllib.loads(config_path.read_text(encoding='utf-8'))['mcp_servers']['building_services']
assert all(effective['transport'][k]==local[k] for k in ('command','args','cwd','env'))
assert all(effective[k]==local[k] for k in ('enabled','startup_timeout_sec','tool_timeout_sec'))
process=subprocess.Popen([cli,'app-server'],cwd=project,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
messages=queue.Queue()
def read():
 for line in process.stdout:
  try:messages.put(json.loads(line))
  except ValueError:pass
threading.Thread(target=read,daemon=True).start();serial=0
def call(method,params):
 global serial
 serial+=1;ident=serial;process.stdin.write(json.dumps(dict(id=ident,method=method,params=params))+'\n');process.stdin.flush();deadline=time.monotonic()+150
 while True:
  if time.monotonic()>=deadline:raise TimeoutError('Codex diagnostic response timed out')
  message=messages.get(timeout=max(.01,deadline-time.monotonic()))
  if 'method' in message and 'id' in message:raise RuntimeError('Diagnostic requires host interaction; no automatic approval supplied')
  if message.get('id')==ident:
   if 'error' in message:raise RuntimeError(method+': '+str(message['error'].get('message','RPC error')))
   return message['result']
try:
 call('initialize',dict(clientInfo=dict(name='bsa_local_setup_probe',version='1')));process.stdin.write(json.dumps(dict(method='initialized'))+'\n');process.stdin.flush()
 started=call('thread/start',dict(cwd=str(project),ephemeral=True));thread_id=started['thread']['id'];print('Ephemeral diagnostic context initialized',flush=True)
 status=call('mcpServerStatus/list',dict(serverName='building_services',threadId=thread_id));server=next(x for x in status['data'] if x['name']=='building_services');assert not server.get('toolsError'),server.get('toolsError');assert len(server['tools'])==38
 print('Actual Codex backend discovered all 38 BSA tools',flush=True)
 result=call('mcpServer/tool/call',dict(threadId=thread_id,server='building_services',tool='bsa_reference_catalogue',arguments=dict(limit=1)));assert not result.get('isError');assert result.get('structuredContent') is not None
 catalogue=result['structuredContent'];assert catalogue['total']>0 and len(catalogue['references'])==1 and catalogue['design_accepted'] is False
 ledger_count=None
 if a.ledger:
  data_root=Path(local['env']['BSA_PROJECT_ROOT']).resolve();ledger=(data_root/a.ledger).resolve()
  if Path(a.ledger).is_absolute() or not ledger.is_relative_to(data_root):raise ValueError('Project-relative ledger directory required')
  result=call('mcpServer/tool/call',dict(threadId=thread_id,server='building_services',tool='bsa_list_pressure_evidence_gaps',arguments=dict(out=a.ledger,record_sha256=digest(ledger/'pressure-ledger.json'),limit=1)))
  assert not result.get('isError');page=result['structuredContent'];assert len(page['gaps'])==min(1,page['total']) and page['design_accepted'] is False;ledger_count=page['total']
 receipt=dict(codex_sha256=digest(Path(cli)),local_config_sha256=digest(config_path),effective_config_matches_local=True,readonly_reference_count=len(catalogue['references']),project_ledger_numeric_gap_count=ledger_count,actual_codex_backend_catalogue_count=len(server['tools']),actual_codex_readonly_tool_call_pass=True,ephemeral_context=True,model_turns_sent=0,project=str(project),current_desktop_chat_hot_reload_verified=False,design_accepted=False)
 output.mkdir(parents=True);(output/'backend-probe.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt),flush=True)
finally:
 process.stdin.close()
 try:process.wait(timeout=5)
 except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=5)

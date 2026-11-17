import contextlib,io,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from bsa import mcp_worker

ROOT=Path(__file__).resolve().parents[1]

class WorkerResponseChannel(unittest.TestCase):
    def test_os_level_stdout_cannot_pollute_the_response(self):
        code='''import os,sys
from unittest.mock import patch
from bsa import mcp_worker
def operation():
 os.write(1,b'native stdout diagnostic\\n')
 return {'synthetic_transport_probe':True}
with patch('bsa.mcp_worker.resolve',return_value=operation):
 raise SystemExit(mcp_worker.main(sys.argv[1]))
'''
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            response=Path(folder)/'response.json';request=json.dumps(dict(operation='bsa.reference_library.catalogue',args=[],kwargs={}))
            result=subprocess.run([sys.executable,'-c',code,str(response)],input=request.encode(),capture_output=True,cwd=ROOT,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stdout,b'native stdout diagnostic\n')
            self.assertEqual(json.loads(response.read_text())['value'],{'synthetic_transport_probe':True})

    def test_response_never_overwrites_existing_file(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            response=Path(folder)/'response.json';response.write_text('Preserve original')
            request=json.dumps(dict(operation='not.registered',args=[],kwargs={}))
            with patch('sys.stdin',io.StringIO(request)),self.assertRaises(FileExistsError):mcp_worker.main(response)
            self.assertEqual(response.read_text(),'Preserve original')

class ServerResponseChannel(unittest.IsolatedAsyncioTestCase):
    async def test_server_uses_private_response_and_keeps_logs_off_result(self):
        from bsa.mcp_server import create_server
        server=create_server();paths=[]
        def worker(args,**kwargs):
            path=Path(args[args.index('--response-file')+1]);paths.append(path)
            self.assertEqual(json.loads(kwargs['input'])['operation'],'bsa.reference_library.catalogue')
            path.write_text(json.dumps(dict(ok=True,value={'synthetic_transport_probe':True,'design_accepted':False})))
            return subprocess.CompletedProcess(args,0,stdout=b'\xffnative stdout\n',stderr=b'python diagnostics\n')
        stderr=io.StringIO()
        with patch('bsa.mcp_server.subprocess.run',side_effect=worker),contextlib.redirect_stderr(stderr):
            await server.call_tool('bsa_reference_catalogue',{})
        self.assertIn('native stdout',stderr.getvalue());self.assertIn('python diagnostics',stderr.getvalue())
        self.assertIn('\ufffd',stderr.getvalue())
        self.assertTrue(paths);self.assertFalse(paths[0].parent.exists())

    async def test_missing_or_malformed_response_is_not_success(self):
        from bsa.mcp_server import create_server
        server=create_server()
        for content in [None,'[]','{"ok":true}']:
            def worker(args,**kwargs):
                if content is not None:Path(args[args.index('--response-file')+1]).write_text(content)
                return subprocess.CompletedProcess(args,0,stdout=b'log only',stderr=b'')
            with patch('bsa.mcp_server.subprocess.run',side_effect=worker),contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaisesRegex(Exception,'response'):
                    await server.call_tool('bsa_reference_catalogue',{})

if __name__=='__main__':unittest.main()

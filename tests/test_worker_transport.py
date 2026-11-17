import contextlib
import io
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from bsa import worker_transport

ROOT=Path(__file__).resolve().parents[1]


class WorkerTransportTests(unittest.TestCase):
    def test_log_reads_are_bounded_and_utf8_survives_chunk_boundaries(self):
        class Observed(io.BytesIO):
            sizes=[]
            def read(self,size=-1):
                self.sizes.append(size)
                return super().read(size)
        data=b'a'*(worker_transport.LOG_CHUNK_BYTES-1)+'中'.encode()+b'\xff\xe4'
        source=Observed(data);sink=io.StringIO()
        worker_transport._forward_logs(source,sink)
        self.assertEqual(sink.getvalue(),data.decode('utf-8',errors='replace'))
        self.assertTrue(source.sizes)
        self.assertTrue(all(0<size<=worker_transport.LOG_CHUNK_BYTES for size in source.sizes))

    def test_unregistered_operation_never_launches_a_process(self):
        with patch('bsa.worker_transport.subprocess.run') as run:
            with self.assertRaisesRegex(ValueError,'Fixed engineering operation'):
                worker_transport.invoke('arbitrary.operation',[],{},cwd=ROOT)
        run.assert_not_called()

    def test_nonzero_exit_cannot_be_success_even_with_successful_json(self):
        paths=[]
        def worker(args,**kwargs):
            path=Path(args[args.index('--response-file')+1]);paths.append(path)
            path.write_text(json.dumps(dict(ok=True,value={})),encoding='utf-8')
            kwargs['stdout'].write(b'failed native process diagnostic\n')
            return subprocess.CompletedProcess(args,2)
        stderr=io.StringIO()
        with patch('bsa.worker_transport.subprocess.run',side_effect=worker),contextlib.redirect_stderr(stderr):
            with self.assertRaisesRegex(ValueError,'worker failed'):
                worker_transport.invoke('bsa.reference_library.catalogue',[],{},cwd=ROOT)
        self.assertIn('failed native process diagnostic',stderr.getvalue())
        self.assertFalse(paths[0].parent.exists())


if __name__=='__main__':unittest.main()

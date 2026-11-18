import importlib.metadata as metadata
import json
import os
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bsa import doctor,workspace,drawing_access

class DoctorTests(unittest.TestCase):
    def test_dwg_runtime_needs_adjacent_reader_without_executing_binaries(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            worker, dotnet = root / 'worker.dll', root / 'dotnet.exe'
            worker.touch()
            dotnet.touch()
            with patch.dict(os.environ, BSA_ACADSHARP_DOTNET=str(dotnet), BSA_ACADSHARP_WORKER=str(worker)):
                missing = doctor.check(dwg_readback=True)
                self.assertEqual(missing['status'], 'needs_setup')
                self.assertIn('adjacent ACadSharp.dll', missing['dwg_readback']['problem'])
                reader = root / 'ACadSharp.dll'
                reader.touch()
                checked = doctor.check(dwg_readback=True)['dwg_readback']
                self.assertTrue(checked['paths_ready'])
                self.assertEqual(checked['reader'], str(reader.resolve()))
                self.assertFalse(checked['execution_verified'])

    def profile(self,root,args):
        path=root/'profile.toml'
        path.write_text('[mcp_servers.building_services]\ncommand='+json.dumps(sys.executable.replace('\\','/'))+
            '\ncwd='+json.dumps(root.as_posix())+'\nargs='+json.dumps(args)+'\n',encoding='utf-8')
        return path

    def test_profile_missing_runtime_is_detected_without_execution_or_writes(self):
        with tempfile.TemporaryDirectory(dir=workspace.ROOT/'runs') as folder:
            root=Path(folder);missing=root/'removed-poppler.exe'
            config=self.profile(root,['-m','bsa.mcp_server','--pdftoppm',missing.as_posix()])
            before=config.read_bytes();inventory=list(root.iterdir())
            result=doctor.check(mcp_config=config)
            self.assertEqual(result['status'],'needs_setup')
            self.assertFalse(result['mcp_profile']['runtimes']['--pdftoppm']['present'])
            self.assertFalse(result['mcp_profile']['execution_verified'])
            self.assertEqual(config.read_bytes(),before);self.assertEqual(list(root.iterdir()),inventory)

    def test_profile_types_and_equals_syntax_are_presence_only(self):
        with tempfile.TemporaryDirectory(dir=workspace.ROOT/'runs') as folder:
            root=Path(folder);exe=root/'not-executable.exe';exe.write_text('Do not execute')
            config=self.profile(root,['--autocad='+exe.as_posix(),'--radiance-bin',root.as_posix()])
            result=doctor.profile_paths(config)
            self.assertTrue(result['paths_ready']);self.assertFalse(result['runtimes']['--autocad']['execution_verified'])
            self.profile(root,['--radiance-bin',exe.as_posix()])
            self.assertFalse(doctor.profile_paths(config)['paths_ready'])
            self.profile(root,['--autocad','relative.exe'])
            self.assertFalse(doctor.profile_paths(config)['runtimes']['--autocad']['absolute'])

    def test_malformed_or_ambiguous_profile_rejects(self):
        with tempfile.TemporaryDirectory(dir=workspace.ROOT/'runs') as folder:
            root=Path(folder)
            for args in [['--autocad'],['--autocad','--radiance-bin'],['--autocad',sys.executable,'--autocad='+sys.executable]]:
                with self.subTest(args=args),self.assertRaises(ValueError):doctor.profile_paths(self.profile(root,args))
            config=root/'profile.toml';config.write_text('[mcp_servers.other]\ncommand="other"')
            with self.assertRaisesRegex(ValueError,'building_services'):doctor.profile_paths(config)
            self.profile(root,[7])
            with self.assertRaisesRegex(ValueError,'string list'):doctor.profile_paths(config)

    def test_installed_command_reports_stale_profile_with_exit_two(self):
        with tempfile.TemporaryDirectory(dir=workspace.ROOT/'runs') as folder:
            root=Path(folder);config=self.profile(root,['--pdftoppm',(root/'removed.exe').as_posix()])
            result=subprocess.run([sys.executable,'-m','bsa.cli','doctor','--mcp-config',str(config)],
                capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(result.returncode,2,result.stderr)
            self.assertNotIn('Traceback',result.stderr)
            self.assertFalse(json.loads(result.stdout)['mcp_profile']['paths_ready'])

    def test_missing_pin_and_unknown_extra_are_explicit(self):
        def version(name):
            if name=='pypdf':raise metadata.PackageNotFoundError(name)
            return '1.4.5'
        with patch('bsa.doctor.metadata.version',side_effect=version):
            result=doctor.check(extras=['drawing'])
        self.assertEqual(result['status'],'needs_setup')
        self.assertIsNone(next(p for p in result['packages'] if p['package']=='pypdf')['installed'])
        self.assertFalse(result['design_accepted'])
        with self.assertRaisesRegex(ValueError,'Unknown extras'):doctor.check(extras=['guess'])

    def test_existing_executable_is_presence_only(self):
        with tempfile.TemporaryDirectory(dir=workspace.ROOT/'runs') as folder:
            exe=Path(folder)/'fixture.exe';exe.write_text('Not an executable')
            result=doctor.check(autocad=exe)
            self.assertTrue(result['autocad']['is_file']);self.assertFalse(result['autocad']['execution_verified'])
            self.assertEqual(doctor.check(autocad=Path(folder)/'missing')['status'],'needs_setup')

    def test_missing_native_dependency_rejects_before_output(self):
        with tempfile.TemporaryDirectory(dir=workspace.ROOT/'runs') as folder:
            root=Path(folder);exe=root/'fixture.exe';exe.touch();out=root/'new'
            with patch('bsa.drawing_access.metadata.version',side_effect=metadata.PackageNotFoundError('pypdf')):
                with self.assertRaisesRegex(ValueError,'drawing extra'):
                    drawing_access.run(workspace.ROOT/'examples/drawing-document.json',out,autocad=exe)
            self.assertFalse(out.exists())

if __name__=='__main__':unittest.main()

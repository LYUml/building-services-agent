import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from bsa.cli import digest
from bsa.workflow import execute,passages
from bsa.workflow_status import diagnose
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]


class AnnualRuntimeFailureTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.exe=self.root/'engine.exe';self.exe.write_bytes(b'Synthetic path fixture;never launched')
        brief=self.root/'brief.md';brief.write_text('Run the explicit annual scenario and retain startup diagnostics.')
        row=passages(brief)[0]
        shutil.copyfile(ROOT/'examples/annual-energy/project.json',self.root/'project.json')
        shutil.copyfile(ROOT/'examples/annual-energy/USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw.gz',self.root/'weather.epw.gz')
        self.plan=self.root/'plan.json';self.plan.write_text(json.dumps(dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={row['id']:'requirement'},tasks=[dict(id='annual',kind='annual_energy',project='project.json',weather='weather.epw.gz')],requirements=[dict(id='R1',task='annual',passage=row['id'],quote=row['text'],acceptance='Actual annual execution or retained explicit startup failure;no fabricated values.')])) )

    def test_policy_and_other_import_errors_retain_distinct_unexecuted_diagnostics(self):
        for name,message,kind in [('policy','An Application Control policy has blocked this file.','application_control_block'),('missing','No module named openstudio','dependency_import_error')]:
            out=self.root/name
            with patch('bsa.annual_energy.subprocess.check_output') as version,patch('bsa.annual_energy.importlib.import_module',side_effect=ImportError(message)):
                result=execute(self.plan,out,energyplus=self.exe)
            version.assert_not_called();self.assertEqual(result['tasks']['annual']['status'],'fail')
            report=json.loads((out/'annual/runtime-failure.json').read_text());self.assertEqual(report['kind'],kind)
            self.assertFalse(report['simulation_executed']);self.assertFalse((out/'annual/baseline').exists())
            diagnosis=diagnose(self.plan,out);failure=diagnosis['actions'][0]['runtime_failures'][0]
            self.assertEqual(failure['kind'],kind);self.assertIn('approved environment',diagnosis['actions'][0]['next_action'])
            if name=='policy':
                report['kind']='dependency_import_error';path=out/'annual/runtime-failure.json';path.write_text(json.dumps(report))
                result['artifact_hashes']['annual/runtime-failure.json']=digest(path);(out/'workflow.json').write_text(json.dumps(result))
                with self.assertRaisesRegex(ProjectError,'classification differs'):diagnose(self.plan,out)

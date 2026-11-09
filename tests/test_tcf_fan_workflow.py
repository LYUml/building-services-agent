import json
from pathlib import Path
import runpy
import tempfile
import unittest
from bsa.workflow import execute,verify,validate_plan
from bsa.engine import ProjectError
ROOT=Path(__file__).resolve().parents[1];PDF=ROOT/'runs/tcf-fan-intake-v1/tcf-m300.pdf';EXTRACTION=ROOT/'runs/tcf-calibrated-vectors-v2';PYTHON=ROOT/'tools/pdf2plot-runtime/Scripts/python.exe'

@unittest.skipUnless(PDF.is_file() and PYTHON.is_file() and (EXTRACTION/'extraction.json').is_file(),'requires pinned source/runtime')
class TCFFanWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.addClassCleanup(cls.temp.cleanup);cls.root=Path(cls.temp.name)
        cls.runner=runpy.run_path(str(ROOT/'scripts/run_tcf_fan_workflow_demo.py'))
        cls.actual=cls.runner['run'](cls.root/'actual',PDF,EXTRACTION,PYTHON)

    def stage(self,label):return self.runner['stage'](self.root/label,PDF,EXTRACTION)

    def test_unified_cli_produces_pending_source_bound_diagnosis(self):
        root=self.root/'actual';r=self.actual
        self.assertEqual(r['states'],{'air':'pass','research':'pending','review':'pending'})
        self.assertTrue(verify(root/'workflow')['integrity_pass'])
        record=json.loads((root/'workflow/research/tcf-research.json').read_text())
        self.assertTrue(record['native_path_correspondence_pass']);self.assertTrue(record['interpolation_only_checks_pass']);self.assertFalse(record['calculated_checks_pass'])
        diagnosis=(root/'workflow/diagnosis.json').read_text()
        self.assertIn('manufacturer performance tolerance',diagnosis)
        _,inputs=validate_plan(root/'plan.json');self.assertIn(root/'extraction/disjoint-paths.json',inputs)
        self.assertIn(ROOT/'src/bsa/rectangular_fan.py',inputs)

    def test_missing_runtime_stays_pending_without_generated_results(self):
        r=self.runner['run'](self.root/'missing',PDF,EXTRACTION)
        self.assertEqual(r['states']['research'],'pending');self.assertFalse((self.root/'missing/workflow/research').exists())

    def test_upstream_failure_blocks_research(self):
        path=self.stage('upstream');p=path.parent/'project.json';data=json.loads(p.read_text());data['supply']['total_pressure_pa']=1;p.write_text(json.dumps(data))
        r=execute(path,path.parent/'workflow',pdf2plot_python=PYTHON)
        self.assertEqual(r['tasks']['air']['status'],'fail');self.assertEqual(r['tasks']['research']['status'],'pending');self.assertFalse((path.parent/'workflow/research').exists())

    def test_reordered_speed_metadata_cannot_relabel_a_curve(self):
        path=self.stage('relabel');report=path.parent/'extraction/extraction.json';r=json.loads(report.read_text());r['speed_labels_rpm'][0],r['speed_labels_rpm'][1]=r['speed_labels_rpm'][1],r['speed_labels_rpm'][0];report.write_text(json.dumps(r))
        r=execute(path,path.parent/'workflow',pdf2plot_python=PYTHON)
        self.assertEqual(r['tasks']['research']['status'],'fail');self.assertIn('speed labels differ',r['tasks']['research']['scope'])
        self.assertFalse((path.parent/'workflow/research/sensitivity').exists())

    def test_replacement_model_and_plan_executable_reject(self):
        path=self.stage('replace');original=path.read_text()
        for key,value in [('project','project.json'),('runtime','manufacturer.pdf')]:
            p=json.loads(original);p['tasks'][1][key]=value;path.write_text(json.dumps(p))
            with self.assertRaisesRegex(ProjectError,'replacements forbidden'):validate_plan(path)

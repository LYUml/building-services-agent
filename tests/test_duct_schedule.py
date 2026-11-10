import json
import tempfile
import unittest
from pathlib import Path
from bsa.duct_schedule import run


class DuctScheduleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root/'project.json'
        self.data = dict(basis='Synthetic assumptions, not code limits',
                         air=dict(density_kg_m3=1.2, viscosity_Pa_s=1.81e-5, roughness_m=.00009),
                         sections=[dict(id='S1', flow_m3_s=1, width_m=.8, height_m=.4,
                                        limits=dict(actual_velocity_m_s=8, friction_Pa_m=2, aspect_ratio=4))])

    def execute(self):
        self.project.write_text(json.dumps(self.data), encoding='utf-8')
        return run(self.project, self.root/'out')

    def test_saved_schedule_and_source(self):
        import csv, hashlib
        r = self.execute()
        self.assertEqual(r['status'], 'pass')
        self.assertFalse(r['design_accepted'])
        self.assertEqual(r['input_sha256'], hashlib.sha256(self.project.read_bytes()).hexdigest())
        with (self.root/'out/schedule.csv').open() as f:
            row = next(csv.DictReader(f))
        self.assertAlmostEqual(float(row['Velocity m/s']), 3.125)
        self.assertEqual(float(row['Flow L/s']), 1000)
        with self.assertRaises(ValueError): run(self.project, self.root/'out')

    def test_failed_limit_is_retained(self):
        self.data['sections'][0]['limits']['actual_velocity_m_s'] = 2
        r = self.execute()
        self.assertEqual(r['status'], 'fail')
        self.assertEqual(r['sections'][0]['failures'], ['actual_velocity_m_s'])
        self.assertTrue((self.root/'out/schedule.csv').exists())

    def test_invalid_batch_creates_no_output(self):
        self.data['sections'] *= 2
        with self.assertRaises(ValueError): self.execute()
        self.assertFalse((self.root/'out').exists())

        self.data['sections'] = self.data['sections'][:1]
        self.data['sections'][0]['limits']['friction_Pa_m'] = float('nan')
        with self.assertRaises(ValueError): self.execute()
        self.assertFalse((self.root/'out').exists())

    def test_workflow_gates_and_source_integrity(self):
        from bsa.workflow import execute, verify
        from bsa.cli import digest
        for fail in (False, True):
            with self.subTest(fail=fail):
                self.data['sections'][0]['limits']['actual_velocity_m_s'] = 2 if fail else 8
                self.project.write_text(json.dumps(self.data), encoding='utf-8')
                brief = self.root/'brief.md'
                brief.write_text('Calculate duct sections and review acceptance.\n', encoding='utf-8')
                plan = dict(version=1, brief='brief.md', brief_sha256=digest(brief),
                            passage_dispositions={'P001':'requirement'},
                            tasks=[dict(id='ducts', kind='duct_schedule', project='project.json'),
                                   dict(id='review', kind='manual', requires_pass=['ducts'], description='Engineering acceptance pending')],
                            requirements=[dict(id=id, passage='P001', quote='Calculate duct sections and review acceptance.', task=task, acceptance='Separate calculation and engineering review') for id,task in [('R1','ducts'),('R2','review')]])
                path = self.root/'plan.json'
                path.write_text(json.dumps(plan), encoding='utf-8')
                out = self.root/('failed' if fail else 'passed')
                result = execute(path, out)
                self.assertEqual(result['tasks']['ducts']['status'], 'fail' if fail else 'pass')
                self.assertEqual(result['tasks']['review']['status'], 'pending')
                if fail: self.assertIn('ducts', result['tasks']['review']['scope'])
                self.assertFalse(result['design_accepted'])
                self.assertTrue(verify(out)['integrity_pass'])
                self.project.write_text('{}', encoding='utf-8')
                self.assertFalse(verify(out)['integrity_pass'])

    def candidates(self):
        section=self.data['sections'][0]
        section.pop('width_m');section.pop('height_m')
        section.update(candidate_basis='Synthetic size options, not products',candidates=[dict(id='small',width_m=.2,height_m=.2),dict(id='large',width_m=.8,height_m=.4)])
        return section

    def test_candidate_selection_retains_rejected_options(self):
        section=self.candidates()
        r=self.execute();row=r['sections'][0]
        self.assertEqual(r['status'],'pass')
        self.assertEqual(row['selection']['selected']['id'],'large')
        self.assertIn('actual_velocity_m_s',row['selection']['candidates'][0]['failures'])
        self.assertEqual(row['inputs']['width_m'],.8)
        self.assertFalse(r['design_accepted'])

    def test_no_feasible_size_saves_failure_without_fake_dimensions(self):
        import csv
        section=self.candidates();section['candidates']=section['candidates'][:1]
        r=self.execute();row=r['sections'][0]
        self.assertEqual(r['status'],'fail')
        self.assertIsNone(row['calculation'])
        self.assertIsNone(row['selection']['selected'])
        self.assertNotIn('width_m',row['inputs'])
        with (self.root/'out/schedule.csv').open() as f:record=next(csv.DictReader(f))
        self.assertEqual(record['Width mm'],'')
        self.assertEqual(record['Failed criteria'],'no_feasible_size')

    def test_candidate_replacement_and_missing_basis_rejected(self):
        section=self.candidates();section['width_m']=.8
        with self.assertRaisesRegex(ValueError,'not both'):self.execute()
        del section['width_m'];section['candidate_basis']=''
        with self.assertRaisesRegex(ValueError,'candidate size'):self.execute()

import unittest
from shapely.geometry import box,mapping
from bsa.air_allocation import prepare
from bsa.air_load import UNITS


class AirAllocationTests(unittest.TestCase):
    def test_layout_change_updates_flows_and_preserves_totals(self):
        values=dict(area=100,cooling_allowance=200,sensible_fraction=.8,density=1.25,specific_heat=1000,temperature_difference=10)
        inputs={k:dict(value=v,unit=UNITS[k],source='Synthetic test',classification='assumed') for k,v in values.items()}
        for right,expected_fraction in [(5,.3),(7,.4)]:
            with self.subTest(right=right):
                r=prepare(mapping(box(0,0,10,4)),[dict(id='A',center_m=[1,2]),dict(id='B',center_m=[right,2])],inputs,.4)
                self.assertAlmostEqual(r['terminals'][0]['maximum_flow_L_s'],1280*expected_fraction)
                self.assertAlmostEqual(r['terminals'][0]['minimum_flow_L_s'],1280*expected_fraction*.4)
                self.assertAlmostEqual(r['checks']['allocated_flow_L_s'],1280)
                self.assertFalse(r['design_accepted'])
                self.assertEqual(r['load']['inputs'],inputs)

    def test_invalid_turndown_precedes_calculation(self):
        for value in (0,1.1,True,float('nan')):
            with self.subTest(value=value),self.assertRaises(ValueError):prepare({},[],{},value)

    def test_project_source_guard_and_saved_output(self):
        import tempfile,json,hashlib
        from pathlib import Path
        from bsa.air_allocation import run
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);boundary=root/'boundary.json'
            boundary.write_text(json.dumps(mapping(box(0,0,10,4))),encoding='utf-8')
            values=dict(area=100,cooling_allowance=200,sensible_fraction=.8,density=1.25,specific_heat=1000,temperature_difference=10)
            data=dict(boundary='boundary.json',boundary_sha256=hashlib.sha256(boundary.read_bytes()).hexdigest(),geometry_basis='Synthetic metre polygon',terminals=[dict(id='A',center_m=[1,2]),dict(id='B',center_m=[5,2])],load_inputs={k:dict(value=v,unit=UNITS[k],source='Synthetic',classification='assumed') for k,v in values.items()},turndown=.4)
            project=root/'project.json';project.write_text(json.dumps(data),encoding='utf-8')
            result=run(project,root/'out')
            self.assertEqual(json.loads((root/'out/allocation.json').read_text())['checks'],result['checks'])
            with self.assertRaises(ValueError):run(project,root/'out')
            boundary.write_text('{}',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):run(project,root/'changed')
            self.assertFalse((root/'changed').exists())

    def test_workflow_geometry_integrity_and_failed_allocation_gate(self):
        import tempfile,json,hashlib
        from pathlib import Path
        from bsa.workflow import execute,verify,validate_plan
        from bsa.engine import ProjectError
        from bsa.cli import digest
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            boundary=root/'boundary.json';boundary.write_text(json.dumps(mapping(box(0,0,10,4))))
            brief=root/'brief.md';brief.write_text('Allocate flow and review design.\n')
            values=dict(area=100,cooling_allowance=200,sensible_fraction=.8,density=1.25,specific_heat=1000,temperature_difference=10)
            data=dict(boundary='boundary.json',boundary_sha256=digest(boundary),geometry_basis='Synthetic metre polygon',terminals=[dict(id='A',center_m=[1,2]),dict(id='B',center_m=[5,2])],load_inputs={k:dict(value=v,unit=UNITS[k],source='Synthetic',classification='assumed') for k,v in values.items()},turndown=.4)
            project=root/'project.json'
            plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={'P001':'requirement'},tasks=[dict(id='allocation',kind='air_allocation',project='project.json'),dict(id='review',kind='manual',requires_pass=['allocation'],description='Engineering review pending')],requirements=[dict(id='R'+str(i),passage='P001',quote='Allocate flow and review design.',task=task,acceptance='Separate numerical and engineering review') for i,task in enumerate(('allocation','review'))])
            path=root/'plan.json';path.write_text(json.dumps(plan))
            for valid in (True,False):
                data['terminals'][1]['center_m']=[5,2] if valid else [50,2]
                project.write_text(json.dumps(data))
                out=root/('valid' if valid else 'invalid')
                r=execute(path,out)
                self.assertEqual(r['tasks']['allocation']['status'],'pass' if valid else 'fail')
                self.assertEqual(r['tasks']['review']['status'],'pending')
                if not valid:self.assertIn('allocation',r['tasks']['review']['scope'])
                self.assertFalse(r['design_accepted'])
                self.assertTrue(verify(out)['integrity_pass'])
                boundary.write_text('{}')
                self.assertFalse(verify(out)['integrity_pass'])
                with self.assertRaisesRegex(ProjectError,'hash mismatch'):validate_plan(path)
                boundary.write_text(json.dumps(mapping(box(0,0,10,4))))
            data['boundary']='../outside.json';project.write_text(json.dumps(data))
            with self.assertRaises(ProjectError):validate_plan(path)

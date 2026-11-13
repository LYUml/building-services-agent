import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import ezdxf
from bsa import autocad_schedule as adapter
from bsa.cli import digest

ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless((adapter.UPSTREAM/'.git').exists(),'requires pinned upstream checkout')
class AutoCADScheduleTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(temp.cleanup);self.root=Path(temp.name)
        env=patch.dict(os.environ,{'BSA_PROJECT_ROOT':str(self.root)});env.start();self.addCleanup(env.stop)
        doc=ezdxf.new('R2018');doc.units=6;doc.layers.new('SCHEDULE')
        m=doc.modelspace();line=m.add_line((0,0),(2,0));self.base=m.add_circle((4,4),1).dxf.handle
        block=doc.blocks.new('SOURCE_BLOCK');block.add_line((0,0),(1,1));m.add_blockref('SOURCE_BLOCK',(5,5))
        self.cells=[m.add_text(v,dxfattribs={'insert':(i,3),'layer':'SCHEDULE'}).dxf.handle for i,v in enumerate(['S','old q','old size','old v','old f'])]
        self.source=self.root/'source.dxf';doc.saveas(self.source)
        spec=dict(source_sha256=digest(self.source),basis='Explicit synthetic section binding',sections=dict(S=dict(line_handle=line.dxf.handle,from_m=[0,0,0],to_m=[2,0,0],cells=[dict(handle=h,expected_text=doc.entitydb[h].dxf.text) for h in self.cells])))
        self.binding=self.root/'binding.json';self.binding.write_text(json.dumps(spec))
        self.project=self.root/'duct.json';self.data=dict(basis='Synthetic defined constant section',air=dict(density_kg_m3=1.2,viscosity_Pa_s=1.81e-5,roughness_m=.00009),sections=[dict(id='S',flow_m3_s=1,width_m=.8,height_m=.4,limits=dict(actual_velocity_m_s=8,friction_Pa_m=2,aspect_ratio=4))]);self.project.write_text(json.dumps(self.data))
        self.out=self.root/'written'

    def execute(self):return adapter.run(self.source,self.project,self.binding,self.out)

    def test_actual_upstream_writes_fresh_schedule_and_preserves_base(self):
        before=self.source.read_bytes();record=self.execute();self.assertEqual(record['status'],'written')
        checked=adapter.verify(self.out);self.assertEqual(checked['sections'],1);self.assertEqual(checked['changed_cells'],4)
        self.assertFalse(checked['native_reopen_pass']);self.assertFalse(checked['design_accepted'])
        doc=ezdxf.readfile(self.out/'Supply Air Distribution.dxf')
        self.assertEqual(doc.entitydb[self.cells[2]].dxf.text,'800 x 400');self.assertEqual(doc.entitydb[self.base].dxf.radius,1)
        self.assertEqual(self.source.read_bytes(),before)

    def test_shared_cli_executes_and_verifies_actual_upstream(self):
        import contextlib, io
        from bsa.cli import main
        before=self.source.read_bytes()
        for args in (['autocad-sheet','run','--source',self.source,'--project',self.project,'--binding',self.binding,'--out',self.out], ['autocad-sheet','verify',self.out]):
            with patch('sys.argv',['bsa',*map(str,args)]),contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(),0)
            result=json.loads(output.getvalue());self.assertFalse(result['design_accepted'])
        self.assertTrue(result['integrity_pass']);self.assertEqual(self.source.read_bytes(),before)
        self.source.write_bytes(self.source.read_bytes()+b'changed')
        with patch('sys.argv',['bsa','autocad-sheet','verify',str(self.out)]),contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as failed:main()
        self.assertEqual(failed.exception.code,2)

    @unittest.skipUnless((ROOT/'.venv/Scripts/bsa.exe').exists(),'requires installed Windows entry')
    def test_installed_command_runs_actual_worker_and_verifier(self):
        import subprocess
        command=str(ROOT/'.venv/Scripts/bsa.exe')
        for args in (['autocad-sheet','run','--source',self.source,'--project',self.project,'--binding',self.binding,'--out',self.out],['autocad-sheet','verify',self.out]):
            completed=subprocess.run([command,*map(str,args)],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(completed.returncode,0,completed.stdout+completed.stderr)
            result=json.loads(completed.stdout);self.assertFalse(result['design_accepted'])
        self.assertTrue(result['integrity_pass'])

    def test_shared_cli_failed_limits_return_failure_without_writer(self):
        import contextlib, io
        from bsa.cli import main
        self.data['sections'][0]['limits']['actual_velocity_m_s']=.01
        self.project.write_text(json.dumps(self.data))
        args=['bsa','autocad-sheet','run','--source',self.source,'--project',self.project,'--binding',self.binding,'--out',self.out]
        with patch('sys.argv',list(map(str,args))),contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(),2)
        result=json.loads(output.getvalue());self.assertEqual(result['status'],'failed')
        self.assertFalse(result['native_reopen_pass']);self.assertFalse((self.out/'writer.json').exists())

    def test_failed_source_section_never_reaches_writer(self):
        self.data['sections'][0]['limits']['actual_velocity_m_s']=.01;self.project.write_text(json.dumps(self.data))
        record=self.execute();self.assertEqual(record['status'],'failed');self.assertFalse((self.out/'writer.json').exists())
        with self.assertRaises(ValueError):adapter.verify(self.out)

    def test_rehashed_forged_cell_cannot_replace_source_calculation(self):
        self.execute();path=self.out/'Supply Air Distribution.dxf';doc=ezdxf.readfile(path);doc.entitydb[self.cells[1]].dxf.text='9999';doc.saveas(path)
        writer=self.out/'writer.json';d=json.loads(writer.read_text());d['target_sha256']=digest(path);writer.write_text(json.dumps(d))
        receipt=self.out/'schedule-drawing.json';d=json.loads(receipt.read_text());d['artifacts'][path.name]=digest(path);d['artifacts']['writer.json']=digest(writer);receipt.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError,'Original drawing or approved edit'):adapter.verify(self.out)

    def test_rehashed_counts_and_injected_allocation_lineage_reject(self):
        self.execute();receipt=self.out/'schedule-drawing.json';original=receipt.read_bytes()
        data=json.loads(original);data['sections']=999;receipt.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'coverage counts'):adapter.verify(self.out)
        receipt.write_bytes(original)
        study=self.out/'schedule/results.json';data=json.loads(study.read_text());data['allocation_input']={'invented': '0'*64};study.write_text(json.dumps(data))
        data=json.loads(original);data['artifacts']['schedule/results.json']=digest(study);receipt.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'Allocation lineage'):adapter.verify(self.out)

    def test_changed_source_and_outside_output_reject(self):
        with self.assertRaises(ValueError):adapter.run(self.source,self.project,self.binding,ROOT/'runs/outside-project')
        self.execute();self.project.write_text(self.project.read_text()+' ')
        with self.assertRaisesRegex(ValueError,'pins changed'):adapter.verify(self.out)

if __name__=='__main__':unittest.main()

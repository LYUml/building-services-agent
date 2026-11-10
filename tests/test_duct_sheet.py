import tempfile,json,unittest
from pathlib import Path
import ezdxf
from bsa.cli import digest
from bsa.duct_sheet import run

class DuctSheetTests(unittest.TestCase):
 def test_saved_update_and_invalid_binding_controls(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);d=ezdxf.new();d.units=6;m=d.modelspace();line=m.add_line((0,0),(2,0));base=m.add_circle((4,4),1)
   cells=[m.add_text(v,dxfattribs={'insert':(i,3)}) for i,v in enumerate(['S','old q','old size','old v','old f'])]
   source=root/'source.dxf';d.saveas(source)
   row=dict(id='S',inputs=dict(flow_m3_s=1,width_m=.8,height_m=.4),calculation=dict(actual_velocity_m_s=3.125,friction_Pa_m=.2),failures=[])
   schedule=root/'schedule.json';schedule.write_text(json.dumps(dict(status='pass',sections=[row])))
   spec=dict(source_sha256=digest(source),schedule_sha256=digest(schedule),basis='Synthetic single-line sheet',sections=dict(S=dict(line_handle=line.dxf.handle,from_m=[0,0,0],to_m=[2,0,0],cells=[dict(handle=e.dxf.handle,expected_text=e.dxf.text) for e in cells])))
   binding=root/'binding.json';binding.write_text(json.dumps(spec))
   r=run(source,schedule,binding,root/'ok');self.assertTrue(r['saved_dxf_correspondence']);self.assertFalse(r['native_reopen_pass'])
   saved=ezdxf.readfile(root/'ok/Supply Air Distribution.dxf');self.assertEqual(saved.entitydb[cells[2].dxf.handle].dxf.text,'800 x 400')
   self.assertEqual(saved.entitydb[base.dxf.handle].dxf.radius,1)
   spec['sections']['S']['to_m']=[3,0,0];binding.write_text(json.dumps(spec))
   with self.assertRaisesRegex(ValueError,'geometry differs'):run(source,schedule,binding,root/'bad-geometry')
   spec['sections']['S']['to_m']=[2,0,0];spec['sections']['S']['cells'][1]['expected_text']='wrong';binding.write_text(json.dumps(spec))
   with self.assertRaisesRegex(ValueError,'cell or identity'):run(source,schedule,binding,root/'bad-cell')
   schedule.write_text(json.dumps(dict(status='fail',sections=[row])));spec['schedule_sha256']=digest(schedule);binding.write_text(json.dumps(spec))
   with self.assertRaisesRegex(ValueError,'Passing'):run(source,schedule,binding,root/'failed-study')

 def test_inherited_workflow_and_failed_producer(self):
  from bsa.workflow import execute,verify,validate_plan
  from bsa.engine import ProjectError
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder).resolve();d=ezdxf.new();d.units=6;m=d.modelspace();line=m.add_line((0,0),(2,0))
   cells=[m.add_text(v,dxfattribs={'insert':(i,3)}) for i,v in enumerate(['S','q','size','v','f'])]
   source=root/'source.dxf';d.saveas(source)
   spec=dict(source_sha256=digest(source),basis='Synthetic single-line sheet',sections=dict(S=dict(line_handle=line.dxf.handle,from_m=[0,0,0],to_m=[2,0,0],cells=[dict(handle=e.dxf.handle,expected_text=e.dxf.text) for e in cells])))
   binding=root/'binding.json';binding.write_text(json.dumps(spec))
   duct=dict(basis='Synthetic trial',air=dict(density_kg_m3=1.2,viscosity_Pa_s=1.81e-5,roughness_m=.00009),sections=[dict(id='S',flow_m3_s=1,width_m=.8,height_m=.4,limits=dict(actual_velocity_m_s=8,friction_Pa_m=2,aspect_ratio=4))])
   project=root/'duct.json';project.write_text(json.dumps(duct))
   brief=root/'brief.md';brief.write_text('Size ducts and update drawing.\n')
   plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={'P001':'requirement'},tasks=[dict(id='duct',kind='duct_schedule',project='duct.json'),dict(id='sheet',kind='duct_sheet',depends_on='duct',drawing='source.dxf',binding='binding.json')],requirements=[dict(id='R'+str(i),passage='P001',quote='Size ducts and update drawing.',task=t,acceptance='Scoped execution only; full acceptance pending') for i,t in enumerate(('duct','sheet'))])
   (root/'native.json').write_text(json.dumps(dict(layers=['0'],sheet={})))
   plan['tasks'].append(dict(id='native',kind='duct_sheet_native',depends_on='sheet',settings='native.json'))
   plan['requirements'].append(dict(plan['requirements'][0],id='RN',task='native'))
   path=root/'plan.json';path.write_text(json.dumps(plan))
   r=execute(path,root/'pass');self.assertEqual(r['tasks']['sheet']['status'],'pass');self.assertFalse(r['design_accepted'])
   sheet=json.loads((root/'pass/sheet/drawing-update.json').read_text());self.assertFalse(sheet['native_reopen_pass'])
   self.assertIn(str(root/'pass/duct/results.json'),sheet['inputs']);self.assertTrue(verify(root/'pass')['integrity_pass'])
   self.assertEqual(r['tasks']['native']['status'],'pending')
   self.assertIn('AutoCAD runtime not supplied',r['tasks']['native']['scope'])
   self.assertFalse((root/'pass/native').exists())
   from bsa.duct_sheet_native import run as native_run
   fake_exe=root/'fake.exe';fake_exe.write_bytes(b'Runtime pin test only; never executed')
   def changed_native(*args,**kwargs):
    Path(args[0]).write_text('changed')
    return native_run(*args,**kwargs)
   with patch('bsa.duct_sheet_native.run',side_effect=changed_native):
    native_result=execute(path,root/'native-tamper',autocad=fake_exe)
   self.assertEqual(native_result['tasks']['native']['status'],'fail')
   self.assertIn('producer changed',native_result['tasks']['native']['scope'])
   self.assertFalse((root/'native-tamper/native').exists())
   original=run
   def tamper(*args,**kwargs):
    Path(args[1]).write_text('{}')
    return original(*args,**kwargs)
   with patch('bsa.duct_sheet.run',side_effect=tamper):r=execute(path,root/'tamper')
   self.assertEqual(r['tasks']['sheet']['status'],'fail');self.assertIn('producer changed',r['tasks']['sheet']['scope'])
   self.assertFalse((root/'tamper/sheet').exists())
   duct['sections'][0]['limits']['actual_velocity_m_s']=.1;project.write_text(json.dumps(duct))
   r=execute(path,root/'failed');self.assertEqual(r['tasks']['duct']['status'],'fail');self.assertEqual(r['tasks']['sheet']['status'],'pending')
   self.assertFalse((root/'failed/sheet').exists())
   self.assertEqual(r['tasks']['native']['status'],'pending')
   spec['schedule_sha256']='replacement';binding.write_text(json.dumps(spec))
   with self.assertRaisesRegex(ProjectError,'override'):validate_plan(path)

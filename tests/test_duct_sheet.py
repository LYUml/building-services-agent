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

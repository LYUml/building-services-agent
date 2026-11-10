import json,unittest
from pathlib import Path
from bsa.hvac_report import run,compose

class HVACReportTests(unittest.TestCase):
 def test_real_workflow_export_and_stale_evidence_rejection(self):
  from tests.test_allocation_lookup import AllocationLookupTests
  fixture=AllocationLookupTests();fixture.setUp();self.addCleanup(fixture.temp.cleanup)
  root=fixture.root
  duct=dict(basis='Synthetic <design> & assumptions',air=dict(density_kg_m3=1.2,viscosity_Pa_s=1.81e-5,roughness_m=.00009),tree=dict(root='R',sections=[dict(id='SA',**{'from':'R','to':'A'}),dict(id='SB',**{'from':'R','to':'B'})],leaf_terminals=dict(A=['A'],B=['B']),basis='Synthetic'),sections=[dict(id=k,width_m=.8,height_m=.4,limits=dict(actual_velocity_m_s=8,friction_Pa_m=2,aspect_ratio=4)) for k in ('SA','SB')])
  (root/'ducts.json').write_text(json.dumps(duct));fixture.plan['tasks'].append(dict(id='ducts',kind='duct_schedule',project='ducts.json',depends_on='allocation'));fixture.plan['requirements'].append(dict(fixture.plan['requirements'][0],id='RD',task='ducts'))
  fixture.run_plan('workflow');directory=root/'workflow';r=run(directory,root/'report')
  self.assertEqual(r['counts'],dict(terminal_direction_rows=2,leaf_groups=2,duct_sections=2,requirements=3));self.assertFalse(r['design_accepted'])
  text=(root/'report/HVAC System Design.html').read_text();self.assertIn('&lt;design&gt; &amp; assumptions',text);self.assertIn('pending review',text)
  import reportlab
  from bsa.hvac_report_pdf import run as render
  font=Path(reportlab.__file__).parent/'fonts/Vera.ttf'
  pdf=render(root/'report',root/'pdf',font)
  self.assertEqual(pdf['numerical_rows_checked'],7)
  self.assertEqual(pdf['requirement_rows'],3)
  self.assertFalse(pdf['design_accepted'])
  with self.assertRaises(ValueError):render(root/'report',root/'pdf',font)
  from bsa.hvac_package import run as package
  bundled=package(root/'plan.json',root/'package',font=font)
  self.assertEqual(bundled['status'],'review_required');self.assertFalse(bundled['design_accepted'])
  self.assertTrue((root/'package/delivery-review.json').is_file())
  self.assertEqual(bundled['stages']['report_pdf']['numerical_rows_checked'],7)
  with self.assertRaises(ValueError):package(root/'plan.json',root/'package',font=font)
  raw=(root/'allocation.json').read_bytes();changed=json.loads(raw);changed['terminals'][0]['center_m']=[99,99]
  (root/'allocation.json').write_text(json.dumps(changed))
  failed=package(root/'plan.json',root/'failed-package',font=font)
  self.assertEqual(failed['status'],'incomplete');self.assertIn('report',failed['stage_errors'])
  self.assertFalse((root/'failed-package/report-pdf').exists())
  self.assertTrue(failed['unresolved_tasks'])
  (root/'allocation.json').write_bytes(raw)
  allocation=json.loads((directory/'allocation/allocation.json').read_text());lookup=json.loads((directory/'lookup/terminal-results.json').read_text());schedule=json.loads((directory/'ducts/results.json').read_text());workflow=json.loads((directory/'workflow.json').read_text())
  lookup['terminals'][0]['directions']['east']['cases']['maximum']['flow_L_s']+=1
  with self.assertRaisesRegex(ValueError,'flow differs'):compose(workflow,allocation,lookup,schedule)
  (directory/'ducts/results.json').write_text('{}')
  with self.assertRaisesRegex(ValueError,'stale or changed'):run(directory,root/'stale')
  self.assertFalse((root/'stale').exists())

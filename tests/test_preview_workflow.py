import json
from pathlib import Path
import shutil
import tempfile
import unittest
import ifcopenshell
import ifcopenshell.api as api
from bsa.bim import run as author
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.workflow import execute, verify, validate_plan, inventory_source_bindings

ROOT=Path(__file__).resolve().parents[1]


class PreviewWorkflowTests(unittest.TestCase):
    def test_actual_information_gate_and_preview(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp)
            shutil.copyfile(ROOT/'examples/circulation-ifc/model.json',root/'model.json')
            shutil.copyfile(ROOT/'examples/ids/pump-selection.ids',root/'contract.ids')
            author(root/'model.json',root/'authored')
            model=ifcopenshell.open(str(root/'authored/model.ifc'))
            pump=model.by_type('IfcPump')[0]
            ps=api.run('pset.add_pset',model,product=pump,name='BSA_ScreenedPumpCurve')
            api.run('pset.edit_pset',model,pset=ps,properties={k:'Synthetic presence fixture' for k in ('CandidateId','HeadCurve_m3_s_m','ScreeningReportSHA256','Source')})
            model.write(str(root/'source.ifc'))
            brief=root/'brief.md';brief.write_text('Check information and generate a geometric preview for separate visual review.')
            tasks=[dict(id='information',kind='ids_check',ifc='source.ifc',ids='contract.ids'),
                   dict(id='preview',kind='ifc_preview',ifc='source.ifc',guid=pump.GlobalId,requires_pass=['information'])]
            plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={'P001':'requirement'},tasks=tasks,
                      requirements=[dict(id=t['id'],task=t['id'],passage='P001',quote=brief.read_text(),acceptance=brief.read_text()) for t in tasks])
            path=root/'plan.json';path.write_text(json.dumps(plan))
            r=execute(path,root/'positive')
            self.assertTrue(r['execution_pass'],r['tasks'])
            self.assertTrue(verify(root/'positive')['integrity_pass'])
            preview=json.loads((root/'positive/preview/preview.json').read_text())
            self.assertEqual(preview['ifc_sha256'],digest(root/'source.ifc'))
            self.assertEqual(preview['visual_review'],'pending')
            self.assertFalse(preview['design_accepted'])
            api.run('pset.edit_pset',model,pset=ps,properties={'Source':None})
            model.write(str(root/'source.ifc'))
            r=execute(path,root/'negative')
            self.assertEqual(r['tasks']['information']['status'],'fail')
            self.assertEqual(r['tasks']['preview']['status'],'pending')
            self.assertFalse((root/'negative/preview').exists())
            tasks[-1]['depends_on']='information';path.write_text(json.dumps(plan))
            with self.assertRaisesRegex(ProjectError,'exactly one'):validate_plan(path)

    def test_transitive_ids_and_inventory_source_identity(self):
        tasks=[dict(id='a',kind='product_ports'),dict(id='b',kind='product_ports'),
               dict(id='ids',kind='ids_check',depends_on='a'),
               dict(id='review',kind='manual',requires_pass=['ids']),
               dict(id='preview',kind='ifc_preview',depends_on='a',requires_pass=['review'])]
        # Only this unit graph tests producer identities; full plans validate dependencies separately.
        tasks[0]['kind']=tasks[1]['kind']='bim'
        rows=inventory_source_bindings(tasks,ROOT)
        self.assertEqual(rows[-1]['check'],'ids')
        tasks[-1]['depends_on']='b'
        with self.assertRaisesRegex(ProjectError,'different model'):inventory_source_bindings(tasks,ROOT)
        tasks[2]['kind']='ifc_query'
        with self.assertRaisesRegex(ProjectError,'different model'):inventory_source_bindings(tasks,ROOT)

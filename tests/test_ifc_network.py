import json
from pathlib import Path
import tempfile
import unittest
import shutil
from bsa.cli import digest
from bsa.workflow import execute,passages
import ifcopenshell
from bsa.bim import run as author
from bsa.ifc_network import run,verify_producer
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'examples/hk-plumbing-pumps'


class SavedIFCNetworkTests(unittest.TestCase):
    def test_fresh_analysis_pressure_failure_and_solid_tampering(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp);author(SOURCE/'route-model.json',root/'author')
            ifc=root/'author/model.ifc'
            args=(SOURCE/'route-template.json',SOURCE/'route-model.json',SOURCE/'route-binding.json')
            result=run(*args,ifc,root/'positive');self.assertTrue(result['calculated_checks_pass'])
            proof=verify_producer(root/'positive',*args,ifc)
            self.assertTrue(proof['saved_geometry_reconciled'])
            generated=root/'positive/network-input.json'
            changed=json.loads(generated.read_text());changed['segments'][0]['length_m']+=1
            generated.write_text(json.dumps(changed))
            report=root/'positive/ifc-network.json';manifest=json.loads(report.read_text())
            manifest['artifacts']['network-input.json']=digest(generated);report.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ProjectError,'source reconstruction'):
                verify_producer(root/'positive',*args,ifc)
            low=json.loads(args[0].read_text());low['supply']['total_pressure_pa']=100000
            (root/'low.json').write_text(json.dumps(low))
            result=run(root/'low.json',*args[1:],ifc,root/'low')
            self.assertFalse(result['calculated_checks_pass']);self.assertTrue(result['saved_ifc_geometry_match'])
            for name in ('route-model.json','route-binding.json'):
                shutil.copyfile(SOURCE/name,root/name)
            shutil.copyfile(ROOT/'examples/water-riser/drawing-settings.json',root/'drawing.json')
            brief=root/'brief.md';brief.write_text('Synthetic low-pressure case must block saved-model drawing.')
            row=passages(brief)[0]
            tasks=[dict(id='analysis',kind='ifc_network',ifc='author/model.ifc',project='low.json',model='route-model.json',binding='route-binding.json'),
                   dict(id='drawing',kind='ifc_drawing',ifc='author/model.ifc',settings='drawing.json',requires_pass=['analysis'])]
            plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={row['id']:'requirement'},tasks=tasks,
                      requirements=[dict(id=t['id'],task=t['id'],passage=row['id'],quote=row['text'],acceptance=row['text']) for t in tasks])
            (root/'plan.json').write_text(json.dumps(plan))
            workflow=execute(root/'plan.json',root/'blocked')
            self.assertEqual(workflow['tasks']['analysis']['status'],'fail')
            self.assertEqual(workflow['tasks']['drawing']['status'],'pending')
            self.assertFalse((root/'blocked/drawing').exists())
            f=ifcopenshell.open(str(ifc));f.by_type('IfcExtrudedAreaSolid')[0].Depth+=.1
            f.write(str(root/'changed.ifc'))
            with self.assertRaisesRegex(ProjectError,'profiles/ports'):
                run(*args,root/'changed.ifc',root/'changed')
            self.assertFalse((root/'changed').exists())

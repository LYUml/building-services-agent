import json
from pathlib import Path
import shutil
import tempfile
import unittest
from bsa.engine import ProjectError
from bsa.workflow import regulatory_source_bindings

ROOT=Path(__file__).resolve().parents[1]


class FluidBindingTests(unittest.TestCase):
    def test_chain_reverse_and_sibling_conflicts(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp)
            for name in ('project.json','thermal-duty.json','regulatory-bases.json'):
                shutil.copyfile(ROOT/'examples/hvac-circulation'/name,root/name)
            for layout in ('forward','reverse','siblings'):
                duty=dict(id='duty',kind='circulation_duty',project='project.json',basis='thermal-duty.json')
                rules=dict(id='rules',kind='epanet_pipe_regulations',project='project.json',basis='regulatory-bases.json')
                if layout=='forward':rules['requires_pass']=['duty'];tasks=[duty,rules]
                elif layout=='reverse':duty['requires_pass']=['rules'];tasks=[rules,duty]
                else:tasks=[duty,rules,dict(id='water',kind='water_network',project='project.json',requires_pass=['duty','rules'])]
                basis=json.loads((root/'regulatory-bases.json').read_text());basis['density']['value']=1000
                (root/'regulatory-bases.json').write_text(json.dumps(basis))
                bindings=regulatory_source_bindings(tasks,root)
                self.assertTrue(any(b['field']=='density_consistency' for b in bindings))
                basis['density']['value']=998;(root/'regulatory-bases.json').write_text(json.dumps(basis))
                with self.subTest(layout=layout),self.assertRaisesRegex(ProjectError,'conflicting density'):
                    regulatory_source_bindings(tasks,root)

    def test_inconsistent_targets_in_one_fluid_model(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp);shutil.copyfile(ROOT/'examples/hvac-circulation/project.json',root/'project.json')
            b=json.loads((ROOT/'examples/hvac-circulation/thermal-duty.json').read_text())
            second=json.loads(json.dumps(b['targets'][0]));second['link']='RETURN-PIPE';second['density']['value']=998
            b['targets'].append(second);(root/'basis.json').write_text(json.dumps(b))
            with self.assertRaisesRegex(ProjectError,'conflicting density'):
                regulatory_source_bindings([dict(id='duty',kind='circulation_duty',project='project.json',basis='basis.json')],root)

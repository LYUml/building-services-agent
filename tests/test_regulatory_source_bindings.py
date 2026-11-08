from pathlib import Path
import tempfile
import unittest
from bsa.engine import ProjectError
from bsa.workflow import regulatory_source_bindings

ROOT=Path(__file__).resolve().parents[1]


class RegulatorySourceBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for name,value in [('project.json',b'original electrical'),('copy.json',b'original electrical'),('changed.json',b'changed electrical'),('geometry.json',b'original room'),('other-geometry.json',b'changed room')]:
            (self.root/name).write_bytes(value)
        self.check=dict(id='rules',kind='lighting_regulations',project='project.json',geometry='geometry.json')
        self.model=dict(id='model',kind='electrical_coordination',project='project.json',geometry='geometry.json',requires_pass=['rules'])

    def test_known_shared_fields_record_hashes_and_allow_identical_copy(self):
        self.model['project']='copy.json'
        rows=regulatory_source_bindings([self.check,self.model],self.root)
        self.assertEqual({r['field'] for r in rows},{'project','geometry'})
        self.assertTrue(all(len(r['sha256'])==64 for r in rows))

    def test_mismatched_project_or_geometry_rejected(self):
        for field,changed in [('project','changed.json'),('geometry','other-geometry.json')]:
            with self.subTest(field=field),self.assertRaisesRegex(ProjectError,'different '+field):
                regulatory_source_bindings([self.check,dict(self.model,**{field:changed})],self.root)

    def test_gate_through_manual_checkpoint_still_matches_original_sources(self):
        checkpoint=dict(id='checkpoint',kind='manual',requires_pass=['rules'])
        model=dict(self.model,requires_pass=['checkpoint'],project='changed.json')
        with self.assertRaisesRegex(ProjectError,'different project'):
            regulatory_source_bindings([self.check,checkpoint,model],self.root)

    def test_native_consumer_uses_its_actual_producer_inputs(self):
        producer=dict(self.model,requires_pass=[],project='changed.json')
        native=dict(id='native',kind='native_cad',depends_on='model',requires_pass=['rules'])
        with self.assertRaisesRegex(ProjectError,'consumer native'):
            regulatory_source_bindings([self.check,producer,native],self.root)

    def test_unrelated_independent_task_is_not_implicitly_gated(self):
        independent=dict(self.model,requires_pass=[],project='changed.json')
        self.assertEqual(regulatory_source_bindings([self.check,independent],self.root),[])

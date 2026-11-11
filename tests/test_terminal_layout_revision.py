import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import ezdxf
from bsa.cli import digest
from bsa.terminal_layout_revision import run
from bsa.duct_sheet import snapshot
from tests import test_air_terminal_drawing as fixtures


class TerminalLayoutRevisionTests(unittest.TestCase):
    def setUp(self):
        f=fixtures.TerminalDrawingTests();f.setUp();self.layers=f.layers
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.old=dict(f.allocation,load=dict(supply_flow_L_s=200),turndown=.4)
        self.new=copy.deepcopy(self.old);self.new['terminals'][0]['center_m']=[3,1]
        self.new['terminals'][0]['maximum_flow_L_s']=110;self.new['terminals'][1]['maximum_flow_L_s']=90
        labels={}
        for t in self.old['terminals']:
            e=f.doc.modelspace().add_text(t['id'],dxfattribs=dict(insert=[*t['center_m'],0],height=.1))
            labels[t['id']]=dict(handle=e.dxf.handle,expected_text=t['id'])
        self.unrelated=f.doc.modelspace().add_text('Unrelated source note',dxfattribs=dict(insert=[4,4,0],height=.1)).dxf.handle
        f.doc.saveas(self.root/'source.dxf')
        binding=dict(f.binding,source_sha256=digest(self.root/'source.dxf'))
        self.settings=dict(layers=f.layers,labels=labels,basis='Synthetic scoped terminal revision')
        for name,data in [('old.json',self.old),('new.json',self.new),('ducts.json',dict(tree=f.tree)),('binding.json',binding),('settings.json',self.settings)]:
            (self.root/name).write_text(json.dumps(data))

    def execute(self):return run(*(self.root/name for name in ('source.dxf','old.json','new.json','ducts.json','binding.json','settings.json','output')))

    def test_saved_geometry_labels_and_routes_follow_new_centres_only(self):
        source=(self.root/'source.dxf').read_bytes();before=snapshot(ezdxf.readfile(self.root/'source.dxf'))
        r=self.execute();after=snapshot(ezdxf.readfile(self.root/'output/Supply Air Distribution.dxf'))
        self.assertEqual(len(r['changes']),1);self.assertEqual(r['changed_entity_count'],3)
        self.assertEqual(before[self.unrelated],after[self.unrelated]);self.assertEqual((self.root/'source.dxf').read_bytes(),source)
        self.assertAlmostEqual(r['new_correspondence']['maximum_plan_length_m'],2)
        self.assertEqual(r['new_correspondence']['groups'][0]['maximum_flow_L_s'],110)
        self.assertFalse(r['native_reopen_pass']);self.assertFalse(r['design_accepted'])
        with self.assertRaises(ValueError):self.execute()

    def test_missing_label_binding_source_hash_and_flow_drift_reject(self):
        original=copy.deepcopy(self.settings)
        self.settings['labels'].pop('TA');(self.root/'settings.json').write_text(json.dumps(self.settings))
        with self.assertRaisesRegex(ValueError,'Complete explicit'):self.execute()
        (self.root/'settings.json').write_text(json.dumps(original))
        bad=copy.deepcopy(self.new);bad['terminals'][0]['maximum_flow_L_s']=120;(self.root/'new.json').write_text(json.dumps(bad))
        with self.assertRaisesRegex(ValueError,'conserve'):self.execute()
        (self.root/'new.json').write_text(json.dumps(self.new));(self.root/'source.dxf').write_bytes((self.root/'source.dxf').read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'binding hash'):self.execute()
        self.assertFalse((self.root/'output').exists())

    def test_reversed_flex_is_supported(self):
        doc=ezdxf.readfile(self.root/'source.dxf')
        for e in doc.modelspace():
            if e.dxf.layer==self.layers['flex']:e.dxf.start,e.dxf.end=e.dxf.end,e.dxf.start
        doc.saveas(self.root/'source.dxf');p=self.root/'binding.json';b=json.loads(p.read_text());b['source_sha256']=digest(self.root/'source.dxf');p.write_text(json.dumps(b))
        self.assertTrue(self.execute()['saved_dxf_correspondence'])

    def test_source_mutation_before_save_rejects(self):
        from bsa.air_terminal_drawing import inspect
        def mutate(*args):
            result=inspect(*args);p=self.root/'settings.json';p.write_text(p.read_text()+' ');return result
        with patch('bsa.terminal_layout_revision.inspect',side_effect=mutate),self.assertRaisesRegex(ValueError,'changed during'):
            self.execute()
        self.assertFalse((self.root/'output').exists())

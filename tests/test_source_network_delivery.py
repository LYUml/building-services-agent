import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import ezdxf
from bsa.source_network_delivery import compose
from bsa import source_network_delivery as tool
from bsa.cli import digest


class SourceNetworkDeliveryTests(unittest.TestCase):
    def test_missing_native_artifact_coverage_stops_before_ancestry_execution(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'BSA_PROJECT_ROOT':folder}):
            root=Path(folder);source=root/'source';source.mkdir();(source/'analysis.json').write_text('{}')
            engine=root/'fictional-runtime.txt';engine.write_text('Not executable; rejection control only')
            out=root/'delivery';out.mkdir()
            record=dict(source_analysis=str(source),autocad=str(engine),artifacts={},inputs={str(p):digest(p) for p in [source/'analysis.json',engine,*tool.methods()]})
            (out/'delivery.json').write_text(json.dumps(record))
            with patch.object(tool.analysis,'verify',side_effect=AssertionError('Must not execute ancestry')):
                with self.assertRaisesRegex(ValueError,'coverage missing'):tool.verify(out)

    def fixture(self,folder):
        # Explicitly fictional layout controls, not a verified engineering model.
        doc=ezdxf.new('R2018');doc.units=6;doc.appids.new('BSA_IFC');doc.layers.new('BSA_SECTION_REFERENCE')
        p=doc.modelspace().add_lwpolyline([(0,0),(8,0),(8,4),(0,4)],close=True);p.set_xdata('BSA_IFC',[(1000,'fixture-body')])
        line=doc.modelspace().add_line((0,-1),(1,-1),dxfattribs={'layer':'BSA_SECTION_REFERENCE'});line.set_xdata('BSA_IFC',[(1000,'fixture-body')])
        doc.modelspace().add_text('Original draft title',dxfattribs={'height':.2,'insert':(0,6)})
        doc.saveas(folder/'Supply Network Plan.dxf')
        sheet=dict(source='Fictional source-layout control',window_drawing_units=[-1,-2,9,10],scale_denominator=100,reference_ifc_guid='fixture-body',reference_layer='BSA_SECTION_REFERENCE',drawing_name='section',pdf_tolerance_mm=.3)
        (folder/'sheet.json').write_text(json.dumps(sheet));source=folder/'source.txt';source.write_text('Fictional source only')
        data=dict(inputs={str(source):digest(source)},artifacts={n:digest(folder/n) for n in ['Supply Network Plan.dxf','sheet.json']},products=[dict(guid='fixture-body',bounds_xy_m=[[0,0],[8,4]])],product_count=1,original_requirement_ids=['R-fixture'])
        (folder/'drawing.json').write_text(json.dumps(data));return p.dxf.handle

    def test_deterministic_layout_preserves_geometry_and_requirements(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'BSA_PROJECT_ROOT':folder}):
            folder=Path(folder);handle=self.fixture(folder);before=digest(folder/'Supply Network Plan.dxf')
            a,sheet,data=compose(folder);b,again,_=compose(folder)
            self.assertEqual(sheet,again);self.assertEqual(sheet['scale_denominator'],50)
            self.assertEqual(list(a.entitydb[handle].get_points()),list(b.entitydb[handle].get_points()))
            self.assertEqual(data['original_requirement_ids'],['R-fixture'])
            texts=[e.dxf.text for e in a.modelspace().query('TEXT')]
            self.assertEqual(len(texts),5);self.assertIn('1 m model reference',texts)
            self.assertNotIn('Original draft title',texts);self.assertEqual(digest(folder/'Supply Network Plan.dxf'),before)

    def test_source_drift_invalid_scale_and_clipped_layout_reject(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'BSA_PROJECT_ROOT':folder}):
            folder=Path(folder);self.fixture(folder)
            for scale in (True,0,-1,float('nan'),10000):
                with self.assertRaises(ValueError):compose(folder,scale)
            (folder/'source.txt').write_text('Changed')
            with self.assertRaisesRegex(ValueError,'source/method'):compose(folder)

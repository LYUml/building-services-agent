import copy
import json
import unittest
import ezdxf
from bsa.spatial_terminal_drawing import run,verify
from bsa.cli import digest
from tests import test_spatial_terminal_performance as fixtures

class SpatialTerminalDrawingTests(unittest.TestCase):
    def test_saved_source_geometry_flows_and_tampering(self):
        f=fixtures.SpatialTerminalPerformanceTests();f.setUp();self.addCleanup(f.temp.cleanup);out,_=f.run_workflow()
        settings=f.root/'drawing-settings.json';settings.write_text(json.dumps(dict(annotation_height_m=.08,source='Explicit synthetic annotation design choice')))
        folder=f.root/'drawing';r=run(out/'terminal-allocation/terminal-allocation.json',settings,folder)
        self.assertFalse(r['native_reopen_pass']);self.assertEqual(r['entity_count'],18)
        drawing=folder/'Terminal Airflow Schematic.dxf';doc=ezdxf.readfile(drawing)
        self.assertIn('TERMINAL AIRFLOW SCHEMATIC',[e.dxf.text for e in doc.modelspace().query('TEXT')])
        self.assertEqual(len(doc.modelspace().query('POINT')),3);self.assertEqual(len(doc.modelspace().query('LWPOLYLINE')),3)
        point=next(iter(doc.modelspace().query('POINT')));point.dxf.location=(999,999,0);doc.saveas(drawing)
        record=folder/'drawing.json';changed=json.loads(record.read_text());changed['dxf_sha256']=digest(drawing);record.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError,'source replay'):verify(folder)
        with self.assertRaises(ValueError):run(out/'terminal-allocation/terminal-allocation.json',settings,folder)

    def test_room_label_anchor_independent_of_boundary_start(self):
        from bsa.spatial_terminal_drawing import expected
        report={'calculation':{'rooms':{'room':dict(floor_elevation_m=0,allocation=dict(terminals=[]))}}}
        producer=dict(payload_schema='bsa.spatial-polygons/1',payload=dict(spaces=[dict(id='room',boundary_vertices=[[0,0],[4,0],[4,3],[0,3]])]))
        settings=dict(annotation_height_m=.2,source='Synthetic annotation control')
        first=expected(report,producer,settings);changed=copy.deepcopy(producer);points=changed['payload']['spaces'][0]['boundary_vertices'];changed['payload']['spaces'][0]['boundary_vertices']=points[2:]+points[:2]
        labels=lambda rows:[r for r in rows if r['kind']=='TEXT']
        self.assertEqual(labels(first),labels(expected(report,changed,settings)))

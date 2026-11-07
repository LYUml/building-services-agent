import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
import ezdxf
from bsa.cad_intake import inventory,measure,polygon_area,run
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.native_cad import DEFAULT_EXE,execute,lisp_string

ROOT=Path(__file__).resolve().parents[1]


def fixture(root):
    doc=ezdxf.new('R2018');doc.units=4
    doc.layers.new('ROOM_BOUNDARY');doc.layers.new('DIM_CHECK')
    m=doc.modelspace()
    polygon=m.add_lwpolyline([(0,0),(6000,0),(6000,2000),(3000,2000),(3000,4000),(0,4000)],close=True,dxfattribs={'layer':'ROOM_BOUNDARY'})
    line=m.add_line((0,-1000,0),(6000,-1000,0),dxfattribs={'layer':'DIM_CHECK'})
    m.add_text('Synthetic L room',dxfattribs={'insert':(1000,1000),'height':200})
    block=doc.blocks.new('UNRESOLVED_SYMBOL');block.add_circle((0,0),100)
    m.add_blockref('UNRESOLVED_SYMBOL',(2000,2000),dxfattribs={'rotation':30})
    m.add_point((1000,1000))
    path=root/'base.dxf';doc.saveas(path)
    selection=dict(drawing_sha256=digest(path),source='Synthetic author-selected L-shaped room boundary; no coursework data',
        unit_check=dict(handle=line.dxf.handle,known_length_m=6,absolute_tolerance_m=1e-9,source='Synthetic fixture dimension: 6000 mm = 6 m'),
        areas=[dict(id='L_ROOM',handle=polygon.dxf.handle,source='Explicit synthetic floor boundary without holes; not inferred from labels')])
    return path,selection


class CADIntakeTests(unittest.TestCase):
    def test_mm_l_shaped_area_inventory_and_source_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path,selection=fixture(root);before=digest(path)
            data=inventory(path);result=measure(data,selection)
            self.assertEqual(result['areas'][0]['area_m2'],18)
            self.assertEqual(result['unit_check']['measured_length_m'],6)
            self.assertEqual(data['insunits'],4)
            self.assertEqual(data['counts']['INSERT'],1)
            self.assertEqual(data['counts']['POINT'],1)
            self.assertIn('unexpanded',next(e for e in data['entities'] if e['type']=='INSERT')['geometry_status'])
            self.assertIn('unsupported',next(e for e in data['entities'] if e['type']=='POINT')['geometry_status'])
            selected=root/'selection.json';selected.write_text(json.dumps(selection))
            report=run(path,root/'run',selected)
            self.assertTrue(report['inputs_unchanged']);self.assertTrue(report['measurements_pass'])
            self.assertEqual(digest(path),before);self.assertFalse(report['design_accepted'])

    def test_unit_mismatch_unitless_and_curved_or_open_boundary_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path,s=fixture(root);data=inventory(path)
            for update in ({'metres_per_unit':None},{'metres_per_unit':1}):
                candidate=copy.deepcopy(data);candidate.update(update)
                with self.assertRaises(ProjectError):measure(candidate,s)
            for values in ({'closed':False},{'bulges':[1,0,0,0,0,0]},{'has_width':True}):
                candidate=copy.deepcopy(data)
                next(e for e in candidate['entities'] if e['type']=='LWPOLYLINE').update(values)
                with self.assertRaises(ProjectError):measure(candidate,s)
            bad=copy.deepcopy(s);bad['unit_check']['known_length_m']=5
            with self.assertRaises(ProjectError):measure(data,bad)
            bad=copy.deepcopy(s);bad['drawing_sha256']='0'*64
            with self.assertRaises(ProjectError):measure(data,bad)

    def test_polygon_self_intersection_nonplanarity_and_clockwise(self):
        with self.assertRaises(ProjectError):polygon_area([[0,0,0],[2,2,0],[0,2,0],[2,0,0]])
        with self.assertRaises(ProjectError):polygon_area([[0,0,0],[1,0,0],[1,1,1]])
        points=[[1e9,1e9,0],[1e9,1e9+2,0],[1e9+3,1e9+2,0],[1e9+3,1e9,0]]
        self.assertEqual(polygon_area(points),6)

    def test_missing_engine_and_output_source_overlap_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path,_=fixture(root)
            with self.assertRaises(ProjectError):run(path,root)
            dwg=root/'fake.dwg';dwg.write_bytes(b'not DWG')
            with self.assertRaises(ProjectError):run(dwg,root/'run')
            self.assertFalse((root/'run').exists())

    def test_workflow_tracks_selection_and_missing_dwg_engine_stays_pending(self):
        from bsa.workflow import execute as workflow,verify
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);drawing,selection=fixture(root)
            selected=root/'selection.json';selected.write_text(json.dumps(selection))
            brief=root/'brief.md';brief.write_text('Extract the selected room boundary after the known dimension check.\n')
            plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={'P001':'requirement'},
                tasks=[dict(id='drawing',kind='drawing_intake',drawing='base.dxf',selection='selection.json')],
                requirements=[dict(id='R1',passage='P001',quote='Extract the selected room boundary after the known dimension check.',task='drawing',acceptance='geometry evidence and unchanged source')])
            path=root/'plan.json';path.write_text(json.dumps(plan))
            result=workflow(path,root/'run')
            self.assertEqual(result['tasks']['drawing']['status'],'pass')
            self.assertIn(str(selected.resolve()),result['inputs']);self.assertIn(str(drawing.resolve()),result['inputs'])
            self.assertTrue(verify(root/'run')['integrity_pass'])
            (root/'base.dwg').write_bytes(b'engine must not be simulated')
            plan['tasks'][0]['drawing']='base.dwg';path.write_text(json.dumps(plan))
            pending=workflow(path,root/'pending')
            self.assertEqual(pending['tasks']['drawing']['status'],'pending')
            self.assertFalse(pending['design_accepted'])

    @unittest.skipUnless(os.environ.get('BSA_TEST_AUTOCAD')=='1' and DEFAULT_EXE.is_file(),'requires explicit AutoCAD test')
    def test_actual_dwg_export_preserves_source_and_mm_measurement(self):
        (ROOT/'runs').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);path,selection=fixture(root);dwg=root/'synthetic-base.dwg'
            condition=f'(= (strcase (vl-string-translate (chr 92) "/" (strcat (getvar "DWGPREFIX") (getvar "DWGNAME")))) (strcase {lisp_string(path)}))'
            script=root/'create.scr';script.write_text(f'(if {condition} (progn (setvar "FILEDIA" 0) (command "_.SAVEAS" "2018" {lisp_string(dwg)})))\n_.QUIT\n_Y\n',encoding='ascii')
            execute(DEFAULT_EXE,path,script,root/'create.log',120)
            self.assertTrue(dwg.is_file());before=digest(dwg)
            selection['drawing_sha256']=before
            selected=root/'selection.json';selected.write_text(json.dumps(selection))
            result=run(dwg,root/'intake',selected,DEFAULT_EXE)
            self.assertTrue(result['inputs_unchanged']);self.assertEqual(digest(dwg),before)
            measurements=json.loads((root/'intake/measurements.json').read_text())
            self.assertEqual(measurements['areas'][0]['area_m2'],18)
            self.assertFalse(result['design_accepted'])


if __name__=='__main__':unittest.main()

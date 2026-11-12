import copy
import json
import unittest
import ifcopenshell
from bsa.cli import digest
from bsa.spatial_terminal_ifc import run as author
from bsa.spatial_terminal_inlets import run,verify
from tests import test_spatial_terminal_ifc as fixtures

class SpatialTerminalInletTests(unittest.TestCase):
    def setUp(self):
        f=fixtures.SpatialTerminalIFCTests();f.setUp();self.addCleanup(f.doCleanups);self.f=f
        self.source=f.f.root/'inlet-model';model=author(f.source,f.basis,self.source)
        self.rows={r['id']:dict(offset_m=dict(value=[.05,.05,.1],unit='m',source='Synthetic top-face centre',classification='design_choice'),outward_axis=dict(value=[0,0,1],unit='1',source='Synthetic outward axis',classification='design_choice'),diameter_m=dict(value=.04,unit='m',source='Synthetic nominal diameter',classification='assumed'),system=dict(id='Trial Air',predefined_type='VENTILATION',source='Explicit synthetic grouping',classification='design_choice')) for r in model['terminals']}
        self.basis=f.f.root/'inlet-basis.json';self.basis.write_text(json.dumps(self.rows))

    def test_native_inlet_system_and_mutated_direction_reject(self):
        out=self.f.f.root/'inlets';r=run(self.source/'terminal-ifc.json',self.basis,out);self.assertEqual(len(verify(out)['inlets']),3);self.assertTrue(r['original_entities_unchanged']);self.assertFalse(r['design_accepted'])
        target=out/'Terminal Inlet Study.ifc';model=ifcopenshell.open(str(target));port=model.by_guid(r['inlets'][0]['port_guid']);port.FlowDirection='SOURCE';model.write(str(target))
        path=out/'terminal-inlets.json';r['ifc_sha256']=digest(target);path.write_text(json.dumps(r))
        with self.assertRaisesRegex(ValueError,'direction'):verify(out)

    def test_missing_basis_bad_diameter_face_axis_and_source_reject(self):
        for kind in ('coverage','diameter','face','axis','source'):
            rows=copy.deepcopy(self.rows);row=next(iter(rows.values()))
            if kind=='coverage':rows.pop(next(iter(rows)))
            elif kind=='diameter':row['diameter_m']['value']=.2
            elif kind=='face':row['offset_m']['value'][2]=.05
            elif kind=='axis':row['outward_axis']['value']=[0,1,1]
            else:row['system']['source']=''
            self.basis.write_text(json.dumps(rows));out=self.f.f.root/('rejected-'+kind)
            with self.subTest(kind=kind),self.assertRaises(ValueError):run(self.source/'terminal-ifc.json',self.basis,out)
            self.assertFalse(out.exists())


class InletIdentityTests(unittest.TestCase):
    def test_header_only_changes_preserve_project_based_inlet_identity(self):
        import tempfile
        from pathlib import Path
        from bsa.spatial_terminal_inlets import stable
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=root/'runs') as folder:
            a=Path(folder)/'a.ifc';b=Path(folder)/'b.ifc';model=ifcopenshell.file(schema='IFC4');project=model.create_entity('IfcProject',GlobalId=ifcopenshell.guid.new());model.write(str(a))
            model.header.file_description.description=('Synthetic metadata-only identity control',);model.write(str(b))
            self.assertEqual(stable(a,'inlet','T1'),stable(b,'inlet','T1'))
            project.GlobalId=ifcopenshell.guid.new();model.write(str(b))
            self.assertNotEqual(stable(a,'inlet','T1'),stable(b,'inlet','T1'))

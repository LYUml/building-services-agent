import copy
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest
from bsa.bim import validate,run
from bsa.circular_geometry import WALL,MIXED_SCOPE,specification,verify,configure
from bsa.engine import ProjectError
from bsa.cli import digest

ROOT=Path(__file__).resolve().parents[1]


def model_input():
    model=json.loads((ROOT/'examples/network-model-design/model.json').read_text())
    model['name']='Synthetic explicit circular wall refinement'
    model['geometry_scope']=MIXED_SCOPE
    model['sources']['wall']='Synthetic independently specified 0.40 m bore and 0.50 m outside diameter; uniform straight wall only, no manufacturer/material certification'
    d=model['devices'][1];d['body_shape']=WALL;d['properties']['OutsideDiameter_m']=.5;d['source']='wall'
    return model


class CircularGeometryTests(unittest.TestCase):
    def test_explicit_diameters_and_boundary_ports_required(self):
        source=model_input();validate(source)
        for mutate in (lambda p:p['devices'][1]['properties'].pop('OutsideDiameter_m'),
                       lambda p:p['devices'][1]['properties'].update(OutsideDiameter_m=.4),
                       lambda p:p['devices'][1]['size_m'].__setitem__(1,.6),
                       lambda p:p['devices'][1]['ports'][0]['offset_m'].__setitem__(0,.1),
                       lambda p:p.update(geometry_scope='axis-aligned bounding envelopes'),
                       lambda p:p['devices'][1].update(body_shape='guess a round body')):
            candidate=copy.deepcopy(source);mutate(candidate)
            with self.assertRaises(ProjectError):validate(candidate)

    def test_reverse_flow_keeps_outward_normals_and_analytic_volume(self):
        model=model_input();d=model['devices'][1];spec=specification(d)
        self.assertEqual(spec['normals']['in'],[-1,0,0]);self.assertEqual(spec['normals']['out'],[1,0,0])
        self.assertAlmostEqual(spec['volume_m3'],math.pi*(.5**2-.4**2)*3/4)
        d['ports'][0]['offset_m'],d['ports'][1]['offset_m']=d['ports'][1]['offset_m'],d['ports'][0]['offset_m']
        reversed_spec=specification(d)
        self.assertEqual(reversed_spec['normals']['in'],[1,0,0]);self.assertEqual(reversed_spec['normals']['out'],[-1,0,0])

    @unittest.skipUnless(importlib.util.find_spec('ifcopenshell'),'requires IFC runtime')
    def test_actual_hollow_profiles_mesh_volumes_axes_and_reverse_ports(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for rotation in range(3):
                model=model_input();model['connections']=[]
                for _ in range(rotation):
                    for space in model['spaces']:
                        for key in ('origin_m','size_m'):space[key]=space[key][1:]+space[key][:1]
                    for d in model['devices']:
                        for key in ('origin_m','size_m'):d[key]=d[key][1:]+d[key][:1]
                        for port in d['ports']:port['offset_m']=port['offset_m'][1:]+port['offset_m'][:1]
                if rotation!=1:
                    model['systems'][0]['predefined_type']='DOMESTICCOLDWATER'
                    model['devices'][0]['ifc_class']='IfcPump';model['devices'][1]['ifc_class']='IfcPipeSegment';model['devices'][2]['ifc_class']='IfcSanitaryTerminal'
                    ports=model['devices'][1]['ports'];ports[0]['offset_m'],ports[1]['offset_m']=ports[1]['offset_m'],ports[0]['offset_m']
                path=root/f'axis-{rotation}.json';path.write_text(json.dumps(model));before=digest(path)
                result=run(path,root/f'axis-{rotation}')
                d=next(d for d in result['devices'] if d['id']=='DUCT1');checks=d['circular_checks']
                self.assertTrue(result['model_checks_pass']);self.assertTrue(checks['closed_mesh'])
                self.assertEqual(checks['euler_characteristic'],0)
                self.assertAlmostEqual(checks['mesh_wall_volume_m3'],math.pi*(.5**2-.4**2)*3/4,delta=.0001)
                self.assertEqual(digest(path),before);self.assertFalse(result['design_accepted'])

    @unittest.skipUnless(importlib.util.find_spec('ifcopenshell'),'requires IFC runtime')
    def test_changed_native_hollow_profile_is_rejected(self):
        import ifcopenshell
        import ifcopenshell.geom
        import ifcopenshell.api as api
        import ifcopenshell.util.element as element
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);model=model_input();path=root/'source.json';path.write_text(json.dumps(model))
            run(path,root/'run');native=ifcopenshell.open(str(root/'run/model.ifc'))
            native.by_type('IfcCircleHollowProfileDef')[0].WallThickness=.04
            obj=next(o for o in native.by_type('IfcDuctSegment') if o.Name=='DUCT1')
            settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True);configure(settings)
            shape=ifcopenshell.geom.create_shape(settings,obj)
            with self.assertRaises(ProjectError):verify(obj,model['devices'][1],shape)
            native.by_type('IfcCircleHollowProfileDef')[0].WallThickness=.05
            properties=element.get_psets(obj)['BSA_DesignInputs']
            api.run('pset.edit_pset',native,pset=native.by_id(properties['id']),properties={'OutsideDiameter_m':.6})
            shape=ifcopenshell.geom.create_shape(settings,obj)
            with self.assertRaisesRegex(ProjectError,'metadata'):verify(obj,model['devices'][1],shape)

    @unittest.skipUnless(importlib.util.find_spec('ifcopenshell') and importlib.util.find_spec('fluids'),'requires IFC/network runtimes')
    def test_sizing_rebuilds_wall_and_reconciles_pressure(self):
        from bsa.network_model_design import run as model_design
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);base=ROOT/'examples/network-model-design';paths=[]
            for name in ('network','model','binding','catalogue','geometry'):
                data=model_input() if name=='model' else json.loads((base/(name+'.json')).read_text())
                path=root/(name+'.json');path.write_text(json.dumps(data));paths.append(path)
            result=model_design(*paths,root/'run')
            self.assertTrue(result['calculated_checks_pass']);self.assertTrue(result['stable_object_port_ids_match'])
            saved=json.loads((root/'run/selected-coordination/bim/bim-verification.json').read_text())
            d=next(d for d in saved['devices'] if d['id']=='DUCT1')
            self.assertAlmostEqual(d['circular_checks']['analytic_wall_volume_m3'],math.pi*(.22**2-.2**2)*3/4)
            self.assertEqual(d['body_shape'],WALL);self.assertTrue(d['circular_checks']['closed_mesh'])


if __name__=='__main__':unittest.main()

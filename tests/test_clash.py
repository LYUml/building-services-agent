import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from bsa.clash import SCOPE,validate_policy,inspect,run
from bsa.engine import ProjectError
from bsa.cli import digest

ROOT=Path(__file__).resolve().parents[1]


def policy():
    return dict(scope=SCOPE,sources={'demo':'Synthetic 50 mm clearance, 0.1 mm intersection/contact tolerances; not a regulation or maintenance requirement'},
        source='demo',minimum_clearance_m=.05,intersection_tolerance_m=.0001,contact_tolerance_m=.0001,
        overlap_volume_tolerance_m3=1e-10,maximum_boolean_pairs=1000,allowed_contacts=[])


def boxes(gap):
    return dict(name='Synthetic independent box distance fixture',geometry_scope='axis-aligned bounding envelopes',
        sources={'demo':'Synthetic explicit unit cubes and gap for geometric verification'},
        spaces=[dict(id='Room',origin_m=[-2,-2,-2],size_m=[10,10,10],source='demo')],
        systems=[dict(id='System',predefined_type='VENTILATION',source='demo')],
        devices=[dict(id=id,ifc_class='IfcFan',origin_m=[x,0,0],size_m=[1,1,1],space='Room',system='System',source='demo') for id,x in [('A',0),('B',1+gap)]],connections=[])


class ClashPolicyTests(unittest.TestCase):
    def test_invalid_policy_distances_sources_and_waivers(self):
        for mutate in (lambda p:p.update(minimum_clearance_m=-1),lambda p:p.update(contact_tolerance_m=.1),
                       lambda p:p.update(source='missing'),lambda p:p.update(scope='only ignore inconvenient objects'),
                       lambda p:p['allowed_contacts'].append(dict(from_port_guid='A',to_port_guid='B',source='demo'))):
            p=policy();mutate(p)
            with self.assertRaises(ProjectError):validate_policy(p)


@unittest.skipUnless(importlib.util.find_spec('ifcopenshell') and importlib.util.find_spec('manifold3d'),'requires IFC and Manifold runtimes')
class ClashGeometryTests(unittest.TestCase):
    def author(self,root,model):
        from bsa.bim import run as author
        path=root/'model.json';path.write_text(json.dumps(model));author(path,root/'model')
        return root/'model/model.ifc'

    def test_known_gap_clearance_and_intersection(self):
        for gap,passing in ((.1,True),(.02,False),(-.2,False)):
            with self.subTest(gap=gap),tempfile.TemporaryDirectory() as folder:
                root=Path(folder);native=self.author(root,boxes(gap));before=digest(native)
                result=inspect(native,policy())
                self.assertEqual(result['calculated_checks_pass'],passing);self.assertEqual(digest(native),before)
                names={e['guid']:e['name'] for e in result['elements']}
                for row in result['intersections']+result['clearance_findings']:self.assertEqual(row['names'],[names[id] for id in row['pair']])
                if gap==.02:self.assertAlmostEqual(result['clearance_violations'][0]['engine_distance_m'],.02,places=8)
                if gap<0:
                    self.assertTrue(result['intersections'])
                    self.assertAlmostEqual(next(r['overlap_volume_m3'] for r in result['intersections'] if r['type']=='manifold_mesh_overlap'),.2,places=8)

    def test_full_containment_is_not_missed_by_surface_clearance(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);model=boxes(0);model['devices'][1].update(origin_m=[.3,.3,.3],size_m=[.2,.2,.2])
            result=inspect(self.author(root,model),policy())
            self.assertTrue(result['intersections']);self.assertFalse(result['calculated_checks_pass'])
            self.assertAlmostEqual(result['solid_pair_checks'][0]['mesh_common_volume_m3'],.008,places=8)

    def test_native_millimetre_units_normalise_to_metre_clearance(self):
        import ifcopenshell
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);model=boxes(20);model['spaces'][0]['size_m']=[40,10,10]
            path=self.author(root,model);native=ifcopenshell.open(str(path))
            next(u for u in native.by_type('IfcSIUnit') if u.UnitType=='LENGTHUNIT').Prefix='MILLI'
            native.write(str(path));result=inspect(path,policy())
            self.assertEqual(result['source_length_unit_to_m'],.001)
            self.assertAlmostEqual(result['clearance_violations'][0]['engine_distance_m'],.02,places=8)

    def test_actual_hollow_bore_avoids_bbox_false_collision(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);model=json.loads((ROOT/'examples/circular-network/model.json').read_text())
            tube=model['devices'][1];sensor=copy.deepcopy(model['devices'][2])
            sensor.update(id='SENSOR',ifc_class='IfcSensor',origin_m=[2,2.21,2.21],size_m=[.08,.08,.08],ports=[])
            model['devices']=[tube,sensor];model['connections']=[]
            result=inspect(self.author(root,model),policy())
            self.assertTrue(result['calculated_checks_pass']);self.assertEqual(result['potential_pair_count'],1)
            self.assertAlmostEqual(result['solid_pair_checks'][0]['mesh_common_volume_m3'],0,places=10)

    def test_coincident_reverse_tubes_cannot_be_waived_as_a_connection(self):
        import ifcopenshell
        import math
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);model=json.loads((ROOT/'examples/circular-network/model.json').read_text())
            first=model['devices'][1];second=copy.deepcopy(first);second['id']='REVERSE'
            ports=second['ports'];ports[0]['offset_m'],ports[1]['offset_m']=ports[1]['offset_m'],ports[0]['offset_m']
            model['devices']=[first,second];model['connections']=[dict(source='demo',**{'from':'DUCT1.out','to':'REVERSE.in'})]
            path=self.author(root,model);native=ifcopenshell.open(str(path));relation=native.by_type('IfcRelConnectsPorts')[0]
            p=policy();p['allowed_contacts']=[dict(from_port_guid=relation.RelatingPort.GlobalId,to_port_guid=relation.RelatedPort.GlobalId,region_radius_m=.3,source='demo')]
            result=inspect(path,p)
            self.assertFalse(result['calculated_checks_pass']);self.assertFalse(result['accepted_contacts'])
            volume=next(r['overlap_volume_m3'] for r in result['intersections'] if r['type']=='manifold_mesh_overlap')
            self.assertAlmostEqual(volume,math.pi*(.5**2-.4**2)*3/4,delta=.0001)

    def test_connected_contact_policy_does_not_hide_hard_intersection(self):
        import ifcopenshell
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);model=boxes(0)
            model['devices'][0]['ports']=[dict(id='out',direction='SOURCE',offset_m=[1,.5,.5],source='demo')]
            model['devices'][1]['ports']=[dict(id='in',direction='SINK',offset_m=[0,.5,.5],source='demo')]
            model['connections']=[dict(source='demo',**{'from':'A.out','to':'B.in'})]
            native_path=self.author(root,model);native=ifcopenshell.open(str(native_path))
            ports={p.Name:p for p in native.by_type('IfcDistributionPort')};p=policy()
            p['allowed_contacts']=[dict(from_port_guid=ports['out'].GlobalId,to_port_guid=ports['in'].GlobalId,region_radius_m=.8,source='demo')]
            result=inspect(native_path,p);self.assertTrue(result['calculated_checks_pass']);self.assertEqual(len(result['accepted_contacts']),1)
            # Keep the connected ports at x=1, but enlarge A into B; this must remain a hard clash.
            model['devices'][0]['size_m'][0]=1.2
            from bsa.bim import run as author
            model_path=root/'overlap.json';model_path.write_text(json.dumps(model));author(model_path,root/'overlap')
            overlap=ifcopenshell.open(str(root/'overlap/model.ifc'));new_ports={port.Name:port for port in overlap.by_type('IfcDistributionPort')}
            p['allowed_contacts'][0].update(from_port_guid=new_ports['out'].GlobalId,to_port_guid=new_ports['in'].GlobalId)
            result=inspect(root/'overlap/model.ifc',p)
            self.assertTrue(result['intersections']);self.assertFalse(result['calculated_checks_pass']);self.assertFalse(result['accepted_contacts'])

    def test_rotated_mesh_and_missing_geometry_coverage(self):
        import ifcopenshell
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);model=boxes(-.2);native_path=self.author(root,model);native=ifcopenshell.open(str(native_path))
            obj=next(e for e in native.by_type('IfcFan') if e.Name=='B');coordinates=obj.Representation.Representations[0].Items[0].Coordinates
            s=2**-.5
            coordinates.CoordList=[(.5+(x-.5)*s-(y-.5)*s,.5+(x-.5)*s+(y-.5)*s,z) for x,y,z in coordinates.CoordList]
            native.write(str(native_path));result=inspect(native_path,policy())
            self.assertFalse(result['unverified_solid_pairs']);self.assertTrue(result['checks']['geometry_coverage']);self.assertTrue(result['intersections'])
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);model=boxes(.1);third=copy.deepcopy(model['devices'][1]);third.update(id='MISSING',origin_m=[4,0,0]);model['devices'].append(third)
            native_path=self.author(root,model);native=ifcopenshell.open(str(native_path))
            next(e for e in native.by_type('IfcFan') if e.Name=='MISSING').Representation=None;native.write(str(native_path))
            result=inspect(native_path,policy())
            self.assertFalse(result['calculated_checks_pass']);self.assertEqual(result['unrepresented_elements'][0]['name'],'MISSING')

    def test_workflow_dependency_and_saved_ifc_integrity(self):
        from bsa.workflow import execute,verify,validate_plan
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'model.json').write_text(json.dumps(boxes(.02)));(root/'policy.json').write_text(json.dumps(policy()))
            brief=root/'brief.md';brief.write_text('Create the model and check all represented objects for clashes.\n')
            plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={'P001':'requirement'},
                tasks=[dict(id='model',kind='bim',project='model.json'),dict(id='qa',kind='ifc_clash',depends_on='model',policy='policy.json')],
                requirements=[dict(id='R'+str(i),passage='P001',quote='Create the model and check all represented objects for clashes.',task=task,acceptance='source model and scoped geometry checks') for i,task in enumerate(('model','qa'),1)])
            path=root/'plan.json';path.write_text(json.dumps(plan));result=execute(path,root/'run')
            self.assertEqual(result['tasks']['model']['status'],'pass');self.assertEqual(result['tasks']['qa']['status'],'fail')
            self.assertTrue((root/'run/qa/clash.json').exists());self.assertTrue(verify(root/'run')['integrity_pass'])
            output=root/'run/model/model.ifc';output.write_bytes(output.read_bytes()+b'\n')
            self.assertFalse(verify(root/'run')['integrity_pass'])
            plan['tasks'][1]['depends_on']='qa';path.write_text(json.dumps(plan))
            with self.assertRaises(ProjectError):validate_plan(path)


if __name__=='__main__':unittest.main()

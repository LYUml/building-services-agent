import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from bsa.network_binding import prepare,run,reconcile
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]


class NetworkBindingTests(unittest.TestCase):
    def inputs(self):
        model=json.loads((ROOT/'examples/mep-ifc/ventilation.json').read_text())
        model['devices'][1]['properties']={'InternalDiameter_m':0.4}
        network=json.loads((ROOT/'examples/network/air.json').read_text())
        network['nodes']=[dict(id='FAN',demand_m3_s=0,required_total_pressure_pa=0,source='demo'),
                          dict(id='A',demand_m3_s=0.2,required_total_pressure_pa=30,source='demo')]
        network['segments']=[{k:v for k,v in network['segments'][0].items() if k not in ('length_m','diameter_m')}]
        network['segments'][0].update(to='A')
        binding=dict(source='Synthetic matching model port and network mapping; not measured',
                     nodes={'FAN':'FAN1.out','A':'AT1.in'},segments={'MAIN':['DUCT1']})
        return network,model,binding

    def test_model_geometry_derives_lengths_diameter_elevation(self):
        n,m,b=self.inputs();before=copy.deepcopy((n,m,b));p,e=prepare(n,m,b)
        self.assertEqual(p['segments'][0]['length_m'],3)
        self.assertEqual(p['segments'][0]['diameter_m'],0.4)
        self.assertEqual(p['nodes'][0]['elevation_m'],2.25)
        self.assertEqual((n,m,b),before)
        self.assertEqual(e[0]['devices'],['DUCT1'])

    def test_repeated_dimensions_missing_mapping_and_offset_ports_rejected(self):
        n,m,b=self.inputs()
        for key in ('length_m','diameter_m'):
            changed=copy.deepcopy(n);changed['segments'][0][key]=3
            with self.assertRaises(ProjectError):prepare(changed,m,b)
        changed=copy.deepcopy(b);changed['nodes'].pop('A')
        with self.assertRaises(ProjectError):prepare(n,m,changed)
        for mutate in (
            lambda d:d['ports'][1]['offset_m'].__setitem__(1,0.3),
            lambda d:d['properties'].update(InternalDiameter_m=0.6),
            lambda d:d['properties'].pop('InternalDiameter_m')):
            changed=copy.deepcopy(m);mutate(changed['devices'][1])
            with self.assertRaises(ProjectError):prepare(n,changed,b)

    def test_geometry_change_propagates_and_endpoint_mismatch_rejected(self):
        n,m,b=self.inputs()
        m['devices'][1]['size_m'][0]=4;m['devices'][1]['ports'][1]['offset_m'][0]=4
        with self.assertRaises(ProjectError):prepare(n,m,b)
        m['devices'][2]['origin_m'][0]=5
        p,_=prepare(n,m,b)
        self.assertEqual(p['segments'][0]['length_m'],4)

    def test_connected_chain_and_disconnected_or_reused_piece_rejected(self):
        n,m,b=self.inputs();first=m['devices'][1];second=copy.deepcopy(first)
        first['size_m'][0]=1.5;first['ports'][1]['offset_m'][0]=1.5
        second['id']='DUCT2';second['origin_m'][0]=2.5
        second['size_m'][0]=1.5;second['ports'][1]['offset_m'][0]=1.5
        m['devices'].append(second)
        m['connections'][1]['to']='DUCT2.in'
        m['connections'].append(dict(source='demo',**{'from':'DUCT2.out','to':'AT1.in'}))
        b['segments']['MAIN']=['DUCT1','DUCT2']
        p,_=prepare(n,m,b);self.assertEqual(p['segments'][0]['length_m'],3)
        broken=copy.deepcopy(m);broken['connections'].pop(1)
        with self.assertRaises(ProjectError):prepare(n,broken,b)
        b['segments']['MAIN']=['DUCT1','DUCT1']
        with self.assertRaises(ProjectError):prepare(n,m,b)

    @unittest.skipUnless(importlib.util.find_spec('ifcopenshell') and importlib.util.find_spec('fluids'),'requires BIM and network libraries')
    def test_real_ifc_and_pressure_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);paths=[]
            for name,data in zip(('network','model','binding'),self.inputs()):
                p=root/(name+'.json');p.write_text(json.dumps(data));paths.append(p)
            result=run(*paths,root/'run')
            self.assertTrue(result['calculated_checks_pass'])
            self.assertTrue(result['inputs_unchanged'])
            self.assertFalse(result['design_accepted'])
            self.assertTrue((root/'run/bim/model.ifc').is_file())
            report=json.loads((root/'run/analysis/network.json').read_text())
            self.assertEqual(report['supply_flow_m3_s'],0.2)
            import ifcopenshell
            import ifcopenshell.api as api
            import ifcopenshell.util.element as element
            model_path=root/'run/bim/model.ifc';native=ifcopenshell.open(str(model_path))
            obj=next(d for d in native.by_type('IfcDuctSegment') if d.Name=='DUCT1')
            ps=element.get_psets(obj)['BSA_DesignInputs']
            api.run('pset.edit_pset',native,pset=native.by_id(ps['id']),properties={'InternalDiameter_m':0.3})
            native.write(str(model_path))
            with self.assertRaises(ProjectError):reconcile(model_path,root/'run/network-input.json',self.inputs()[2])


if __name__=='__main__':unittest.main()

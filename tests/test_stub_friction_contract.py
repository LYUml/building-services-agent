import copy
import json
from pathlib import Path
import tempfile
import unittest
import ifcopenshell
from bsa.module_contract import validate
from bsa.providers.stub_friction import common
from bsa.spatial_stub_friction import point

ROOT=Path(__file__).resolve().parents[1]

def quantity(value,unit):return dict(value=value,unit=unit,source='Explicit synthetic contract control',classification='assumed')

class FrictionContractTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        frame=dict(id='synthetic-contract-frame',kind='source-world-si',length_unit='m',georeferenced=False)
        row=dict(stub_guid=ifcopenshell.guid.new(),space_guid=ifcopenshell.guid.new(),inlet_port_guid=ifcopenshell.guid.new(),outlet_port_guid=ifcopenshell.guid.new(),native_length_m=.15,native_internal_diameter_m=.2,inlet_point_m=[0,0,.15],outlet_point_m=[0,0,0],inherited_density=quantity(1.25,'kg/m3'),inherited_stub_basis={k:quantity(v,'m') for k,v in dict(length_m=.15,internal_diameter_m=.2,wall_thickness_m=.0008).items()},length_over_diameter=.15/.2,cases={label:point(q,.2,.15,1.25,1.8e-5,.00009,-.15) for label,q in [('maximum',100),('minimum',40)]})
        self.report=dict(calculation=dict(coordinate_frame=frame,status='calculated',terminals={'T1':row},basis=dict(dynamic_viscosity_pa_s=quantity(1.8e-5,'Pa.s'),roughness_m=quantity(.00009,'m'))));(self.root/'straight-friction.json').write_text(json.dumps(self.report));self.request=dict(coordinate_frame=frame)

    def test_common_units_pending_engineering_and_aggregation_guards(self):
        payload=common(self.request,self.report,self.root);self.assertEqual(payload['status'],'pass');self.assertEqual(payload['engineering_status'],'pending');self.assertFalse(payload['whole_system_pressure_complete'])
        for kind in ('count','flag','units','ports','frame','path'):
            bad=copy.deepcopy(payload)
            if kind=='count':bad['case_count']+=1
            elif kind=='flag':bad['design_accepted']=True
            elif kind=='units':bad['units']['pressure']='kPa'
            elif kind=='ports':bad['components']['T1']['outlet_port_guid']=bad['components']['T1']['inlet_port_guid']
            elif kind=='frame':bad['coordinate_frame']['length_unit']='mm'
            else:bad['report']['path']='../escape.json'
            with self.subTest(kind=kind),self.assertRaises(ValueError):validate(bad)

    def test_pending_case_retains_null_friction_and_wrong_source_frame_rejects(self):
        case=self.report['calculation']['terminals']['T1']['cases']['minimum'];case.update(status='pending',darcy_friction_factor=None,straight_friction_Pa=None,regime='Synthetic unsupported transition');self.report['calculation']['status']='pending'
        payload=common(self.request,self.report,self.root);self.assertEqual(payload['status'],'pending');self.assertIsNone(payload['components']['T1']['cases']['minimum']['straight_friction_Pa'])
        request=copy.deepcopy(self.request);request['coordinate_frame']['id']='different'
        with self.assertRaisesRegex(ValueError,'frame'):common(request,self.report,self.root)

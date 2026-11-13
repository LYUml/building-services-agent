import copy
import json
from pathlib import Path
import tempfile
import unittest
import ifcopenshell
from bsa import compound_junction as tool


class CompoundJunctionTests(unittest.TestCase):
    def fixture(self):
        return dict(project_uuid='0d51f671-9501-40ed-96ef-6e277bb5c753',source='Synthetic compound geometry, not a product',classification='assumed',placement=dict(source='Synthetic rotated/elevated construction',origin_m=[4.,5.,3.],rotation=[[0.,-1.,0.],[1.,0.,0.],[0.,0.,1.]]),wall_thickness_m=.001,stations=[dict(y_m=0.,width_m=.8,height_m=.6),dict(y_m=1.5,width_m=1.,height_m=.7),dict(y_m=3.,width_m=1.2,height_m=.8)],branches=[dict(id='a',y_m=.8,side=1,width_m=.4,height_m=.3,reach_m=1.),dict(id='b',y_m=1.8,side=-1,width_m=.5,height_m=.4,reach_m=1.),dict(id='c',y_m=1.8,side=1,width_m=.4,height_m=.3,reach_m=1.)],port_directions=dict(lower='SOURCE',upper='SINK',a='SOURCE',b='SOURCE',c='SOURCE'))

    def test_native_five_port_material_and_source_tamper(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'runs') as folder:
            folder=Path(folder);data=self.fixture();source=folder/'project.json';source.write_text(json.dumps(data));result=tool.run(source,folder/'native')
            self.assertEqual(result['checks']['ports'],5);self.assertEqual(result['checks']['euler_characteristic'],-6);self.assertTrue(result['checks']['all_centre_bores_open'])
            wrong=copy.deepcopy(data);wrong['stations'][1]['width_m']+=.01
            with self.assertRaisesRegex(ValueError,'station'):tool.inspect(folder/'native/junction.ifc',wrong)
            file=ifcopenshell.open(str(folder/'native/junction.ifc'));file.by_type('IfcDistributionPort')[0].FlowDirection='SOURCEANDSINK';file.write(str(folder/'bad.ifc'))
            with self.assertRaisesRegex(ValueError,'cap'):tool.inspect(folder/'bad.ifc',data)

    def test_independent_constant_union_has_known_volume(self):
        data=self.fixture();data['stations']=[dict(y_m=0.,width_m=1.,height_m=.8),dict(y_m=3.,width_m=1.,height_m=.8)]
        # Three non-overlapping side half-prisms contribute only the length outside half-width.
        expected=3*1*.8+sum(b['width_m']*b['height_m']*(b['reach_m']-.5) for b in data['branches'])
        self.assertAlmostEqual(tool.integral(data,False)[0],expected)

    def test_crossed_caps_overlap_and_unsupported_height_reject(self):
        data=self.fixture();data['branches'][0]['y_m']=.1
        with self.assertRaises(ValueError):tool.validate(data)
        data=self.fixture();data['branches'][2]['y_m']=.9
        with self.assertRaisesRegex(ValueError,'separated'):tool.validate(data)
        data=self.fixture();data['branches'][0]['height_m']=.9
        with self.assertRaisesRegex(ValueError,'height'):tool.validate(data)


if __name__=='__main__':unittest.main()

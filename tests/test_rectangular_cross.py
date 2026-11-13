import copy
import json
from pathlib import Path
import tempfile
import unittest
import ifcopenshell
from bsa import rectangular_cross as tool


class RectangularCrossTests(unittest.TestCase):
    def fixture(self):
        return dict(project_uuid='92244432-6bcd-42a7-a995-51ec0a29754b',source='Synthetic geometry; not a product',classification='assumed',internal_width_m=.6,internal_height_m=.3,wall_thickness_m=.001,main_half_length_m=.5,branch_length_m=.5,port_directions={'main-a':'SINK','main-b':'SOURCE','branch-a':'SOURCE','branch-b':'SOURCE'},placement=dict(source='Synthetic rotated elevated placement',origin_m=[4.,5.,3.],rotation=[[0.,0.,1.],[1.,0.,0.],[0.,1.,0.]]))

    def test_native_four_bores_and_source_tamper(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'runs') as folder:
            folder=Path(folder);spec=self.fixture();source=folder/'cross.json';source.write_text(json.dumps(spec))
            result=tool.run(source,folder/'native');self.assertEqual(result['checks']['ports'],4);self.assertEqual(result['checks']['euler_characteristic'],-4)
            wrong=copy.deepcopy(spec);wrong['branch_length_m']+=.01
            with self.assertRaisesRegex(ValueError,'depth|section|placement'):tool.inspect(folder/'native/cross.ifc',wrong)
            file=ifcopenshell.open(str(folder/'native/cross.ifc'));file.by_type('IfcDistributionPort')[0].FlowDirection='SOURCEANDSINK';file.write(str(folder/'bad.ifc'))
            with self.assertRaisesRegex(ValueError,'port'):tool.inspect(folder/'bad.ifc',spec)

    def test_four_arms_and_sufficient_core_reach_required(self):
        spec=self.fixture();spec['port_directions'].pop('branch-a')
        with self.assertRaises(ValueError):tool.validate(spec)
        spec=self.fixture();spec['branch_length_m']=.3
        with self.assertRaises(ValueError):tool.validate(spec)


if __name__=='__main__':unittest.main()

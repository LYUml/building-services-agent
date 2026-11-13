import copy
import unittest
from unittest.mock import patch
import numpy as np
from bsa import source_cross_network as tool
from bsa.tee_geometry import stable_guid
from bsa import rectangular_cross as cross
from tests import test_source_tee_network as tee_tests
from tests import test_rectangular_cross as cross_tests


class SourceCrossNetworkTests(unittest.TestCase):
    def test_cross_trim_keeps_prior_tee_consumption_and_sources(self):
        model,junction,selected,old_rows=tee_tests.SourceTeeNetworkTests().fixture()
        model['devices'][0]['properties'].update(AppliedTeeFromTrim_m=.12,AppliedTeeToTrim_m=.23)
        rows={name:dict(fit=row['fit']['arms']) for name,row in old_rows.items()};original=copy.deepcopy(model)
        with patch.object(tool.network.bim,'validate'):
            actual,interfaces,budgets=tool.compile_model(model,junction,selected,rows,{'A':['Existing source blocker']})
        props=actual['devices'][0]['properties'];self.assertEqual(model,original)
        self.assertEqual(props['AppliedTeeFromTrim_m'],.12);self.assertEqual(props['AppliedTeeToTrim_m'],.23)
        self.assertEqual(props['AppliedCrossFromTrim_m'],0);self.assertEqual(props['AppliedCrossToTrim_m'],.7)
        self.assertAlmostEqual(budgets[0]['remaining_m'],2.3);self.assertEqual([r['node'] for r in interfaces],['B'])

    def test_cross_cap_position_supply_and_roll_required(self):
        spec=cross_tests.RectangularCrossTests().fixture();owner=stable_guid(spec,'IfcDuctFitting',cross.KEY)
        first=np.eye(4);last=np.diag([1.,-1.,-1.,1.]);rows={'J':dict(data=dict(cross=spec,arms={n:dict(kind='bare') for n in cross.NAMES}))}
        expected=dict(objects={'s':dict(name='S',ifc_class='IfcDuctSegment',frame=first.tolist()),owner:dict(name='C',ifc_class='IfcDuctFitting',frame=first.tolist())},ports={'a':dict(owner='s',name='out',direction='SOURCE',frame=first.tolist()),'b':dict(owner=owner,name='main-a',direction='SINK',frame=last.tolist())})
        interfaces=[dict(node='J',arm='main-a',section='S',port='out')]
        self.assertEqual(tool.cross_links(expected,interfaces,rows),[('a','b')])
        wrong=copy.deepcopy(expected);wrong['ports']['b']['direction']='SOURCE'
        with self.assertRaisesRegex(ValueError,'cap'):tool.cross_links(wrong,interfaces,rows)
        wrong=copy.deepcopy(expected);wrong['ports']['b']['frame'][0][3]=.01
        with self.assertRaisesRegex(ValueError,'cap'):tool.cross_links(wrong,interfaces,rows)
        wrong=copy.deepcopy(expected);wrong['ports']['b']['frame']=np.array([[0,1,0,0],[1,0,0,0],[0,0,-1,0],[0,0,0,1.]]).tolist()
        with self.assertRaisesRegex(ValueError,'roll'):tool.cross_links(wrong,interfaces,rows)


if __name__=='__main__':unittest.main()

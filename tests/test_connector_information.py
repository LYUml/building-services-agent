from pathlib import Path
import tempfile
import unittest
import ifcopenshell.api as api
from bsa.ids_check import run
from test_product_information import model,ROOT


class ConnectorInformationTests(unittest.TestCase):
    def test_every_model_node_requires_axis_provenance(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp);path=root/'model.ifc';f=model(path)
            for port in f.by_type('IfcDistributionPort'):
                ps=api.run('pset.add_pset',f,product=port,name='BSA_ConnectorAnchor')
                api.run('pset.edit_pset',f,pset=ps,properties={k:'Synthetic presence test' for k in ('Source','PointHandle','AxisEndpoint','AxisLineHandle','SourceDXFSHA256','Scope')})
            f.write(str(path));ids=ROOT/'examples/ids/cad-connector-provenance.ids'
            self.assertTrue(run(ids,path,root/'positive')['calculated_checks_pass'])
            api.run('pset.edit_pset',f,pset=ps,properties={'AxisLineHandle':None});f.write(str(path))
            r=run(ids,path,root/'negative')
            self.assertFalse(r['calculated_checks_pass']);self.assertEqual(r['requirements_failed'],1)

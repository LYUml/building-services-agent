import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import ifcopenshell
import ifcopenshell.util.system as system
from bsa import source_fitting_data as tool,source_network_analysis as analysis,rectangular_tee
from tests import test_rectangular_cross as fixtures


class SourceFittingDataTests(unittest.TestCase):
    def test_native_literal_profile_restores_exact_geometry_without_widening_conditions(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'runs') as folder:
            folder=Path(folder);spec=fixtures.RectangularCrossTests().fixture();spec['port_directions']={'main-a':'SINK','main-b':'SOURCE','branch':'SOURCE'};p=folder/'source.json';p.write_text(json.dumps(spec));rectangular_tee.run(p,folder/'native');model=ifcopenshell.open(str(folder/'native/rectangular-tee.ifc'));obj=model.by_type('IfcDuctFitting')[0];ports={p.Name:p for p in system.get_ports(obj)};flows={'main-a':.5,'main-b':.3,'branch':.2};expected={p.GlobalId:dict(flow_m3_s=flows[p.Name],source_section=p.Name,source_node='Synthetic',classification='synthetic') for p in ports.values()};air=dict(density_kg_m3=1.2,viscosity_Pa_s=1.81e-5,roughness_m=.00009);case=analysis.calculate(model,expected,air);case['air']=air
            case['port_flows'][ports['main-b'].GlobalId]['width_m']*=1+1e-14;original=copy.deepcopy(case);canonical=tool.native_case(model,case);self.assertEqual(case,original)
            table=dict(source_id='synthetic',citation_location='Fictional test only',classification='synthetic',applicability_note='No physical data',friction_scope='local_dynamic_only',product_guid=obj.GlobalId,geometry_sha256=tool.tables.shape_hash(obj),inlet_port_guid=ports['main-a'].GlobalId,outlet_port_guid=ports['main-b'].GlobalId,reference_port_guid=ports['main-a'].GlobalId,axes=[dict(quantity='outlet_to_inlet_velocity_ratio',values=[.01,1.])],coefficients=[-.2,-.1],conditions=[dict(quantity='outlet_to_inlet_area_ratio',minimum=1.,maximum=1.)])
            result=tool.tables.calculate(model,canonical,dict(sources={'synthetic':{}},tables=[table]));self.assertEqual(result['calculated_table_paths'],1);self.assertLess(result['table_results'][0]['signed_tabulated_contribution_Pa'],0);self.assertFalse(result['pressure_budget_complete']);self.assertIsNone(result['critical_path'])
            changed=copy.deepcopy(case);changed['port_flows'][ports['main-b'].GlobalId]['width_m']+=.01
            with self.assertRaisesRegex(ValueError,'material cap'):tool.native_case(model,changed)

    def test_only_explicit_host_selected_external_basis_is_allowed(self):
        # The table values and text source are fictional software controls, not real correlations.
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder);document=folder/'synthetic.txt';document.write_text('Fictional coefficient source for software controls only')
            table=dict(source_id='synthetic',citation_location='Fictional test',classification='synthetic',applicability_note='Not physical',friction_scope='local_dynamic_only',product_guid='test',geometry_sha256='0'*64,inlet_port_guid='in',outlet_port_guid='out',reference_port_guid='in',axes=[dict(quantity='outlet_to_inlet_velocity_ratio',values=[.1,1.])],coefficients=[-.2,-.1])
            basis=folder/'basis.json';basis.write_text(json.dumps(dict(sources={'synthetic':dict(document=document.name,sha256=tool.digest(document),citation='Fictional test document',edition='Synthetic')},tables=[table])))
            with patch.dict(os.environ,{'BSA_PROJECT_ROOT':str(folder)}):
                data,pins=tool.tables.prepare(basis);self.assertEqual(len(pins),2);self.assertEqual(len(data['tables']),1)
            with patch.dict(os.environ,{'BSA_PROJECT_ROOT':''}):
                with self.assertRaisesRegex(ValueError,'workspace'):tool.tables.prepare(basis)


if __name__=='__main__':unittest.main()

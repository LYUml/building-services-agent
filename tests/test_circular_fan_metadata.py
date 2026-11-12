import json
from pathlib import Path
import unittest

import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.util.element as element
import ifcopenshell.util.system as system

from bsa.cli import digest
from bsa.circular_fan_metadata import BODY,PORT,annotate,inspect,read_operation,scenario_records
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]


class CircularFanMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tests.test_route_join import RouteJoinTests
        cls.fixture=RouteJoinTests;cls.fixture.setUpClass();cls.folder=cls.fixture.folder
        f=ifcopenshell.open(str(cls.fixture.joined))
        cls.records=dict(bodies={o.GlobalId:{'OperatingFlowRate':(.08,'flow'),'InletTotalPressure':(4.,'pressure'),'Scenario':('Explicit unit test calculated scenario','text')} for o in f.by_type('IfcElement')},ports={p.GlobalId:{'OperatingFlowRate':(.08,'flow'),'TotalPressure':(3.,'pressure'),'Scenario':('Explicit unit test calculated port scenario','text')} for p in f.by_type('IfcDistributionPort')})
        cls.target=cls.folder/'metadata.ifc';cls.source_sha=digest(cls.fixture.joined);cls.checks,cls.expected=annotate(cls.fixture.joined,cls.target,cls.records)

    @classmethod
    def tearDownClass(cls):cls.fixture.tearDownClass()

    def test_typed_properties_roundtrip_without_source_or_project_unit_changes(self):
        self.assertTrue(self.checks['original_geometry_and_properties_preserved'])
        self.assertTrue(self.checks['typed_explicit_units_pass']);self.assertTrue(self.checks['schema_valid'])
        self.assertEqual(self.checks['body_count'],3);self.assertEqual(self.checks['port_count'],6)
        self.assertEqual(digest(self.fixture.joined),self.source_sha)
        stored=json.loads(json.dumps(self.expected));self.assertTrue(inspect(self.target,stored)['typed_explicit_units_pass'])

    def test_missing_explicit_unit_changed_value_and_original_geometry_reject(self):
        for fault in ('unit','value','geometry','original_property','original_unit'):
            model=ifcopenshell.open(str(self.target));obj=model.by_type('IfcDuctSegment')[0]
            pset=model.by_id(element.get_psets(obj)[BODY]['id']);prop=next(p for p in pset.HasProperties if p.Name=='OperatingFlowRate')
            if fault=='unit':prop.Unit=None
            elif fault=='value':prop.NominalValue.wrappedValue=.081
            elif fault=='geometry':model.by_type('IfcExtrudedAreaSolid')[0].Depth+=.01
            elif fault=='original_property':
                original=model.by_id(element.get_psets(obj)['BSA_DesignInputs']['id']);next(p for p in original.HasProperties if p.Name=='InternalDiameter_m').NominalValue.wrappedValue=.2
            else:
                original=model.by_id(element.get_psets(obj)['BSA_DesignInputs']['id']);next(p for p in original.HasProperties if p.Name=='InternalDiameter_m').Unit=model.create_entity('IfcSIUnit',UnitType='LENGTHUNIT',Prefix='CENTI',Name='METRE')
            path=self.folder/('metadata-'+fault+'.ifc');model.write(str(path))
            with self.subTest(fault=fault),self.assertRaises(ProjectError):inspect(path,self.expected)

    def test_existing_scenario_namespace_is_not_overwritten(self):
        target=self.folder/'overwritten.ifc'
        with self.assertRaises(ProjectError):annotate(self.target,target,self.records)
        self.assertFalse(target.exists())

    def test_unrelated_existing_scenario_is_preserved(self):
        model=ifcopenshell.open(str(self.fixture.joined));outside=model.by_type('IfcElement')[-1]
        old=api.run('pset.add_pset',model,product=outside,name=BODY);api.run('pset.edit_pset',model,pset=old,properties={'ExistingScenario':'Unrelated original state'})
        excluded={p.GlobalId for p in system.get_ports(outside)}
        for p in system.get_ports(outside):
            old=api.run('pset.add_pset',model,product=p,name=PORT);api.run('pset.edit_pset',model,pset=old,properties={'ExistingScenario':'Unrelated port state'})
        records=dict(bodies={g:v for g,v in self.records['bodies'].items() if g!=outside.GlobalId},ports={g:v for g,v in self.records['ports'].items() if g not in excluded})
        source=self.folder/'unrelated-original.ifc';target=self.folder/'unrelated-preserved.ifc';model.write(str(source));checks,_=annotate(source,target,records)
        self.assertTrue(checks['original_geometry_and_properties_preserved'])
        saved=ifcopenshell.open(str(target));self.assertEqual(element.get_psets(saved.by_guid(outside.GlobalId))[BODY]['ExistingScenario'],'Unrelated original state')

    def test_unproven_or_failed_operating_report_is_not_a_model_source(self):
        for name,report in [('old',{}),('failed',dict(input_roles={'pressure_producer':str(self.folder),'curve':str(ROOT/'examples/route-search/circular-fan-curve.json')},calculated_checks_pass=False,selected_rerun_pass=False,design_accepted=False))]:
            producer=self.folder/name;producer.mkdir();(producer/'fan.json').write_text(json.dumps(report))
            with self.subTest(name=name),self.assertRaises(ProjectError):read_operation(producer)

    def test_coincident_interface_loss_keeps_two_distinct_port_pressures(self):
        baseline=dict(length_m=2,ledger=[dict(owner_guid='a',inlet_port_guid='a.in',outlet_port_guid='a.out',length_m=1,body_excess_k=0,downstream_interface_excess_k=.2,from_point_m=[0,0,0],to_point_m=[1,0,0]),dict(owner_guid='b',inlet_port_guid='b.in',outlet_port_guid='b.out',length_m=1,body_excess_k=0,downstream_interface_excess_k=0,from_point_m=[1,0,0],to_point_m=[2,0,0])])
        fresh=dict(operating_point=dict(flow_m3_s=.09,supply_total_pressure_pa=5),design_flow_m3_s=.08,terminal_node='END',network_analysis=dict(segments=[dict(friction_pa=2,velocity_m_s=2)],nodes=[dict(id='END',total_pressure_pa=2.52)]))
        records=scenario_records({},fresh,baseline,{'fluid':{'density_kg_m3':1.2}},'source','fan','curve')
        self.assertAlmostEqual(records['ports']['a.out']['TotalPressure'][0],4)
        self.assertAlmostEqual(records['ports']['b.in']['TotalPressure'][0],3.52)
        self.assertAlmostEqual(records['bodies']['a']['FollowingInterfacePressureDrop'][0],.48)

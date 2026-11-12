import copy
import json
from pathlib import Path
import tempfile
import unittest

import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.util.placement as placement
import numpy as np

from bsa.bim import run as author
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.route_ports import prepare, run

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT/'examples/route-search'


class SourcePortRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(dir=ROOT/'runs')
        cls.folder = Path(cls.temp.name)
        author(EXAMPLES/'port-source-model.json', cls.folder/'source')
        cls.ifc = cls.folder/'source/model.ifc'

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.basis, self.routing, self.settings = [json.loads((EXAMPLES/name).read_text()) for name in
            ('port-routing-basis.json', 'port-routing-template.json', 'vertical-air-settings.json')]

    def test_native_cap_frames_generate_endpoint_geometry_without_mutating_sources(self):
        before = digest(self.ifc)
        routing, records = prepare(self.ifc, self.basis, self.routing, self.settings)
        np.testing.assert_allclose(routing['start_m'], [0, 1.5], atol=1e-9)
        np.testing.assert_allclose(routing['end_m'], [4, 1.5], atol=1e-9)
        self.assertEqual(routing['endpoint_directions']['start']['axis'], [0, 1])
        self.assertEqual(routing['endpoint_directions']['end']['axis'], [0, -1])
        self.assertEqual(routing['endpoint_directions']['start']['classification'], 'geometry-derived')
        self.assertTrue(all(r['native_wall_cap_match'] for r in records.values()))
        self.assertEqual(digest(self.ifc), before)
        self.assertNotIn('start_m', self.routing)

    def test_duplicate_endpoints_and_replacement_owner_reject(self):
        for fault in ('start_m', 'endpoint_directions', 'owner'):
            routing = copy.deepcopy(self.routing)
            basis = copy.deepcopy(self.basis)
            if fault == 'owner':
                basis['start']['owner_guid'] = basis['end']['owner_guid']
            else:
                routing[fault] = [0, 1] if fault == 'start_m' else {}
            with self.subTest(fault=fault), self.assertRaises(ProjectError):
                prepare(self.ifc, basis, routing, self.settings)

    def test_native_bore_mismatch_and_off_plane_geometry_reject(self):
        for fault in ('bore', 'plane', 'grid'):
            settings = copy.deepcopy(self.settings)
            routing = copy.deepcopy(self.routing)
            if fault == 'bore':
                settings['inside_diameter_m'] = .2
            elif fault == 'plane':
                settings['plane_frame']['origin_m'][1] = 2
            else:
                routing['grid_step_m'] = .7
            with self.subTest(fault=fault), self.assertRaises(ProjectError):
                prepare(self.ifc, self.basis, routing, settings)

    def test_same_point_wrong_native_normal_and_connected_port_reject(self):
        for fault in ('normal', 'connected', 'direction', 'system', 'cap'):
            model = ifcopenshell.open(str(self.ifc))
            port = model.by_guid(self.basis['start']['port_guid'])
            if fault == 'normal':
                matrix = placement.get_local_placement(port.ObjectPlacement)
                matrix[:3, :3] = np.array([[0., 0., 1.], [1., 0., 0.], [0., 1., 0.]])
                api.run('geometry.edit_object_placement', model, product=port, matrix=matrix, is_si=True)
            elif fault == 'connected':
                api.run('system.connect_port', model, port1=port, port2=model.by_guid(self.basis['end']['port_guid']), direction='SOURCE')
            elif fault == 'direction':
                port.FlowDirection = 'SOURCEANDSINK'
            elif fault == 'system':
                model.by_type('IfcDistributionSystem')[0].PredefinedType = 'DOMESTICCOLDWATER'
            else:
                matrix = placement.get_local_placement(port.ObjectPlacement)
                matrix[2, 3] += .1
                api.run('geometry.edit_object_placement', model, product=port, matrix=matrix, is_si=True)
            target = self.folder/(fault+'.ifc')
            model.write(str(target))
            with self.subTest(fault=fault), self.assertRaises(ProjectError):
                prepare(target, self.basis, self.routing, self.settings)

    def test_invalid_source_does_not_create_optimization_output(self):
        target = self.folder/'invalid-output'
        settings = copy.deepcopy(self.settings)
        settings['inside_diameter_m'] = .2
        path = self.folder/'mismatch.json'
        path.write_text(json.dumps(settings))
        with self.assertRaises(ProjectError):
            run(self.ifc, EXAMPLES/'port-routing-basis.json', EXAMPLES/'port-routing-template.json', path,
                EXAMPLES/'vertical-air-network.json', target)
        self.assertFalse(target.exists())

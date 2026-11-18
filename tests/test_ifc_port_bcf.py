from datetime import timedelta
from importlib.util import find_spec
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4
from zipfile import ZipFile

from bsa.ifc_port_bcf import run, verify, verify_export, write
from bsa.source_refs import file_hash


@unittest.skipUnless(find_spec('mcp') and find_spec('bcf'), 'requires MCP and BCF runtimes')
class IfcPortBcfMcpTests(unittest.IsolatedAsyncioTestCase):
    async def test_round_trip_binds_tolerance_with_no_topics(self):
        import ifcopenshell
        from ifcopenshell.guid import new
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        repository = Path(__file__).resolve().parents[1]
        with TemporaryDirectory(dir=repository / 'runs') as temporary:
            root = Path(temporary)
            model = ifcopenshell.file(schema='IFC4')
            model.write(str(root / 'missing-project.ifc'))
            unit = model.create_entity('IfcSIUnit', UnitType='LENGTHUNIT', Name='METRE')
            units = model.create_entity('IfcUnitAssignment', Units=[unit])
            model.create_entity('IfcProject', GlobalId=new(), UnitsInContext=units)
            model.write(str(root / 'source.ifc'))
            millimetre = model.create_entity('IfcSIUnit', UnitType='LENGTHUNIT', Name='METRE', Prefix='MILLI')
            units.Units = [unit, millimetre]
            model.write(str(root / 'ambiguous-units.ifc'))
            params = StdioServerParameters(
                command=sys.executable, args=['-m', 'bsa.mcp_server'], cwd=str(repository),
                env={**os.environ, 'BSA_PROJECT_ROOT': str(root)},
            )
            async with stdio_client(params) as streams:
                async with ClientSession(*streams, read_timeout_seconds=timedelta(seconds=60)) as session:
                    await session.initialize()
                    malformed = await session.call_tool('bsa_export_ifc_port_bcf', {
                        'source': 'missing-project.ifc', 'out': 'rejected.bcf', 'tolerance_m': 0.001,
                    })
                    self.assertTrue(malformed.isError)
                    self.assertIn('Exactly one IfcProject', str(malformed.content))
                    self.assertFalse((root / 'rejected.bcf').exists())
                    ambiguous = await session.call_tool('bsa_export_ifc_port_bcf', {
                        'source': 'ambiguous-units.ifc', 'out': 'ambiguous.bcf', 'tolerance_m': 0.001,
                    })
                    self.assertTrue(ambiguous.isError)
                    self.assertIn('Multiple IFC project length units', str(ambiguous.content))
                    self.assertFalse((root / 'ambiguous.bcf').exists())
                    export = await session.call_tool('bsa_export_ifc_port_bcf', {
                        'source': 'source.ifc', 'out': 'review.bcf', 'tolerance_m': 0.001,
                    })
                    self.assertFalse(export.isError, export.content)
                    args = {'source': 'source.ifc', 'archive': 'review.bcf', 'tolerance_m': 0.001}
                    verified = await session.call_tool('bsa_verify_ifc_port_bcf', args)
                    self.assertFalse(verified.isError, verified.content)
                    self.assertEqual(verified.structuredContent, export.structuredContent)
                    self.assertEqual(verified.structuredContent['topics'], 0)
                    self.assertEqual(verified.structuredContent['ifc_review_status'], 'pending')
                    self.assertTrue(verified.structuredContent['archive_tolerance_bound'])
                    rejected = await session.call_tool('bsa_verify_ifc_port_bcf', dict(args, tolerance_m=0.002))
                    self.assertTrue(rejected.isError)
                    self.assertIn('does not match the supplied port gap tolerance', str(rejected.content))


@unittest.skipUnless(find_spec('bcf'), 'requires the optional BCF runtime')
class IfcPortBcfTests(unittest.TestCase):
    def test_saved_ifc_reversed_duplicate_survives_export_and_replay(self):
        import ifcopenshell
        from ifcopenshell.guid import new
        from bcf.v3.bcfxml import BcfXml

        runs = Path(__file__).resolve().parents[1] / 'runs'
        with TemporaryDirectory(dir=runs) as temporary:
            root = Path(temporary)
            source, archive = root / 'source.ifc', root / 'review.bcf'
            model = ifcopenshell.file(schema='IFC4')
            unit = model.create_entity('IfcSIUnit', UnitType='LENGTHUNIT', Name='METRE')
            units = model.create_entity('IfcUnitAssignment', Units=[unit])
            model.create_entity('IfcProject', GlobalId=new(), UnitsInContext=units)
            origin = model.create_entity('IfcCartesianPoint', Coordinates=(0.0, 0.0, 0.0))
            axes = model.create_entity('IfcAxis2Placement3D', Location=origin)
            placement = model.create_entity('IfcLocalPlacement', RelativePlacement=axes)
            ports = []
            for _ in range(2):
                port = model.create_entity('IfcDistributionPort', GlobalId=new(), ObjectPlacement=placement)
                owner = model.create_entity('IfcPipeSegment', GlobalId=new())
                model.create_entity('IfcRelNests', GlobalId=new(), RelatingObject=owner, RelatedObjects=[port])
                ports.append(port)
            relationships = []
            for first, second in (ports, ports[::-1]):
                relationship = model.create_entity('IfcRelConnectsPorts', GlobalId=new(),
                                                   RelatingPort=first, RelatedPort=second)
                relationships.append(relationship.GlobalId)
            model.write(str(source))

            exported = run(source, archive, 0.001)
            self.assertEqual(verify_export(source, archive, 0.001), exported)
            self.assertEqual((exported['ifc_review_status'], exported['measured_relationships']), ('fail', 2))
            with BcfXml.load(archive) as bcf:
                topic, = bcf.topics.values()
                self.assertTrue(topic.topic.title.startswith('IFC duplicate port pair'))
                for guid in relationships:
                    self.assertIn(guid, topic.topic.description)

    def test_rejects_topic_folder_with_different_guid(self):
        runs = Path(__file__).resolve().parents[1] / 'runs'
        with TemporaryDirectory(dir=runs) as temporary:
            root = Path(temporary)
            source = root / 'source.ifc'
            source.write_bytes(b'stand-in for the source hash in verifier tests')
            report = {
                'source_sha256': file_hash(source),
                'ports': [{'guid': 'port', 'origin_m': None, 'owner_evidence': []}],
                'connection_gaps': {'tolerance_m': 0.001, 'separated_relationships': [],
                                    'measured_relationships': 0, 'unavailable_relationships': []},
                'connection_ownership': {'conflicting_ports': ['port']},
            }
            original = root / 'original.bcf'
            result = write(report, source, original)
            self.assertEqual(result['topics'], 1)
            self.assertTrue(result['archive_tolerance_bound'])
            self.assertEqual(result['ifc_review_status'], 'fail')
            report['connection_gaps']['tolerance_m'] = 0.002
            with self.assertRaisesRegex(ValueError, 'does not match the supplied port gap tolerance'):
                verify(report, original)
            report['connection_gaps']['tolerance_m'] = 0.001
            changed = root / 'changed.bcf'
            different_guid = str(uuid4())
            with ZipFile(original) as saved, ZipFile(changed, 'x') as modified:
                for name in saved.namelist():
                    _, separator, member = name.partition('/')
                    modified.writestr(f'{different_guid}/{member}' if separator else name, saved.read(name))

            with self.assertRaisesRegex(ValueError, 'topic directory differs from its markup GUID'):
                verify(report, changed)

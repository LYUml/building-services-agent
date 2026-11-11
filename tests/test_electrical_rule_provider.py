"""Registered electrical rules reuse the actual consumer;no fake numerical worker."""
import json
import runpy
from pathlib import Path
import tempfile
import unittest
from bsa.cli import digest
from bsa.modules import run,verify_result
from bsa.module_electrical_rules import run as direct

ROOT=Path(__file__).resolve().parents[1]

class ElectricalRuleProviderTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        cache=self.root/'cache';cache.mkdir()
        build=runpy.run_path(str(ROOT/'examples/modular/build_electrical_rules_inputs.py'))['build']
        self.folder=build(self.root/'inputs',cache).parent
        source=self.folder/'sources/emsd-wiring-2025.pdf';source.write_bytes(b'SYNTHETIC REGISTRY CONTROL;NOT OFFICIAL EVIDENCE')
        pack=self.folder/'source/pack.json';d=json.loads(pack.read_text());d['sources']['emsd_wiring_2025']['sha256']=digest(source);pack.write_text(json.dumps(d))
        self.producer=self.root/'producer';result=run(self.folder/'request.json','bsa.single-phase-circuits',self.producer)
        request=json.loads((self.folder/'request.json').read_text());request['capability']='regulation.electrical.radial-paths'
        sources=dict(producer=self.producer/'result.json',topology=self.folder/'source/topology.json',basis=self.folder/'source/basis.json',pack=pack)
        import os
        request['sources']={k:dict(path=Path(os.path.relpath(v,self.folder)).as_posix(),sha256=digest(v)) for k,v in sources.items()}
        self.request=self.folder/'rules-request.json';self.request.write_text(json.dumps(request));self.sources=sources

    def test_registered_matches_direct_and_rehashed_assessment_mutation_rejects(self):
        r=run(self.request,'bsa.electrical-path-rules',self.root/'registered',runtime=dict(sources=self.folder/'sources'))
        d=direct(*[self.sources[k] for k in ('producer','topology','basis','pack')],self.folder/'sources',self.root/'direct')
        self.assertEqual(r['payload'],d['assessment']);self.assertEqual(r['payload']['status'],'pass')
        path=self.root/'registered/result.json';verify_result(path)
        r['payload']['status']='fail';path.write_text(json.dumps(r))
        with self.assertRaises(ValueError):verify_result(path)

    def test_disable_missing_cache_and_missing_official_bytes(self):
        for name,options in [('disabled',dict(disabled=True)),('unconfigured',{})]:
            r=run(self.request,'bsa.electrical-path-rules',self.root/name,**options)
            self.assertEqual(r['execution']['status'],'unavailable');self.assertIsNone(r['payload']);verify_result(self.root/name/'result.json')
        (self.folder/'sources/emsd-wiring-2025.pdf').unlink()
        r=run(self.request,'bsa.electrical-path-rules',self.root/'missing',runtime=dict(sources=self.folder/'sources'))
        self.assertEqual(r['execution']['status'],'completed');self.assertEqual(r['payload']['status'],'pending');verify_result(self.root/'missing/result.json')

    def test_identity_mismatch_rejects_without_payload(self):
        d=json.loads(self.request.read_text());d['project_id']='different-project';self.request.write_text(json.dumps(d))
        r=run(self.request,'bsa.electrical-path-rules',self.root/'wrong',runtime=dict(sources=self.folder/'sources'))
        self.assertEqual(r['execution']['status'],'failed');self.assertIsNone(r['payload']);verify_result(self.root/'wrong/result.json')

    def test_exceeded_path_is_completed_execution_with_failed_assessment(self):
        path=self.sources['topology'];data=json.loads(path.read_text());data['feeders'][0]['route_length_m']=300;path.write_text(json.dumps(data))
        request=json.loads(self.request.read_text());request['sources']['topology']['sha256']=digest(path);self.request.write_text(json.dumps(request))
        r=run(self.request,'bsa.electrical-path-rules',self.root/'exceeded',runtime=dict(sources=self.folder/'sources'))
        self.assertEqual(r['execution']['status'],'completed');self.assertEqual(r['payload']['status'],'fail')
        self.assertFalse(r['design_accepted']);verify_result(self.root/'exceeded/result.json')

    def test_frame_mismatch_rejects_and_unknown_source_role_is_not_dispatched(self):
        request=json.loads(self.request.read_text());request['coordinate_frame']['id']='replacement-frame';self.request.write_text(json.dumps(request))
        r=run(self.request,'bsa.electrical-path-rules',self.root/'frame',runtime=dict(sources=self.folder/'sources'))
        self.assertEqual(r['execution']['status'],'failed');self.assertIsNone(r['payload'])
        request['sources']['commands']=request['sources']['basis'];self.request.write_text(json.dumps(request))
        with self.assertRaisesRegex(ValueError,'exact producer/topology/basis/pack'):
            run(self.request,'bsa.electrical-path-rules',self.root/'not-created')
        self.assertFalse((self.root/'not-created').exists())

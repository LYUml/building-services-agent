import copy
import json
from pathlib import Path
import tempfile
import unittest

from bsa.duct_schedule import run as produce
from bsa.duct_schedule_check import ROOT, calculate, section


class DuctScheduleCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.project=dict(basis='Synthetic source and criteria;not real hardware',
            air=dict(density_kg_m3=1.2,viscosity_Pa_s=1.81e-5,roughness_m=9e-5),
            sections=[dict(id='S',flow_m3_s=.5,candidate_basis='Synthetic finite grid',
                candidates=[dict(id=str(w),width_m=w,height_m=w) for w in (.2,.4,.6)],
                limits=dict(actual_velocity_m_s=8,friction_Pa_m=2,aspect_ratio=4))])
        path=self.root/'project.json';path.write_text(json.dumps(self.project))
        self.saved=produce(path,self.root/'producer')

    def test_saved_candidates_and_prescribed_source_dimensions(self):
        result=calculate(self.saved,self.project)
        self.assertEqual(result['section_count'],1);self.assertEqual(result['candidate_count'],3)
        self.assertTrue(result['independent_equation_checks_pass']);self.assertTrue(result['source_candidate_ranking_pass'])
        self.assertLess(result['maximum_absolute_colebrook_residual'],1e-10)
        self.assertFalse(result['scanned_chart_readings_verified']);self.assertFalse(result['design_accepted'])
        original=copy.deepcopy(self.project)
        row=original['sections'][0];row.pop('candidates');row.pop('candidate_basis');row.update(width_m=.8,height_m=.4)
        path=self.root/'prescribed.json';path.write_text(json.dumps(original))
        saved=produce(path,self.root/'prescribed')
        result=calculate(saved,original)
        q=result['sections'][0]['independent_quantities']
        self.assertAlmostEqual(q['actual_velocity_m_s'],1.5625)
        self.assertNotEqual(q['actual_velocity_m_s'],q['equivalent_round_velocity_m_s'])
        self.assertIsNone(result['source_candidate_ranking_pass'])

    def test_coherently_forged_factor_and_pressure_still_fail_residual(self):
        row=self.saved['sections'][0]
        changed=copy.deepcopy(row['calculation']);changed['darcy_factor']*=1.01;changed['friction_Pa_m']*=1.01
        with self.assertRaisesRegex(ValueError,'Colebrook residual'):
            section(row['inputs'],self.project['air'],changed)
        for name in ('reynolds','actual_velocity_m_s','equivalent_round_velocity_m_s','equivalent_diameter_m','friction_Pa_m'):
            changed=copy.deepcopy(row['calculation']);changed[name]*=1.01
            with self.subTest(name=name),self.assertRaisesRegex(ValueError,'equation mismatch'):
                section(row['inputs'],self.project['air'],changed)

    def test_unselected_candidate_tamper_coverage_ranking_and_limits_reject(self):
        for case in ('unselected_factor','missing_candidate','candidate_dimension','rejected_as_passing','wrong_rank','source_limit','source_flow'):
            saved=copy.deepcopy(self.saved);source=copy.deepcopy(self.project)
            selection=saved['sections'][0]['selection']
            if case=='unselected_factor':
                c=selection['candidates'][-1]['calculation'];c['darcy_factor']*=1.01;c['friction_Pa_m']*=1.01
            elif case=='missing_candidate':selection['candidates'].pop()
            elif case=='candidate_dimension':selection['candidates'][-1]['width_m']+=.01
            elif case=='rejected_as_passing':selection['candidates'][0]['failures']=[]
            elif case=='wrong_rank':selection['selected']=selection['candidates'][-1]
            elif case=='source_limit':source['sections'][0]['limits']['friction_Pa_m']=3
            elif case=='source_flow':source['sections'][0]['flow_m3_s']*=1.01
            with self.subTest(case=case),self.assertRaises(ValueError):calculate(saved,source)

    def test_invalid_empty_nonfinite_and_unsupported_cases_reject(self):
        for key in ('flow_m3_s','width_m','height_m'):
            inputs=copy.deepcopy(self.saved['sections'][0]['inputs']);inputs[key]=float('nan')
            with self.assertRaises(ValueError):section(inputs,self.project['air'],self.saved['sections'][0]['calculation'])
        saved=copy.deepcopy(self.saved);saved['status']='fail'
        with self.assertRaises(ValueError):calculate(saved,self.project)
        saved=copy.deepcopy(self.saved);saved['sections']=[]
        source=copy.deepcopy(self.project);source['sections']=[]
        with self.assertRaisesRegex(ValueError,'coverage'):calculate(saved,source)

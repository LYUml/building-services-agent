import copy
import json
from pathlib import Path
import tempfile
import unittest

import ezdxf
from bsa.drawing_document import author, audit, run, validate, verify

ROOT=Path(__file__).resolve().parents[1]


class DrawingDocumentTests(unittest.TestCase):
    def setUp(self):
        self.spec=json.loads((ROOT/'examples/drawing-document.json').read_text())
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def drawings(self):
        doc,_=author(self.spec);a=self.root/'source.dxf';b=self.root/'changed.dxf';doc.saveas(a);doc.saveas(b)
        return a,b

    def test_dimensions_preserve_real_measurements_and_unit_scale(self):
        before=copy.deepcopy(self.spec)
        doc,_=author(self.spec)
        self.assertEqual(self.spec,before)
        dims=list(doc.modelspace().query('DIMENSION'))
        for dim,expected in zip(dims,[105.,55.,30.]):self.assertAlmostEqual(float(dim.get_measurement()),expected,places=10)
        for d in dims:
            self.assertEqual(d.get_acad_dstyle(d.get_dim_style())['dimlfac'],1.)
            self.assertTrue(list(d.virtual_entities()))
        a,b=self.drawings();self.assertEqual(audit(a,b)['entity_types']['DIMENSION'],3)

    def test_symbol_and_dimension_mutation_rejected(self):
        for mutation in ('symbol','dimension','layer','hidden','units'):
            with self.subTest(mutation=mutation):
                a,b=self.drawings();d=ezdxf.readfile(b)
                if mutation=='symbol':d.blocks['VALVE'].query('CIRCLE')[0].dxf.radius=2
                elif mutation=='dimension':
                    dim=d.modelspace().query('DIMENSION')[0];o=dim.override();o['dimlfac']=100;o.commit()
                elif mutation=='layer':d.layers.get('GEOMETRY').off()
                elif mutation=='hidden':d.modelspace().query('LINE')[0].dxf.invisible=1
                else:d.units=6
                d.saveas(b)
                with self.assertRaises(ValueError):audit(a,b)

    def test_bad_coordinates_duplicate_identity_and_nested_blocks_rejected(self):
        for mutation in ('nan','identity','nested','runtime'):
            with self.subTest(mutation=mutation):
                s=copy.deepcopy(self.spec)
                if mutation=='nan':s['entities'][0]['points'][0][0]=float('nan')
                elif mutation=='identity':s['entities'][1]['id']=s['entities'][0]['id']
                elif mutation=='nested':s['blocks']['VALVE'].append(copy.deepcopy(next(e for e in s['entities'] if e['kind']=='insert')))
                else:s['autocad']='untrusted document-selected executable'
                with self.assertRaises(ValueError):validate(s)

    def test_no_native_claim_without_autocad_and_no_overwrite(self):
        p=self.root/'drawing.json';p.write_text(json.dumps(self.spec));out=self.root/'result'
        r=run(p,out);self.assertFalse(r['native_reopen_pass']);self.assertFalse((out/'Drawing.dwg').exists())
        with self.assertRaises(ValueError):run(p,out)

    def test_rehashed_geometry_forgery_and_source_changes_rejected(self):
        from bsa.cli import digest
        p=self.root/'drawing.json';p.write_text(json.dumps(self.spec));out=self.root/'result';run(p,out)
        self.assertTrue(verify(p,out)['integrity_pass'])
        doc=ezdxf.readfile(out/'Drawing.dxf');doc.modelspace().query('CIRCLE')[0].dxf.radius=12;doc.saveas(out/'Drawing.dxf')
        result=json.loads((out/'drawing-result.json').read_text());result['dxf_sha256']=digest(out/'Drawing.dxf')
        (out/'drawing-result.json').write_text(json.dumps(result))
        with self.assertRaisesRegex(ValueError,'entity or symbol mismatch'):verify(p,out)
        p.write_text(json.dumps(dict(self.spec,source='Changed source')))
        with self.assertRaisesRegex(ValueError,'source, methods'):verify(p,out)


if __name__=='__main__':unittest.main()

import copy
import json
import os
import re
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest
from bsa.cli import digest
from bsa.energy_completion import KNOWN_BUILD,KNOWN_EXE_SHA256,assess,inspect

ROOT=Path(__file__).resolve().parents[1]


def evidence():
    return dict(returncode=0,stdout='EnergyPlus Completed Successfully.\n',
                end_report='EnergyPlus Completed Successfully-- 0 Warning; 0 Severe Errors; Elapsed Time=00hr 00min 1sec\n',
                diagnostics='No severe diagnostics',sql_flags=['FALSE','FALSE'],
                sql_version='EnergyPlus, Version '+KNOWN_BUILD+', YMD=2026.11.08',
                engine_version='EnergyPlus, Version '+KNOWN_BUILD,engine_sha256=KNOWN_EXE_SHA256)


class CompletionClassificationTests(unittest.TestCase):
    def test_official_initial_flags_explained_but_never_rewritten(self):
        data=evidence();original=copy.deepcopy(data);r=assess(**data)
        self.assertTrue(r['completion_verified']);self.assertEqual(r['status'],'verified_with_known_unwritten_sql_flags')
        self.assertFalse(r['native_sql_success_flags_true']);self.assertEqual(r['sql_flags_raw'],['FALSE','FALSE'])
        self.assertEqual(data,original);self.assertFalse(r['design_accepted'])

    def test_initial_flags_never_clear_failed_process_end_or_diagnostics(self):
        for change in (dict(returncode=1),dict(stdout='EnergyPlus Terminated--Error(s) Detected.'),
                       dict(end_report='EnergyPlus Terminated--Error(s) Detected.'),
                       dict(end_report='EnergyPlus Completed Successfully-- 1 Warning; 1 Severe Errors; Elapsed Time=1sec'),
                       dict(diagnostics=' ** Severe ** invalid equipment'),dict(sql_flags=[1,0])):
            data=evidence();data.update(change);r=assess(**data)
            self.assertFalse(r['completion_verified']);self.assertEqual(r['status'],'failed')

    def test_unknown_binary_version_malformed_and_impossible_flags_need_review(self):
        for change in (dict(engine_sha256='0'*64),dict(engine_version='EnergyPlus, Version 26.1.0-abcdef'),
                       dict(sql_flags=[None,None]),dict(sql_flags=[0,1]),dict(sql_version='EnergyPlus, Version 24.2.0-abcdef')):
            data=evidence();data.update(change);r=assess(**data)
            self.assertFalse(r['completion_verified']);self.assertEqual(r['status'],'needs_review')
        data=evidence();data.update(sql_flags=[1,1],engine_sha256='0'*64)
        self.assertEqual(assess(**data)['status'],'verified')

    def test_readonly_audit_pins_native_files_and_preserves_sql_defaults(self):
        data=evidence()
        with tempfile.TemporaryDirectory() as f:
            root=Path(f)/'case # data';root.mkdir()
            for name,key in [('engine.log','stdout'),('eplusout.end','end_report'),('eplusout.err','diagnostics')]:
                (root/name).write_text(data[key])
            sql=root/'eplusout.sql';con=sqlite3.connect(sql)
            con.execute('CREATE TABLE Simulations (EnergyPlusVersion TEXT,Completed BOOL,CompletedSuccessfully BOOL)')
            con.execute('INSERT INTO Simulations VALUES (?,?,?)',(data['sql_version'],'FALSE','FALSE'));con.commit();con.close()
            before={p.name:digest(p) for p in root.iterdir()}
            r=inspect(root,0,data['engine_version'],data['engine_sha256'])
            self.assertTrue(r['completion_verified']);self.assertEqual(r['artifacts'],before)
            self.assertEqual({p.name:digest(p) for p in root.iterdir()},before)
            self.assertEqual(list(Path(f).iterdir()),[root])

    def test_success_markers_without_native_sql_cannot_prove_completion(self):
        data=evidence()
        with tempfile.TemporaryDirectory() as f:
            root=Path(f)
            for name,key in [('engine.log','stdout'),('eplusout.end','end_report'),('eplusout.err','diagnostics')]:
                (root/name).write_text(data[key])
            r=inspect(root,0,data['engine_version'],data['engine_sha256'])
            self.assertFalse(r['completion_verified']);self.assertEqual(r['status'],'needs_review')
            self.assertEqual(r['missing_artifacts'],['eplusout.sql'])


@unittest.skipUnless(os.environ.get('BSA_TEST_ENERGYPLUS'),'requires actual EnergyPlus')
class NativeCompletionTests(unittest.TestCase):
    def test_actual_fatal_run_is_not_cleared_by_known_engine_policy(self):
        exe=Path(os.environ['BSA_TEST_ENERGYPLUS']).resolve()
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as f:
            root=Path(f);idf=root/'invalid.idf'
            source=(ROOT/'docs/evidence/annual-energy/baseline/model.idf').read_text(encoding='utf-8')
            changed,count=re.subn(r'(?m)^(\s*)Construction 1,(\s*!- Construction Name)',r'\1MISSING_TEST_CONSTRUCTION,\2',source,count=1)
            self.assertEqual(count,1);idf.write_text(changed,encoding='utf-8')
            from bsa.annual_energy import weather_bytes
            weather=root/'weather.epw';weather.write_bytes(weather_bytes(ROOT/'examples/annual-energy/USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw.gz'))
            with (root/'engine.log').open('wb') as stream:proc=subprocess.run([str(exe),'-x','-w',str(weather),'-d',str(root),str(idf)],cwd=root,stdout=stream,stderr=subprocess.STDOUT,timeout=120)
            self.assertNotEqual(proc.returncode,0)
            version=subprocess.check_output([str(exe),'--version'],text=True).strip()
            r=inspect(root,proc.returncode,version,digest(exe))
            self.assertEqual(r['status'],'failed');self.assertFalse(r['completion_verified'])

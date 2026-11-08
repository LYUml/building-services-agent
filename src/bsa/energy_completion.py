"""Read-only native EnergyPlus completion diagnosis; never rewrite SQL flags.

The one known default-flag exception is bound to the inspected official Windows
25.2 executable bytes, source commit and normal-finalization ordering.
"""
import re
import sqlite3
from pathlib import Path
from .cli import digest
from .engine import ProjectError

KNOWN_BUILD='25.2.0-cf7368216c'
KNOWN_EXE_SHA256='51715987663666eaff1c8d3bd6ac2d7fe0486d8bc93673eea87c6912a79103f0'
SOURCE_COMMIT='cf7368216c73c43181e057fa33b479c4e0c86df0'
SOURCE_FACTS={
    'api/EnergyPlusPgm.cc':dict(sha256='d230aa32b5acc6bdcb8c55d95022f1ecca351719b9b2d43f53a8270e7b1214d2',fact='normal wrapUpEnergyPlus releases the SQLite object before calling EndEnergyPlus'),
    'UtilityRoutines.cc':dict(sha256='bf0c2e9175b374ce100b0b262523d8d6c507baaf3922f5cc84fb6a3651152a3d',fact='EndEnergyPlus updates success flags only when the SQLite object still exists'),
    'SQLiteProcedures.cc':dict(sha256='b324324996a62c6fc5cf93a3039a2ea2d5788292faf77b07030b55debfa9c1a1',fact='Simulations completion columns initially contain text FALSE/FALSE')}


def version_token(value):
    match=re.search(r'\b(\d+\.\d+\.\d+-[0-9a-f]+)\b',value or '')
    return match.group(1) if match else None


def boolean(value):
    if type(value) is bool:return value
    if type(value) is int and value in (0,1):return bool(value)
    if isinstance(value,str) and value.strip().upper() in ('TRUE','FALSE'):return value.strip().upper()=='TRUE'
    return None


def assess(returncode,stdout,end_report,diagnostics,sql_flags,sql_version,engine_version,engine_sha256):
    flags=[boolean(v) for v in sql_flags] if isinstance(sql_flags,(tuple,list)) and len(sql_flags)==2 else [None,None]
    build=version_token(engine_version);sql_build=version_token(sql_version)
    defaults=flags==[False,False]
    known=defaults and build==KNOWN_BUILD and engine_sha256==KNOWN_EXE_SHA256
    match=re.match(r'^EnergyPlus Completed Successfully--\s*(\d+) Warning;\s*(\d+) Severe Errors;',end_report.strip())
    checks=dict(process_exit_zero=type(returncode) is int and returncode==0,
                stdout_success='EnergyPlus Completed Successfully.' in stdout and 'EnergyPlus Terminated' not in stdout,
                end_report_success=bool(match) and int(match.group(2))==0,
                no_severe_fatal=not bool(re.search(r'\*\*\s*(?:Severe|Fatal)\s*\*\*',diagnostics,re.I)),
                sql_engine_version_match=build is not None and sql_build==build,
                sql_flags_compatible=flags==[True,True] or known)
    verified=all(checks.values())
    failure=not checks['process_exit_zero'] or not checks['stdout_success'] or not checks['end_report_success'] or not checks['no_severe_fatal'] or flags==[True,False]
    status='verified_with_known_unwritten_sql_flags' if verified and known else 'verified' if verified else 'failed' if failure else 'needs_review'
    return dict(status=status,completion_verified=verified,checks=checks,process_returncode=returncode,
                sql_flags_raw=sql_flags,sql_flags_decoded=flags,native_sql_success_flags_true=flags==[True,True],
                known_unwritten_initial_flags=known,engine_version=engine_version,engine_sha256=engine_sha256,
                source_inference=dict(commit=SOURCE_COMMIT,facts={name:dict(row,url='https://github.com/NatLabRockies/EnergyPlus/blob/'+SOURCE_COMMIT+'/src/EnergyPlus/'+name) for name,row in SOURCE_FACTS.items()},
                                      scope='pinned source ordering plus observed official executable reproduction; not instruction tracing') if known else None,
                scope='Native process/log/end/error/SQL-version completion evidence only; period coverage, numerical/model validity and engineering acceptance remain separate',
                design_accepted=False)


def inspect(folder,returncode,engine_version,engine_sha256):
    folder=Path(folder).resolve();files=[folder/name for name in ('engine.log','eplusout.end','eplusout.err','eplusout.sql')]
    missing=[p.name for p in files if not p.is_file()];before={p.name:digest(p) for p in files if p.is_file()};rows=[];sql_error=None
    if files[-1].is_file():
        con=sqlite3.connect(files[-1].as_uri()+'?mode=ro',uri=True)
        try:rows=con.execute('SELECT EnergyPlusVersion,Completed,CompletedSuccessfully FROM Simulations').fetchall()
        except sqlite3.DatabaseError as exc:sql_error=str(exc)
        finally:con.close()
    text=lambda p:p.read_text(errors='replace') if p.is_file() else ''
    valid_sql=len(rows)==1 and sql_error is None
    result=assess(returncode,text(files[0]),text(files[1]),text(files[2]),list(rows[0][1:]) if valid_sql else [None,None],rows[0][0] if valid_sql else None,engine_version,engine_sha256)
    result['checks'].update(native_files_complete=not missing,one_readable_sql_record=valid_sql)
    result['completion_verified']=all(result['checks'].values())
    if not result['completion_verified'] and result['status'].startswith('verified'):result['status']='needs_review'
    if any(not (folder/name).is_file() or digest(folder/name)!=sha for name,sha in before.items()) or any((folder/name).exists() for name in missing):raise ProjectError('native completion source changed during read-only audit')
    result.update(artifacts=before,missing_artifacts=missing,sql_parse_error=sql_error,source_files_unchanged=True)
    return result

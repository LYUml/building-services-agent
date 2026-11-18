"""Host-controlled HVAC package execution and source-bound artifact inventory."""
import json
from pathlib import Path
from . import hvac_project,hvac_package,workflow
from .cli import digest


def prepare(plan,out,**settings):
    data=hvac_project.create(plan,out,**settings)
    return dict(configuration=str(Path(out).resolve()),configuration_sha256=digest(Path(out)),
        files=data['files'],selectors=data['selectors'],design_accepted=False)


def inspect(configuration,out):
    configuration,out=hvac_project.local(configuration),hvac_project.local(out)
    files,selectors,pins=hvac_project.load(configuration)
    receipt=json.loads((out/'project-run.json').read_text())
    if receipt['configuration']!=str(configuration) or receipt['configuration_sha256']!=digest(configuration) or receipt['input_hashes']!={str(p):sha for p,sha in pins.items()}:
        raise ValueError('HVAC project receipt differs from current configuration')
    if receipt['generator_sha256']!=digest(Path(hvac_project.__file__)) or receipt['package_sha256']!=digest(out/'package.json') or receipt['design_accepted'] is not False:
        raise ValueError('HVAC package receipt or method changed')
    package=json.loads((out/'package.json').read_text())
    if receipt['status']!=package['status'] or package['generator_sha256']!=digest(Path(hvac_package.__file__)) or package['plan_sha256']!=digest(files['plan']) or package['design_accepted'] is not False:
        raise ValueError('HVAC package source or method changed')
    artifacts=[]
    for name,sha in package['artifact_hashes'].items():
        path=(out/name).resolve()
        if not path.is_relative_to(out) or not path.is_file() or digest(path)!=sha:raise ValueError('HVAC package artifact changed or escaped')
        artifacts.append(dict(path=Path(name).as_posix(),sha256=sha,bytes=path.stat().st_size))
    for stage in package['stages'].values():
        if any(not Path(name).is_file() or digest(Path(name))!=sha for name,sha in stage.get('inputs',{}).items()):
            raise ValueError('HVAC stage source or runtime changed')
    if package['workflow_sha256']!=digest(out/'workflow/workflow.json'):raise ValueError('HVAC workflow changed')
    checked=workflow.verify(out/'workflow')
    if not checked['integrity_pass']:raise ValueError('HVAC workflow source verification failed: '+str(checked['issues']))
    terminal_gate = 'not_configured'
    stages, errors = package['stages'], package['stage_errors']
    if 'terminal_review' in files:
        settings_path = files['terminal_review']
        settings = json.loads(settings_path.read_bytes())
        expected = dict(path=str(settings_path), sha256=pins[settings_path], settings=settings)
        if package.get('terminal_review_configuration') != expected:
            raise ValueError('HVAC terminal review configuration differs from the package')
        if 'terminal_review' in errors:
            if (package['status'] != 'incomplete' or 'terminal_review' in stages
                    or {'report', 'report_pdf'}.intersection(stages)
                    or any((out/name).exists() for name in ('report', 'report-pdf', 'terminal-review.json'))):
                raise ValueError('HVAC package contains report output despite failed terminal review')
            terminal_gate = 'blocked'
        else:
            evidence = stages.get('terminal_review', {})
            if ('terminal-review.json' not in package['artifact_hashes']
                    or json.loads((out/'terminal-review.json').read_bytes()) != evidence
                    or evidence.get('workflow_sha256') != package['workflow_sha256']
                    or evidence.get('plan_sha256') != package['plan_sha256']
                    or evidence.get('lineage', [])[:1] != [settings['native_task']]
                    or evidence.get('layers') != settings['layers']
                    or evidence.get('correspondence_pass') is not True):
                raise ValueError('HVAC package lacks matching terminal review evidence')
            terminal_gate = 'passed'
    elif (package.get('terminal_review_configuration') is not None
          or 'terminal_review' in stages or 'terminal_review' in errors
          or (out/'terminal-review.json').exists()):
        raise ValueError('HVAC terminal review evidence requires a configured review')
    return dict(configuration_sha256=digest(configuration),package_sha256=digest(out/'package.json'),
        status=package['status'],stage_errors=package['stage_errors'],stages=list(package['stages']),
        terminal_review_gate=terminal_gate,
        unresolved_tasks=package['unresolved_tasks'],artifacts=artifacts,
        plan=str(files['plan']),workflow=str(out/'workflow'),output=str(out),
        integrity_pass=True,design_accepted=False,
        scope='Current source/method and recorded artifact correspondence; actual visual and full engineering acceptance remain separate')


def run(configuration,out,*,font=None,autocad=None,module_providers=None,disabled_module_providers=()):
    if font is None or not Path(font).is_file():raise ValueError('Host report font required before HVAC execution')
    hvac_project.run(configuration,out,font=font,autocad=autocad,
        module_providers=module_providers,disabled_module_providers=disabled_module_providers)
    return inspect(configuration,out)

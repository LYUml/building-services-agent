"""Pin a reviewed project's HVAC package settings for repeatable invocation."""
import argparse
import json
import os
from pathlib import Path
import re

from .cli import digest
from . import hvac_package
from .workflow import validate_plan

ROOT = Path(__file__).resolve().parents[2]
FILES = ('plan', 'terminal_review', 'adpi_settings', 'plan_clearance', 'terminal_performance')
SELECTORS = ('junction_review_native_task', 'system_paths_native_task')
KEYS = {'schema', 'files', 'selectors', 'input_hashes'}


def local(path):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError('Repository-local project configuration and inputs required')
    return path


def inventory(files, selectors):
    """Reuse plan intake and dependency discovery; do not interpret a raw brief."""
    plan, inputs = validate_plan(files['plan'])
    inputs = {local(p) for p in inputs} | set(files.values())
    for key in SELECTORS:
        value = selectors[key]
        if value is not None and (not isinstance(value, str) or not any(
                t['id'] == value and t['kind'] == 'duct_sheet_native' for t in plan['tasks'])):
            raise ValueError('Project review selector must name a declared native sheet task')
    if 'adpi_settings' in files:
        from .adpi_review import settings_inputs
        _,adpi_pins = settings_inputs(files['adpi_settings'])
        inputs.update(local(p) for p in adpi_pins)
    if 'terminal_performance' in files:
        from .terminal_performance import settings_inputs
        _,performance_pins=settings_inputs(files['terminal_performance'])
        inputs.update(local(p) for p in performance_pins)
        if len([t for t in plan['tasks'] if t['kind']=='terminal_throw'])!=1:
            raise ValueError('One declared terminal lookup required for performance stage')
    return {p: digest(p) for p in sorted(inputs)}


def relative(path, parent):
    return Path(os.path.relpath(path, parent)).as_posix()


def create(plan, configuration, *, terminal_review=None, adpi_settings=None,
           plan_clearance=None, junction_review_native_task=None, system_paths_native_task=None,terminal_performance=None):
    configuration = local(configuration)
    if configuration.exists():
        raise ValueError('New project configuration required; existing files are preserved')
    files = {'plan': local(plan)}
    for key, value in (('terminal_review', terminal_review), ('adpi_settings', adpi_settings),
                       ('plan_clearance', plan_clearance),('terminal_performance',terminal_performance)):
        if value is not None:
            files[key] = local(value)
    selectors = dict(junction_review_native_task=junction_review_native_task,
                     system_paths_native_task=system_paths_native_task)
    pins = inventory(files, selectors)
    if configuration in pins:
        raise ValueError('Configuration cannot replace an input')
    data = dict(schema='bsa.hvac_project', files={k: relative(v, configuration.parent) for k, v in files.items()},
                selectors=selectors, input_hashes={relative(p, configuration.parent): sha for p, sha in pins.items()})
    configuration.parent.mkdir(parents=True, exist_ok=True)
    with configuration.open('x', encoding='utf-8') as stream:
        json.dump(data, stream, indent=2)
    return data


def load(configuration):
    configuration = local(configuration)
    configuration_hash = digest(configuration)
    data = json.loads(configuration.read_text(encoding='utf-8-sig'))
    if not isinstance(data, dict) or set(data) != KEYS or data['schema'] != 'bsa.hvac_project':
        raise ValueError('Exact HVAC project configuration required; no engine or command fields permitted')
    if not isinstance(data['files'], dict) or 'plan' not in data['files'] or set(data['files']) - set(FILES):
        raise ValueError('Explicit supported project files required')
    if not isinstance(data['selectors'], dict) or set(data['selectors']) != set(SELECTORS):
        raise ValueError('Exact review selectors required; omitted reviews must remain null')
    def resolve(value):
        if not isinstance(value, str) or not value.strip() or Path(value).is_absolute():
            raise ValueError('Nonempty relative repository-local reference required')
        return local(configuration.parent / value)
    files = {key: resolve(value) for key, value in data['files'].items()}
    expected = data['input_hashes']
    if not isinstance(expected, dict) or not expected or any(
            not isinstance(v, str) or not re.fullmatch('[0-9a-f]{64}', v) for v in expected.values()):
        raise ValueError('Explicit source input hashes required')
    pins = {resolve(p): sha for p, sha in expected.items()}
    if len(pins) != len(expected) or configuration in pins:
        raise ValueError('Distinct source paths separate from configuration required')
    if any(digest(p) != sha for p, sha in pins.items()):
        raise ValueError('Project source changed; review and create a new configuration')
    actual = inventory(files, data['selectors'])
    if pins != actual:
        raise ValueError('Complete current plan/settings input inventory required')
    if digest(configuration) != configuration_hash:
        raise ValueError('Project configuration changed during input validation')
    pins[configuration] = configuration_hash
    return files, data['selectors'], pins


def run(configuration, output, *, font, autocad=None):
    files, selectors, pins = load(configuration)
    output = local(output)
    if output.exists() or any(p == output or p.is_relative_to(output) for p in pins):
        raise ValueError('New output directory separate from all configured sources required')
    # Engines/fonts stay explicit host arguments. Document/configuration content
    # cannot select a program or issue a shell command.
    result = hvac_package.run(files['plan'], output, font=font, autocad=autocad,
        **{k: v for k, v in files.items() if k != 'plan'}, **selectors)
    if any(digest(p) != sha for p, sha in pins.items()):
        raise ValueError('Project configuration or source changed during package execution')
    receipt = dict(configuration=str(Path(configuration).resolve()), configuration_sha256=digest(Path(configuration).resolve()),
        input_hashes={str(p): sha for p, sha in pins.items()},
        package_sha256=digest(output/'package.json'), generator_sha256=digest(Path(__file__)),
        status=result['status'], design_accepted=False,
        scope='Pinned interpreted-project settings replay only; raw brief interpretation, actual visual review and full engineering acceptance remain separate')
    (output/'project-run.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prepare = commands.add_parser('create')
    prepare.add_argument('plan'); prepare.add_argument('--out', required=True)
    for key in FILES[1:] + SELECTORS:
        prepare.add_argument('--' + key.replace('_', '-'))
    execute = commands.add_parser('run')
    execute.add_argument('configuration'); execute.add_argument('--out', required=True)
    execute.add_argument('--font', required=True); execute.add_argument('--autocad')
    args = parser.parse_args()
    if args.command == 'create':
        create(args.plan, args.out, **{k: getattr(args, k) for k in FILES[1:] + SELECTORS})
        print('Project configuration saved; engineering interpretation and acceptance remain separate')
        return 0
    result = run(args.configuration, args.out, font=args.font, autocad=args.autocad)
    print(result['status'] + '; full engineering acceptance pending')
    return 2


if __name__ == '__main__':
    raise SystemExit(main())

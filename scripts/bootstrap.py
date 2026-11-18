"""Project-local source installation. No global config, trust or native installs."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = 'https://github.com/LYUml/building-services-agent.git'
PROFILES = {
    'cad': ['drawing', 'mcp', 'codex-setup', 'documents', 'modules', 'reports'],
    'hvac': ['drawing', 'mcp', 'codex-setup', 'documents', 'modules', 'reports', 'network', 'spatial'],
}


def run(args, **kwargs):
    return subprocess.run([str(x) for x in args], cwd=ROOT, check=True, **kwargs)


def validate_root(root):
    root = root.resolve()
    historical = [Path.home() / 'Desktop' / 'polyu_bse3124', root.parent / 'polyu_bse3124']
    if any(root == p.resolve() or root.is_relative_to(p.resolve()) for p in historical):
        raise ValueError('Completed historical project is read-only')
    owned = root / '.bsa'
    if not owned.resolve().is_relative_to(root):
        raise ValueError('Setup directory escapes source root')
    if owned.exists() and not (owned / 'setup-owner.json').is_file():
        raise ValueError('Existing .bsa is not owned by this installer; preserve it')
    return owned


def restore_source_git():
    """A source ZIP needs Git objects for immutable library references.

    Populate the index only: never checkout/reset/delete working files.
    """
    manifest = ROOT / '.bsa-release.json'
    if (ROOT / '.git').exists() and not manifest.exists():
        return
    if not manifest.is_file():
        raise ValueError('Use a Git clone or an official source release ZIP')
    import re
    commit = json.loads(manifest.read_text(encoding='utf-8'))['commit']
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('Invalid release commit')
    if not (ROOT / '.git').exists():
        run(['git', 'init', '-b', 'main'])
        run(['git', 'remote', 'add', 'origin', ORIGIN])
    run(['git', 'fetch', 'origin', commit])
    run(['git', 'update-ref', 'HEAD', commit])
    run(['git', 'read-tree', commit])
    # A modified extracted source is preserved, but must be reconciled explicitly.
    changed = run(['git', 'diff', '--name-status', '--no-renames', '-z', 'HEAD'], capture_output=True).stdout
    if not changed:
        return
    fields = changed.rstrip(b'\0').split(b'\0')
    if len(fields) % 2 == 0 and all(status == b'D' for status in fields[::2]):
        paths = fields[1::2]
        attributes = run(['git', 'check-attr', '--source=' + commit, '-z', '--stdin', 'export-ignore'],
                         capture_output=True, input=b'\0'.join(paths) + b'\0').stdout
        expected = b''.join(path + b'\0export-ignore\0set\0' for path in paths)
        if attributes == expected:
            return
    raise ValueError('Extracted tracked sources differ from the release; no files overwritten')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=PROFILES, default='cad')
    parser.add_argument('--project-root', type=Path, help='Existing user project; defaults to this source checkout')
    parser.add_argument('--autocad', type=Path, help='Existing accoreconsole.exe; no native software is installed')
    parser.add_argument('--dwg-dotnet', type=Path, help='Absolute .NET host path for an existing DWG worker')
    parser.add_argument('--dwg-worker', type=Path, help='Absolute path to an existing ACadSharp worker DLL')
    args = parser.parse_args(argv)
    if sys.version_info[:2] != (3, 12):
        raise ValueError('This prerelease installer requires tested CPython 3.12')
    owned = validate_root(ROOT)
    # Validate the selected project before creating anything or installing dependencies.
    sys.path.insert(0, str(ROOT / 'src'))
    from bsa import workspace
    from bsa import project_skills
    if args.project_root:
        os.environ['BSA_PROJECT_ROOT'] = str(args.project_root.resolve())
    selected = workspace.project_root()  # includes protected-path checks
    if selected is not None and workspace.protected(selected):
        raise ValueError('Completed historical project is read-only')
    if args.autocad and not args.autocad.resolve().is_file():
        raise ValueError('Existing AutoCAD Core Console executable required')
    dwg_options = []
    if args.dwg_dotnet is not None or args.dwg_worker is not None:
        if args.dwg_dotnet is None or args.dwg_worker is None:
            raise ValueError('Supply both --dwg-dotnet and --dwg-worker')
        from bsa.dwg_readback import host_runtime_files

        dotnet, worker, _ = host_runtime_files(args.dwg_dotnet, args.dwg_worker)
        dwg_options = ['--dwg-dotnet', dotnet, '--dwg-worker', worker]
    expected_python = owned / 'venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    project_skills.install(selected or ROOT, expected_python, check_only=True)
    restore_source_git()
    owned.mkdir(exist_ok=True)
    marker = owned / 'setup-owner.json'
    if not marker.exists():
        marker.write_text(json.dumps({'schema': 'bsa.setup-owner/1'}), encoding='utf-8')
    environment = owned / 'venv'
    if not environment.resolve().is_relative_to(owned.resolve()):
        raise ValueError('Environment escapes setup directory')
    python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not python.exists():
        if environment.exists():
            raise ValueError('Incomplete environment preserved; choose a fresh source folder')
        venv.EnvBuilder(with_pip=True).create(environment)
    extras = PROFILES[args.profile]
    command = [python, '-m', 'pip', 'install', '-e', str(ROOT) + '[' + ','.join(extras) + ']']
    if os.name == 'nt':
        command += ['-c', ROOT / 'locks/hvac-mcp-windows-py312.txt']
    run(command)
    run([python, '-m', 'pip', 'check'])
    autocad = args.autocad
    if autocad is None and os.name == 'nt':
        candidates = sorted((Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Autodesk').glob('AutoCAD */accoreconsole.exe'))
        if len(candidates) == 1:
            autocad = candidates[0]
    command = [python, '-m', 'bsa.codex_setup', '--python', python, '--refresh']
    if autocad:
        command += ['--autocad', autocad.resolve()]
    run(command + dwg_options)
    audit = owned / 'mcp-check.json'
    skills_result = json.loads(run([python, '-m', 'bsa.project_skills', '--project', selected or ROOT,
                                   '--python', python], capture_output=True, text=True).stdout)
    print(json.dumps(skills_result, indent=2))
    # Existing SDK contract audit creates a fresh receipt under source runs.
    import uuid
    target = ROOT / 'runs' / ('setup-' + uuid.uuid4().hex + '.json')
    run([python, ROOT / 'scripts/check_mcp_contract.py', '--out', target])
    audit.write_bytes(target.read_bytes())
    config = (selected or ROOT) / '.codex/config.toml'
    run([python, ROOT / 'scripts/probe_setup_transport.py', '--config', config,
         '--out', owned / 'transport-check.json'])
    receipt = dict(schema='bsa.setup/1', profile=args.profile, python=str(python),
                   skills_installed=True,
                   skill_count=skills_result['skill_count'],
                   project=str(selected or ROOT), mcp_contract_verified=True, stdio_transport_verified=True,
                   autocad_path_present=bool(autocad), dwg_readback_paths_supplied=bool(dwg_options),
                   native_execution_verified=False,
                   host_connection_verified=False, design_accepted=False)
    (owned / 'setup-result.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps(receipt, indent=2))
    print('Open the selected project in your MCP host. Review project trust normally. Native drawing acceptance still requires reopening and visual plot review.')
    return receipt


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print('SETUP FAILED: ' + str(exc), file=sys.stderr)
        sys.exit(1)

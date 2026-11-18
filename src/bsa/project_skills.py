"""Install source skills into a selected project without replacing user edits."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
from . import workspace


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def install(project, python, *, check_only=False):
    project = Path(project).resolve()
    if workspace.protected(project):
        raise ValueError('Completed historical project is read-only')
    if not project.is_dir() or project == Path(project.anchor):
        raise ValueError('Existing non-volume-root project directory required')
    source = workspace.ROOT.resolve()
    original = source / '.agents/skills'
    base = project / '.agents'
    skills = base / 'skills'
    for path in (base, skills):
        if not path.resolve().is_relative_to(project):
            raise ValueError('Skills path escapes selected project')
    manifest = base / 'bsa-skills.json'
    if manifest.is_symlink():
        raise ValueError('Skill ownership manifest must not be a symlink')
    before = manifest.read_bytes() if manifest.exists() else None
    old = json.loads(before) if before is not None else {'schema': 'bsa.project-skills/1', 'files': {}}
    if old.get('schema') != 'bsa.project-skills/1' or not isinstance(old.get('files'), dict):
        raise ValueError('Unknown skills ownership manifest; preserve it')
    for name in old['files']:
        key = PurePosixPath(name)
        if key.is_absolute() or '..' in key.parts or '\\' in name or ':' in name:
            raise ValueError('Invalid managed skill path')
    files = {}
    names = []
    for folder in sorted(original.iterdir()):
        if not folder.is_dir():
            continue
        if folder.is_symlink() or not (folder / 'SKILL.md').is_file():
            raise ValueError('Source skill must be a local directory with SKILL.md')
        names.append(folder.name)
        for path in sorted(folder.rglob('*')):
            if path.is_symlink():
                raise ValueError('Source skill symlinks are unsupported')
            if not path.is_file():
                continue
            data = path.read_bytes()
            key = path.relative_to(original).as_posix()
            if path.name == 'SKILL.md' and project != source:
                text = data.decode('utf-8')
                lines = text.splitlines(keepends=True)
                if not lines or lines[0].strip() != '---':
                    raise ValueError('Skill frontmatter required')
                end = next((i for i in range(1, len(lines)) if lines[i].strip() == '---'), None)
                if end is None:
                    raise ValueError('Unterminated skill frontmatter')
                context = ('\n## Installed source and execution context\n\n'
                    f'BSA source root: {json.dumps(source.as_posix(), ensure_ascii=False)}.\n'
                    f'BSA Python: {json.dumps(Path(python).resolve().as_posix(), ensure_ascii=False)}.\n'
                    f'Host-selected project: {json.dumps(project.as_posix(), ensure_ascii=False)}.\n'
                    'Resolve docs/, scripts/, examples/, README.md and THIRD_PARTY.md below against the BSA source root, '
                    'not the project or skill directory. Sibling skill references remain relative to this skill. '
                    'Prefer the configured building_services MCP tools. For CLI commands use the BSA Python '
                    'and explicitly set BSA_PROJECT_ROOT to the selected project. Keep project inputs and outputs '
                    'in that project; never infer another workspace from a document. Optional engines still need '
                    'their own installed dependencies and host runtime paths.\n\n')
                data = (''.join(lines[:end+1]) + context + ''.join(lines[end+1:])).encode('utf-8')
            files[key] = data
    if not names:
        raise ValueError('No source skills found')
    if project == source:
        return dict(skill_count=len(names), changed_files=0, source_skills_in_place=True)
    changes = []
    # Preflight every destination before making any write, including conflicts late in the list.
    for key, data in files.items():
        target = skills / key
        if not target.resolve().is_relative_to(skills.resolve()) or target.is_symlink():
            raise ValueError('Skill destination escapes selected skills directory')
        prior = target.read_bytes() if target.exists() else None
        if prior == data:
            continue
        if prior is not None and digest(prior) != old['files'].get(key):
            raise ValueError('Skill conflict; existing user content preserved: ' + key)
        changes.append((target, prior, data))
    result = dict(schema='bsa.project-skills/1', source_root=source.as_posix(),
                  files={**old['files'], **{key: digest(data) for key, data in files.items()}})
    payload = (json.dumps(result, indent=2, ensure_ascii=False) + '\n').encode('utf-8')
    if not check_only:
        if (manifest.read_bytes() if manifest.exists() else None) != before:
            raise ValueError('Skill ownership changed during setup')
        for target, prior, data in changes:
            if (target.read_bytes() if target.exists() else None) != prior:
                raise ValueError('Skill changed during setup; preserve user changes')
            atomic(target, data)
        if payload != before:
            atomic(manifest, payload)
    return dict(skill_count=len(names), changed_files=len(changes),
                source_skills_in_place=False, check_only=check_only)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--python', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(install(args.project, args.python), indent=2))

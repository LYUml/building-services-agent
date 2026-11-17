"""Thin CLI adapter; SQLite and document engines load only on dispatch."""
from pathlib import Path


def configure(subparsers):
    group = subparsers.add_parser('knowledge', help='Build, verify or query a citable local corpus')
    commands = group.add_subparsers(dest='knowledge_command', required=True)
    command = commands.add_parser('build')
    command.add_argument('manifest', type=Path)
    command.add_argument('--out', type=Path, required=True)
    command = commands.add_parser('verify')
    command.add_argument('index', type=Path)
    command = commands.add_parser('query')
    command.add_argument('index', type=Path)
    command.add_argument('--text', required=True)
    command.add_argument('--role')
    command.add_argument('--discipline')
    command.add_argument('--jurisdiction')
    command.add_argument('--limit', type=int, default=5)
    command.add_argument('--include-project-facts', action='store_true')
    command.add_argument('--expected-context', type=Path)


def dispatch(args):
    from . import index
    try:
        if args.knowledge_command == 'build':
            return index.build(args.manifest, args.out)
        if args.knowledge_command == 'verify':
            return index.verify(args.index)
        return index.query(args.index, args.text, role=args.role, discipline=args.discipline,
            jurisdiction=args.jurisdiction, limit=args.limit,
            include_project_facts=args.include_project_facts, expected_context=args.expected_context)
    except index.sqlite3.Error as exc:
        raise ValueError('Knowledge lookup engine error: '+str(exc)) from exc

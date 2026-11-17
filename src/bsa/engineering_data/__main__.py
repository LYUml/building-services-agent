"""Export/verify supported common data without launching new domain calculations."""
import argparse
import json
from .module_bridge import export, verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    command = commands.add_parser('context')
    command.add_argument('--name', required=True)
    command.add_argument('--scenario', required=True)
    command.add_argument('--out', required=True)
    command = commands.add_parser('export')
    command.add_argument('source_result')
    command.add_argument('--out', required=True)
    command.add_argument('--include-inputs', action='store_true')
    command = commands.add_parser('verify')
    command.add_argument('out')
    args = parser.parse_args()
    if args.command == 'context':
        from .context import create
        print(json.dumps(create(args.name, args.scenario, args.out), indent=2))
        return
    result = export(args.source_result, args.out, include_inputs=args.include_inputs) if args.command == 'export' else verify(args.out)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

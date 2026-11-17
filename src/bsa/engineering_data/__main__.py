"""Export/verify supported common data without launching new domain calculations."""
import argparse
import json
from .module_bridge import export, verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    command = commands.add_parser('export')
    command.add_argument('source_result')
    command.add_argument('--out', required=True)
    command = commands.add_parser('verify')
    command.add_argument('out')
    args = parser.parse_args()
    result = export(args.source_result, args.out) if args.command == 'export' else verify(args.out)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

import argparse
import json
import sys
from .cli import configure, dispatch


def main():
    parser = argparse.ArgumentParser(description='Source-backed knowledge retrieval')
    commands = parser.add_subparsers(dest='command', required=True)
    configure(commands)
    args = parser.parse_args(['knowledge', *sys.argv[1:]])
    try:
        print(json.dumps(dispatch(args), indent=2, ensure_ascii=False))
    except (ValueError, OSError) as exc:
        parser.exit(2, str(exc)+'\n')


if __name__ == '__main__':
    main()

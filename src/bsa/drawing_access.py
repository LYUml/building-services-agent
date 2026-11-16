"""Shared CLI and MCP boundary for general drawing authoring and inspection."""
import argparse
import json
from pathlib import Path


def engine(project):
    from . import workspace
    if not workspace.allowed(project):raise ValueError('Host project workspace required')
    schema=json.loads(Path(project).read_text(encoding='utf-8-sig')).get('schema')
    if schema=='bsa.drawing-graph/1':
        from . import drawing_graph
        return drawing_graph
    if schema=='bsa.drawing-ifc-sections/1':
        from . import drawing_ifc_sections
        return drawing_ifc_sections
    if schema=='bsa.drawing-labels/1':
        from . import drawing_labels
        return drawing_labels
    if schema=='bsa.drawing-revision/1':
        from . import drawing_revision
        return drawing_revision
    if schema=='bsa.drawing-layout/1':
        from . import drawing_layout
        return drawing_layout
    if schema=='bsa.drawing-document/1':
        from . import drawing_document
        return drawing_document
    raise ValueError('Unsupported drawing schema')


def run(project,out,*,autocad,graphviz=None):
    if autocad is None:raise ValueError('Explicit host AutoCAD startup configuration required')
    selected=engine(project)
    options={'autocad':autocad}
    if selected.__name__=='bsa.drawing_graph':options['graphviz']=graphviz
    selected.run(project,out,**options)
    return selected.verify(project,out)


def inspect(project,out):
    return engine(project).verify(project,out)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    for action in ('run','inspect'):
        command=sub.add_parser(action)
        command.add_argument('project')
        command.add_argument('--out',required=True)
        if action=='run':
            command.add_argument('--autocad',required=True)
            command.add_argument('--graphviz')
    args=parser.parse_args(argv)
    try:
        result=(run(args.project,args.out,autocad=args.autocad,graphviz=args.graphviz)
                if args.action=='run' else inspect(args.project,args.out))
    except (ValueError,OSError,KeyError,TypeError) as error:
        parser.exit(1,f'Drawing {args.action} failed: {error}\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()

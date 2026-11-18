"""Shared CLI and MCP boundary for general drawing authoring and inspection."""
import argparse
import json
import importlib.metadata as metadata
import importlib
from pathlib import Path

RECEIPTS=('drawing-result.json','layout-result.json','labels-result.json','revision-result.json',
          'graph-result.json','section-result.json','ifc-graph-result.json')


def needs_graphviz(project):
    spec=json.loads(Path(project).read_text(encoding='utf-8-sig'))
    return spec.get('schema') in ('bsa.drawing-graph/1','bsa.drawing-ifc-graph/1')


def workflow_inputs(project):
    """Bind existing recipe sources/methods, without executing CAD or a layout program.

    Existing compositors remain authoritative for geometry and native acceptance.
    IFC source binding here is deliberately not a second geometry validator.
    """
    from . import workspace,drawing_document
    from .cli import digest
    project=Path(project).resolve();selected=engine(project)
    spec=json.loads(project.read_text(encoding='utf-8-sig'));schema=spec['schema']
    files={project,Path(__file__).resolve()}
    methods=set(drawing_document.methods());methods.add(Path(selected.__file__).name)

    def bound(value,expected):
        if not isinstance(value,str) or Path(value).is_absolute():raise ValueError('Recipe-relative drawing source required')
        path=(project.parent/value).resolve()
        if not workspace.allowed(path) or digest(path)!=expected:raise ValueError('Drawing workflow source escaped workspace or changed')
        files.add(path)

    def upstream(name):
        pinfile=workspace.ROOT/'third_party'/('rectpack-0.2.2.json' if name=='rectpack' else 'textalloc-1.2.4.json')
        pin=json.loads(pinfile.read_text());folder=Path(importlib.import_module(name).__file__).resolve().parent
        if metadata.version(name)!=pin['version']:raise ValueError('Pinned drawing upstream required: '+name)
        files.add(pinfile)
        for relative,expected in pin['runtime_files'].items():
            path=folder/relative
            if digest(path)!=expected:raise ValueError('Drawing upstream source changed: '+name)
            files.add(path)

    if schema=='bsa.drawing-document/1':drawing_document.validate(spec)
    elif schema=='bsa.drawing-layout/1':
        selected.compose(spec);upstream('rectpack')
    elif schema=='bsa.drawing-labels/1':
        selected.compose(spec);upstream('textalloc')
        methods.update(('cad_text_layout.py','route_drawing_qa.py','route_annotations.py'))
    elif schema=='bsa.drawing-revision/1':
        _,source,_=selected.configuration(project);files.add(source);methods.update(selected.methods())
    elif schema=='bsa.drawing-graph/1':
        selected.configuration(project)
        for row in spec['source_files']:bound(row['path'],row['sha256'])
        methods.add('three_phase_drawing.py')
    elif schema in ('bsa.drawing-ifc-sections/1','bsa.drawing-ifc-graph/1'):
        bound(spec['ifc'],spec['ifc_sha256'])
        if schema=='bsa.drawing-ifc-sections/1':
            methods.update(selected.methods());upstream('rectpack')
        else:
            for row in spec['graph']['source_files']:bound(row['path'],row['sha256'])
            methods.update(('drawing_graph.py','three_phase_drawing.py'))
    files.update(Path(__file__).with_name(name).resolve() for name in methods)
    return files


def engine(project):
    from . import workspace
    if not workspace.allowed(project):raise ValueError('Host project workspace required')
    schema=json.loads(Path(project).read_text(encoding='utf-8-sig')).get('schema')
    if schema=='bsa.drawing-ifc-graph/1':
        from . import drawing_ifc_graph
        return drawing_ifc_graph
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
    if not Path(autocad).is_file():raise ValueError('Explicit existing AutoCAD executable required')
    try:pdf_version=metadata.version('pypdf')
    except metadata.PackageNotFoundError:pdf_version=None
    if pdf_version!='7.0.0':raise ValueError('Native drawing needs pypdf==7.0.0; install the drawing extra before running')
    selected=engine(project)
    options={'autocad':autocad}
    if selected.__name__ in ('bsa.drawing_graph','bsa.drawing_ifc_graph'):options['graphviz']=graphviz
    selected.run(project,out,**options)
    return selected.verify(project,out)


def inspect(project,out):
    return engine(project).verify(project,out)


def inspect_revision_readback(project, out, report):
    """Cross-check the verified native revision against its own reopened export."""
    from . import drawing_revision, dwg_readback

    out, report = (Path(path).resolve() for path in (out, report))
    if report.is_relative_to(out):
        raise ValueError('Independent readback report must be outside the immutable revision')
    if engine(project) is not drawing_revision:
        raise ValueError('Independent revision readback requires a drawing revision recipe')
    receipt = out / 'revision-result.json'
    receipt_bytes = receipt.read_bytes()
    verified = drawing_revision.verify(project, out)
    if receipt.read_bytes() != receipt_bytes:
        raise ValueError('Drawing revision receipt changed during verification')
    dwg_hash = next(row['sha256'] for row in verified['artifacts'] if row['path'] == 'Revised Drawing.dwg')
    dxf_hash = json.loads(receipt_bytes)['artifacts']['reopened/source-export.dxf']
    readback = dwg_readback.run(out / 'Revised Drawing.dwg', report, out / 'reopened/source-export.dxf',
                               expected_hashes=(dwg_hash, dxf_hash))
    return dict(**verified, independent_readback=readback)


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

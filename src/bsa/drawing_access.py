"""Small MCP worker boundary for general drawing authoring and inspection."""
import json
from pathlib import Path


def engine(project):
    schema=json.loads(Path(project).read_text(encoding='utf-8-sig')).get('schema')
    if schema=='bsa.drawing-labels/1':
        from . import drawing_labels
        return drawing_labels
    if schema=='bsa.drawing-revision/1':
        from . import drawing_revision
        return drawing_revision
    if schema=='bsa.drawing-layout/1':
        from . import drawing_layout
        return drawing_layout
    from . import drawing_document
    return drawing_document


def run(project,out,*,autocad):
    if autocad is None:raise ValueError('Explicit host AutoCAD startup configuration required')
    selected=engine(project);selected.run(project,out,autocad=autocad)
    return selected.verify(project,out)


def inspect(project,out):
    return engine(project).verify(project,out)

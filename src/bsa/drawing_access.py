"""Small MCP worker boundary for general drawing authoring and inspection."""


def run(project,out,*,autocad):
    if autocad is None:raise ValueError('Explicit host AutoCAD startup configuration required')
    from .drawing_document import run as author,verify
    author(project,out,autocad=autocad)
    return verify(project,out)


def inspect(project,out):
    from .drawing_document import verify
    return verify(project,out)

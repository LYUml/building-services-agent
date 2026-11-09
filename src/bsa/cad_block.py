"""Extract a source-selected named block definition through isolated native AutoCAD."""
import argparse
from collections import Counter
import json
from pathlib import Path
import shutil

from .cad_intake import inventory, export_dwg
from .cli import digest
from .engine import ProjectError
from .native_cad import DEFAULT_EXE, execute, lisp_string


def select(doc, selection):
    required = {'source', 'drawing_sha256', 'insert_handle', 'block_name', 'insunits', 'attributes'}
    if set(selection) != required:
        raise ProjectError('exact block selection fields required')
    if any(not isinstance(selection[k], str) or not selection[k].strip()
           for k in ('source', 'drawing_sha256', 'insert_handle', 'block_name')):
        raise ProjectError('nonempty source, hash and block identity required')
    if type(selection['insunits']) is not int or selection['insunits'] not in (1, 2, 4, 5, 6):
        raise ProjectError('explicit supported drawing units required')
    if doc.units != selection['insunits']:
        raise ProjectError('drawing units do not match selection')
    attrs = selection['attributes']
    if not isinstance(attrs, dict) or not attrs or any(
        not isinstance(k, str) or not k or not isinstance(v, str) or not v for k, v in attrs.items()
    ):
        raise ProjectError('nonempty identifying attributes required')
    matches = [e for e in doc.modelspace() if e.dxf.handle == selection['insert_handle']]
    if len(matches) != 1 or matches[0].dxftype() != 'INSERT':
        raise ProjectError('selected model-space INSERT missing')
    instance = matches[0]
    if instance.dxf.name != selection['block_name']:
        raise ProjectError('selected block name mismatch')
    tags = [a.dxf.tag for a in instance.attribs]
    if len(tags) != len(set(tags)):
        raise ProjectError('duplicate attribute tags are ambiguous')
    actual = {a.dxf.tag: a.dxf.text for a in instance.attribs}
    if any(actual.get(k) != v for k, v in attrs.items()):
        raise ProjectError('selected identifying attributes mismatch')
    block = doc.blocks.get(instance.dxf.name)
    if block is None or block.name.startswith('*') or block.block.dxf.flags & 12:
        raise ProjectError('named non-xref block required')
    if any(e.dxftype() == 'INSERT' for e in block):
        raise ProjectError('nested block extraction not yet verified')
    if not len(block):
        raise ProjectError('empty block rejected')
    return block, actual


def structure(entities):
    # This deliberately does not certify ACIS shape equality.
    counts = Counter((e.dxftype(), e.dxf.layer) for e in entities)
    definitions = sorted((e.dxf.tag, e.dxf.text) for e in entities if e.dxftype() == 'ATTDEF')
    return {'counts_by_type_layer': sorted((k[0], k[1], v) for k, v in counts.items()),
            'attribute_definitions': definitions}


def run(source, selection_path, out, exe=DEFAULT_EXE, timeout=120):
    import ezdxf
    source, selection_path, out, exe = [Path(p).resolve() for p in (source, selection_path, out, exe)]
    if source.suffix.lower() != '.dwg' or not source.is_file():
        raise ProjectError('existing source DWG required')
    before = {str(p): digest(p) for p in (source, selection_path)}
    selection = json.loads(selection_path.read_text(encoding='utf-8-sig'))
    if selection.get('drawing_sha256') != before[str(source)]:
        raise ProjectError('selection source hash mismatch')
    if (out.exists() or not out.is_relative_to(Path(__file__).resolve().parents[2])
            or any(out == p or out in p.parents for p in (source, selection_path))):
        raise ProjectError('new repository output directory outside inputs required')
    out.mkdir(parents=True)
    exported = export_dwg(source, out / 'source-intake', exe, timeout)
    doc = ezdxf.readfile(exported)
    audit = doc.audit()
    if audit.errors or audit.fixes:
        raise ProjectError('source export requires repair')
    block, attrs = select(doc, selection)
    expected = structure(block)
    copied = out / 'source-copy.dwg'
    shutil.copyfile(source, copied)
    target = out / 'selected-block.dwg'
    script = out / 'extract.scr'
    condition = (f'(= (strcase (vl-string-translate (chr 92) "/" '
                 f'(strcat (getvar "DWGPREFIX") (getvar "DWGNAME")))) '
                 f'(strcase {lisp_string(copied)}))')
    script.write_text(
        f'(if {condition} (progn (setvar "FILEDIA" 0) (setvar "CMDDIA" 0) '
        f'(command "_.-WBLOCK" {lisp_string(target)} {lisp_string(block.name)})) '
        '(princ "BSA WRONG DOCUMENT"))\n_.QUIT\n_Y\n', encoding='ascii')
    execute(exe, copied, script, out / 'extract.log', timeout)
    if not target.is_file():
        raise ProjectError('native block extraction missing')
    reopened = export_dwg(target, out / 'selected-intake', exe, timeout)
    actual_doc = ezdxf.readfile(reopened)
    data = inventory(reopened)  # Audit the independently reopened export.
    checks = {'definition_structure_preserved': structure(actual_doc.modelspace()) == expected,
              'units_preserved': actual_doc.units == selection['insunits'],
              'source_copy_unchanged': digest(copied) == before[str(source)],
              'inputs_unchanged': all(digest(Path(p)) == h for p, h in before.items())}
    result = {'inputs': before, 'selection': selection, 'selected_instance_attributes': attrs,
              'definition_structure': expected, 'checks': checks,
              'native_extraction_pass': all(checks.values()), 'design_accepted': False,
              'scope': 'Local block definition, not transformed instance; structure and units only',
              'pending': ['ACIS geometry fidelity and visual plot review',
                          'port/bore identification and hydraulic applicability',
                          'project and regulatory acceptance'],
              'artifacts': {p.relative_to(out).as_posix(): digest(p) for p in out.rglob('*') if p.is_file()}}
    (out / 'inventory.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
    result['artifacts']['inventory.json'] = digest(out / 'inventory.json')
    (out / 'block-extraction.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    if not all(checks.values()):
        raise ProjectError(f'native extraction checks failed: {checks}')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source'); parser.add_argument('selection')
    parser.add_argument('--out', required=True); parser.add_argument('--autocad', default=str(DEFAULT_EXE))
    args = parser.parse_args()
    report = run(args.source, args.selection, args.out, args.autocad)
    print(json.dumps({'checks': report['checks'], 'design_accepted': False}))

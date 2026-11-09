"""Explicit native annulus, filled-disc and no-intersection controls (AutoCAD required)."""
import argparse
import json
from pathlib import Path
import ezdxf
from bsa.cad_intake import export_dwg
from bsa.cad_sections import run
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.native_cad import DEFAULT_EXE, execute, lisp_string


def main(out):
    out = Path(out).resolve()
    if out.exists() or not out.is_relative_to(Path(__file__).resolve().parents[1]):
        raise ValueError('new repository output required')
    out.mkdir(parents=True)
    results = {}
    for name, hollow, z, expected in [('annulus', True, 10, True),
                                       ('filled', False, 10, False),
                                       ('no_hit', True, 40, False)]:
        folder = out / name; folder.mkdir()
        seed = folder / 'seed.dxf'; doc = ezdxf.new('R2018'); doc.units = 4; doc.saveas(seed)
        target = folder / 'fixture.dwg'; script = folder / 'create.scr'
        guard = (f'(= (strcase (vl-string-translate (chr 92) "/" '
                 f'(strcat (getvar "DWGPREFIX") (getvar "DWGNAME")))) (strcase {lisp_string(seed)}))')
        body = ('(setvar "FILEDIA" 0) (setvar "CMDDIA" 0) (setvar "OSMODE" 0) '
                '(command "_.UCS" "_World") (command "_.CYLINDER" "0,0,0" "10" "20") '
                '(setq outer (entlast)) ')
        if hollow:
            body += ('(command "_.CYLINDER" "0,0,0" "5" "20") (setq inner (entlast)) '
                     '(command "_.SUBTRACT" outer "" inner "") ')
        body += f'(command "_.SAVEAS" "2018" {lisp_string(target)})'
        script.write_text(f'(if {guard} (progn {body}) (princ "BSA WRONG DOCUMENT"))\n_.QUIT\n_Y\n', encoding='ascii')
        execute(DEFAULT_EXE, seed, script, folder / 'create.log', 120)
        exported = export_dwg(target, folder / 'intake', DEFAULT_EXE)
        actual = ezdxf.readfile(exported); solids = list(actual.modelspace().query('3DSOLID'))
        assert len(solids) == 1 and actual.units == 4
        basis = {'source': 'Original synthetic millimetre cylinder: radius 10, height 20; optional radius 5 through bore',
                 'drawing_sha256': digest(target), 'solid_handle': solids[0].dxf.handle,
                 'insunits': 4, 'tolerance_m': 1e-8,
                 'sections': [{'id': 'sample', 'source': 'Explicit synthetic control plane',
                               'plane': 'XY', 'centre_drawing_units': [0, 0, z]}]}
        path = folder / 'basis.json'; path.write_text(json.dumps(basis, indent=2))
        try:
            report = run(target, path, folder / 'run')
        except ProjectError as exc:
            expected_error = ('exactly two circular boundaries' if name == 'filled' else 'single region')
            if expected or expected_error not in str(exc): raise
            results[name] = {'expected_rejection': str(exc), 'source_sha256': digest(target)}
        else:
            assert expected, f'{name} unexpectedly accepted'
            row = report['sections'][0]
            assert abs(row['inner_diameter_m'] - .01) < 1e-9
            assert abs(row['outer_diameter_m'] - .02) < 1e-9
            results[name] = {'known_dimensions_match': True, 'report_sha256': digest(folder / 'run/sections.json')}
    (out / 'controls.json').write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--out', required=True)
    main(p.parse_args().out)

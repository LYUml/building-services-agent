"""Synthetic source-driven continuous cable and fresh numerical study."""
import argparse
import json
import math
from pathlib import Path
import runpy
import shutil
from bsa.engine import ProjectError
from bsa.three_phase import ROOT
from bsa.three_phase_ifc_project import run as derive


def run(out, python, lead=0.):
    out = Path(out).resolve()
    if not out.is_relative_to(ROOT) or out.exists():
        raise ProjectError('new repository output required')
    source = out / 'source'
    shutil.copytree(ROOT / 'examples/cable-coordination', source)
    geometry = json.loads((source / 'geometry.json').read_text())
    geometry['scope'] = 'Synthetic continuous quarter plus 2 m tangent; all geometry assumed; no intermediate loads, equipment joints or installation acceptance'
    geometry['tangent_extensions_m'] = {'feeder': 2.}
    geometry['buses_m']['DB-A'] = [-2., 0., 1.7]
    if type(lead) not in (int,float) or not math.isfinite(lead) or lead<0:raise ProjectError('nonnegative finite synthetic lead length required')
    if lead:
        geometry['lead_extensions_m']={'feeder':lead}
        geometry['buses_m']['source']=[.3,0.,2.+lead]
        geometry['scope']='Synthetic lead straight, quarter and 2 m tail; all geometry assumed; no intermediate loads or installation acceptance'
    (source / 'geometry.json').write_text(json.dumps(geometry, indent=2), encoding='utf-8')
    project = json.loads((source / 'project.json').read_text())
    project['lines'][0]['length_m'] = .3 * math.pi / 2 + 2 + lead
    # The length has its own explicit assumption source, not the inherited electrical basis.
    from bsa.cli import digest
    project['sources']['route'] = dict(path='geometry.json', sha256=digest(source / 'geometry.json'),
        locator='quarter_bends, tangent_extensions_m, optional lead_extensions_m and buses_m; synthetic SI dimensions', kind='assumption')
    project['lines'][0]['length_source'] = 'route'
    path = source / 'project.json'
    path.write_text(json.dumps(project, indent=2), encoding='utf-8')
    author = runpy.run_path(str(ROOT / 'scripts/author_three_phase_ifc_fixture.py'))['run']
    author(path, source / 'geometry.json', out / 'fixture', 'straight-quarter-straight' if lead else 'quarter-straight')
    report = derive(path, out / 'fixture/cables.ifc', out / 'fixture/binding.json', out / 'derived', python)
    (out / 'summary.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--lead',type=float,default=0.)
    result = run(**vars(parser.parse_args()))
    print(json.dumps({k: result[k] for k in ('derived_geometry_correspondence_pass', 'numerical_status', 'design_accepted')}))

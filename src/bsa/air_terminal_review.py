"""Inspect terminal connections inherited from a verified native HVAC workflow."""
import argparse
from pathlib import Path
from . import workspace


def add_arguments(parser):
    for name in ('plan', 'workflow', 'native_task'):
        parser.add_argument(name)
    parser.add_argument('--out', required=True)
    for name in ('supply', 'vav', 'terminal', 'flex'):
        parser.add_argument('--' + name + '-layer', required=True)


def review(plan, workflow, native_task, out, *, supply_layer, vav_layer, terminal_layer, flex_layer):
    from .air_terminal_drawing import from_workflow

    plan, workflow, out = (Path(path).resolve() for path in (plan, workflow, out))
    if not all(workspace.allowed(path) for path in (plan, workflow, out)):
        raise ValueError('Use paths in the permitted workspace')
    return from_workflow(plan, workflow, native_task, out,
                         layers=dict(supply=supply_layer, vav=vav_layer, terminal=terminal_layer, flex=flex_layer))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    add_arguments(p)
    r=review(**vars(p.parse_args()))
    print(r['terminal_count'],'inherited terminal correspondences; design acceptance pending')

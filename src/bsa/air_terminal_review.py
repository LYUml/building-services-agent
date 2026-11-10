"""Inspect terminal connections inherited from a verified native HVAC workflow."""
import argparse
from .air_terminal_drawing import from_workflow


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('plan','workflow','native_task'):p.add_argument(name)
    p.add_argument('--out',required=True)
    for name in ('supply','vav','terminal','flex'):p.add_argument('--'+name+'-layer',required=True)
    a=p.parse_args()
    r=from_workflow(a.plan,a.workflow,a.native_task,a.out,
                    layers={k:getattr(a,k+'_layer') for k in ('supply','vav','terminal','flex')})
    print(r['terminal_count'],'inherited terminal correspondences; design acceptance pending')

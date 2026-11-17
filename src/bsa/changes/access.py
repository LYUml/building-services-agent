"""Existing project/delivery guards around read-only checkpoint and impact APIs."""
from pathlib import Path


def checkpoint(plan,out,target):
    from ..delivery import context
    from .core import checkpoint as create
    context(Path(plan),Path(out))
    return create(Path(out),Path(target))


def inspect(checkpoint,plan,parameter_offset=0,parameter_limit=50):
    from .core import impact
    return impact(Path(checkpoint),plan=Path(plan),parameter_offset=parameter_offset,parameter_limit=parameter_limit)

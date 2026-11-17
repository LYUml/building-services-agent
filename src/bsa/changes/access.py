"""Existing project/delivery guards around read-only checkpoint and impact APIs."""
from pathlib import Path


def checkpoint(plan,out,target):
    from ..delivery import context
    from .core import checkpoint as create
    context(Path(plan),Path(out))
    return create(Path(out),Path(target))


def inspect(checkpoint,plan):
    from .core import impact
    return impact(Path(checkpoint),plan=Path(plan))

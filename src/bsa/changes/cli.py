"""Lazy root-CLI adapter for source-bound change analysis."""
from pathlib import Path


def configure(subparsers):
    group=subparsers.add_parser('changes',help='Checkpoint, analyze and reuse verified numerical evidence')
    commands=group.add_subparsers(dest='changes_command',required=True)
    command=commands.add_parser('checkpoint');command.add_argument('workflow',type=Path);command.add_argument('--out',type=Path,required=True)
    command=commands.add_parser('analyze');command.add_argument('checkpoint',type=Path);command.add_argument('--plan',type=Path)
    command.add_argument('--parameter-offset',type=int,default=0);command.add_argument('--parameter-limit',type=int,default=50)
    command=commands.add_parser('reuse');command.add_argument('checkpoint',type=Path);command.add_argument('--task',required=True);command.add_argument('--out',type=Path,required=True);command.add_argument('--plan',type=Path)
    command=commands.add_parser('verify-reuse');command.add_argument('bundle',type=Path)


def dispatch(args):
    from . import core
    if args.changes_command=='checkpoint':return core.checkpoint(args.workflow,args.out)
    if args.changes_command=='analyze':return core.impact(args.checkpoint,plan=args.plan,parameter_offset=args.parameter_offset,parameter_limit=args.parameter_limit)
    if args.changes_command=='reuse':return core.reuse(args.checkpoint,args.task,args.out,plan=args.plan)
    return core.verify_reuse(args.bundle)

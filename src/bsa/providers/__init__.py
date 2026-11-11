"""Trusted code registry;documents cannot supply import paths or commands."""


def get_provider(id):
    if id=='moosas.box-space-exchange':
        from . import moosas_exchange
        return moosas_exchange
    raise ValueError('Unknown registered module provider: '+str(id))

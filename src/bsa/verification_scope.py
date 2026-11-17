"""Bounded JSON replay memo inside one host operation, never a saved-result cache."""
from contextlib import contextmanager
from contextvars import ContextVar
import json

_current=ContextVar('bsa_verification_scope',default=None)
MAX_ENTRIES=4
MAX_BYTES=128*1024


@contextmanager
def operation_scope(*,enabled=True):
    if type(enabled) is not bool:raise ValueError('Explicit host boolean required')
    token=_current.set({} if enabled else None)
    try:yield
    finally:_current.reset(token)


def replay_json(key,produce):
    """Caller must revalidate every source/method/runtime pin before and after use."""
    memo=_current.get()
    if memo is None:return produce()
    encoded_key=json.dumps(key,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
    if encoded_key in memo:return json.loads(memo[encoded_key])
    value=produce()  # Exceptions and failed extractions are never memoized.
    encoded=json.dumps(value,allow_nan=False,separators=(',',':')).encode('utf-8')
    if len(encoded_key)+len(encoded)>MAX_BYTES:return value
    while memo and (len(memo)>=MAX_ENTRIES or sum(len(k)+len(v) for k,v in memo.items())+len(encoded_key)+len(encoded)>MAX_BYTES):
        del memo[next(iter(memo))]
    memo[encoded_key]=encoded
    return json.loads(encoded)  # Consumers cannot mutate the retained replay.

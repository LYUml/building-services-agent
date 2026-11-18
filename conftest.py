"""Prepare the scratch directory used by repository integration tests."""

from pathlib import Path


def pytest_sessionstart():
    (Path(__file__).resolve().parent / 'runs').mkdir(exist_ok=True)

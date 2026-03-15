#!/usr/bin/env python3
import importlib
import inspect
import sys

print('PYTHONPATH:', sys.path)
mod = importlib.import_module("tayfin_indicator_jobs.config.loader")
print('MODULE FILE:', mod.__file__)
print('---SOURCE---')
print(inspect.getsource(mod))

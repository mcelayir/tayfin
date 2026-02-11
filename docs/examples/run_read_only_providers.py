#!/usr/bin/env python3
import sys
import os
import json
from datetime import datetime
from importlib import util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
prov_dir = os.path.join(ROOT, 'tayfin-ingestor', 'tayfin-ingestor-jobs', 'src', 'tayfin_ingestor_jobs', 'fundamentals', 'providers')
# Ensure the ingestor src is on sys.path so internal imports resolve
ingestor_src = os.path.join(ROOT, 'tayfin-ingestor', 'tayfin-ingestor-jobs', 'src')
if ingestor_src not in sys.path:
    sys.path.insert(0, ingestor_src)
# Also add the inner package dir so modules that `import fundamentals` (no prefix) resolve
inner = os.path.join(ingestor_src, 'tayfin_ingestor_jobs')
if inner not in sys.path:
    sys.path.insert(0, inner)
if not os.path.isdir(prov_dir):
    print('Providers directory missing:', prov_dir)
    sys.exit(2)

TICKERS = ['BTCUSD', 'AAPL']
results = {'meta': {'run_at': datetime.utcnow().isoformat() + 'Z', 'tickers': TICKERS, 'cwd': ROOT}, 'providers': {}}

for fn in sorted(os.listdir(prov_dir)):
    if not fn.endswith('.py'):
        continue
    path = os.path.join(prov_dir, fn)
    modname = f'fundamentals.providers.{fn[:-3]}'
    try:
        spec = util.spec_from_file_location(modname, path)
        mod = util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as e:
        results['providers'][fn] = {'error': f'failed to import: {e}'}
        continue

    provider_obj = None
    if hasattr(mod, 'create_provider'):
        try:
            provider_obj = mod.create_provider()
        except Exception as e:
            results['providers'][fn] = {'error': f'create_provider() failed: {e}'}
            continue
    else:
        for attr in dir(mod):
            if 'Provider' in attr or attr.lower().endswith('provider'):
                cls = getattr(mod, attr)
                try:
                    inst = cls()
                    if hasattr(inst, 'compute'):
                        provider_obj = inst
                        break
                except Exception:
                    continue
    if provider_obj is None:
        results['providers'][fn] = {'error': 'no suitable provider object found'}
        continue

    prov_results = {}
    for ticker in TICKERS:
        try:
            # pass a default country code 'US' for compute; provider may ignore for some symbols
            out = provider_obj.compute(ticker, 'US')
            prov_results[ticker] = {'ok': True, 'result': out}
        except Exception as e:
            prov_results[ticker] = {'ok': False, 'error': str(e)}
    results['providers'][fn] = prov_results

out_dir = os.path.join(ROOT, 'docs', 'examples', 'fundamentals_read_only_out')
os.makedirs(out_dir, exist_ok=True)
ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
out_path = os.path.join(out_dir, f'read_only_traces_{ts}.json')
with open(out_path, 'w') as f:
    json.dump(results, f, indent=2, default=str)

print('WROTE', out_path)

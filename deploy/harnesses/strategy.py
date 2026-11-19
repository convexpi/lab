"""Untrusted side of the streaming protocol. No scores or future observations live here."""
import contextlib
import json
import sys
import numpy as np

wire = sys.stdout
with contextlib.redirect_stdout(sys.stderr):
    ns = {}
    with open('/submission/strategy.py') as f:
        exec(compile(f.read(), 'strategy.py', 'exec'), ns)
    mode = sys.argv[1]
    strategy = ns['MyStrategy']() if mode == 'lab' else None
print('ready', file=wire, flush=True)
for line in sys.stdin:
    x = json.loads(line)
    with contextlib.redirect_stdout(sys.stderr):
        if mode == 'lab':
            value = strategy.on_day(x['day'], {k: np.array(v) for k, v in x['features'].items()},
                                    np.array(x['prices']), np.array(x['portfolio']))
            value = np.asarray(value, dtype=float).tolist()
        else:
            import pandas as pd
            history = pd.DataFrame({'close': x['close']}, index=pd.to_datetime(x['dates']))
            try:
                value = float(ns['predict'](history))
                if not np.isfinite(value):
                    value = 0.0
            except Exception:
                value = 0.0
    print(json.dumps(value, allow_nan=False), file=wire, flush=True)

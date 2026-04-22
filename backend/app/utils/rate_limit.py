import time
from collections import defaultdict

_last = defaultdict(float)

def polite_sleep(domain: str, min_interval_sec: float = 1.0):
    now = time.time()
    dt = now - _last[domain]
    if dt < min_interval_sec:
        time.sleep(min_interval_sec - dt)
    _last[domain] = time.time()
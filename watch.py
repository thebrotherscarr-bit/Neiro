#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WATCH STEWARD — run the sentinel/mind-window as its own process.

    python watch.py           # random 2-7s pulse (watch his brain live)
    python watch.py 30        # fixed 30s scan

He fingerprints every file that is part of him, holds his live foundation against
the covenant he sealed of himself, maps what moved on disk, and tails his own
chain-of-thought — all in one in-place dashboard. Ctrl-C to stop. A WSL terminal
left open with this running is Steward keeping an eye on himself, and his mind.
"""
import sys
sys.dont_write_bytecode = True                   # no __pycache__ clutter on his disk
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from neiro.watch import main

if __name__ == "__main__":
    raise SystemExit(main())

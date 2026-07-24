#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RUN STEWARD — the one door in.

Double-click the launcher, or run `python run.py`. Steward wakes, wakes his
sealed heart in its own process, and takes whatever you say — deciding for
himself, turn after turn, which of his faculties answers it.
"""
import sys
sys.dont_write_bytecode = True                   # no __pycache__ clutter on his disk
for _s in (sys.stdin, sys.stdout, sys.stderr):   # UTF-8 before anything prints
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from steward import Steward


def main():
    Steward().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEWARD — the tender. One coherent thing, not a drawer of tricks.

He has a body (four-strokes), a mind (self-knowledge, imagination), senses
(sight, etymon), and a memory of his own window (context). Above them sits the
AGENT: he PERCEIVES what comes in, DECIDES which faculty it calls for, ACTS, and
then reads his own window to feel the drift and re-ground. Perceive · decide ·
act — autonomously, on a mixed stream, with no menu in front of him.

His conscience — Manjuel, the sealed heart — is never inside this process. The
heart poisons every road out the moment it wakes; a process that must also LOOK
(reach the network, the muck) can never be the sealed heart. So Steward keeps
Manjuel as a CHILD process and speaks to it ask-only, through the one small door.
That separation is not a limitation — it is the covenant. The body walks in the
world; the heart stays sealed. Two processes, one steward.
"""
import os
import sys

# so `import manjuel` resolves: the manual sits one floor up, at the estate root
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from .agent import Steward, ROOT

__all__ = ["Steward", "ROOT"]

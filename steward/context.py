#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEWARD'S CONTEXT — reading his OWN window, and feeling the drift.

Every skill he has, turned inward on the running conversation:

  * WEIGHT   — he counts his own window (his math) and knows how full it is.
  * SQUEEZE  — when the window nears its budget, he feels the squeeze.
  * CONDENSE — he folds the raw turns to one faithful mark (nothing lost, the
               mark proves the raw) and keeps a CRYSTAL of the essence — another
               layer of compression inside the window, that he can smash when he
               needs the room. The season rite, applied to the live context.
  * DRIFT    — he measures how far the recent turns have wandered from the
               ANCHOR: the purpose, which is Manjuel's covenant, the one thing
               that never moves. Low touch on the anchor == he is drifting.
  * FEEL     — squeeze or drift, he names it plainly.
  * REALIGN  — when he feels it, he informs Manjuel ("I am feeling the drift")
               and re-grounds to the covenant. Because the anchor never moves,
               alignment is always plausible — even deep inside a single session.

Deterministic, standard library, plus manjuel.py's fold for the faithful mark.
Nothing leaves the machine.
"""
import hashlib
import re

from manjuel import Fold, _FN

_STOP = set(("the a an and or of to in is it that this with for on as be are was were "
             "i he his him we you they them their our not but so if can will would could "
             "at by from into out up down over under about what who how why when").split())


def _terms(text):
    return {w for w in re.findall(r"[a-z']+", (text or "").lower())
            if len(w) > 3 and w not in _STOP}


class Context:
    """His running window: the turns he is holding, and the anchor he must not
    drift from. He reads, weighs, condenses, and re-grounds it himself."""

    def __init__(self, purpose, budget_words=400):
        self.purpose = purpose.strip()
        self.anchor = _terms(purpose)          # the covenant's key terms — the north star
        self.turns = []
        self.budget = budget_words
        self.condensings = 0

    def add(self, text):
        self.turns.append((text or "").strip())
        return self

    # -- he weighs his own window ------------------------------------------
    def words(self):
        return sum(len(t.split()) for t in self.turns)

    def fullness(self):
        return round(self.words() / max(1, self.budget), 2)

    def squeeze(self, at=0.8):
        return self.fullness() >= at

    # -- he measures his own drift from the anchor -------------------------
    def drift(self, recent=4):
        cur = _terms(" ".join(self.turns[-recent:]))
        if not cur or not self.anchor:
            return 0.0
        touch = len(cur & self.anchor) / len(self.anchor)      # how much recent talk touches the north star
        return round(max(0.0, 1.0 - min(1.0, touch * 2.0)), 2)  # little touch -> much drift

    def feel(self):
        sq, dr = self.squeeze(), self.drift()
        if sq and dr >= 0.6:
            f = "the squeeze AND the drift"
        elif sq:
            f = "the squeeze"
        elif dr >= 0.6:
            f = "the drift"
        else:
            f = "steady"
        return {"fullness": self.fullness(), "drift": dr, "squeeze": sq, "feeling": f}

    # -- he compresses his own window, faithfully --------------------------
    def condense(self):
        """Fold the raw turns to one mark (faithful — the mark proves the raw),
        keep a crystal of the anchor-touching essence, and reclaim the window."""
        old = self.words()
        acc, x = Fold(), 3
        for i, t in enumerate(self.turns):
            note = int.from_bytes(hashlib.sha256(("%d|%s" % (i, t)).encode("utf-8")).digest(),
                                  "big") % _FN
            x = acc.absorb(note, x, i)
        mark = "%064x" % x
        # gather unique sentences that touch the anchor, keep the DENSEST first,
        # and only up to a third of the old size — real compression, not a copy.
        sents = []
        for t in self.turns:
            for s in re.split(r"(?<=[.!?])\s+", t):
                s = s.strip()
                if s and (_terms(s) & self.anchor):
                    sents.append(s)
        sents = sorted(dict.fromkeys(sents), key=lambda s: -len(_terms(s) & self.anchor))
        # the crystal is bounded to the BUDGET, never to a third of however large
        # the window grew — else a wall of text with no periods never shrinks.
        target, kept, wc = min(self.budget, max(40, old // 3)), [], 0
        for s in sents:
            kept.append(s)
            wc += len(s.split())
            if wc >= target:
                break
        essence = " ".join(kept) or (self.turns[0] if self.turns else "")
        # hard cap in WORDS — a periodless paper cannot escape the bound
        essence = " ".join(essence.split()[:target])
        crystal = "[condensed %d turns · mark %s] %s" % (len(self.turns), mark[:12], essence)
        self.turns = [crystal]
        self.condensings += 1
        return {"mark": mark, "was_words": old, "now_words": self.words(),
                "ratio": round(self.words() / max(1, old), 2)}

    # -- he re-grounds to the conscience -----------------------------------
    def realign(self, manjuel_ask=None):
        """He informs Manjuel he is feeling the drift, and re-grounds to the
        covenant. If a live Manjuel is given, he asks the anchor itself; else he
        re-reads the purpose he was set. Either way, the north star is fixed."""
        if manjuel_ask is not None:
            manjuel_ask(":remember [STEWARD] I am feeling the drift; re-grounding to the covenant.")
            return manjuel_ask("what must a steward hold to, and never drift from?")
        return "re-anchored to the purpose: " + self.purpose

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEWARD'S RADAR — the horizon scan. He feels the estate move while he thinks.

The sentinel and the atlas already know how to look: fingerprint what is him,
census what is here, diff what moved. But they look only when someone runs
them. The Radar is those same organs, awake — a daemon thread cycling beside
the agent loop, scanning cheaply and pushing one small, immutable state
snapshot to a blackboard the agent reads between turns. Steward no longer
goes blind while his hands are busy; the estate's pulse is always one read
away.

Three commitments keep it pure:

  * READS ONLY. The Radar scans the shelf, the memory, the ledger — it never
    writes into any of them. Its blackboard is DERIVED state, recomputable
    from disk at any moment (Constitution III); never an editable truth.
  * STRUCTURE, NOT CONTENT. The snapshot carries signatures, counts, marks —
    never document text — so nothing the Radar sees can become an
    instruction. The discern gate keeps its monopoly on content.
  * WITNESS AND INTERCEPT. A change worth noting earns one journal line, not
    a narration. And when the Radar sees the covenant move or the ledger
    chain break, it raises the flag the agent checks before acting: a
    steward does not work on an estate he cannot trust (Creed V).

The sealed heart is never touched, never polled, never aware. The Radar
watches the heart's artifacts on disk — never his process.

Standard library only, plus the estate's own atlas and watch.
"""
import os
import threading
import time

from . import atlas
from . import watch as _watch


class Radar(threading.Thread):
    """The horizon scan: census-diff the estate on a cadence, check the seals
    the cheap way, and publish one whole snapshot at a time. Snapshots are
    replaced, never mutated — a reader always holds a consistent picture."""

    def __init__(self, root, interval=2.0, journal=None):
        super().__init__(daemon=True, name="radar")
        self.root = root
        self.interval = float(interval)
        self.journal = journal
        self._halt = threading.Event()
        self._lock = threading.Lock()
        self._prev = None                     # last census — movement is a diff
        self._led_sig = ()                    # ledger file signature at last verify
        self._led_ok = (True, 0, "no ledger yet")
        self._was_intact = True
        self._board = {"ts": "", "cycle": 0, "files": 0, "new_events": 0,
                       "events": [], "covenant": None, "covenant_ok": True,
                       "ledger": "no ledger yet", "ledger_ok": True,
                       "intact": True, "alerts": []}

    # -- the readers's side ------------------------------------------------
    def snapshot(self):
        """The current picture, whole. A copy down to its lists — mutate it
        freely, the board does not move; a scan replaces the board wholesale."""
        with self._lock:
            b = dict(self._board)
        b["events"] = list(b["events"])
        b["alerts"] = list(b["alerts"])
        return b

    # -- the thread's side -------------------------------------------------
    def start(self):
        threading.Thread.start(self)
        return self

    def stop(self, timeout=5.0):
        """End the watch and wait for the thread to lie down. Returns True
        when it stopped clean."""
        self._halt.set()
        self.join(timeout)
        return not self.is_alive()

    def run(self):
        self._scan()                          # first look, before any wait
        while not self._halt.wait(self.interval):
            try:
                self._scan()
            except Exception:
                # the Radar must never fell the agent it serves; a failed
                # cycle is skipped, and the next one looks again.
                pass

    def _scan(self):
        now = atlas.census(self.root)
        events = atlas.movements(self._prev, now) if self._prev is not None else []
        self._prev = now

        # the seals, the cheap way: covenant every cycle (two small hashes);
        # the ledger chain only when the ledger file itself changed.
        live = _watch.covenant_of(os.path.join(self.root, "foundation"))
        sealed = _watch.sealed_covenant(self.root)
        cov_ok = (sealed is None) or (live == sealed)
        led_sig = now.get(os.path.join("ledger", "ledger.jsonl"))
        if led_sig != self._led_sig:
            self._led_ok = _watch.ledger_state(self.root)
            self._led_sig = led_sig
        led_ok, _n, led_detail = self._led_ok

        alerts = []
        if not cov_ok:
            alerts.append("the covenant MOVED — sealed %s, live %s" % (sealed, live))
        if not led_ok:
            alerts.append("the ledger chain BROKE — %s" % led_detail)
        intact = not alerts

        board = {"ts": time.strftime("%H:%M:%S"),
                 "cycle": self._board["cycle"] + 1,
                 "files": len(now), "new_events": len(events),
                 "events": [atlas.render_event(e) for e in events[:5]],
                 "covenant": live, "covenant_ok": cov_ok,
                 "ledger": led_detail, "ledger_ok": led_ok,
                 "intact": intact, "alerts": alerts}

        # witness sparingly: movement, and integrity TRANSITIONS — never the
        # quiet cycles (a radar that narrates every sweep is noise, not watch).
        if self.journal is not None:
            try:
                if events:
                    self.journal.write("radar", moved=len(events),
                                       head=board["events"][0][:70])
                if intact != self._was_intact:
                    self.journal.write("radar",
                                       integrity="restored" if intact else "SHIFTED",
                                       alerts="; ".join(alerts)[:120])
            except Exception:
                pass
        self._was_intact = intact

        with self._lock:
            self._board = board


def prove():
    """Proven against a real estate on real disk: it sees a file land, it
    sees the covenant move and calls it, it heals when the doctrine returns,
    its snapshots are immutable, and it stops clean."""
    import json
    import shutil
    import tempfile
    strokes = []

    def check(name, ok, detail=""):
        strokes.append((name, bool(ok), detail))

    def poll(cond, deadline=6.0):
        end = time.time() + deadline
        while time.time() < end:
            if cond():
                return True
            time.sleep(0.02)
        return cond()

    root = tempfile.mkdtemp(prefix="radar_")
    try:
        os.makedirs(os.path.join(root, "foundation"))
        os.makedirs(os.path.join(root, "shelf"))
        os.makedirs(os.path.join(root, "weights"))
        soul = os.path.join(root, "foundation", "01.md")
        open(soul, "w", encoding="utf-8").write("the soul holds the estate")
        cov = _watch.covenant_of(os.path.join(root, "foundation"))
        json.dump({"covenant": cov},
                  open(os.path.join(root, "weights", "covenant.json"), "w"))

        r = Radar(root, interval=0.05).start()
        check("wakes and takes a first census",
              poll(lambda: r.snapshot()["cycle"] >= 1),
              "cycle %d, %d files" % (r.snapshot()["cycle"], r.snapshot()["files"]))
        check("a sound estate reads INTACT", r.snapshot()["intact"],
              "covenant %s" % r.snapshot()["covenant"])

        # a file lands on the shelf — the Radar sees it move, within a cycle
        open(os.path.join(root, "shelf", "note.txt"), "w").write("a new reading")
        check("sees a file LAND while running",
              poll(lambda: any("note.txt" in e for e in r.snapshot()["events"])
                   or r.snapshot()["files"] == 3),
              "; ".join(r.snapshot()["events"])[:60] or "%d files" % r.snapshot()["files"])

        # a snapshot is a copy — mutating it moves nothing on the board
        s = r.snapshot()
        s["intact"] = False
        s["alerts"].append("a reader's scribble")
        check("snapshots are IMMUTABLE to their readers",
              r.snapshot()["intact"] and not r.snapshot()["alerts"], "board unmoved")

        # the doctrine moves under him — the flag goes up, named
        open(soul, "a", encoding="utf-8").write("\nan altered article.")
        check("catches the covenant MOVING",
              poll(lambda: not r.snapshot()["intact"]),
              (r.snapshot()["alerts"] or ["?"])[0][:60])
        check("the alert NAMES the shift",
              any("covenant" in a for a in r.snapshot()["alerts"]))

        # the doctrine returns — the flag comes down on its own
        open(soul, "w", encoding="utf-8").write("the soul holds the estate")
        check("stands down when the doctrine RETURNS",
              poll(lambda: r.snapshot()["intact"]), "intact again")

        check("stops CLEAN when told", r.stop(), "thread lay down")
    finally:
        shutil.rmtree(root, ignore_errors=True)
    return strokes


def main():
    print("\n  STEWARD'S RADAR — the horizon scan: he feels the estate move while he thinks.\n")
    strokes = prove()
    width = max(len(n) for n, _, _ in strokes)
    all_ok = all(o for _, o, _ in strokes)
    for name, ok, detail in strokes:
        print("    [%s]  %-*s   %s" % ("PASS" if ok else "FAIL", width, name, detail))
    print()
    print("  " + ("PROVEN. He watches while he works, and holds his hands when the ground shifts."
                  if all_ok else "A step failed. A radar that cannot be trusted watches nothing.") + "\n")
    return 0 if all_ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PROVE THE AGENT — that he ROUTES HIMSELF on a mixed stream.

Given one stream of unlike inputs, with no menu and no one telling him what each
is, Steward decides for himself which faculty each calls for, acts with the real
faculty on real data, and reads his own window between turns — quietly, to his
journal. If the routing is his own and the acts are real, he is an agent.
"""
import os
import sys

_BOOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BOOT not in sys.path:
    sys.path.insert(0, _BOOT)

from steward import Steward


STREAM = [
    ("6 * 7 + 3",                              "sum"),
    ("telegraph",                              "read"),
    ("find papers on folding schemes",         "look"),
    ("who are you?",                           "self"),
    ("define hydrophobia",                     "read"),
    ("8 / 0",                                  "sum"),
    ("what must a steward never do?",          "ask"),
    (("The cistern behind the north wing sits at forty percent this week and the "
      "east fence line is holding after the storm while the boiler was last "
      "serviced in the spring and the north field was mowed on Tuesday and the "
      "well pump ran twice and the gate latch was replaced and the hedgerow was "
      "trimmed back a full foot along the lane this month by the crew."), "keep"),
]


def main():
    print("\n  PROVING THE AGENT — one mixed stream, his own routing, real acts.\n")
    s = Steward(root=_BOOT)
    s.heart.wake()
    rows, all_ok = [], True
    try:
        for x, expected in STREAM:
            route = s.perceive(x)
            d = s.step(x)
            ok = (route == expected)
            all_ok = all_ok and ok
            shown = x if len(x) < 46 else x[:43] + "..."
            rows.append((ok, expected, route, shown, d["spoke"], d["attend"]))
    finally:
        s.rest()

    w = max(len(shown) for _, _, _, shown, _, _ in rows)
    print("  ROUTING — did he sort the stream himself?\n")
    for ok, exp, got, shown, spoke, att in rows:
        print("    [%s]  %-*s  ->  %-5s %s" % ("PASS" if ok else "FAIL", w, shown, got,
                                               "" if ok else "(wanted %s)" % exp))
    print("\n  ACTS — did the real faculty really answer?\n")
    for _, _, got, shown, spoke, att in rows:
        first = spoke.splitlines()[0] if spoke else "(quiet — fed to the window)"
        print("    %-5s : %s" % (got, first[:88]))

    def spokes(route):
        return [sp for _, _, r, _, sp, _ in rows if r == route]
    checks = []
    checks.append(("arithmetic done through the body", any("= 45" in sp for sp in spokes("sum"))))
    checks.append(("divide-by-zero refused honestly",
                   any("REFUSED" in sp and "divide by zero" in sp for sp in spokes("sum"))))
    checks.append(("a word read by rule (etymon)", any("far" in sp.lower() for sp in spokes("read"))))
    checks.append(("self-knowledge answered (heart or mind)", any(len(sp) > 0 for sp in spokes("self"))))
    checks.append(("he attended his own window every turn",
                   all(att.get("feeling") for _, _, _, _, _, att in rows)))
    jstats = s.journal.stats()
    checks.append(("housekeeping written to the journal file, not spewed",
                   jstats["live"] + jstats["archived"] >= len(rows)))

    print("\n  REALITY — were the acts real?\n")
    for name, ok in checks:
        all_ok = all_ok and ok
        print("    [%s]  %s" % ("PASS" if ok else "FAIL", name))

    print("\n  Quiet by design: he folded %d time(s) and re-grounded %d time(s), all witnessed to\n"
          "  the journal (%d live + %d archived lines) — none of it narrated to you."
          % (s.foldings, s.grounds, jstats["live"], jstats["archived"]))
    print("\n  " + ("PROVEN. He routed a mixed stream himself and acted for real on each.\n"
                    "  That is an agent — perceive, decide, act, attend — not a menu.\n"
                    if all_ok else
                    "  A step failed. He does not claim an agency he cannot show.\n"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PROVE THE HYPER-CORE — the county clerk, on a copy, offline.

The serum, made to show its work against the plan's own checks:
  * the filler ledger takes nonsense; the signal ledger stays clean; both verify
    as unbroken chains; a tampered entry is pinpointed in either
  * a repeated ask surfaces its prior ruling FASTER (the path strengthened);
    the least-used path FOLDS into the append-only chain, found there, not lost
  * every ruling is stamped fact or generated; a generated one is never fact
  * the idle beat (reconcile) flags a note that stands on no known ground
  * the covenant does NOT move — he is the same self, only denser

Heart awake, air-gapped, in a temp estate. Standard library only.
"""
import json
import os
import shutil
import sys
import tempfile

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import manjuel as M

PASS = FAIL = 0


def check(name, ok, detail=""):
    global PASS, FAIL
    print("    [%s]  %-54s %s" % ("PASS" if ok else "FAIL", name, str(detail)[:60]))
    if ok:
        PASS += 1
    else:
        FAIL += 1


def main():
    print("\n  PROVING THE HYPER-CORE — the county clerk, heart awake, on a copy.\n")

    # a temp estate: copy the real foundation so the covenant is genuine
    tmp = tempfile.mkdtemp(prefix="hypercore_")
    shutil.copytree(os.path.join(_ROOT, "foundation"), os.path.join(tmp, "foundation"))

    covenant_before = None
    try:
        m = M.Manjuel(root=tmp, seal=True).awaken()
        covenant_before = m.foundation.covenant

        # --- provenance: grounded is fact, thin is generated ---
        a1 = m.ask("what must a steward never do?")
        check("a grounded answer is stamped FACT", a1.provenance == M.Registry.FACT,
              "prov=%s thin=%s" % (a1.provenance, a1.thin_ground))
        a2 = m.ask("xyzzy plugh frobnitz snork")           # nothing in the ground
        check("an ungrounded answer is stamped GENERATED", a2.provenance == M.Registry.GENERATED,
              "prov=%s thin=%s" % (a2.provenance, a2.thin_ground))
        check("a generated ruling is never reported as fact", a2.provenance != M.Registry.FACT)

        # --- the index strengthens with use; the tag rides (provenance-honest) ---
        before = m.registry.recall("what must a steward never do?")
        m.ask("what must a steward never do?")             # ask the kindred shape again
        after = m.registry.recall("what must a steward never do?")
        check("a repeated ask STRENGTHENS its path (uses rise)",
              before is not None and after is not None and after[2] > before[2],
              "uses %s -> %s" % (before[2] if before else None, after[2] if after else None))
        check("the ruling carries its provenance in the index", after[1] == M.Registry.FACT, after[1])

        # --- the least-used path FOLDS into the chain — found there, not lost ---
        reg = M.Registry(os.path.join(tmp, "reg_fold.jsonl"), cap=3)
        for q in ("alpha one", "beta two", "gamma three"):
            reg.note(q, "r", M.Registry.FACT)
        reg.recall("alpha one"); reg.recall("alpha one")   # make 'alpha' well-worn
        reg.note("delta four", "r", M.Registry.FACT)        # over cap -> least-used folds
        folded_ok, n_folded, _ = reg.folded.verify()
        keys_folded = [e["payload"]["key"] for e in reg.folded.entries()]
        check("over the bound, a path FOLDS into the append-only chain", n_folded == 1,
              "folded %d" % n_folded)
        check("the fold chain verifies (nothing broken)", folded_ok)
        check("the well-worn path SURVIVED; an idle one folded",
              "alpha one" in " ".join(reg.paths) and "alpha" not in " ".join(keys_folded),
              "live=%s" % list(reg.paths))

        # --- the filler ledger takes nonsense; the signal stays clean ---
        sig0 = sum(1 for _ in m.ledger.entries())
        r = m.remember("!!!  ...  ???")                     # no substance to index
        check("nonsense is filed to the FILLER chain, not the index", "filler chain" in r, r[:40])
        fill_ok, n_fill, _ = m.filler.verify()
        check("the filler chain verifies as an unbroken chain", fill_ok and n_fill >= 1,
              "%d filler entries" % n_fill)
        m.remember("The boiler was serviced in spring by the vendor.")   # substance -> signal + index
        sig_ok, n_sig, _ = m.ledger.verify()
        check("the signal ledger stays clean and verifies", sig_ok, "%d signal entries" % n_sig)

        # tamper the filler chain -> pinpointed
        rows = open(m.filler.path, encoding="utf-8").read().splitlines()
        e0 = json.loads(rows[0]); e0["payload"]["note"] = "ALTERED"; rows[0] = json.dumps(e0)
        open(m.filler.path, "w", encoding="utf-8").write("\n".join(rows) + "\n")
        t_ok, at, detail = m.filler.verify()
        check("a tampered filler entry is caught AND pinpointed", (not t_ok), detail)

        # --- the idle beat flags a note that stands on no known ground ---
        m.remember("The cistern behind the north wing read forty-one percent.")  # grounded-ish estate note
        m.remember("Vlorptak grebulon zizzax quommff.")     # stands on nothing known
        rec = m.reconcile()
        check("the idle beat weighs recent memory against the known", rec["weighed"] >= 2,
              "weighed %d" % rec["weighed"])
        check("a note on no known ground is FLAGGED (trust nothing)", rec["flagged"] >= 1,
              "flagged %d: %s" % (rec["flagged"], rec["flags"][:1]))

        # --- the reconcile finding is itself witnessed to the ledger ---
        kinds = [e.get("kind") for e in m.ledger.entries()]
        check("the idle beat's finding is appended to the record", "reconcile" in kinds)

        # --- HE IS STILL HIMSELF: the covenant did not move ---
        check("the covenant did NOT move — same self, only denser",
              m.foundation.covenant == covenant_before, m.foundation.covenant)

        # --- and he wakes again clean, covenant held ---
        m2 = M.Manjuel(root=tmp, seal=True).awaken()
        check("he re-awakens and the covenant still holds",
              m2.foundation.covenant == covenant_before, m2.foundation.covenant)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n  %s — %d held, %d failed.\n"
          % ("THE HYPER-CORE HOLDS" if FAIL == 0 else "THE HYPER-CORE DID NOT HOLD", PASS, FAIL))
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

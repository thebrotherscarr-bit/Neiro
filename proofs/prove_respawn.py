#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PROVE THE RESPAWN — a child agent comes up from a parent, knowing before.

Two estates in temp dirs, heart awake in each:
  * a PARENT learns something no fresh agent could know, then is condensed
  * the child VERIFIES the bundle (same self, sound mark, intact chain) before
    trusting it — and REFUSES a different self, a tampered bundle, a broken chain
  * the child RESPAWNS and, on its own awakening, RECALLS what only the parent
    knew — it inherited, it did not relearn
  * the fat weights did NOT travel — the child regrew lean from the crystal

Standard library only; the transport is in-process (the estate rides the proven
encrypted channel). Nothing reaches the network.
"""
import os
import shutil
import sys
import tempfile

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from steward import respawn as R
import manjuel as M

PASS = FAIL = 0


def check(name, ok, detail=""):
    global PASS, FAIL
    print("    [%s]  %-56s %s" % ("PASS" if ok else "FAIL", name, str(detail)[:52]))
    if ok:
        PASS += 1
    else:
        FAIL += 1


def _estate(foundation_src):
    d = tempfile.mkdtemp(prefix="estate_")
    shutil.copytree(foundation_src, os.path.join(d, "foundation"))
    return d


def main():
    print("\n  PROVING THE RESPAWN — a child comes up from a parent, knowing before.\n")
    real_foundation = os.path.join(_ROOT, "foundation")

    parent = _estate(real_foundation)
    child = _estate(real_foundation)          # same doctrine — a valid continuation
    stranger = None
    try:
        # --- the PARENT learns something no fresh agent could know ---
        pm = M.Manjuel(root=parent, seal=True).awaken()
        secret = "The cabin key is under the third stone by the north fence."
        pm.remember(secret)
        # what fat did the parent grow? (to prove it does NOT travel)
        parent_has_weights = any(f.startswith("weights_") for f in
                                 os.listdir(os.path.join(parent, "weights")))
        check("the parent grew fat weights while it lived", parent_has_weights)

        # --- CONDENSE: the portable bundle, marked ---
        bundle = R.condense(parent)
        check("the bundle carries the covenant (which self)", bool(bundle["covenant"]),
              bundle["covenant"])
        check("the bundle carries the living ring (the crystal)", secret in bundle["ring"])
        check("the bundle carries the ledger", "remember" in bundle["ledger"])
        check("the fat weights are NOT in the bundle",
              "weights" not in bundle and "vectors" not in json_dump(bundle))

        # --- the child REFUSES what it should refuse (trust nothing) ---
        # a different self:
        stranger = _estate(real_foundation)
        # move the stranger's foundation to a different doctrine -> different covenant
        with open(os.path.join(stranger, "foundation", "01_MYTHOS.md"), "a",
                  encoding="utf-8") as f:
            f.write("\n\nAN ALTERED DOCTRINE — a different self entirely.\n")
        ok, detail = R.respawn(stranger, bundle)
        check("a DIFFERENT self is refused (covenant mismatch)", not ok, detail[:48])

        # a tampered bundle:
        bad = R.sync(bundle)
        bad["ring"] = bad["ring"] + "  SMUGGLED LINE"      # altered after the mark
        ok, detail = R.respawn(child, bad)
        check("a TAMPERED bundle is refused (mark mismatch)", not ok, detail[:48])

        # a broken chain:
        import json as _json
        bad2 = R.sync(bundle)
        lines = bad2["ledger"].splitlines()
        e0 = _json.loads(lines[0]); e0["kind"] = e0["kind"] + "X"   # change hashed content, keep old hash
        lines[0] = _json.dumps(e0, ensure_ascii=False)
        bad2["ledger"] = "\n".join(lines)
        bad2["mark"] = R._bundle_mark(bad2)                  # re-mark so it passes the mark gate
        ok, detail = R.respawn(child, bad2)
        check("a BROKEN ledger chain is refused", not ok, detail[:48])

        # --- the GOOD bundle: the child respawns and KNOWS ---
        ok, detail = R.respawn(child, R.sync(bundle))
        check("the good bundle respawns the child", ok, detail[:48])
        # the child never grew fat weights yet — it inherited, not trained
        child_weights_before = [f for f in os.listdir(os.path.join(child, "weights"))
                                if f.startswith("weights_")] if os.path.isdir(
                                os.path.join(child, "weights")) else []
        check("the child has NOT trained fat weights (inherited, not relearned)",
              not child_weights_before)

        # now the child's heart awakens FROM the inherited state and recalls the secret
        cm = M.Manjuel(root=child, seal=True).awaken()
        ans = cm.ask("where is the cabin key?")
        check("the child KNOWS what only the parent knew (inherited)",
              "third stone" in ans.text.lower() or "north fence" in ans.text.lower(),
              ans.text[:48])
        check("and the child is the SAME self (covenant held)",
              cm.foundation.covenant == bundle["covenant"], cm.foundation.covenant)
    finally:
        for d in (parent, child, stranger):
            if d:
                shutil.rmtree(d, ignore_errors=True)

    print("\n  %s — %d held, %d failed.\n"
          % ("THE RESPAWN HOLDS" if FAIL == 0 else "THE RESPAWN DID NOT HOLD", PASS, FAIL))
    return 0 if FAIL == 0 else 1


def json_dump(o):
    import json
    return json.dumps(o)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RESPAWN — the kernel respawn: a child agent comes up from a parent's condensed
state, already knowing, verified before it trusts a byte.

The way the Windows kernel brings a process up against a stable, known-good
image instead of cold-booting from nothing: a long-standing parent agent (the
home server) condenses its life into a portable bundle; a child device pulls it,
VERIFIES it, and respawns from it — inheriting what the parent knew rather than
relearning it. Robust, secure, stable, all at once.

Two laws shape it:

  * THE GATEWAY SYNCS; THE HEART AWAKENS. This runs at the Steward layer, which
    may reach the network. It prepares the child's disk — foundation already
    shared, condensed memory written and verified — and only THEN does the
    child's sealed heart awaken from those files. The heart never touches the
    wire; the air-gap holds.

  * SAME SELF, OR IT REFUSES. A child may only respawn a parent of the SAME
    covenant — the same doctrine, the same self. Pouring one self's memory into
    a different doctrine would be pollution; respawn checks the covenant first
    and refuses on mismatch. That check IS the kernel stability: every agent in
    the fleet is a faithful continuation of one known-good self.

What travels is the CONDENSED state — the living ring (the crystal), the ledger,
the strata — never the fat grown weights. The child regrows those lean from the
crystal on wake: lowest capability first, grown only as needed. Best of both
worlds — deep grown capability, carried as constant-size condensed state.

The transport is injectable. In proof it runs in-process; in the estate it rides
the proven encrypted channel (the sync spine). Standard library only.
"""
import hashlib
import json
import os


# --- the covenant, read without waking a heart --------------------------------
def covenant_of(foundation_dir):
    """The self's mark — the SHA-256 over the foundation documents, computed
    exactly as the heart computes it, but touching nothing and waking nothing.
    Two estates are the same self iff their covenants match."""
    if not os.path.isdir(foundation_dir):
        return None
    shas = []
    for fn in sorted(os.listdir(foundation_dir)):
        if fn.lower().endswith((".md", ".txt")):
            with open(os.path.join(foundation_dir, fn), "r", encoding="utf-8",
                      errors="replace") as f:
                shas.append(hashlib.sha256(f.read().encode("utf-8")).hexdigest())
    if not shas:
        return None
    # the FULL 64-char covenant, computed exactly as the heart's Foundation does
    # (join each doc's sha, hash once more). 'Same self' must be identical, not a
    # 16-char prefix — respawn checks the whole self, never a short form.
    return hashlib.sha256("".join(shas).encode("utf-8")).hexdigest()


def _read(path):
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    return None


def _bundle_mark(bundle):
    """One digest over the condensed state — the parent's word that this is what
    it condensed. The child re-derives it and refuses a bundle that does not
    match (trust nothing without provenance)."""
    core = {"covenant": bundle["covenant"], "ring": bundle["ring"],
            "ledger": bundle["ledger"], "strata": bundle["strata"]}
    return hashlib.sha256(
        json.dumps(core, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


# --- CONDENSE — the parent winds its life down into a portable bundle ----------
def condense(root):
    """Read a source estate's condensed state into a portable, integrity-marked
    bundle: which self (covenant), the living ring (crystal), the ledger, the
    strata. NOT the fat weights — the child regrows those. Reads files only; it
    wakes no heart and reaches no network."""
    foundation = os.path.join(root, "foundation")
    ring = _read(os.path.join(root, "memory", "notes.md")) or ""
    ledger = _read(os.path.join(root, "ledger", "ledger.jsonl")) or ""
    strata = {}
    sdir = os.path.join(root, "strata")
    if os.path.isdir(sdir):
        for fn in sorted(os.listdir(sdir)):
            if fn.endswith((".md", ".txt", ".jsonl")):
                strata[fn] = _read(os.path.join(sdir, fn)) or ""
    bundle = {"covenant": covenant_of(foundation), "ring": ring,
              "ledger": ledger, "strata": strata}
    bundle["mark"] = _bundle_mark(bundle)
    return bundle


# --- the transport seam (proof: in-process; estate: the encrypted spine) -------
def _passthrough(bundle):
    """The trivial transport — hand the bundle across in one process. The real
    transport serializes this and sends it over the proven encrypted channel."""
    return json.loads(json.dumps(bundle))


def sync(bundle, transport=None):
    """Carry a condensed bundle from parent to child. Transport is injectable;
    the estate rides the encrypted channel, the proof rides passthrough."""
    return (transport or _passthrough)(bundle)


# --- RESPAWN — the child comes up from the bundle, verified first --------------
def respawn(child_root, bundle):
    """Bring a child estate up from a parent's condensed bundle. VERIFY BEFORE
    ADOPTING (trust nothing): same covenant, sound bundle mark, intact ledger
    chain. Only then write the condensed state into the child. The child's heart
    then awakens from it — knowing before, regrown lean. Returns (ok, detail).
    Refuses, and writes nothing, on any failed check."""
    child_cov = covenant_of(os.path.join(child_root, "foundation"))
    if child_cov is None:
        return False, "the child has no foundation — nothing to be a continuation of"

    # GATE 1 — same self, or refuse. A different doctrine may not inherit this.
    if bundle.get("covenant") != child_cov:
        return False, ("covenant mismatch — the child is a different self (%s vs %s); "
                       "respawn refuses to pour one self's memory into another"
                       % (bundle.get("covenant"), child_cov))

    # GATE 2 — the bundle is what the parent condensed (provenance).
    claimed = bundle.get("mark")
    if claimed != _bundle_mark(bundle):
        return False, "bundle mark does not match its contents — refused (tampered in transit)"

    # GATE 3 — the ledger chain is intact (nothing broken in the record).
    ok, n, detail = _verify_ledger(bundle.get("ledger", ""))
    if not ok:
        return False, "the condensed ledger is broken: %s" % detail

    # all gates held — write the condensed state; the child now KNOWS BEFORE.
    os.makedirs(os.path.join(child_root, "memory"), exist_ok=True)
    os.makedirs(os.path.join(child_root, "ledger"), exist_ok=True)
    with open(os.path.join(child_root, "memory", "notes.md"), "w", encoding="utf-8") as f:
        f.write(bundle.get("ring", ""))
    with open(os.path.join(child_root, "ledger", "ledger.jsonl"), "w", encoding="utf-8") as f:
        f.write(bundle.get("ledger", ""))
    if bundle.get("strata"):
        sdir = os.path.join(child_root, "strata")
        os.makedirs(sdir, exist_ok=True)
        for fn, text in bundle["strata"].items():
            with open(os.path.join(sdir, fn), "w", encoding="utf-8") as f:
                f.write(text)
    return True, "respawned: same self (%s), ledger intact (%d), ring inherited" % (child_cov, n)


def _verify_ledger(text):
    """Walk a hash-chained ledger's text the way the heart's Ledger does, without
    importing it. Returns (intact, n, detail)."""
    prev = "0" * 64
    n = 0
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            e = json.loads(line)
        except Exception:
            return False, n, "unreadable entry at %d" % n
        body = {k: e.get(k) for k in ("ts", "kind", "payload", "prev")}
        canon = json.dumps(body, sort_keys=True, ensure_ascii=False)
        h = hashlib.sha256((prev + canon).encode("utf-8")).hexdigest()
        if e.get("prev") != prev:
            return False, n, "chain break at %d (prev mismatch)" % n
        if e.get("hash") != h:
            return False, n, "tamper at %d (hash mismatch)" % n
        prev = e["hash"]
        n += 1
    return True, n, "chain intact"


def handoff(parent_root, child_root, transport=None):
    """The whole kernel respawn, one call: condense the parent, sync to the child,
    respawn the child from it. Returns (ok, detail)."""
    bundle = sync(condense(parent_root), transport=transport)
    return respawn(child_root, bundle)

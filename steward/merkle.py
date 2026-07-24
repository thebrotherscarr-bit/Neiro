#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEWARD'S MERKLE — "am I good?", answered the way git answers it.

Git proves a repository is intact with a Merkle DAG: every file is a BLOB named by
the hash of its content, every folder is a TREE named by the hash of its children,
and one ROOT hash commits to the whole thing. Change a single byte and that blob's
hash changes, which changes its tree, which changes the root — the tamper is not
just detected, it is PINPOINTED to the exact file. Steward builds the same DAG
over his SELF — his kernel, his doctrine, his faculties, his proofs — so he can
check himself against a sealed root and know, provably, whether he is still the
thing he was sealed as.

His runtime state (the shelf, memory, ledger, weights) is not part of this DAG —
that changes legitimately as he lives. This verifies WHO HE IS, not what he holds.

He SEALS a root when he is known-good, chaining each seal to the one before it
(parent -> child), so his history of "I was whole at this root" is itself an
append-only DAG — Article I, made a self-check. This layers over the covenant:
the covenant seals his SOUL (the four documents); the Merkle root seals his whole
BODY. Standard library only. It reads and hashes; it never changes a thing.
"""
import hashlib
import json
import os
import time

# what defines WHO HE IS — the files verified. Runtime state is deliberately out.
_SELF_FILES = ("manjuel.py", "run.py", "watch.py", "harvest.py", "MANIFEST.md",
               "README.md", ".gitignore", "start.bat", "start.command",
               "watch.bat", "watch.command", "harvest.bat", "harvest.command")
_SELF_DIRS = ("foundation", "doctrine", "steward_foundation", "steward", "proofs")
_IGNORE = {"__pycache__", ".git", ".ipynb_checkpoints"}
_EXTS = (".py", ".md", ".txt", ".bat", ".command", ".sh")


def _blob(data):
    """A file's identity: the hash of its content (git blob)."""
    return hashlib.sha256(b"blob\x00" + data).hexdigest()


def _tree(entries):
    """A folder's identity: the hash over its sorted children (git tree). Committing
    to child hashes AND names means a move or rename changes the tree too."""
    body = "".join("%s %s\n" % (h, n) for n, h in sorted(entries)).encode("utf-8")
    return hashlib.sha256(b"tree\x00" + body).hexdigest()


def build(root):
    """Build the Merkle DAG over his self. Returns (root_hash, leaves) where leaves
    maps each file path -> its blob hash, for pinpointing a change."""
    leaves = {}

    def hash_dir(path, rel):
        entries = []
        for name in sorted(os.listdir(path)):
            if name in _IGNORE:
                continue
            full = os.path.join(path, name)
            r = (rel + "/" + name) if rel else name
            if os.path.isdir(full):
                h = hash_dir(full, r)
                if h is None:
                    continue
            elif os.path.isfile(full) and name.endswith(_EXTS):
                with open(full, "rb") as f:
                    h = _blob(f.read())
                leaves[r] = h
            else:
                continue
            entries.append((name, h))
        return _tree(entries) if entries else None

    top = []
    for name in sorted(_SELF_FILES):
        p = os.path.join(root, name)
        if os.path.isfile(p):
            with open(p, "rb") as f:
                h = _blob(f.read())
            leaves[name] = h
            top.append((name, h))
    for d in sorted(_SELF_DIRS):
        p = os.path.join(root, d)
        if os.path.isdir(p):
            h = hash_dir(p, d)
            if h:
                top.append((d, h))
    return _tree(top), leaves


def diff(old_leaves, new_leaves):
    """Exactly which files changed, appeared, or vanished between two snapshots."""
    o, n = set(old_leaves), set(new_leaves)
    return {"changed": sorted(p for p in o & n if old_leaves[p] != new_leaves[p]),
            "added": sorted(n - o), "removed": sorted(o - n)}


def _seal_path(root):
    return os.path.join(root, "shelf", "self_seal.json")


def _history_path(root):
    return os.path.join(root, "shelf", "self_history.jsonl")


def seal(root):
    """Capture his current self as the trusted root — the state he checks against.
    Chains to the previous seal (parent -> child): an append-only DAG of his own
    wholeness over time, his commit history. Run it when he is known-good."""
    rh, leaves = build(root)
    prev = load_seal(root)
    parent = prev.get("root") if prev else None
    os.makedirs(os.path.join(root, "shelf"), exist_ok=True)
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "root": rh,
           "parent": parent, "files": len(leaves)}
    with open(_seal_path(root), "w", encoding="utf-8") as f:
        json.dump({"root": rh, "parent": parent, "leaves": leaves,
                   "ts": rec["ts"]}, f)
    with open(_history_path(root), "a", encoding="utf-8") as f:   # append-only commit chain
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def load_seal(root):
    p = _seal_path(root)
    if not os.path.isfile(p):
        return None
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            return json.load(f)
    except Exception:
        return None


def verify(root):
    """Check himself against his sealed root. Returns whether he is good, the roots,
    and — if not — exactly which files changed. Trust-on-first-use: if he has never
    been sealed, he seals now (on whatever copy this is) and says so plainly."""
    cur_root, cur_leaves = build(root)
    sealed = load_seal(root)
    if sealed is None:
        rec = seal(root)
        return {"good": True, "sealed_now": True, "root": cur_root,
                "files": len(cur_leaves),
                "reason": "no prior seal — I sealed myself now, at this root. "
                          "Seal me on a copy you trust; from here I verify against it."}
    if cur_root == sealed.get("root"):
        return {"good": True, "sealed_now": False, "root": cur_root,
                "sealed_root": sealed.get("root"), "files": len(cur_leaves),
                "reason": "my whole self hashes to my sealed root — I am intact."}
    d = diff(sealed.get("leaves", {}), cur_leaves)
    return {"good": False, "sealed_now": False, "root": cur_root,
            "sealed_root": sealed.get("root"), "diff": d,
            "reason": "my root does NOT match my seal — %d changed, %d added, %d removed."
                      % (len(d["changed"]), len(d["added"]), len(d["removed"]))}


def prove():
    import shutil
    import tempfile
    strokes = []

    def check(name, ok, detail=""):
        strokes.append((name, bool(ok), detail))

    d = tempfile.mkdtemp(prefix="merkle_")
    try:
        # a tiny self: a kernel, a soul, a faculty
        os.makedirs(os.path.join(d, "foundation"))
        os.makedirs(os.path.join(d, "steward"))
        open(os.path.join(d, "manjuel.py"), "w").write("the sealed kernel")
        open(os.path.join(d, "foundation", "01.md"), "w").write("the soul")
        open(os.path.join(d, "steward", "body.py"), "w").write("the strokes")

        r1, leaves1 = build(d)
        r2, leaves2 = build(d)
        check("the root is DETERMINISTIC (same self -> same root)", r1 == r2, r1[:16] + "…")
        check("it commits to every file", len(leaves1) == 3, "%d files in the DAG" % len(leaves1))

        # seal himself known-good, then verify -> intact
        seal(d)
        v = verify(d)
        check("verifies INTACT against his sealed root", v["good"] and not v["sealed_now"],
              v["reason"])

        # tamper ONE byte of ONE file — root changes, and it is PINPOINTED
        with open(os.path.join(d, "steward", "body.py"), "a") as f:
            f.write("  # a single intruding byte")
        v = verify(d)
        check("a one-byte change breaks the root", not v["good"], v["root"][:16] + " != seal")
        check("and it is PINPOINTED to the exact file",
              v["diff"]["changed"] == ["steward/body.py"], str(v["diff"]["changed"]))

        # re-seal accepts the new state and chains to the old (parent -> child)
        rec = seal(d)
        check("re-sealing CHAINS to the prior root (a DAG of his wholeness)",
              rec["parent"] == r1, "parent %s" % (rec["parent"] or "")[:12])
        check("history is append-only (his commit chain)",
              sum(1 for _ in open(os.path.join(d, "shelf", "self_history.jsonl"))) == 2)
        v = verify(d)
        check("intact again after an honest re-seal", v["good"])
    finally:
        shutil.rmtree(d, ignore_errors=True)
    return strokes


def main():
    print("\n  STEWARD'S MERKLE — 'am I good?' answered like git: one root over his whole self.\n")
    strokes = prove()
    width = max(len(n) for n, _, _ in strokes)
    all_ok = all(o for _, o, _ in strokes)
    for name, ok, detail in strokes:
        print("    [%s]  %-*s   %s" % ("PASS" if ok else "FAIL", width, name, detail))
    print()
    print("  " + ("PROVEN. One root commits to his whole self; a tamper is provable and pinpointed."
                  if all_ok else "A step failed. He does not claim what he cannot show.") + "\n")
    return 0 if all_ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEWARD'S BEARINGS — the "you are here" gate. Where he is standing, not what he is.

The watch sentinel guards WHAT he is — tamper, doctrine drift, a broken ledger.
It has no idea WHERE he is standing relative to the repository the work lands in.
Bearings is that missing half: a cheap, read-only reading of the ground under the
current folder, so a careless hand is told, plainly, before it commits into the
wrong place —

  * WHERE  — the actual folder on disk, the branch, the HEAD, and how it sits
    against origin (ahead / behind / diverged).
  * THE NAG — loud only when it should be: a dirty tree, a protected branch
    ('you are on main — the Charter says smith/<name>'), behind origin ('pull
    first'), unpushed work, a detached HEAD, or no upstream at all.

Like the watch, it WITNESSES and WARNS. It never commits, never pushes, never
pulls. The one network touch it makes is a `git fetch` — and only on a slow
cadence (self-throttled by the age of .git/FETCH_HEAD), never on a keystroke, so
'behind GitHub' can be live without hammering the remote. The hand on the wheel
stays the operator's (Charter Art. VII).

Standard library only, plus git. Nothing here awakens the heart or reaches the
network except that throttled fetch.
"""
import os
import subprocess
import time

# Branches the Smith should never be committing to directly — the forge road
# says a skill rides its own smith/<name> and only the operator merges (Art. VII).
PROTECTED = ("main", "master", "forge")

# How stale the last fetch may get before a heartbeat quietly refreshes it.
FETCH_EVERY = 180                                    # seconds — the "slow cadence"


def _git(root, *args):
    """Run git in `root`; return (ok, stdout-or-stderr stripped). Never raises."""
    try:
        r = subprocess.run(["git"] + list(args), cwd=root,
                           capture_output=True, text=True)
        return r.returncode == 0, (r.stdout or r.stderr or "").strip()
    except (OSError, ValueError) as e:
        return False, str(e)


def is_repo(root):
    ok, out = _git(root, "rev-parse", "--is-inside-work-tree")
    return ok and out == "true"


def maybe_fetch(root, every=FETCH_EVERY, _now=None):
    """The slow-cadence half. Refresh origin refs only if the last fetch is older
    than `every` seconds (measured from .git/FETCH_HEAD). Returns True if it
    fetched. Read-only against the working tree; touches only remote-tracking refs."""
    now = time.time() if _now is None else _now
    fh = os.path.join(root, ".git", "FETCH_HEAD")
    try:
        age = now - os.path.getmtime(fh)
    except OSError:
        age = every + 1                              # never fetched — do it once
    if age <= every:
        return False
    ok, _ = _git(root, "fetch", "--quiet")
    return ok


def _counts(root):
    """(behind, ahead) of HEAD vs its upstream, and the upstream's name — or
    (None, None, None) when there is no upstream to measure against."""
    ok, up = _git(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
    if not ok or not up:
        return None, None, None
    ok, lr = _git(root, "rev-list", "--left-right", "--count", "@{upstream}...HEAD")
    if not ok or "\t" not in lr:
        return None, None, up
    behind, ahead = lr.split("\t")[:2]
    try:
        return int(behind), int(ahead), up
    except ValueError:
        return None, None, up


def snapshot(root, fetch=False, _now=None):
    """Read the ground under `root`. `fetch=True` lets the reading self-throttle a
    remote refresh first (the slow-cadence background fetch). Returns a dict; the
    interesting keys are `branch`, `head`, `upstream`, `ahead`, `behind`, `dirty`,
    `untracked`, `detached`, `protected`, and `warnings` (the nag, gravest first)."""
    root = os.path.abspath(root)
    snap = {"folder": root, "repo": False, "warnings": []}
    if not is_repo(root):
        snap["warnings"] = [{"level": "warn", "text": "not a git repository — no bearings here"}]
        return snap
    snap["repo"] = True

    fetched = False
    if fetch:
        fetched = maybe_fetch(root, _now=_now)
    snap["fetched"] = fetched

    ok, branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    ok2, head = _git(root, "rev-parse", "--short", "HEAD")
    snap["head"] = head if ok2 else "?"
    detached = (branch == "HEAD")
    snap["detached"] = detached
    snap["branch"] = ("(detached %s)" % snap["head"]) if detached else branch
    snap["protected"] = (not detached) and (branch in PROTECTED)

    behind, ahead, up = _counts(root)
    snap["upstream"], snap["behind"], snap["ahead"] = up, behind, ahead

    ok, porc = _git(root, "status", "--porcelain")
    dirty = untracked = 0
    if ok and porc:
        for ln in porc.splitlines():
            if ln.startswith("??"):
                untracked += 1
            elif ln.strip():
                dirty += 1
    snap["dirty"], snap["untracked"] = dirty, untracked

    # --- THE NAG — gravest first, loud only when earned --------------------
    w = snap["warnings"]
    if detached:
        w.append({"level": "warn", "text": "detached HEAD — you are on no branch; a commit here is easy to lose"})
    if behind is not None and ahead is not None and behind > 0 and ahead > 0:
        w.append({"level": "warn", "text": "DIVERGED from %s — %d behind, %d ahead; reconcile before you push" % (up, behind, ahead)})
    elif behind and behind > 0:
        w.append({"level": "warn", "text": "%d behind %s — pull first, you are working on stale ground" % (behind, up)})
    if snap["protected"]:
        w.append({"level": "warn", "text": "on '%s' directly — the Charter says a change rides smith/<name>, not this" % branch})
    if dirty:
        w.append({"level": "warn", "text": "%d uncommitted change%s here — commit or stash before you move" % (dirty, "" if dirty == 1 else "s")})
    if up is None and not detached:
        w.append({"level": "note", "text": "branch '%s' has no upstream — nothing on GitHub tracks it yet" % branch})
    if ahead and ahead > 0 and not (behind and behind > 0):
        w.append({"level": "note", "text": "%d unpushed commit%s — GitHub has not seen this work" % (ahead, "" if ahead == 1 else "s")})
    if untracked:
        w.append({"level": "note", "text": "%d untracked file%s — not yet in git at all" % (untracked, "" if untracked == 1 else "s")})

    snap["alert"] = any(x["level"] == "warn" for x in w)
    return snap


def _sync_phrase(snap):
    up, behind, ahead = snap.get("upstream"), snap.get("behind"), snap.get("ahead")
    if not up:
        return "no upstream"
    if behind and ahead:
        return "diverged %d/%d" % (behind, ahead)
    if behind:
        return "%d behind" % behind
    if ahead:
        return "%d ahead" % ahead
    return "in sync"


def line(snap):
    """The one-breath 'hey — this is where you are working' readout."""
    if not snap.get("repo"):
        return "you are in %s — not a git repo" % snap["folder"]
    return "you are in %s · %s @ %s · %s%s" % (
        snap["folder"], snap["branch"], snap["head"], _sync_phrase(snap),
        (" · %d dirty" % snap["dirty"]) if snap.get("dirty") else " · clean")


def render(snap):
    """A small block for the sentinel dashboard — the readout plus the nag."""
    out = [line(snap)]
    for wmsg in snap.get("warnings", []):
        out.append(("  ! " if wmsg["level"] == "warn" else "  - ") + wmsg["text"])
    if snap.get("repo") and not snap.get("warnings"):
        out.append("  ok — right place, clean tree, in step with GitHub")
    return "\n".join(out)


def prove():
    """Prove Bearings reads the ground truthfully: a clean repo, a dirty tree, an
    untracked file, a protected branch, behind/ahead/diverged against a real (local,
    network-free) origin, and a detached HEAD — each state named on disk."""
    import shutil
    import tempfile
    strokes = []

    def check(name, ok, detail=""):
        strokes.append((name, bool(ok), detail))

    def g(root, *a):
        subprocess.run(["git"] + list(a), cwd=root, capture_output=True, text=True)

    tmp = tempfile.mkdtemp(prefix="bearings_")
    try:
        origin = os.path.join(tmp, "origin.git")
        work = os.path.join(tmp, "work")
        other = os.path.join(tmp, "other")
        g(tmp, "init", "--bare", origin)
        g(tmp, "clone", origin, work)
        for k, v in (("user.email", "t@t"), ("user.name", "t"), ("commit.gpgsign", "false")):
            g(work, "config", k, v)
        with open(os.path.join(work, "a.txt"), "w") as f:
            f.write("one\n")
        g(work, "add", "-A")
        g(work, "commit", "-m", "one")
        g(work, "branch", "-M", "main")
        g(work, "push", "-u", "origin", "main")
        g(origin, "symbolic-ref", "HEAD", "refs/heads/main")   # so later clones land on main

        s = snapshot(work)
        check("a clean, in-sync repo reads clean + no alert",
              s["repo"] and not s["dirty"] and s["ahead"] == 0 and s["behind"] == 0,
              line(s))
        check("on 'main' it raises the protected-branch nag",
              any("main" in x["text"] and "Charter" in x["text"] for x in s["warnings"]),
              _sync_phrase(s))

        # a tracked edit + an untracked file
        with open(os.path.join(work, "a.txt"), "a") as f:
            f.write("two\n")
        with open(os.path.join(work, "loose.txt"), "w") as f:
            f.write("x\n")
        s = snapshot(work)
        check("catches a DIRTY tree", s["dirty"] >= 1,
              next((x["text"] for x in s["warnings"] if "uncommitted" in x["text"]), ""))
        check("counts an UNTRACKED file", s["untracked"] >= 1, "")
        g(work, "checkout", "--", "a.txt")
        os.remove(os.path.join(work, "loose.txt"))

        # push a commit into origin from another clone -> we are BEHIND after fetch
        g(tmp, "clone", origin, other)
        for k, v in (("user.email", "t@t"), ("user.name", "t"), ("commit.gpgsign", "false")):
            g(other, "config", k, v)
        g(other, "checkout", "-B", "main", "origin/main")      # ensure it tracks origin/main
        with open(os.path.join(other, "b.txt"), "w") as f:
            f.write("remote\n")
        g(other, "add", "-A")
        g(other, "commit", "-m", "remote work")
        g(other, "push", "origin", "HEAD:main")
        g(work, "fetch", "--quiet")
        s = snapshot(work)
        check("sees it is BEHIND origin after a fetch",
              s["behind"] and s["behind"] >= 1,
              next((x["text"] for x in s["warnings"] if "behind" in x["text"]), ""))

        # our own local commit on top -> now DIVERGED (ahead and behind)
        with open(os.path.join(work, "c.txt"), "w") as f:
            f.write("local\n")
        g(work, "add", "-A")
        g(work, "commit", "-m", "local work")
        s = snapshot(work)
        check("names a DIVERGENCE (ahead AND behind)",
              s["ahead"] >= 1 and s["behind"] >= 1 and
              any("DIVERGED" in x["text"] for x in s["warnings"]),
              _sync_phrase(s))

        # a branch off the road: smith/<name> should NOT be protected
        g(work, "checkout", "-b", "smith/testtool")
        s = snapshot(work)
        check("a smith/<name> branch is NOT flagged protected", not s["protected"], s["branch"])

        # detached HEAD
        ok, sha = _git(work, "rev-parse", "HEAD")
        g(work, "checkout", sha)
        s = snapshot(work)
        check("catches a DETACHED HEAD", s["detached"] and
              any("detached" in x["text"].lower() for x in s["warnings"]), s["branch"])

        # maybe_fetch throttles: an immediate second call must NOT re-fetch
        g(work, "checkout", "smith/testtool")
        first = maybe_fetch(work, every=180)          # FETCH_HEAD is fresh from above
        check("maybe_fetch throttles on the slow cadence", first is False,
              "second fetch within the window was skipped")

        # non-repo ground is handled, not crashed
        plain = os.path.join(tmp, "plain")
        os.makedirs(plain)
        s = snapshot(plain)
        check("a non-repo folder is named, not crashed", s["repo"] is False, line(s))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return strokes


def main():
    root = os.path.abspath(os.sys.argv[1]) if len(os.sys.argv) > 1 else os.getcwd()
    print(render(snapshot(root, fetch=True)))
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main())

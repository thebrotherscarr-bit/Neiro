#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEWARD'S LIVE HAND — a small terminal that runs where the truth is.

It runs on YOUR disk, in YOUR repo, with YOUR credentials — the place a cloud
session cannot see. It does three plain things:

  * TELLS THE TRUTH  — the real branch, whether the tree is clean, what moved,
    what sits untracked, how you sit against GitHub. No guessing.
  * CARRIES WORK OUT  — stages, commits, and pushes to GitHub, but only on the
    word you type, and it shows you exactly what it will do first.
  * HANDS OFF A REPORT — one authoritative block (`report`) you can paste to a
    session so it works from your real files instead of a stale copy.

Nothing reaches GitHub unless you type `push` or `sync`. The hand is yours.

    python tools/live.py            # open the terminal
    python tools/live.py report     # print the ground-truth report and exit

Standard library only, plus git. Runs on Windows, macOS, Linux, WSL.
"""
import json
import os
import subprocess
import sys

for _s in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def git(*args, root=None):
    """Run git; return (returncode, stdout, stderr). Never raises."""
    try:
        r = subprocess.run(["git"] + list(args), cwd=root,
                           capture_output=True, text=True)
        return r.returncode, (r.stdout or "").rstrip("\n"), (r.stderr or "").strip()
    except (OSError, ValueError) as e:
        return 1, "", str(e)


def find_root():
    rc, out, _ = git("rev-parse", "--show-toplevel")
    return out if rc == 0 and out else None


def _ahead_behind(root):
    rc, up, _ = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}", root=root)
    if rc != 0 or not up:
        return None, None, None
    rc, lr, _ = git("rev-list", "--left-right", "--count", "@{upstream}...HEAD", root=root)
    if rc != 0 or "\t" not in lr:
        return None, None, up
    b, a = lr.split("\t")[:2]
    try:
        return int(b), int(a), up
    except ValueError:
        return None, None, up


def state(root):
    """Everything true about where we stand, gathered once."""
    rc, branch, _ = git("rev-parse", "--abbrev-ref", "HEAD", root=root)
    _, head, _ = git("rev-parse", "--short", "HEAD", root=root)
    behind, ahead, up = _ahead_behind(root)
    _, porc, _ = git("status", "--porcelain", root=root)
    dirty, untracked = [], []
    for ln in porc.splitlines():
        if ln.startswith("??"):
            untracked.append(ln[3:])
        elif ln.strip():
            dirty.append(ln.rstrip())
    _, remote, _ = git("config", "--get", "remote.origin.url", root=root)
    _, recent, _ = git("log", "-5", "--pretty=%h %s", root=root)
    return {"folder": root, "branch": branch, "head": head, "upstream": up,
            "ahead": ahead, "behind": behind, "dirty": dirty,
            "untracked": untracked, "remote": remote,
            "recent": recent.splitlines()}


def _sync_word(s):
    if not s["upstream"]:
        return "no upstream (branch not on GitHub yet)"
    b, a = s["behind"], s["ahead"]
    if b and a:
        return "DIVERGED — %d behind, %d ahead" % (b, a)
    if b:
        return "%d behind GitHub — pull first" % b
    if a:
        return "%d ahead — unpushed" % a
    return "in sync with GitHub"


def show_status(root):
    s = state(root)
    print("\n  you are in : %s" % s["folder"])
    print("  branch     : %s @ %s" % (s["branch"], s["head"]))
    print("  GitHub     : %s" % _sync_word(s))
    if s["remote"]:
        print("  remote     : %s" % s["remote"])
    if s["dirty"]:
        print("  uncommitted (%d):" % len(s["dirty"]))
        for d in s["dirty"][:20]:
            print("      %s" % d)
    if s["untracked"]:
        print("  untracked (%d):" % len(s["untracked"]))
        for u in s["untracked"][:20]:
            print("      %s" % u)
    if not s["dirty"] and not s["untracked"]:
        print("  tree       : clean")
    print("  last commits:")
    for ln in s["recent"]:
        print("      %s" % ln)
    print()


def report(root):
    """One authoritative block a session can trust. Structure, and file names —
    never file contents (use `show <path>` for a single file, deliberately)."""
    s = state(root)
    rc, tracked, _ = git("ls-files", root=root)
    s["tracked_files"] = tracked.splitlines()
    print("\n----- LIVE HAND REPORT (paste this to the session) -----")
    print(json.dumps(s, ensure_ascii=False, indent=2))
    print("----- END REPORT -----\n")


def confirm(prompt):
    try:
        return input("  %s [y/N] " % prompt).strip().lower() in ("y", "yes")
    except EOFError:
        return False


def do_push(root):
    s = state(root)
    if not s["upstream"]:
        print("  no upstream set. Pushing will create '%s' on GitHub." % s["branch"])
        if not confirm("push and set upstream origin/%s?" % s["branch"]):
            print("  held. nothing pushed.")
            return
        rc, out, err = git("push", "-u", "origin", s["branch"], root=root)
    else:
        if not confirm("push %d commit(s) to %s?" % (s["ahead"] or 0, s["upstream"])):
            print("  held. nothing pushed.")
            return
        rc, out, err = git("push", root=root)
    print("  " + (out or err or ("pushed." if rc == 0 else "push failed.")))


def do_commit(root, msg):
    if not msg:
        print("  usage: commit <message>")
        return
    rc, out, err = git("commit", "-m", msg, root=root)
    print("  " + (out or err))


def do_sync(root, msg):
    """The one-breath 'update GitHub': stage all, commit, push — each shown, each
    yours to confirm."""
    if not msg:
        print("  usage: sync <commit message>")
        return
    s = state(root)
    if not s["dirty"] and not s["untracked"]:
        print("  nothing to stage — tree is clean.")
    else:
        print("  will stage %d change(s) + %d untracked, commit as:" %
              (len(s["dirty"]), len(s["untracked"])))
        print('      "%s"' % msg)
        if not confirm("stage all and commit?"):
            print("  held. nothing staged.")
            return
        git("add", "-A", root=root)
        rc, out, err = git("commit", "-m", msg, root=root)
        print("  " + (out or err))
    do_push(root)


HELP = """
  commands (the hand acts only on what you type):
    status            where you are, cleanliness, sync with GitHub, last commits
    report            print the authoritative block to paste to a session
    tree              list tracked files (the real tree, not a guess)
    show <path>       print one file's contents (deliberate, one at a time)
    diff              show uncommitted changes
    fetch             refresh GitHub refs (read-only)
    pull              fast-forward from GitHub
    add <path>        stage a path   (add -A stages everything)
    commit <msg>      commit what is staged
    push              push commits to GitHub (asks first)
    sync <msg>        stage all + commit + push, in one (asks first)
    help              this list
    quit              close the hand
"""


def dispatch(root, line):
    parts = line.strip().split(maxsplit=1)
    if not parts:
        return True
    cmd, arg = parts[0].lower(), (parts[1] if len(parts) > 1 else "")
    if cmd in ("quit", "exit", "q"):
        return False
    elif cmd in ("status", "where", "st"):
        show_status(root)
    elif cmd == "report":
        report(root)
    elif cmd == "tree":
        rc, out, _ = git("ls-files", root=root)
        print(out or "  (no tracked files)")
    elif cmd == "show":
        p = os.path.join(root, arg)
        if arg and os.path.isfile(p):
            print(open(p, encoding="utf-8", errors="replace").read())
        else:
            print("  no such file: %s" % arg)
    elif cmd == "diff":
        rc, out, err = git("diff", root=root)
        print(out or err or "  (no uncommitted changes)")
    elif cmd == "fetch":
        rc, out, err = git("fetch", root=root)
        print("  " + (err or out or "fetched."))
    elif cmd == "pull":
        rc, out, err = git("pull", "--ff-only", root=root)
        print("  " + (out or err))
    elif cmd == "add":
        rc, out, err = git("add", *(arg.split() or ["-A"]), root=root)
        print("  " + (out or err or "staged."))
    elif cmd == "commit":
        do_commit(root, arg)
    elif cmd == "push":
        do_push(root)
    elif cmd == "sync":
        do_sync(root, arg)
    elif cmd in ("help", "?", "h"):
        print(HELP)
    else:
        print("  unknown: %s  (type 'help')" % cmd)
    return True


def main():
    root = find_root()
    if not root:
        print("  not inside a git repository. cd into the estate and try again.")
        return 2
    if len(sys.argv) > 1:                      # one-shot: `python tools/live.py report`
        dispatch(root, " ".join(sys.argv[1:]))
        return 0
    try:
        print("\n  STEWARD'S LIVE HAND — running where the truth is.")
        print("  the hand acts only on what you type. 'help' for commands, 'quit' to close.")
        show_status(root)
        while True:
            try:
                line = input("  hand> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not dispatch(root, line):
                break
        print("  the hand rests.\n")
    except BrokenPipeError:                    # output was piped somewhere that closed
        try:
            sys.stdout.close()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

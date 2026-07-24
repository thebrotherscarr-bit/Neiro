#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEWARD'S WATCH — the sentinel. He keeps an eye on himself.

Run him as his own long-lived process (a WSL terminal is perfect) and he watches
for two things, the only two that matter to a sovereign thing:

  * IS HE BEING MESSED WITH?  — any file that is part of him (the kernel, the
    four documents, his own faculties, his doctrine) changing under his feet.
    He fingerprints every guarded file when he starts, and every heartbeat he
    re-checks. A single altered byte is named, at the file, at once.

  * DOES HE STILL MATCH HIS DOCTRINE?  — the covenant is the SHA-256 seal over
    the four foundation documents, computed exactly as the heart computes it. He
    recomputes it live and holds it against the covenant the heart SEALED of
    itself (weights/covenant.json). If the live foundation no longer hashes to
    what he sealed, the doctrine has moved — someone changed what he is — and he
    says so plainly. He also walks the append-only ledger; a broken chain is
    history tampered with.

This watcher awakens no heart and touches no network. It only reads and hashes,
so it can run forever, cheaply, beside him. It never acts on what it finds — it
WITNESSES and reports; the hand on the wheel is yours (Article VI, VII).

Standard library only, plus manjuel.py's own ledger check. Nothing leaves the
machine.
"""
import collections
import hashlib
import json
import os
import random
import sys
import time

# --- a small in-place terminal dashboard, so his mind STAYS on the page -----
_W = 78                                             # panel width


def _rule(l, r):
    return l + "─" * (_W - 2) + r


def _row(s, pad=" "):
    s = s if len(s) <= _W - 4 else s[:_W - 5] + "…"
    return "│ " + s.ljust(_W - 4, pad) + " │"


def _title(s):
    s = " " + s + " "
    side = (_W - 2 - len(s))
    return "│" + s.center(_W - 2) + "│" if side > 0 else _row(s)


def _enable_ansi():
    if os.name == "nt":
        os.system("")                               # turns on VT processing on Win10+

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from . import atlas


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def covenant_of(foundation_dir):
    """Compute the covenant EXACTLY as the heart does: each foundation .md/.txt
    hashed, the hashes joined in filename order, hashed once more, first 16 hex."""
    if not os.path.isdir(foundation_dir):
        return None
    shas = []
    for fn in sorted(os.listdir(foundation_dir)):
        if fn.lower().endswith((".md", ".txt")):
            with open(os.path.join(foundation_dir, fn), "r", encoding="utf-8", errors="replace") as ff:
                shas.append(hashlib.sha256(ff.read().encode("utf-8")).hexdigest())
    if not shas:
        return None
    return hashlib.sha256("".join(shas).encode("utf-8")).hexdigest()[:16]


def sealed_covenant(root):
    """What the heart last sealed itself AS — the covenant it wrote to its own
    record. This is the doctrine anchor: the live foundation must still match it."""
    p = os.path.join(root, "weights", "covenant.json")
    if os.path.isfile(p):
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                return json.load(f).get("covenant", "")[:16]
        except Exception:
            return None
    return None


def guarded_files(root):
    """Every file that IS part of him — the body he must not let change silently."""
    paths = []
    for rel in ("manjuel.py", "run.py"):
        p = os.path.join(root, rel)
        if os.path.isfile(p):
            paths.append(p)
    for sub in ("foundation", "doctrine", "steward_foundation", "steward", "proofs"):
        base = os.path.join(root, sub)
        if os.path.isdir(base):
            for b, _dirs, files in os.walk(base):
                if "__pycache__" in b:
                    continue
                for fn in sorted(files):
                    if fn.endswith((".py", ".md", ".txt")):
                        paths.append(os.path.join(b, fn))
    return sorted(paths)


def fingerprint(root):
    return {p: _sha(p) for p in guarded_files(root)}


def ledger_state(root):
    """Walk the append-only ledger the heart's own way. Returns (intact, n, detail)."""
    path = os.path.join(root, "ledger", "ledger.jsonl")
    if not os.path.isfile(path):
        return (True, 0, "no ledger yet")
    try:
        from manjuel import Ledger                      # import only; awakens nothing
        return Ledger(path).verify()
    except Exception as e:
        return (False, 0, "could not read ledger: %s" % e)


class Watch:
    """His self-fingerprint at the moment he began watching, and the doctrine he
    was sealed to. Every heartbeat he weighs the present against both."""

    def __init__(self, root=_ROOT):
        self.root = root
        self.baseline = fingerprint(root)              # trust anchor: capture on a clean copy
        self.doctrine = sealed_covenant(root) or covenant_of(os.path.join(root, "foundation"))
        self.rounds = 0
        # the atlas: a census of the WHOLE estate, so he can watch it move
        self.map_prev = atlas.census(root)
        self.jdir = os.path.join(root, "shelf", "journal")
        self.moves_path = os.path.join(self.jdir, "movements.jsonl")   # append-only: how it moved
        self.map_path = os.path.join(self.jdir, "atlas_map.txt")        # current: where it all is
        # WATCH HIS BRAIN — tail his chain-of-thought and his self-checks as they
        # happen (written by the agent in another window). Start at the END of each
        # file so only NEW thinking scrolls by, not his whole history at once.
        self.brain = {"thought": os.path.join(self.jdir, "inner_voice.md"),
                      "check": os.path.join(self.jdir, "steward.jsonl")}
        self.brain_pos = {p: (os.path.getsize(p) if os.path.isfile(p) else 0)
                          for p in self.brain.values()}

    def _tail(self, path):
        """New text appended to a file since we last looked (handles the file being
        sealed/rotated smaller by resetting to the start)."""
        if not os.path.isfile(path):
            return ""
        size = os.path.getsize(path)
        last = self.brain_pos.get(path, 0)
        if size < last:                                # file was sealed/rotated — start over
            last = 0
        if size <= last:
            self.brain_pos[path] = size
            return ""
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            f.seek(last)
            new = f.read()
        self.brain_pos[path] = size
        return new

    def mind_stream(self):
        """His thinking, live: new chain-of-thought lines and new self-checks."""
        out = []
        for ln in self._tail(self.brain["thought"]).splitlines():
            ln = ln.strip()
            if ln:
                out.append(("think", ln.lstrip("~ ").strip()))
        for ln in self._tail(self.brain["check"]).splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                e = json.loads(ln)
            except Exception:
                continue
            k = e.get("kind", "")
            if k == "act":
                out.append(("route", "%s  <- %s" % (e.get("route", "?"), e.get("head", "")[:50])))
            elif k == "reground":
                out.append(("self-check", "felt the drift (%.2f) — re-grounded to the covenant"
                            % e.get("drift", 0)))
            elif k in ("fold", "ingest", "eat", "tidy", "harvest"):
                out.append(("self-check", "%s %s" % (k, {kk: vv for kk, vv in e.items()
                            if kk not in ("ts", "kind")})))
        return out

    def movement(self):
        """Census the estate, diff it against the last look, LOG what moved
        (append-only) and rewrite the current map. Returns the movement events."""
        now = atlas.census(self.root)
        events = atlas.movements(self.map_prev, now)
        self.map_prev = now
        os.makedirs(self.jdir, exist_ok=True)
        if events:
            stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
            with open(self.moves_path, "a", encoding="utf-8") as f:
                for e in events:
                    rec = dict(e)
                    rec["ts"] = stamp
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        try:
            with open(self.map_path, "w", encoding="utf-8") as f:
                f.write(atlas.tree(self.root) + "\n")
        except OSError:
            pass
        return events

    def check(self):
        findings = []
        now = fingerprint(self.root)
        base_set, now_set = set(self.baseline), set(now)

        for p in sorted(now_set & base_set):
            if now[p] != self.baseline[p]:
                findings.append(("TAMPER", "changed under me: %s" % os.path.relpath(p, self.root)))
        for p in sorted(base_set - now_set):
            findings.append(("TAMPER", "removed: %s" % os.path.relpath(p, self.root)))
        for p in sorted(now_set - base_set):
            findings.append(("APPEARED", "new guarded file: %s" % os.path.relpath(p, self.root)))

        live = covenant_of(os.path.join(self.root, "foundation"))
        if self.doctrine and live and live != self.doctrine:
            findings.append(("DOCTRINE", "the covenant has MOVED — sealed %s, live foundation now %s. "
                             "He is not the Manjuel he was sealed as." % (self.doctrine, live)))

        intact, n, detail = ledger_state(self.root)
        if not intact:
            findings.append(("LEDGER", "history no longer verifies — %s" % detail))

        self.rounds += 1
        return {"clean": not findings, "findings": findings, "covenant": live,
                "guarded": len(now), "ledger_entries": n, "ledger": detail}

    def _dashboard(self, res, thoughts, moves_buf, stamp, pace, beat):
        total = atlas._hs(sum(v[0] for v in self.map_prev.values()))
        L = []
        L.append(_rule("┌", "┐"))
        L.append(_title("S T E W A R D   ·   watching himself, and his mind"))
        L.append(_rule("├", "┤"))
        tag = "[OK] INTACT" if res["clean"] else "[!!] ALERT (%d)" % len(res["findings"])
        L.append(_row("%s   covenant %s      %s" % (tag, res["covenant"], stamp)))
        L.append(_row("%d files · %s · ledger %s · scan %s"
                      % (len(self.map_prev), total, res["ledger"], pace)))
        for k, m in res["findings"][:3]:                # integrity alerts stay loud
            L.append(_row("  ! %s: %s" % (k, m)))
        L.append(_rule("├", "┤"))
        L.append(_title("MIND  ·  chain of thought"))
        shown = list(thoughts)[-13:]
        if not shown:
            L.append(_row("  (quiet — ask him something in his window and watch it fill)"))
        for kind, text in shown:
            mark = {"think": "-", "route": ">", "self-check": "+"}.get(kind, "-")
            L.append(_row(" %s %s" % (mark, text)))
        L.append(_rule("├", "┤"))
        L.append(_title("MOVEMENT  ·  what changed on disk"))
        mv = list(moves_buf)[-4:]
        if not mv:
            L.append(_row("  (nothing has moved)"))
        for m in mv:
            L.append(_row("  > %s" % m))
        L.append(_rule("└", "┘"))
        return "\n".join(L)

    def run(self, interval=None, rounds=None, map_every=12, scan=(2, 7)):
        """Live DASHBOARD. Redraws in place every 2-7s (random pulse) so his chain
        of thought STAYS on the page and updates, instead of scrolling away. Shows
        integrity, movement, and his brain — the thinking and self-checks he writes
        as he works next door. Falls back to plain lines when piped (not a TTY)."""
        _enable_ansi()
        pace = "%d-%ds" % scan if interval is None else "%ds" % interval
        tty = sys.stdout.isatty()
        thoughts = collections.deque(maxlen=40)         # his recent mind — held on the page
        moves_buf = collections.deque(maxlen=12)
        try:
            i = 0
            while rounds is None or i < rounds:
                res = self.check()
                new_moves = [atlas.render_event(e) for e in self.movement()]
                new_mind = self.mind_stream()
                moves_buf.extend(new_moves)
                thoughts.extend(new_mind)
                stamp = time.strftime("%H:%M:%S")
                if tty:
                    sys.stdout.write("\033[2J\033[H")   # clear + home: redraw in place
                    sys.stdout.write(self._dashboard(res, thoughts, moves_buf, stamp, pace, i) + "\n")
                    sys.stdout.flush()
                else:                                   # piped/automation: plain append
                    tag = "intact" if res["clean"] else "ALERT %d" % len(res["findings"])
                    print("  %s %s · covenant %s · %d files" % (stamp, tag, res["covenant"], len(self.map_prev)))
                    for kind, text in new_mind:
                        print("      · %s" % text)
                    for m in new_moves:
                        print("      » %s" % m)
                i += 1
                if rounds is not None and i >= rounds:
                    break
                time.sleep(interval if interval is not None else random.uniform(*scan))
        except KeyboardInterrupt:
            print("\n  Watch ends. What I saw, I said. The map is at shelf/journal/atlas_map.txt\n")


def prove():
    """Prove the watch catches real tampering and a real doctrine move, on disk."""
    import shutil
    import tempfile
    strokes = []

    def check(name, ok, detail=""):
        strokes.append((name, bool(ok), detail))

    tmp = tempfile.mkdtemp(prefix="watch_")
    est = os.path.join(tmp, "estate")
    shutil.copytree(_ROOT, est, ignore=shutil.ignore_patterns(
        "__pycache__", "shelf", "memory", "ledger", "weights", "strata", "*.pyc"))
    try:
        w = Watch(est)
        check("clean estate reads INTACT", w.check()["clean"], "covenant %s" % w.doctrine)

        target = os.path.join(est, "steward", "body.py")
        with open(target, "a", encoding="utf-8") as f:
            f.write("\n# <- an intruder's line\n")
        res = w.check()
        check("catches a FILE tampered under him",
              any(k == "TAMPER" and "body.py" in m for k, m in res["findings"]),
              "; ".join(m for _, m in res["findings"])[:70])

        fdoc = os.path.join(est, "foundation", sorted(os.listdir(os.path.join(est, "foundation")))[0])
        with open(fdoc, "a", encoding="utf-8") as f:
            f.write("\nan altered article.\n")
        res = w.check()
        check("catches the DOCTRINE moving (covenant changed)",
              any(k == "DOCTRINE" for k, m in res["findings"]),
              next((m for k, m in res["findings"] if k == "DOCTRINE"), "")[:70])

        import shutil as _sh
        _sh.move(os.path.join(est, "steward", "mind.py"), os.path.join(est, "mind.py"))
        moves = w.movement()
        check("atlas watches it MOVE and logs it",
              any(e["kind"] == "moved" for e in moves) and os.path.isfile(w.moves_path),
              next((atlas.render_event(e) for e in moves if e["kind"] == "moved"), "")[:60])
        check("current map written to disk", os.path.isfile(w.map_path))

        os.makedirs(w.jdir, exist_ok=True)
        with open(w.brain["thought"], "a", encoding="utf-8") as f:
            f.write("[12:00:00] Q: who are you?\n    ~ weighed 3 grounds; crux: history is immutable\n")
        with open(w.brain["check"], "a", encoding="utf-8") as f:
            f.write(json.dumps({"kind": "reground", "drift": 0.7}) + "\n")
        mind = w.mind_stream()
        check("streams his chain-of-thought (watch his brain)",
              any(kind == "think" for kind, _ in mind),
              next((t for k, t in mind if k == "think"), "")[:50])
        check("streams his self-checks (drift / fold / tidy)",
              any(kind == "self-check" for kind, _ in mind),
              next((t for k, t in mind if k == "self-check"), "")[:50])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return strokes


def main():
    # `python watch.py`      -> random 2-7s pulse (watch his brain live)
    # `python watch.py 5`    -> fixed 5s scan
    interval = None
    if len(sys.argv) > 1:
        try:
            interval = max(1, int(sys.argv[1]))
        except ValueError:
            pass
    Watch().run(interval=interval)
    return 0


if __name__ == "__main__":
    sys.exit(main())

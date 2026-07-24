#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEWARD'S MISSION — real work, carried out step by step.

His hands do one act. A MISSION is a job of many acts: he takes a goal, plans it
into ordered steps, performs each with his own hands and faculties, reports what
happened at every step, and STOPS the moment one fails rather than blundering on.
Creed VII — leave the World healthier than found — and every step is journaled
(Article IV). Nothing that MODIFIES the World runs on a guess: an organize is a
PREVIEW first, and only moves files when the operator says "now" (Article VI, VII).

Three ways a mission is planned:

  * A LIST — "do this, then that, then the other" / numbered / semicolon-separated.
    Each clause is a step, run through his ordinary action layer in order.
  * ORGANIZE <folder> — he surveys the folder, groups files by kind, and (on
    confirmation) MOVES each into a subfolder. Files are relocated, never deleted.
  * AUDIT <folder> — read-only: he walks it, measures every file, and reports what
    is there and anything that stands out. He touches nothing.

The step runner is injected (his own `act`), so this file orchestrates work
without reaching back into the agent. Standard library only.
"""
import os
import re
import shutil
import time

_GROUPS = {
    "docs": (".md", ".markdown", ".txt", ".pdf", ".doc", ".docx", ".rtf", ".odt", ".rst", ".tex"),
    "code": (".py", ".js", ".ts", ".java", ".c", ".h", ".cpp", ".hpp", ".cs", ".go", ".rs",
             ".rb", ".php", ".sh", ".bat", ".command", ".sql", ".html", ".css", ".lua"),
    "data": (".json", ".jsonl", ".csv", ".tsv", ".xml", ".yaml", ".yml", ".xlsx", ".xls", ".db"),
    "images": (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".webp", ".ico", ".tif"),
    "archives": (".zip", ".tar", ".gz", ".tgz", ".7z", ".rar", ".bz2"),
    "media": (".mp3", ".wav", ".mp4", ".mov", ".avi", ".mkv", ".flac"),
}
_FAILS = ("could not", "refused", "i can't", "i can not", "no file", "not a folder",
          "i heard the command", "nothing there", "that is not")


def _group(fn):
    ext = os.path.splitext(fn)[1].lower()
    for g, exts in _GROUPS.items():
        if ext in exts:
            return g
    return "other"


def _split_steps(g):
    """Break a compound instruction into ordered steps."""
    numbered = re.split(r"(?:^|\s)\d+[\.\)]\s+", g)
    numbered = [p.strip() for p in numbered if p.strip()]
    if len(numbered) > 1:
        return numbered
    parts = re.split(r"\s*(?:;|\n|\bthen\b|,\s*and\s+then\b|,\s*then\b)\s*", g, flags=re.I)
    parts = [p.strip(" .,") for p in parts if p.strip(" .,")]
    return parts


def plan(goal):
    """Turn a goal into a plan: a known compound job, or a list of steps."""
    g = (goal or "").strip()
    g = re.sub(r"^\s*(?:do (?:the following|these steps?)\s*:?\s*)", "", g, flags=re.I)
    m = re.match(r"^(?:organize|sort|tidy up)\s+(.+)$", g, re.I)
    if m:
        tgt = m.group(1).strip().strip('"').strip("'")
        now = bool(re.search(r"\b(now|apply|for real|do it)\b|!$", tgt, re.I))
        tgt = re.sub(r"\s*\b(now|apply|for real|do it)\b|!$", "", tgt, flags=re.I).strip()
        return {"goal": g, "kind": "organize", "target": tgt, "apply": now}
    m = re.match(r"^(?:audit|inspect|report on|check)\s+(.+)$", g, re.I)
    if m and os.path.isdir(m.group(1).strip().strip('"').strip("'")):
        return {"goal": g, "kind": "audit", "target": m.group(1).strip().strip('"').strip("'")}
    steps = _split_steps(g)
    return {"goal": g, "kind": "list", "steps": steps}


def organize(target, apply=False):
    """Survey a folder and group its files by kind. Preview by default; only MOVES
    when apply=True. Files are relocated into subfolders, never deleted."""
    if not os.path.isdir(target):
        return {"kind": "organize", "ok": False, "said": "not a folder: %s" % target}
    files = [f for f in sorted(os.listdir(target))
             if os.path.isfile(os.path.join(target, f))]
    plan_moves = {}
    for f in files:
        g = _group(f)
        plan_moves.setdefault(g, []).append(f)
    lines, moved = [], 0
    for g in sorted(plan_moves):
        lines.append("  %s/  (%d)" % (g, len(plan_moves[g])))
        if apply:
            dest = os.path.join(target, g)
            os.makedirs(dest, exist_ok=True)
            for f in plan_moves[g]:
                src, dst = os.path.join(target, f), os.path.join(dest, f)
                if os.path.abspath(src) == os.path.abspath(dst):
                    continue
                if not os.path.exists(dst):
                    shutil.move(src, dst)
                    moved += 1
    head = ("organized %d file(s) into %d group(s):" % (moved, len(plan_moves))) if apply \
        else ("PREVIEW — %d file(s) would sort into %d group(s) (say 'organize %s now' to do it):"
              % (len(files), len(plan_moves), target))
    return {"kind": "organize", "ok": True, "apply": apply, "moved": moved,
            "said": head + "\n" + "\n".join(lines)}


def audit(target):
    """Read-only: walk a folder, measure everything, report what stands out."""
    if not os.path.isdir(target):
        return {"kind": "audit", "ok": False, "said": "not a folder: %s" % target}
    n, total, by_group, empties, big = 0, 0, {}, [], []
    for base, _dirs, files in os.walk(target):
        for f in files:
            p = os.path.join(base, f)
            try:
                sz = os.path.getsize(p)
            except OSError:
                continue
            n += 1
            total += sz
            by_group[_group(f)] = by_group.get(_group(f), 0) + 1
            if sz == 0:
                empties.append(os.path.relpath(p, target))
            if sz > 25 * 1024 * 1024:
                big.append((os.path.relpath(p, target), sz))
    parts = ["  %d files · %.1f MB total" % (n, total / 1048576.0),
             "  by kind: " + ", ".join("%s %d" % (g, c) for g, c in sorted(by_group.items()))]
    if empties:
        parts.append("  %d empty file(s): %s" % (len(empties), ", ".join(empties[:5])))
    if big:
        parts.append("  %d large file(s) (>25MB): %s" % (len(big), ", ".join(p for p, _ in big[:5])))
    if not empties and not big:
        parts.append("  nothing unusual — no empties, nothing oversized.")
    return {"kind": "audit", "ok": True, "said": "audit of %s:\n%s" % (target, "\n".join(parts))}


def run(goal, runner, journal_write=None):
    """Carry out a mission. `runner(step)` performs one step (his action layer) and
    returns what it said. Returns the full report; halts at the first failed step."""
    p = plan(goal)
    if journal_write:
        journal_write("mission", goal=goal[:80], job=p["kind"])

    if p["kind"] == "organize":
        r = organize(p["target"], apply=p.get("apply", False))
        return {"goal": goal, "kind": "organize", "done": r["ok"], "report": r["said"]}
    if p["kind"] == "audit":
        r = audit(p["target"])
        return {"goal": goal, "kind": "audit", "done": r["ok"], "report": r["said"]}

    steps, results = p["steps"], []
    for i, step in enumerate(steps, 1):
        said = runner(step) or ""
        ok = not any(said.strip().lower().startswith(b) for b in _FAILS)
        results.append({"n": i, "step": step, "ok": ok, "said": said})
        if journal_write:
            journal_write("mission_step", n=i, step=step[:60], ok=ok)
        if not ok:
            break
    done = bool(results) and all(r["ok"] for r in results)
    report = "\n".join("  %d. %s\n     -> %s" % (r["n"], r["step"],
                       (r["said"].splitlines() or [""])[0][:100]) for r in results)
    if not done and results:
        report += "\n  (stopped at step %d — a step failed; I do not blunder on.)" % results[-1]["n"]
    return {"goal": goal, "kind": "list", "done": done, "steps": len(steps),
            "ran": len(results), "report": report}


def prove():
    import tempfile
    strokes = []

    def check(name, ok, detail=""):
        strokes.append((name, bool(ok), detail))

    # --- a real multi-step LIST mission, run through a stub action layer ---
    d = tempfile.mkdtemp(prefix="mission_")
    try:
        done_calls = []

        def runner(step):
            done_calls.append(step)
            if step.startswith("write"):
                _, rest = step.split(" ", 1)
                path, content = rest.split("=>", 1)
                with open(os.path.join(d, path.strip()), "w") as f:
                    f.write(content.strip())
                return "wrote %s" % path.strip()
            if step.startswith("read"):
                p = os.path.join(d, step.split(" ", 1)[1].strip())
                return "read: " + (open(p).read() if os.path.isfile(p) else "could not find it")
            if step.startswith("fail"):
                return "could not do that"
            return "did: " + step

        res = run("write note.txt => hello then read note.txt then say done", runner)
        check("plans a LIST into ordered steps", res["steps"] == 3, "%d steps" % res["steps"])
        check("executes every step in order", len(done_calls) == 3 and res["done"],
              "ran %d, done=%s" % (res["ran"], res["done"]))
        check("a step really happened (file written+read)",
              os.path.isfile(os.path.join(d, "note.txt")), "note.txt exists")

        # HALTS on a failing step — does not blunder on
        res2 = run("read note.txt then fail here then read note.txt", runner)
        check("STOPS at the first failed step", res2["ran"] == 2 and not res2["done"],
              "ran %d of 3" % res2["ran"])

        # --- ORGANIZE: preview, then apply, on a real messy folder ---
        shelf = tempfile.mkdtemp(prefix="messy_")
        for f in ["report.md", "notes.txt", "script.py", "data.json", "photo.png", "readme"]:
            open(os.path.join(shelf, f), "w").write("x")
        prev = organize(shelf, apply=False)
        check("ORGANIZE previews without moving anything",
              prev["ok"] and os.path.isfile(os.path.join(shelf, "script.py")) and prev["moved"] == 0
              if "moved" in prev else True, "preview only")
        appl = organize(shelf, apply=True)
        check("ORGANIZE moves files into kind-folders on apply",
              os.path.isfile(os.path.join(shelf, "code", "script.py"))
              and os.path.isfile(os.path.join(shelf, "docs", "report.md"))
              and os.path.isfile(os.path.join(shelf, "data", "data.json")),
              "%d moved" % appl["moved"])
        check("ORGANIZE never deletes (files relocated, not lost)",
              not os.path.isfile(os.path.join(shelf, "script.py"))
              and os.path.isfile(os.path.join(shelf, "code", "script.py")), "relocated")
        shutil.rmtree(shelf, ignore_errors=True)

        # --- AUDIT: read-only report ---
        a = tempfile.mkdtemp(prefix="audit_")
        open(os.path.join(a, "a.txt"), "w").write("content")
        open(os.path.join(a, "empty.txt"), "w").write("")
        rep = audit(a)
        check("AUDIT reports files, sizes, and flags empties",
              rep["ok"] and "empty" in rep["said"] and "2 files" in rep["said"], "read-only report")
        shutil.rmtree(a, ignore_errors=True)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    return strokes


def main():
    print("\n  STEWARD'S MISSION — real work, step by step: plan, perform, report, halt on failure.\n")
    strokes = prove()
    width = max(len(n) for n, _, _ in strokes)
    all_ok = all(o for _, o, _ in strokes)
    for name, ok, detail in strokes:
        print("    [%s]  %-*s   %s" % ("PASS" if ok else "FAIL", width, name, detail))
    print()
    print("  " + ("PROVEN. He carries out a multi-step job and stops the moment one step fails."
                  if all_ok else "A step failed. He does not claim what he cannot show.") + "\n")
    return 0 if all_ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

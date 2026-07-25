# skill: inspect — property inspection log with tamper-evident hash chain
"""The verification layer, in the Forge's shape. Each inspection entry is
appended to a hash-chained JSONL log: property, checklist results, notes,
timestamp, and the SHA-256 of the previous entry. 'verify' walks the whole
chain; a single altered byte is named at its entry. 'report <property>'
reads back everything on file for a property."""
import hashlib
import json
import os
import time


def _path(base=None):
    if base is None:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        base = os.path.join(root, "shelf", "ops")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "inspections.jsonl")


def _last_hash(path):
    prev = "0" * 64
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    prev = json.loads(line)["hash"]
    return prev


HELP = ("commands:  log <property> | item=result ; item=result ... | <notes>\n"
        "           report <property>   ·   verify")


def run(arg, base=None):
    path = _path(base)
    parts = [p.strip() for p in str(arg or "").split("|")]
    head = parts[0].split()
    cmd = head[0].lower() if head else ""
    rest = parts[0][len(cmd):].strip()

    if cmd == "log":
        if not rest or len(parts) < 2:
            return "log needs:  log <property> | item=result ; item=result [| notes]"
        checks = {}
        for item in parts[1].split(";"):
            if "=" in item:
                k, v = item.split("=", 1)
                checks[k.strip()] = v.strip()
        prev = _last_hash(path)
        body = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "property": rest,
                "checks": checks, "notes": parts[2] if len(parts) > 2 else "",
                "prev": prev}
        body["hash"] = hashlib.sha256(
            (prev + json.dumps({k: body[k] for k in ("ts", "property", "checks", "notes")},
                               sort_keys=True)).encode("utf-8")).hexdigest()
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(body, ensure_ascii=False) + "\n")
        fails = [k for k, v in checks.items() if v.lower() in ("fail", "failed", "no")]
        return ("inspection logged for %s — %d item(s), %s. entry sealed at %s"
                % (rest, len(checks),
                   ("%d FAILED: %s" % (len(fails), ", ".join(fails))) if fails else "all pass",
                   body["hash"][:12]))

    if cmd == "report":
        if not os.path.isfile(path):
            return "no inspections on file."
        out = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                e = json.loads(line)
                if rest and rest.lower() not in e["property"].lower():
                    continue
                marks = ", ".join("%s: %s" % kv for kv in e["checks"].items())
                out.append("%s  %s — %s%s  [%s]"
                           % (e["ts"], e["property"], marks,
                              (" · " + e["notes"]) if e["notes"] else "", e["hash"][:12]))
        return "\n".join(out) or ("nothing on file for '%s'." % rest)

    if cmd == "verify":
        if not os.path.isfile(path):
            return "inspection chain intact (0 entries)"
        prev, n = "0" * 64, 0
        with open(path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                e = json.loads(line)
                want = hashlib.sha256(
                    (prev + json.dumps({k: e[k] for k in ("ts", "property", "checks", "notes")},
                                       sort_keys=True)).encode("utf-8")).hexdigest()
                if e.get("prev") != prev or e.get("hash") != want:
                    return "inspection chain BROKEN at entry %d (%s)" % (n, e.get("property", "?"))
                prev = e["hash"]
                n += 1
        return "inspection chain intact (%d entries)" % n

    return HELP


def describe():
    return "inspection log: log/report/verify — tamper-evident hash chain per entry"


def prove():
    import shutil
    import tempfile
    d = tempfile.mkdtemp(prefix="insp_")
    try:
        r = run("log Red Rock Loop | water heater=pass ; drip zone 3=fail ; smoke detectors=pass | javelina bent the gate", d)
        ok = "1 FAILED: drip zone 3" in r and "sealed" in r
        ok = ok and "all pass" in run("log Juniper Ridge casita | swamp cooler=pass", d)
        rep = run("report red rock", d)
        ok = ok and "javelina" in rep and "Juniper" not in rep
        ok = ok and "intact (2 entries)" in run("verify", d)
        p = _path(d)
        lines = open(p, encoding="utf-8").readlines()
        lines[0] = lines[0].replace("fail", "pass")      # quietly flip a result
        open(p, "w", encoding="utf-8").writelines(lines)
        ok = ok and "BROKEN at entry 0" in run("verify", d)
        return bool(ok)
    finally:
        shutil.rmtree(d, ignore_errors=True)

# skill: workorder — co-hosting maintenance work orders (sqlite + hash-chained audit)
"""A work-order tracker in the Forge's shape: run(arg) does the work, prove()
tests itself. State lives under the estate's shelf/ops/, so every invocation
(each its own child process) reads and writes the same book. Every mutation is
also appended to a hash-chained audit log, Manjuel-style: tamper with one line
and 'verify' names the break."""
import hashlib
import json
import os
import sqlite3
import time


def _base(base=None):
    if base is None:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        base = os.path.join(root, "shelf", "ops")
    os.makedirs(base, exist_ok=True)
    return base


def _db(base):
    con = sqlite3.connect(os.path.join(base, "workorders.db"))
    con.execute("CREATE TABLE IF NOT EXISTS wo ("
                "id INTEGER PRIMARY KEY, property TEXT, issue TEXT, vendor TEXT,"
                "status TEXT, cost REAL, opened TEXT, closed TEXT)")
    return con


def _audit(base, event):
    path = os.path.join(base, "workorders_audit.jsonl")
    prev = "0" * 64
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    prev = json.loads(line)["hash"]
    body = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "event": event, "prev": prev}
    body["hash"] = hashlib.sha256(
        (prev + json.dumps(event, sort_keys=True)).encode("utf-8")).hexdigest()
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(body, ensure_ascii=False) + "\n")


def _verify(base):
    path = os.path.join(base, "workorders_audit.jsonl")
    if not os.path.isfile(path):
        return "audit chain intact (0 entries)"
    prev, n = "0" * 64, 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            e = json.loads(line)
            want = hashlib.sha256(
                (prev + json.dumps(e["event"], sort_keys=True)).encode("utf-8")).hexdigest()
            if e.get("prev") != prev or e.get("hash") != want:
                return "audit chain BROKEN at entry %d" % n
            prev = e["hash"]
            n += 1
    return "audit chain intact (%d entries)" % n


HELP = ("commands:  add <property> | <issue> | <vendor>   ·   assign <id> | <vendor>\n"
        "           done <id> | <cost>   ·   list [open|done|all]   ·   verify")


def run(arg, base=None):
    base = _base(base)
    parts = [p.strip() for p in str(arg or "").split("|")]
    head = parts[0].split()
    cmd = head[0].lower() if head else ""
    rest = parts[0][len(cmd):].strip()
    con = _db(base)
    try:
        if cmd == "add":
            issue = parts[1] if len(parts) > 1 else ""
            vendor = parts[2] if len(parts) > 2 else ""
            if not rest or not issue:
                return "add needs:  add <property> | <issue> [| <vendor>]"
            cur = con.execute(
                "INSERT INTO wo (property,issue,vendor,status,cost,opened,closed) "
                "VALUES (?,?,?,?,?,?,?)",
                (rest, issue, vendor, "open", 0.0, time.strftime("%Y-%m-%d"), ""))
            con.commit()
            _audit(base, {"op": "add", "id": cur.lastrowid, "property": rest,
                          "issue": issue, "vendor": vendor})
            return ("opened work order #%d: %s — %s (vendor: %s)"
                    % (cur.lastrowid, rest, issue, vendor or "unassigned"))
        if cmd == "assign":
            wid, vendor = int(rest), (parts[1] if len(parts) > 1 else "")
            con.execute("UPDATE wo SET vendor=? WHERE id=?", (vendor, wid))
            con.commit()
            _audit(base, {"op": "assign", "id": wid, "vendor": vendor})
            return "work order #%d assigned to %s" % (wid, vendor)
        if cmd == "done":
            wid = int(rest)
            cost = float(parts[1]) if len(parts) > 1 else 0.0
            con.execute("UPDATE wo SET status='done', cost=?, closed=? WHERE id=?",
                        (cost, time.strftime("%Y-%m-%d"), wid))
            con.commit()
            _audit(base, {"op": "done", "id": wid, "cost": cost})
            return "work order #%d closed at $%.2f" % (wid, cost)
        if cmd == "list":
            want = rest.lower() or "open"
            q = "SELECT id,property,issue,vendor,status,cost FROM wo"
            if want in ("open", "done"):
                q += " WHERE status='%s'" % want
            rows = con.execute(q + " ORDER BY id").fetchall()
            if not rows:
                return "no %s work orders." % want
            return "\n".join("#%d [%s] %s — %s (vendor: %s, $%.2f)"
                             % (r[0], r[4], r[1], r[2], r[3] or "unassigned", r[5])
                             for r in rows)
        if cmd == "verify":
            return _verify(base)
        return HELP
    finally:
        con.close()


def describe():
    return "work-order tracker: add/assign/done/list/verify — sqlite + hash-chained audit"


def prove():
    import shutil
    import tempfile
    d = tempfile.mkdtemp(prefix="wo_")
    try:
        ok = "#1" in run("add Juniper Ridge casita | swamp cooler pads worn | Dale", d)
        ok = ok and "#2" in run("add Red Rock Loop | gate hinge javelina damage", d)
        ok = ok and "Marco" in run("assign 2 | Marco", d)
        ok = ok and "closed at $300.00" in run("done 1 | 300", d)
        listing = run("list open", d)
        ok = ok and "#2" in listing and "#1" not in listing
        ok = ok and "closed" not in run("list open", d)
        ok = ok and "intact (4 entries)" in run("verify", d)
        # tamper with the audit -> verify must name the break
        p = os.path.join(d, "workorders_audit.jsonl")
        lines = open(p, encoding="utf-8").readlines()
        lines[1] = lines[1].replace("javelina", "coyote")
        open(p, "w", encoding="utf-8").writelines(lines)
        ok = ok and "BROKEN" in run("verify", d)
        return bool(ok)
    finally:
        shutil.rmtree(d, ignore_errors=True)

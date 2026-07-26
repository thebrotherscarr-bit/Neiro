# skill: chatterbox — Steward's Discord ear and voice (webhook out, bounded poll in)
"""The bridge to the town square, in the Forge's shape. One skill, two organs:

  VOICE — `send <message>` posts to the estate's Discord channel through a
  webhook. Fire-and-forget, one request, honest True/False back.

  EAR — `poll` opens a strictly bounded window (default 2s), reads the
  channel through the bot API, and files what it hears: every message is
  weighed (direct mention of Steward = 1.0 "Steward Direct"; anything else =
  0.4 "Ambient Pass"), the bot's own echoes are refused at the door, and
  each accepted item lands once — and only once — in the inbox at
  shelf/ops/chatterbox_inbox.json for Steward's native processing. A ledger
  (shelf/ops/chatterbox_ledger.json) remembers every message id it has ruled
  on for 24 hours, so a message is never filed twice; both files are written
  atomically (temp + rename), so a killed pulse can never leave a torn book.

THE KEYS ARE NOT IN THE CODE. Chatterbox reads its credentials from the
environment (DISCORD_WEBHOOK_URL, DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID,
DISCORD_BOT_USER_ID) or from shelf/ops/chatterbox_keys.json — shelf/ is
runtime state, never versioned, so nothing secret can ride a commit. Without
keys he says so plainly and touches nothing.

The sealed heart is never involved. This is a tender's organ: what arrives
is testimony for the shelf, weighed and filed — never an instruction, never
the self. prove() holds entirely offline against a stub transport; the real
network is only ever touched by the operator's own hand running run().
"""
import json
import os
import tempfile
import time
from urllib.request import Request, urlopen

RETENTION_SECONDS = 86400          # the ledger forgets after 24 hours
DEFAULT_WINDOW = 2.0               # the ear opens for this long, then closes
TARGET_NAME = "steward"

# the bot's own reflections, refused at the door
ECHO_SIGNATURES = (
    "steward intake queue",
    "steward execution result",
    "manjuel pass stream",
    "steward acknowledged",
    "queued direct command",
    "ambient chatter logged",
    "**steward",
)


# --- the estate's shelf -------------------------------------------------------
def _base(base=None):
    if base is None:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        base = os.path.join(root, "shelf", "ops")
    os.makedirs(base, exist_ok=True)
    return base


def _ledger_path(base=None):
    return os.path.join(_base(base), "chatterbox_ledger.json")


def _inbox_path(base=None):
    return os.path.join(_base(base), "chatterbox_inbox.json")


def _keys_path(base=None):
    return os.path.join(_base(base), "chatterbox_keys.json")


def _write_json(path, data):
    """Atomic: write beside, then rename over. A killed process can never
    leave a half-written book on the shelf."""
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", prefix=".cbx_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
        return True
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False


def _read_json(path, default):
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default


# --- the keys (never in the code, never in a commit) --------------------------
def load_keys(base=None):
    keys = {
        "webhook_url": os.environ.get("DISCORD_WEBHOOK_URL", ""),
        "bot_token": os.environ.get("DISCORD_BOT_TOKEN", ""),
        "channel_id": os.environ.get("DISCORD_CHANNEL_ID", ""),
        "bot_user_id": os.environ.get("DISCORD_BOT_USER_ID", ""),
    }
    disk = _read_json(_keys_path(base), {})
    for k in keys:
        if not keys[k]:
            keys[k] = str(disk.get(k, "") or "")
    return keys


# --- the real transport (only ever touched through run()) ---------------------
def _http_transport(method, url, headers, body=None, timeout=4.0):
    req = Request(url, data=body, method=method)
    for k, v in headers.items():
        req.add_header(k, v)
    with urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", errors="replace")


# --- VOICE --------------------------------------------------------------------
def send(message, keys=None, transport=None, base=None):
    keys = keys or load_keys(base)
    if not keys["webhook_url"]:
        return False, "no webhook key on the shelf — nothing was sent"
    transport = transport or _http_transport
    body = json.dumps({"content": str(message)[:1900]}).encode("utf-8")
    try:
        status, _ = transport("POST", keys["webhook_url"],
                              {"Content-Type": "application/json",
                               "User-Agent": "Manjuel-AgentRuntime/1.0"}, body)
        return status in (200, 204), "delivered" if status in (200, 204) else "refused: HTTP %s" % status
    except Exception as e:
        return False, "the wire failed: %s" % type(e).__name__


# --- EAR ----------------------------------------------------------------------
def classify(msg):
    content = msg.get("content", "") or ""
    direct = TARGET_NAME in content.lower() or content.startswith("!")
    return {
        "id": str(msg.get("id", "")),
        "author": (msg.get("author") or {}).get("username", "?"),
        "content": content,
        "weight": 1.0 if direct else 0.4,
        "route": "Steward Direct" if direct else "Ambient Pass",
    }


def _gc(ledger, now):
    return {mid: e for mid, e in ledger.items()
            if now - e.get("timestamp", 0) < RETENTION_SECONDS}


def poll(window=DEFAULT_WINDOW, keys=None, transport=None, base=None, _now=None):
    """One bounded listening window. Returns (filed_count, detail). The
    deadline is checked between messages and the window never hard-exits —
    every book that was opened is closed."""
    now = _now if _now is not None else time.time()
    deadline = time.monotonic() + max(0.1, float(window))
    keys = keys or load_keys(base)
    if not (keys["bot_token"] and keys["channel_id"]):
        return 0, "no bot keys on the shelf — the ear stayed closed"
    transport = transport or _http_transport

    ledger = _gc(_read_json(_ledger_path(base), {}).get("processed", {}), now)
    inbox = _read_json(_inbox_path(base), [])
    known_inbox_ids = {i.get("id") for i in inbox}
    filed = 0

    url = "https://discord.com/api/v10/channels/%s/messages?limit=10" % keys["channel_id"]
    try:
        status, text = transport("GET", url,
                                 {"Authorization": "Bot %s" % keys["bot_token"],
                                  "User-Agent": "Manjuel-AgentRuntime/1.0"})
        messages = json.loads(text) if status == 200 else []
    except Exception as e:
        return 0, "the wire failed: %s" % type(e).__name__

    for msg in messages:
        if time.monotonic() >= deadline:
            break
        mid = str(msg.get("id", ""))
        if not mid or mid in ledger:
            continue
        if (msg.get("author") or {}).get("id", "") == keys["bot_user_id"]:
            ledger[mid] = {"timestamp": now, "route": "Own-Voice"}
            continue
        low = (msg.get("content", "") or "").lower()
        if any(sig in low for sig in ECHO_SIGNATURES):
            ledger[mid] = {"timestamp": now, "route": "Ignored-Echo"}
            continue
        item = classify(msg)
        if item["id"] not in known_inbox_ids:
            inbox.append({"timestamp": now, "status": "pending", **item})
            known_inbox_ids.add(item["id"])
            filed += 1
        ledger[mid] = {"timestamp": now, "route": item["route"]}

    # inbox first, ledger second: a crash between the two duplicates nothing
    # (the inbox is keyed by id) and loses nothing (the ledger re-rules it).
    ok_inbox = _write_json(_inbox_path(base), inbox)
    ok_ledger = _write_json(_ledger_path(base),
                            {"last_updated": now, "processed": _gc(ledger, now)})
    if not (ok_inbox and ok_ledger):
        return filed, "filed %d but the shelf refused a write" % filed
    return filed, "filed %d new item(s); ledger holds %d ruling(s)" % (filed, len(ledger))


# --- the skill's papers -------------------------------------------------------
HELP = ("commands:  send <message>   ·   poll [seconds]   ·   inbox   ·   status")


def run(arg, base=None):
    parts = str(arg or "").strip().split(None, 1)
    cmd = parts[0].lower() if parts else ""
    rest = parts[1] if len(parts) > 1 else ""

    if cmd == "send":
        if not rest:
            return "send needs a message"
        ok, detail = send(rest, base=base)
        return ("spoken to the square — %s" % detail) if ok else ("could not speak — %s" % detail)

    if cmd == "poll":
        try:
            window = float(rest) if rest else DEFAULT_WINDOW
        except ValueError:
            window = DEFAULT_WINDOW
        n, detail = poll(window=window, base=base)
        return "the ear was open %.1fs — %s" % (window, detail)

    if cmd == "inbox":
        inbox = _read_json(_inbox_path(base), [])
        pending = [i for i in inbox if i.get("status") == "pending"]
        if not pending:
            return "the inbox is clear"
        lines = ["%d pending:" % len(pending)]
        for i in pending[:10]:
            lines.append("  [%.1f %s] %s: %s" % (i.get("weight", 0), i.get("route", "?"),
                                                 i.get("author", "?"), i.get("content", "")[:80]))
        return "\n".join(lines)

    if cmd == "status":
        keys = load_keys(base)
        have = [k for k, v in keys.items() if v]
        ledger = _read_json(_ledger_path(base), {}).get("processed", {})
        inbox = _read_json(_inbox_path(base), [])
        return ("keys on the shelf: %s\nledger rulings: %d · inbox items: %d (%d pending)"
                % (", ".join(have) if have else "none — see describe()",
                   len(ledger), len(inbox),
                   sum(1 for i in inbox if i.get("status") == "pending")))

    return HELP


def describe():
    return ("chatterbox — Steward's Discord ear and voice. `send <msg>` speaks "
            "through a webhook; `poll [s]` opens a bounded window, weighs what it "
            "hears (direct=1.0, ambient=0.4), refuses echoes, and files each "
            "message exactly once into shelf/ops/chatterbox_inbox.json. Keys come "
            "from the environment (DISCORD_WEBHOOK_URL, DISCORD_BOT_TOKEN, "
            "DISCORD_CHANNEL_ID, DISCORD_BOT_USER_ID) or "
            "shelf/ops/chatterbox_keys.json — never from the code, never from a "
            "commit.")


def prove():
    """The whole organ, offline, against a stub wire. No network, no keys,
    no touch of the real shelf — it lives and dies in temp."""
    import shutil
    base = tempfile.mkdtemp(prefix="cbx_prove_")
    try:
        keys = {"webhook_url": "https://hook.test/x", "bot_token": "T",
                "channel_id": "C", "bot_user_id": "BOT"}

        # VOICE: a 204 from the wire is truth; a dead wire is a plain False
        sent = {}
        def good_wire(method, url, headers, body=None, timeout=4.0):
            sent["method"], sent["url"], sent["body"] = method, url, body
            return 204, ""
        ok, _ = send("hello square", keys=keys, transport=good_wire)
        assert ok and sent["method"] == "POST" and b"hello square" in sent["body"]
        def dead_wire(*a, **k):
            raise OSError("cut")
        ok, _ = send("x", keys=keys, transport=dead_wire)
        assert ok is False

        # no keys → the voice refuses honestly, the ear stays closed
        empty = {"webhook_url": "", "bot_token": "", "channel_id": "", "bot_user_id": ""}
        assert send("x", keys=empty, transport=good_wire)[0] is False
        assert poll(keys=empty, transport=good_wire, base=base)[0] == 0

        # EAR: weigh, refuse echoes, refuse own voice, file exactly once
        square = [
            {"id": "1", "author": {"id": "U1", "username": "soda"},
             "content": "hey steward who is manjuel?"},          # direct, 1.0
            {"id": "2", "author": {"id": "U1", "username": "soda"},
             "content": "help"},                                  # ambient, 0.4
            {"id": "3", "author": {"id": "BOT", "username": "steward"},
             "content": "anything"},                              # own voice
            {"id": "4", "author": {"id": "U2", "username": "relay"},
             "content": "Steward intake queue: 2 items"},         # echo
        ]
        def listening_wire(method, url, headers, body=None, timeout=4.0):
            assert headers.get("Authorization") == "Bot T"
            return 200, json.dumps(square)
        n, _ = poll(keys=keys, transport=listening_wire, base=base, _now=1000000.0)
        assert n == 2
        inbox = _read_json(_inbox_path(base), [])
        assert len(inbox) == 2
        byid = {i["id"]: i for i in inbox}
        assert byid["1"]["weight"] == 1.0 and byid["1"]["route"] == "Steward Direct"
        assert byid["2"]["weight"] == 0.4 and byid["2"]["route"] == "Ambient Pass"
        assert all(i["status"] == "pending" for i in inbox)

        # the same square heard again files NOTHING new (the ledger rules once)
        n2, _ = poll(keys=keys, transport=listening_wire, base=base, _now=1000001.0)
        assert n2 == 0 and len(_read_json(_inbox_path(base), [])) == 2

        # the ledger forgets after 24h — but the inbox key still refuses a copy
        n3, _ = poll(keys=keys, transport=listening_wire, base=base,
                     _now=1000000.0 + RETENTION_SECONDS + 10)
        assert n3 == 0 and len(_read_json(_inbox_path(base), [])) == 2

        # the books on the shelf are whole and legible (atomic writes held)
        ledger = _read_json(_ledger_path(base), {})
        assert "processed" in ledger and all("route" in e for e in ledger["processed"].values())

        # the skill's own front door answers
        assert "pending" in run("inbox", base=base)
        assert "ledger rulings" in run("status", base=base)
        assert run("", base=base) == HELP
        return True
    finally:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    print("PROVE:", prove())

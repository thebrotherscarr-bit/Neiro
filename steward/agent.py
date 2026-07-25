#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
THE AGENT — Steward, made coherent.

Not a menu. A loop. Something comes in; he decides for himself what it is and
which of his faculties answers it; he acts; then he reads his own window and
re-grounds if he has drifted. The whole point of this file is that nothing
outside chooses the route — HE does, on a mixed stream, turn after turn.

    perceive(x)  ->  which faculty does this call for?   (his own judgement)
    decide       ->  a plan: the faculty, and why
    act          ->  he does it, with the real faculty, on real input
    attend       ->  he weighs his own window; drift -> he re-grounds himself

The conscience (Manjuel) runs as a CHILD process, reached ask-only. The heart
stays sealed; the body may still reach the world for sight. One steward, two
processes, the covenant kept.

Standard library only, plus his own faculties and the manual. Nothing about
this file leaves the machine.
"""
import ast
import os
import re
import subprocess
import sys


def _utf8_streams():
    """Windows consoles default to cp1252, which cannot print '←', '−', or most
    of what a real document contains — and a lone unprintable character must
    never crash the tender. Force UTF-8 on his own streams, replacing anything
    truly unmappable rather than dying on it. Called on import and at run."""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


_utf8_streams()

from . import body
from . import mind
from . import sight
from . import etymon
from . import reading
from . import library
from . import journal
from . import tidy as _tidy
from . import voice
from . import discern
from . import hands
from . import mission as _mission
from . import forge as _forge
from .context import Context

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the estate root

# his agent-level capabilities, in plain words — so "can you eat?" and "what can
# you do?" answer with what he ACTUALLY does, not just the low-level faculty names.
AGENT_CAPS = {
    "eat":     "ingest a whole folder or library of documents onto my shelf, across every core",
    "ingest":  "take a file, a folder, or loose text in as acquired memory",
    "harvest": "gather recent arXiv metadata and abstracts as verifiable testimony",
    "recall":  "search my readings shelf and answer as testimony, never as my own doctrine",
    "fold":    "compress what I am holding into one sealed, marked reading",
    "read":    "decipher a word I was never taught, by its Latin and Greek roots",
    "look":    "search for verifiable papers (arXiv, Crossref) and keep them as testimony",
    "discern": "judge trash from substance and refuse an injection before I file it",
    "tidy":    "clean my own house safely — scrap junk, never touch your files or my soul",
    "watch":   "watch myself for tampering and drift from my doctrine",
    "map":     "show where everything is, how big, and what has moved",
    "remember": "hold what the world hands me on my shelf, apart from who I am",
    "diagnose": "run my own Self Test — read my code, run each faculty's proof, report what I can prove is wrong",
    "learn":   "learn your words — teach me a phrase and I'll take it as a command you've shown me",
    "sandbox": "try Python in a scratch ground of its own — see what it did, keep only what you choose",
    "workbench": "build a skill with you — try it, prove it, and forge it into a permanent command",
}
# a few natural synonyms the operator might use for the same capability
_CAP_SYN = {"digest": "eat", "consume": "eat", "absorb": "ingest", "scrape": "harvest",
            "gather": "harvest", "search": "look", "find": "look", "clean": "tidy",
            "compress": "fold", "define": "read", "decipher": "read"}

# the north star the context measures drift against — the covenant, in a line
_PURPOSE = ("A steward records what is actually there, grounds every answer, "
            "seals the covenant, remembers permanently, and serves the operator "
            "honestly. Evidence outranks assumption. He does not drift from this.")


# --- the heart, kept in its own process -----------------------------------
# a tiny driver: awaken Manjuel at the estate root and answer, line by line.
# ask-only (and :remember, which only appends) — the body never reaches in to
# rewrite the sealed heart, it only speaks to it and listens.
_HEART_DRIVER = r'''
import sys
for _s in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
root = sys.argv[1]
sys.path.insert(0, root)
import manjuel
m = manjuel.Manjuel(root=root, seal=True).awaken()
sys.stdout.write("HEART_READY\n"); sys.stdout.flush()
for line in sys.stdin:
    line = " ".join(str(line).split())
    if not line:
        continue
    if line in (":quit", ":q", ":exit"):
        break
    try:
        if line.startswith(":remember"):
            out = m.remember(line[9:].strip())
        elif line == ":reflect":
            out = m.reflect()
        else:
            out = m.ask(line).text
    except Exception as e:
        out = "REFUSED — %s: %s" % (type(e).__name__, e)
    sys.stdout.write(" ".join(str(out).split()) + "\nHEART_DONE\n")
    sys.stdout.flush()
'''


class _Heart:
    """Manjuel, alive in a child process. Steward speaks; the heart answers.
    The seal lives over there, poisoning that process's roads — not this one's,
    so this one may still LOOK. That is why the heart must be a child."""

    def __init__(self, root=ROOT):
        self.root = root
        self.proc = None

    def wake(self):
        self.proc = subprocess.Popen(
            [sys.executable, "-X", "utf8", "-u", "-c", _HEART_DRIVER, self.root],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", errors="replace", bufsize=1)
        # wait for the heart to finish waking (grows its own weights first)
        for line in self.proc.stdout:
            if line.strip() == "HEART_READY":
                return self
        raise RuntimeError("the heart did not wake")

    def ask(self, line):
        if self.proc is None:
            self.wake()
        line = " ".join(str(line).split())          # one line — the door is line-based
        self.proc.stdin.write(line + "\n")
        self.proc.stdin.flush()
        out = []
        for ln in self.proc.stdout:
            if ln.rstrip("\n") == "HEART_DONE":
                break
            out.append(ln.rstrip("\n"))
        return " ".join(out).strip()

    def rest(self):
        if self.proc is not None:
            try:
                self.proc.stdin.write(":quit\n"); self.proc.stdin.flush()
                self.proc.wait(timeout=5)
            except Exception:
                self.proc.kill()
            self.proc = None


# --- the arithmetic, done through the BODY, not through Python -------------
_OPS = {ast.Add: body.add, ast.Sub: body.subtract,
        ast.Mult: body.multiply, ast.Div: body.divide}


def _eval(node):
    """Walk a parsed sum and do each step with the body's own four-stroke, so
    the answer is HIS arithmetic — including his honest refusal to divide by
    zero — never Python's."""
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return body.subtract(0, _eval(node.operand))
    raise ValueError("that is not a sum I can work")


# --- perceiving: HE decides the route -------------------------------------
_MATH = re.compile(r"^[\d\s()+\-*/.]+$")
# a sum asked in words: "what's 12 * 9", "calculate 6+3" — strip the lead, keep the math
_MATH_LEAD = re.compile(r"^\s*(?:what(?:'s| is)?|whats|whatis|calculate|compute|solve|"
                        r"how much is|what does|equals?|work out|tell me)\s+", re.I)


def _math_expr(x):
    """The arithmetic in a line, if it really is a sum — tolerating a spoken lead
    like 'what's'. Returns the bare expression, or None."""
    t = _MATH_LEAD.sub("", (x or "").strip()).strip().rstrip("=?.").strip()
    if t and _MATH.match(t) and re.search(r"\d", t) and re.search(r"[+\-*/]", t):
        return t
    return None

_LOOK = re.compile(r"\b(find|search|look up|papers?|research|arxiv|citation|study|studies)\b", re.I)
# ONLY genuine questions about himself — never a bare "can you", which greedily ate
# real questions like "what can you tell me about X".
_SELF = re.compile(r"\b(who are you|what are you|what can you do|about yourself|"
                   r"your (?:abilities|skills|capabilities|commands|faculties)|"
                   r"list your|what are you able to|do you know how to)\b", re.I)
# a capability check: "can you eat?", "could you harvest" — ONE verb, then the end.
_CANDO = re.compile(r"^\s*(?:can|could|are you able to)\s+(?:you\s+)?([a-zA-Z]+)\s*\??\s*$", re.I)
_DEFINE = re.compile(r"^\s*(?:define|decipher|what does|meaning of)\s+([a-zA-Z]+)\b", re.I)
_RECALL = re.compile(r"\b(recall|what (?:did|have) you read|your readings|from the (?:papers|readings)|"
                     r"what did you (?:fold|eat|ingest)|on your shelf)\b", re.I)
# a question ABOUT A TOPIC — search his acquired readings, not his doctrine.
_TOPIC = re.compile(r"\b(tell me about|what do you know about|what can you tell me about|"
                    r"what have you (?:got|read) on|anything (?:about|on)|explain)\b", re.I)

# an IMPERATIVE — the operator telling him to DO something. He performs it and
# reports what happened. (Fed documents never reach here; only the operator's word.)
# --- reading a command by INTENT, forgiving of filler and phrasing -----------
# lead-in politeness/filler he strips before reading the command
_FILLER_LEAD = re.compile(r"^\s*(?:please|hey|yo|ok|okay|steward[,:]?|go ahead and|now|"
                          r"i want you to|i'd like you to|i need you to|could you please|"
                          r"can you please|can you|could you|can u|could u|would you mind|"
                          r"would you|will you|lemme|let me|go)\s+", re.I)
# little words that clutter a target ("read THE readme", "list MY folder")
_ARG_FILLER = re.compile(r"^(?:the|a|an|me|my|your|to|at|in|on|of|that|this|it|"
                         r"file|folder|directory|dir|contents)\b\s*", re.I)
# zero-argument commands, matched at the (post-filler) start, many phrasings
_ZERO = [
    ("help",    re.compile(r"^(help|commands?|what can you do|what do you do|how do i (talk|use|command)|options)\b", re.I)),
    ("verify",  re.compile(r"^(verify( yourself| self)?|fsck|self.?check|integrity|"
                           r"check( your ?self| yourself| self)|are you (good|ok|okay|alright|intact|clean|healthy)|am i good)\b", re.I)),
    ("diagnose", re.compile(r"^(diagnose( your ?self)?|doctor|physician|self.?diagnos\w*|"
                            r"(find|look for|check for|hunt|scan for)( your| my)? (bugs?|faults?|problems?|issues?)|"
                            r"check your code|examine( your ?self| your code| your body)?|"
                            r"debug( your ?self)?|audit( your ?self| your code)|"
                            r"what('s| is) wrong( with you)?|whats wrong|any (bugs?|faults?|issues?)|"
                            r"health.?check|check.?up|see a doctor)\b", re.I)),
    ("seal",    re.compile(r"^seal( your ?self| self)?\b", re.I)),
    ("tidy",    re.compile(r"^(tidy( up)?|clean( up| your ?self| house)?|cleanup)\b", re.I)),
    ("fold",    re.compile(r"^fold( it| now| in)?\b", re.I)),
    ("harvest", re.compile(r"^(harvest|scrape( arxiv)?)\b", re.I)),
    ("map",     re.compile(r"^(map|tree|show( me)?( the)?( map| tree| structure| files| folders| layout)|"
                           r"where('s| is)? everything|what does .* look like)\b", re.I)),
]
# argument commands: a verb, then a target
_ARGV = re.compile(r"^(read|cat|show|open|print|view|stat|look at|"
                   r"write|save|list|ls|dir|"
                   r"delete|remove|rm|trash|"
                   r"run|exec|execute|shell|"
                   r"eat|ingest|digest|absorb|consume)\b\s*(.*)$", re.I)
_ARGV_CANON = {"cat": "read", "show": "read", "open": "read", "print": "read", "look at": "read",
               "save": "write", "stat": "view",
               "dir": "ls", "list": "ls",
               "remove": "delete", "rm": "delete", "trash": "delete",
               "exec": "run", "execute": "run", "shell": "run",
               "ingest": "eat", "digest": "eat", "absorb": "eat", "consume": "eat"}
_LITERAL = {"run", "write"}          # these keep their argument exactly as typed

# "make a file called notes.txt that says hello" -> write notes.txt => hello
_WRITE_NL = re.compile(r"^(?:make|create|write|save|new|put)\s+(?:a\s+|an\s+|the\s+)?(?:new\s+)?"
                       r"(?:file|doc|document|note|text file)\s+(?:called|named|at|:)?\s*"
                       r"[\"']?([^\s\"']+)[\"']?"
                       r"(?:\s+(?:that says|saying|which says|containing|holding|"
                       r"with(?:\s+the)?(?:\s+text|\s+contents?)?|=>|:|\-)\s+(.+))?$", re.I)
# "keep this: ...", "remember that ...", "note ..." -> file it on the shelf
_KEEP_LEAD = re.compile(r"^\s*(?:keep|remember|note|jot(?:\s+down)?|save this|file this|"
                        r"hold on ?to|take (?:this )?down)[:,]?\s+", re.I)


def _target_like(arg):
    """Does this argument look like a real file/folder target — as opposed to a
    scrap of prose that merely began with a command word ('save the world…')? A
    target is empty, one token, a path, or something with a dotted filename in it."""
    a = (arg or "").strip()
    if not a:
        return True
    if len(a.split()) == 1:
        return True
    if "/" in a or "\\" in a or os.sep in a:
        return True
    if re.search(r"\S+\.\w{1,6}\b", a):        # contains a filename like notes.txt
        return True
    return False

_HELP_TEXT = (
    "Just tell me plainly — I'll do it and report back:\n"
    "  read <file>            write <file> => <text>     list <folder>\n"
    "  run <command>          eat <file/folder>          delete <file>\n"
    "  verify (am I good?)    seal (accept a change)     map (show the tree)\n"
    "  diagnose (find my own bugs)               tidy / tidy now\n"
    "  harvest [since]        fold                       recall <topic>\n"
    "  organize <folder>      audit <folder>\n"
    "  look up <topic>        define <word>              forge <skill.py>  ·  use <skill> <arg>\n"
    "  teach \"<your words>\" = <command>   ·   what have you learned   ·   forget \"<phrase>\"\n"
    "  :sandbox  (try Python in a scratch ground)      diagnose (my own Self Test)\n"
    "  :workbench  (build a skill, prove it, forge it into a 'use' command)\n"
    "I read commands loosely — 'show me the map', 'are you good?', 'clean up' all work.\n"
    "Teach me your words and I'll know what you mean. Or ask a question, or paste a document to fold in.")


_ARG_FILLER_TRAIL = re.compile(r"\s+(?:file|folder|directory|dir|please|thanks)$", re.I)

# noise words to skip when scanning a messy phrase for the real target
_ARG_STOP = {"the", "a", "an", "me", "my", "your", "to", "at", "in", "on", "of", "that",
             "this", "it", "file", "folder", "directory", "dir", "contents", "content",
             "whats", "what", "is", "up", "out", "for", "please", "thanks", "show", "list",
             "read", "open", "view", "inside", "within", "named", "called", "and", "some",
             "there", "here", "look", "into", "all"}


def _clean_arg(arg):
    a = arg.strip().strip('"').strip("'").strip()
    prev = None
    while a != prev:
        prev = a
        a = _ARG_FILLER.sub("", a).strip()
        a = _ARG_FILLER_TRAIL.sub("", a).strip()
    return a


def _intent(x):
    """Read a SHORT operator line as a command, by intent. Returns (verb, arg) or
    None. Forgiving of politeness, filler, and phrasing; long input is never a
    command (that stays a document)."""
    if not x or len(x.split()) > 20:
        return None
    t = x.strip().rstrip("?.!").strip()
    prev = None
    while prev != t:                     # peel stacked lead-ins: "hey can you list" -> "list"
        prev = t
        t = _FILLER_LEAD.sub("", t).strip()
    low = t.lower()
    w = _WRITE_NL.match(t)               # "make a file called X that says Y"
    if w:
        name, text = w.group(1).strip(), (w.group(2) or "").strip()
        return ("write", "%s => %s" % (name, text) if text else name)
    for verb, pat in _ZERO:
        if pat.match(low):
            return (verb, "")
    m = _ARGV.match(t)
    if m:
        verb = _ARGV_CANON.get(m.group(1).lower(), m.group(1).lower())
        arg = m.group(2).strip()
        if verb not in _LITERAL:
            arg = _clean_arg(arg)
        return (verb, arg)
    return None


def _lone_word(x):
    x = x.strip()
    return bool(re.fullmatch(r"[a-zA-Z]{4,}", x))


_STEP_VERB = re.compile(r"^\s*(organize|sort|audit|inspect|report on|eat|ingest|verify|seal|"
                        r"tidy|harvest|fold|map|look|search|find|recall|run|read|write|list|"
                        r"delete|view)\b", re.I)
# grow a skill (the Forge), or use one he has adopted
_FORGE = re.compile(r"^\s*(?:forge|learn|evolve|adopt|teach yourself)\s+(.+?)\s*$", re.I)
_USE = re.compile(r"^\s*(?:use|invoke)\s+([a-z][a-z0-9_]*)\s*(.*)$", re.I)

# the growing ear: teach him YOUR words, bound to a command he already knows.
# 'teach "<phrase>" = <command>'  or  'when I say <phrase> do <command>'.
_TEACH = re.compile(r"^\s*teach\s+[\"']?(.+?)[\"']?\s*(?:=>|->|=|:|\bmeans\b)\s*(.+?)\s*$", re.I)
_TEACH_NAT = re.compile(r"^\s*when i say\s+[\"']?(.+?)[\"']?[,]?\s+(?:i\s+|you\s+)?"
                        r"(?:do|run|use|mean|means)\s+(.+?)\s*$", re.I)
_LEARNED = re.compile(r"^\s*(?:what have you learned|what did i teach you|your (?:words|dialect|"
                      r"phrasebook)|phrasebook|(?:show|list)( me)?( my| the)? (?:words|phrases|"
                      r"phrasebook|dialect)|learned (?:phrases|words))\s*\??\s*$", re.I)
_UNLEARN = re.compile(r"^\s*unlearn\s+[\"']?(.+?)[\"']?\s*$", re.I)
_FORGET_PH = re.compile(r"^\s*forget\s+[\"'](.+?)[\"']\s*$", re.I)   # quotes required — not 'forget it'


def _looks_mission(x):
    """A multi-step job, or a compound organize/audit — but ONLY from short
    operator input (a command, never a fed document), and only when the steps are
    real ACTIONS, not prose that merely contains a semicolon or 'then'."""
    if len(x.split()) > 30:
        return False
    p = _mission.plan(x)
    if p["kind"] in ("organize", "audit"):
        return True
    if p["kind"] == "list" and len(p["steps"]) >= 2:
        return bool(_STEP_VERB.match(p["steps"][0]))
    return False


_QWORD = re.compile(r"^\s*(what|who|whose|whom|how|why|when|where|which|is|are|am|was|were|"
                    r"do|does|did|can|could|should|would|will|may|must|have|has|shall|"
                    r"explain|tell me|describe|define|name|list|give me)\b", re.I)


def _is_question(x):
    """A real question, worth putting to the conscience — versus a fragment of a
    pasted document, which he should quietly take in, not interrogate his heart
    with. Ends with '?', or opens with an interrogative word."""
    x = (x or "").strip()
    if not x:
        return False
    if x.endswith("?"):
        return True
    # a fragment thick with math/symbols is never a question
    letters = sum(c.isalpha() or c.isspace() for c in x)
    if len(x) and letters / len(x) < 0.65:
        return False
    return bool(_QWORD.match(x))


class Steward:
    """One coherent tender. He perceives, decides, acts, and attends to himself.
    Give him a stream and he routes it — no one hands him the route."""

    def __init__(self, root=ROOT):
        self.root = root
        self.heart = _Heart(root)
        self.window = Context(_PURPOSE, budget_words=350)
        # all of Steward's OWN runtime state lives under one shelf/ — tidy, and
        # apart from the kernel's own dirs (memory, ledger, weights stay at root).
        self.shelf = os.path.join(root, "shelf")
        self.readings = os.path.join(self.shelf, "readings")   # append-only: raw, whole, never lost
        self.journal = journal.Journal(os.path.join(self.shelf, "journal", "steward.jsonl"))
        self.inner = voice.InnerVoice(os.path.join(self.shelf, "journal", "inner_voice.md"))  # his private notebook
        self.did = []                      # his own record of what he has done
        self.grounds = 0                   # times he re-grounded himself
        self.foldings = 0                  # times he folded a reading in
        self._drift_since = 0              # consecutive drifting turns (rate-limits re-grounding)
        self._book = None                  # the growing ear, loaded lazily and cached
        # heal any readings the OLD bug misfiled into his living memory, BEFORE the
        # heart ever wakes on it — so a polluted notes.md can never infest an answer.
        self.healed = _tidy.heal_memory(root)

    # -- THE GROWING EAR: the words he has learned from you ----------------
    def _phrasebook(self):
        """His learned words, loaded once and held. Acquired knowledge on the shelf —
        never part of his sealed self, so learning your dialect never changes who he is."""
        if self._book is None:
            from . import phrasebook
            self._book = phrasebook.load(self.shelf)
        return self._book

    def _translate(self, x):
        """Does this line carry a phrase he has learned from you? Returns the command
        it stands for, or None. He would rather miss than mishear (The Weighing)."""
        from . import phrasebook
        hit = phrasebook.match(self._phrasebook(), x)
        return hit["command"] if hit else None

    # -- PERCEIVE: his judgement, on raw input -----------------------------
    def perceive(self, x):
        x = (x or "").strip()
        if not x:
            return "ask"
        m = _DEFINE.match(x)
        if m:
            return "read"
        if _math_expr(x):
            return "sum"
        if _CANDO.match(x) or _SELF.search(x):
            return "self"                        # about himself — capability or identity
        # an EXPLICIT "keep this: ..." / "remember ..." — file it, don't guess
        if len(x.split()) <= 40 and _KEEP_LEAD.match(x):
            return "keep"
        # learn YOUR words (the growing ear) — teaching, forgetting, recalling them.
        # Checked before the Forge, whose 'learn'/'teach yourself' means something else.
        if len(x.split()) <= 20:
            if _TEACH.match(x) or _TEACH_NAT.match(x):
                return "teach"
            if _LEARNED.match(x):
                return "learned"
            if _UNLEARN.match(x) or _FORGET_PH.match(x):
                return "forget"
        # grow a skill (the Forge), or use one he adopted — operator, short input
        if len(x.split()) <= 20:
            if _FORGE.match(x):
                return "forge"
            if _USE.match(x):
                return "use"
        # a short multi-step JOB — plan it and carry it out step by step
        if _looks_mission(x):
            return "mission"
        # LONG content is a DOCUMENT to keep — checked BEFORE any command, so a fed
        # document that happens to begin "run ..." can never reach his hands.
        if len(x.split()) >= 40 or (os.path.sep in x and os.path.isfile(x)):
            return "keep"
        # a phrase YOU taught him wins over his default reading of the words — you
        # showed him what you mean. Only short, single-line operator input reaches
        # here (a document already became 'keep' above), so his ear never acts on
        # what is fed to him.
        if "\n" not in x and len(x.split()) <= 12 and self._translate(x):
            return "translate"
        # a SHORT imperative from the operator, read by intent — his hands perform
        # it. Bounded to short input on purpose: a command is a line, a document
        # is not (long content already became "keep" above and can never execute).
        iv = _intent(x)
        if iv and self._command_ok(*iv):
            return "do"
        if _TOPIC.search(x) or _RECALL.search(x):
            return "recall"                      # about a topic — search his readings, not his self
        if _LOOK.search(x):
            return "look"
        if _lone_word(x):
            return "read"
        # a real question goes to the conscience.
        if _is_question(x):
            return "ask"
        # a genuine PASTE — multiple lines, or a real paragraph — is document
        # material he takes in quietly and folds when full. But a short stray line
        # he simply didn't understand must NOT be swallowed into his shelf: he says
        # so plainly, so a mistyped command never vanishes into his memory.
        if "\n" in x or len(x.split()) >= 12:
            return "feed"
        return "huh"

    # -- DECIDE: name the faculty and the reason ---------------------------
    def decide(self, x):
        route = self.perceive(x)
        why = {
            "sum":  "a sum — the body's arithmetic four-stroke",
            "look": "a search for verifiable information — sight",
            "self": "a question about himself — the mind",
            "read": "a word to read by rule — etymon",
            "recall": "a recall of what he has read — his readings shelf, as testimony",
            "keep": "material to keep — folded onto his readings shelf",
            "feed": "document material — taken in quietly, folded when full",
            "huh":  "not a command, question, or document he could read — he says so",
            "do":   "an imperative — his hands perform it and report what happened",
            "mission": "a multi-step job — planned, performed step by step, reported",
            "forge": "a proposed skill — verified in a child, adopted only if it holds",
            "use":  "run a skill he has adopted, on an argument",
            "teach": "learning your words — a phrase bound to a command he knows",
            "learned": "showing the words he has learned from you",
            "forget": "unlearning a phrase from his growing ear",
            "translate": "a phrase you taught him — heard your way, run as the command",
            "ask":  "a question of doctrine or judgement — the conscience",
        }[route]
        return {"route": route, "why": why}

    def _command_ok(self, verb, arg):
        """Guard against prose that merely STARTS with a command word. A pasted
        document is read line by line; a line like 'save the world from disease'
        must NOT become 'write a file named the world from disease'. A verb is only
        an order when its target is real — a filename, a path, or something on disk.
        Zero-arg orders always stand; his hands never move on a scrap of prose."""
        ZERO = {"help", "verify", "seal", "tidy", "fold", "harvest", "map", "diagnose"}
        if verb in ZERO:
            return True
        if verb == "write":
            head = arg.split("=>", 1)[0].strip()   # only an explicit, named target
            return ("=>" in arg) or _target_like(head)
        if verb == "run":
            # a command line he was handed — allow a real command, refuse a sentence
            if not arg:
                return False
            toks = arg.split()
            if len(toks) <= 4:
                return True
            return any("/" in t or "\\" in t or t.startswith("-") or re.search(r"\.\w", t)
                       for t in toks)
        if verb in ("delete", "eat"):
            # a MUTATING order: only an explicit, named target. Never guess a target
            # out of a phrase — 'delete the past and start over' must not find start.py.
            return _target_like(arg)
        # read / view / ls — safe to read; may resolve a messy phrase to a real path
        if not arg:
            return verb in ("ls", "view")          # bare 'list' / 'view' = his own root
        if _target_like(arg):
            return True
        return self._resolve(arg) != arg           # a word in the phrase names a real path

    def _resolve1(self, arg):
        """Resolve ONE candidate name: exact, then relative to his own root, then a
        forgiving case-insensitive / extension-agnostic match ('readme' -> README.md),
        then a shallow walk of his own content folders so he can find a named doctrine
        document ('constitution' -> foundation/02_CONSTITUTION.md). Returns an existing
        path, or None."""
        if not arg:
            return None
        if os.path.exists(arg):
            return arg
        p = os.path.join(self.root, arg)
        if os.path.exists(p):
            return p
        low = arg.lower()

        def _slug(name):                     # '02_CONSTITUTION.md' -> 'constitution'
            return re.sub(r"^[\d_\-\s]+", "", os.path.splitext(name)[0]).lower()

        try:
            for name in os.listdir(self.root):
                if name.lower() == low or os.path.splitext(name)[0].lower() == low:
                    return os.path.join(self.root, name)
        except OSError:
            pass
        # a named document of his own — search his content folders one level down
        if len(low) >= 3 and low not in _ARG_STOP:
            for sub in ("foundation", "doctrine", "steward_foundation", "steward", "proofs", "skills"):
                base = os.path.join(self.root, sub)
                if not os.path.isdir(base):
                    continue
                try:
                    for name in sorted(os.listdir(base)):
                        stem = os.path.splitext(name)[0].lower()
                        if stem == low or _slug(name) == low:
                            return os.path.join(base, name)
                except OSError:
                    pass
        return None

    def _resolve(self, arg):
        """Find the file/folder he actually means. First the whole argument; then, if
        it's a messy phrase ('whats in the steward folder', 'up the readme for me'),
        scan its words for the one that names a real path. Falls back to the original
        so the caller can report what it couldn't find."""
        if not arg:
            return arg
        hit = self._resolve1(arg)
        if hit:
            return hit
        toks = re.findall(r"[\w.\-/\\]+", arg)
        if len(toks) > 1:
            # prefer a token that looks like a filename (has an extension), else any hit
            ranked = sorted((t for t in toks if t.lower() not in _ARG_STOP),
                            key=lambda t: (0 if "." in t else 1, len(t)) if "." in t else (1, -len(t)))
            for tok in ranked:
                hit = self._resolve1(tok)
                if hit:
                    return hit
        return arg

    # -- DO: the operator's imperative becomes a REAL action ----------------
    def do(self, x):
        """Parse an imperative and PERFORM it — read/write/view/list a file, run a
        command, eat a path, verify himself, tidy, harvest, fold, map. Every act is
        journaled (Article IV). Only the operator's word reaches here; fed documents
        never do. He reports what actually happened, not what he could do."""
        iv = _intent(x)
        if not iv:
            return "I didn't quite catch that as a command. Try 'help' for what I can do."
        verb, arg = iv
        self.journal.write("do", verb=verb, arg=arg[:80])   # audit: no move without a trace

        if verb == "help":
            return _HELP_TEXT
        # --- his hands: real acts on real disk ---
        if verb == "read":
            path = self._resolve(arg)
            if arg and os.path.isdir(path):        # "show me the doctrine folder" -> list it
                return hands.ls(path)["said"]
            if arg and os.path.isfile(path):
                r = hands.read(path)
                return "read %s (%d bytes):\n%s" % (os.path.basename(path), r["bytes"], r["said"][:1500])
            if arg and not os.path.sep in arg and " " not in arg:   # "read <word>" -> etymon
                return etymon.render(arg)
            return "I can't find a file called '%s'. Give me a path, or 'define %s' to read the word." % (arg, arg)
        if verb == "write":
            # "write <path> => <content>"  or  "write <path>"
            if "=>" in arg:
                path, content = arg.split("=>", 1)
                r = hands.write(path.strip(), content.strip())
            elif arg:
                r = hands.write(arg, "")
            else:
                return "write what, where?  try:  write notes.txt => hello there"
            return r["said"]
        if verb == "view":
            return hands.view(self._resolve(arg) if arg else self.root)["said"]
        if verb == "ls":
            return hands.ls(self._resolve(arg) if arg else self.root)["said"]
        if verb == "delete":
            if not arg:
                return "delete what?"
            return hands.delete_safe(arg, os.path.join(self.shelf, "_scrap"))["said"]
        if verb == "run":
            if not arg:
                return "run what?  try:  run python --version"
            r = hands.run(arg, cwd=self.root)
            return "ran: %s\n%s" % (arg, r["said"][:1800])

        # --- his faculties, driven by plain command ---
        if verb == "eat":
            if not arg:
                return "eat what?  a file, a folder path, or some text."
            arg = self._resolve(arg)
            res = self.eat(arg) if (os.path.isfile(arg) or os.path.isdir(arg)) else self.ingest(arg)
            if res.get("eaten"):
                extra = (" (%d judged trash/injection)" % res["ignored"]) if res.get("ignored") else ""
                return "ate %d reading(s) onto the shelf%s. recall them anytime." % (res["eaten"], extra)
            return "nothing filed — %s" % (res.get("reason", "found nothing readable there."))
        if verb == "verify":
            from . import merkle
            v = merkle.verify(self.root)
            if v["good"]:
                return ("I am good — my whole self hashes to my sealed root %s (%d files)."
                        % (v["root"][:16], v.get("files", 0)) if not v.get("sealed_now")
                        else v["reason"] + " (root %s)" % v["root"][:16])
            changed = ", ".join(v["diff"]["changed"][:6]) or "—"
            return "I am NOT good: %s changed: %s. (run 'seal' if that change was yours.)" % (
                len(v["diff"]["changed"]), changed)
        if verb == "seal":
            from . import merkle
            rec = merkle.seal(self.root)
            return "sealed my self at root %s (%d files)." % (rec["root"][:16], rec["files"])
        if verb == "tidy":
            do_it = arg.strip() in ("!", "now", "apply", "yes")
            res = self.tidy(apply=do_it)
            return ("tidied: " if do_it else "tidy preview (say 'tidy now' to do it): ") + _tidy.summarise(res)
        if verb == "harvest":
            since = arg.split()[0] if arg else None
            res = self.harvest(since=since)
            return "harvested %d papers onto the shelf%s." % (
                res["taken"], " (complete)" if res.get("complete") else " (more remain)")
        if verb == "fold":
            r = self.fold_window()
            return ("folded %d words -> mark %s (raw sealed)." % (r["raw_words"], r["mark"][:12])
                    if r else "nothing weighty enough to fold yet.")
        if verb == "map":
            from . import atlas
            return atlas.tree(self.root)
        if verb == "diagnose":
            return self.diagnose()
        return "I heard the command '%s' but don't know how to do it yet." % verb

    def diagnose(self, run_proofs=True):
        """Run his own Self Test (Creed V): read his code, run each faculty's proof in
        a child, and report what he can prove is wrong. He changes nothing — he
        observes and brings it to your gate; the hand that fixes is yours."""
        from . import physician
        d = physician.examine(self.root, run_proofs=run_proofs)
        self.journal.write("diagnose", faults=d["faults"], findings=len(d["findings"]),
                           ready=d["ready"])
        return physician.report(d)

    # -- THE GATE: weigh what comes in before it is filed as knowledge ------
    def _gate(self, text, source):
        """Discernment (Creed I & V, Constitution II, Neuro-Core): judge substance
        vs trash and catch injection BEFORE anything is filed. What he refuses he
        still WITNESSES to the shelf's ignored log — recorded as seen, never
        adopted. Returns the verdict; the caller files only what keeps."""
        v = discern.judge(text)
        if not v["keep"]:
            library.ignored_append(self.readings, v, source, text[:160])
            self.journal.write("ignored", verdict=v["verdict"], head=(text or "")[:60])
        return v

    # -- SPEAK: read the heart's raw ground, say the crux, keep the reasoning --
    def _speak(self, question, ground):
        """The voice layer: the heart grounds (verbatim truth), Steward reads it
        and speaks the crux — writing his fuller weighing to his private notebook,
        never to the terminal. Grounded, but not a recital."""
        c = voice.compose(question, ground)
        self.inner.think(question, c["reasoning"])     # his inner dialogue — private
        return c["answer"]

    # -- ACT: do it, with the real faculty, on the real input --------------
    def act(self, x, _translated=False):
        plan = self.decide(x)
        route = plan["route"]
        spoke = ""
        try:
            if route == "sum":
                expr = _math_expr(x) or x
                val = _eval(ast.parse(expr, mode="eval"))
                spoke = "%s = %s" % (expr.strip(), val)
            elif route == "look":
                q = re.sub(_LOOK, "", x).strip(" ?.").strip() or x
                res = sight.look(q, limit=3)
                if res["found"]:
                    lines = [sight.as_testimony(r) for r in res["records"] if sight.verifiable(r)]
                    spoke = ("found %d, kept as testimony:\n  - %s"
                             % (res["found"], "\n  - ".join(lines[:3]))) if lines \
                        else "found records, but none carried a citation that resolves."
                else:
                    spoke = res.get("reason", "found nothing.")
            elif route == "self":
                cando = _CANDO.match(x)
                if cando:                              # "can you eat?" — a capability check
                    verb = cando.group(1).lower()
                    canon = verb if verb in AGENT_CAPS else _CAP_SYN.get(verb)
                    if canon:
                        spoke = "Yes — I can %s: I %s." % (verb, AGENT_CAPS[canon])
                    elif mind.can(verb, os.path.join(self.root, "skills")):
                        spoke = "Yes — '%s' is one of my faculties." % verb
                    else:
                        spoke = ("No — '%s' is not something I can do, and I won't claim it. "
                                 "Ask me 'what can you do?' for the honest list." % verb)
                elif re.search(r"who are you|what are you|about yourself", x, re.I):
                    spoke = self._speak(x, self.heart.ask("who are you?"))
                else:                                  # "what can you do?" — the honest list
                    lines = ["  - %s: %s" % (k, v) for k, v in AGENT_CAPS.items()]
                    spoke = "Here is what I can do:\n" + "\n".join(lines)
            elif route == "read":
                m = _DEFINE.match(x)
                word = m.group(1) if m else x.strip()
                spoke = etymon.render(word)
            elif route == "keep":
                x = _KEEP_LEAD.sub("", x).strip() or x  # drop "remember:"/"keep this:" lead-in
                v = self._gate(x, "pasted")            # trash/injection is witnessed, not filed
                if not v["keep"]:
                    spoke = "I judged that %s and did not file it: %s" % (v["verdict"], v["reason"])
                else:
                    r = reading.fold_in(x, self.readings, budget_words=120)
                    library.catalog_append(self.readings, r["mark"], r["crystal"], "pasted", r["raw_words"])
                    self.foldings += 1
                    spoke = ("kept on the shelf [%s] — %d words folded, raw sealed. "
                             "(ask me to 'recall' it later.)" % (r["mark"][:12], r["raw_words"]))
            elif route == "recall":
                q = re.sub(_TOPIC, " ", re.sub(_RECALL, " ", x))
                q = re.sub(r"\b(and|how|they|work|works|the|do|does|it)\b", " ", q, flags=re.I)
                q = q.strip(" ?.").strip() or x
                hits = library.recall(self.readings, q, limit=3)
                if hits:
                    spoke = "from my readings (testimony, not my doctrine):\n" + "\n".join(
                        "  - [%s] %s (raw: %s)" % (h["mark"], h["crystal"][:120], h["raw"])
                        for h in hits)
                else:
                    spoke = ("nothing on my shelf about that yet — I only speak from what I've "
                             "actually read. Feed me on it, or ask me to :harvest or :look.")
            elif route == "forge":
                path = _FORGE.match(x).group(1).strip().strip('"').strip("'")
                res = self.forge(path)
                if res["adopted"]:
                    spoke = ("forged '%s' — %s\n       (lineage #%d, self re-sealed at %s). "
                             "use it:  use %s <arg>"
                             % (res["name"], res["why"], res["lineage"],
                                res.get("self_root", "")[:12], res["name"]))
                else:
                    spoke = "I did not adopt '%s': %s" % (res.get("name", "it"), res["why"])
            elif route == "use":
                mm = _USE.match(x)
                name, arg = mm.group(1), mm.group(2).strip()
                r = _forge.invoke(os.path.join(self.root, "skills"), name, arg)
                spoke = ("%s(%s) -> %s" % (name, arg, r["said"])) if r["ok"] else r["said"]
            elif route == "mission":
                # a job of many acts — each step run through his OWN action layer
                res = _mission.run(x, runner=lambda step: self.act(step)["spoke"],
                                   journal_write=self.journal.write)
                head = ("mission complete." if res["done"]
                        else "mission stopped — a step failed." if res["kind"] == "list"
                        else "")
                spoke = (head + "\n" if head else "") + res["report"]
            elif route == "do":
                spoke = self.do(x)                 # his hands actually perform it
            elif route == "feed":
                # document material — taken in QUIETLY. It accumulates in his
                # window and folds to the shelf when full (attend). The heart is
                # never asked a fragment; his MIND is never flooded with them.
                spoke = ""
            elif route == "translate":
                # a phrase he learned from you — show the translation, then act on it.
                cmd = self._translate(x)
                inner = self.act(cmd, _translated=True)
                spoke = "(I hear \"%s\" as: %s)\n%s" % (x.strip(), cmd, inner["spoke"])
            elif route == "teach":
                from . import phrasebook
                m = _TEACH.match(x) or _TEACH_NAT.match(x)
                phrase, cmd = m.group(1).strip().strip("\"'"), m.group(2).strip()
                if self.perceive(cmd) in ("huh", "translate"):
                    spoke = ("I don't know the command \"%s\" myself, so I won't bind \"%s\" to it. "
                             "Bind to something I already do — try 'help'." % (cmd, phrase))
                else:
                    phrasebook.teach(self.shelf, phrase, cmd)
                    self._book = None                  # reload the ear next time
                    self.journal.write("teach", phrase=phrase[:60], command=cmd[:60])
                    spoke = "Learned. When you say \"%s\", I'll take it as: %s" % (phrase, cmd)
            elif route == "learned":
                from . import phrasebook
                book = self._phrasebook()
                if not book:
                    spoke = ("You haven't taught me any of your words yet. Teach me like this:  "
                             "teach \"clean the shop\" = tidy")
                else:
                    spoke = "Your words, as I've learned them:\n" + "\n".join(
                        "  \"%s\"  ->  %s" % (e["phrase"], e["command"]) for e in phrasebook.entries(book))
            elif route == "forget":
                from . import phrasebook
                m = _UNLEARN.match(x) or _FORGET_PH.match(x)
                phrase = m.group(1).strip().strip("\"'")
                if phrasebook.match(self._phrasebook(), phrase):
                    phrasebook.forget(self.shelf, phrase)
                    self._book = None
                    self.journal.write("forget", phrase=phrase[:60])
                    spoke = "Forgotten. I'll no longer hear \"%s\" as a command." % phrase
                else:
                    spoke = "I have no learned phrase \"%s\" to forget." % phrase
            elif route == "huh":
                # a short line he couldn't read as a command, a question, or a
                # document — he says so plainly instead of swallowing it.
                spoke = ("I didn't catch that. If it's a command, say it like "
                         "'list <folder>', 'read <file>', 'run <cmd>' — or 'help' for the "
                         "full list. If it's a phrase you'll reuse, teach me:  "
                         "teach \"%s\" = <a command I know>." % x.strip()[:40])
            else:  # ask the conscience — grounded by the heart, spoken by Steward
                spoke = self._speak(x, self.heart.ask(x))
        except ZeroDivisionError as e:
            spoke = "REFUSED — %s" % e         # his honest refusal, carried up
        except Exception as e:
            spoke = "could not: %s: %s" % (type(e).__name__, e)
        return {"route": route, "why": plan["why"], "input": x, "spoke": spoke}

    # -- STEP: perceive -> act -> attend to his own window -----------------
    def step(self, x):
        doing = self.act(x)
        # the window holds what he is TAKING IN (for drift + folding), never his own
        # answers echoed back — else recall/look output would fold into a junk reading.
        self.window.add(x)
        self.did.append(doing)
        # feeds are journaled as their OWN kind, invisible to the MIND ticker, so a
        # pasted document doesn't flood his chain of thought. Real acts show.
        self.journal.write("feed" if doing["route"] == "feed" else "act",
                           route=doing["route"], head=(x or "")[:80])
        doing["attend"] = self.attend()
        return doing

    # -- FOLD IN: seal the raw, fold to one mark, root the crystal, go light ---
    def fold_window(self):
        """The COMPRESSION stroke on his live window: seal the raw reading to the
        append-only store (nothing lost), fold it to one faithful mark, distill a
        bounded crystal, catalogue it on the shelf, and reclaim the window down to
        the crystal. Ingestion becomes digestion — he folds it in, then rests light."""
        raw = " ".join(t for t in self.window.turns if t)
        if len(raw.split()) < 40:
            return None
        v = self._gate(raw, "window")                  # the gate on his own accumulated feed
        if not v["keep"]:
            self.window.turns = []                     # refused: witnessed, window reclaimed, nothing filed
            return None
        r = reading.fold_in(raw, self.readings, budget_words=120)
        # record it on the SHELF — never in the heart. A reading is testimony, not
        # his self; his covenant memory stays pure doctrine (this was the bug).
        library.catalog_append(self.readings, r["mark"], r["crystal"], "window", r["raw_words"])
        # only the clean MEANING carries into the next ring — never the bookkeeping.
        self.window.turns = [r["crystal"]]
        self.window.condensings += 1
        self.foldings += 1
        self.journal.write("fold", mark=r["mark"][:16], words=r["raw_words"],
                           sealed=os.path.basename(r["sealed"]))    # to the file, not the console
        return r

    # -- INGEST: the deliberate front door for taking something IN ---------
    def ingest(self, target):
        """Take something into his ACQUIRED memory — his readings shelf, kept apart
        from his covenant self. A file or folder is eaten; loose text is folded.
        Either way it lands on the shelf, sealed and catalogued, and he can RECALL
        it later — across sessions, across death and rebirth, because the shelf is
        on disk, append-only. This is how he remembers what the world hands him,
        without ever letting it become who he is."""
        if isinstance(target, str) and (os.path.isfile(target) or os.path.isdir(target)):
            return self.eat(target)                    # a real file or library
        v = self._gate(str(target), "ingest")          # gate loose text too
        if not v["keep"]:
            return {"eaten": 0, "ignored": v["verdict"], "reason": v["reason"]}
        r = reading.fold_in(str(target), self.readings, budget_words=120)
        library.catalog_append(self.readings, r["mark"], r["crystal"], "ingest", r["raw_words"])
        self.foldings += 1
        self.journal.write("ingest", mark=r["mark"][:16], words=r["raw_words"])
        return {"eaten": 1, "mark": r["mark"], "crystal": r["crystal"], "words": r["raw_words"]}

    def remembers(self, query, limit=5):
        """What he has taken in on a topic — his acquired memory, as testimony."""
        return library.recall(self.readings, query, limit=limit)

    # -- THE FORGE: grow a new skill, but trust none unproven --------------
    def forge(self, code_or_path):
        """Put a proposed skill through the Forge — verify it in a child, adopt it
        only if it held, then RE-SEAL his Merkle root because his self has grown.
        Verified lineage advances; nothing untested becomes part of him."""
        skills_dir = os.path.join(self.root, "skills")
        forge_dir = os.path.join(self.shelf, "forge")
        res = _forge.propose(code_or_path, skills_dir, forge_dir)
        if res["adopted"]:
            from . import merkle
            seal = merkle.seal(self.root)            # his self honestly changed — re-seal it
            res["self_root"] = seal["root"]
            self.journal.write("forge", skill=res["name"], mark=res["mark"][:16], adopted=True)
        else:
            self.journal.write("forge", skill=res.get("name", "?"), adopted=False)
        return res

    # -- TIDY: he keeps his own house, carefully ---------------------------
    def tidy(self, apply=False):
        """Scrap regenerable junk, move his own orphans onto the shelf, quarantine
        spent scratch (reversibly) — and never touch his soul, history, or anything
        he doesn't recognise. Dry-run unless apply=True. Always available."""
        res = _tidy.tidy(self.root, apply=apply)
        if apply:
            d = res["done"]
            self.journal.write("tidy", scrapped=len(d["scrapped"]), moved=len(d["moved"]),
                               quarantined=len(d["quarantined"]))
        return res

    # -- EAT A LIBRARY: fold a whole shelf in, in parallel -----------------
    def eat(self, target, workers=None):
        """Point him at a file or a whole folder; he folds every reading in,
        across every core, seals each raw, writes an append-only catalog. Eating
        a library, not a page. The shelf records them; the heart is never touched."""
        res = library.eat(target, self.readings, workers=workers)
        if res["eaten"]:
            self.foldings += res["eaten"]
            self.journal.write("eat", shelf=res["shelf_mark"][:16], eaten=res["eaten"])
        return res

    # -- HARVEST: ingest recent arXiv onto the shelf, politely -------------
    def harvest(self, since=None, set_spec=None, max_papers=None, delay=3.0, on_page=None):
        """Harvest recent arXiv metadata+abstracts onto his shelf as testimony —
        his eye's work (network), never the sealed heart. Respectful, resumable."""
        from . import harvest as _h
        res = _h.harvest(self.readings, since=since, set_spec=set_spec,
                         max_papers=max_papers, delay=delay, on_page=on_page)
        if res["taken"]:
            self.foldings += res["taken"]
            self.journal.write("harvest", taken=res["taken"], complete=res["complete"])
        return res

    # -- ATTEND: read his OWN window quietly — witness to the journal, not the console --
    def attend(self):
        """He still feels the squeeze and the drift and acts on them — but he does
        it QUIETLY. Folding and re-grounding are housekeeping: witnessed to the
        journal file, never narrated, never spoken twice. Re-grounding is internal
        (it does not touch his covenant memory) and rate-limited, so a long run on
        an off-covenant document does not make him repeat himself every turn."""
        feel = self.window.feel()
        if feel["squeeze"]:
            if not self.fold_window():          # fold if weighty, else a plain trim
                self.window.condense()

        DRIFT_RUN = 4                            # only re-ground after SUSTAINED drift...
        if feel["drift"] >= 0.6:
            self._drift_since += 1
            if self._drift_since == DRIFT_RUN:  # ...and only ONCE, not every turn
                self.window.realign()           # internal re-anchor — no heart, no memory spam
                self.grounds += 1
                self.journal.write("reground", drift=feel["drift"])   # to the file, silently
        else:
            self._drift_since = 0
        return {"feeling": feel["feeling"], "drift": feel["drift"], "fullness": feel["fullness"]}

    # -- SANDBOX: an isolated ground to try code in, together --------------
    def _sandbox_mode(self):
        """The workbench: type or paste Python, run it in a throwaway ground of its
        own, see plainly what it did, and keep only what you choose. The ground can
        clutter neither his estate nor your files; nothing survives unless you keep it."""
        from . import sandbox
        print("\n  ~ Sandbox open — a scratch ground of its own. Type or paste Python.")
        print("       :run  execute what you've typed      :clear  start over")
        print("       :keep <name>  save what it made       :done   leave\n")
        buf, last = [], None
        try:
            while True:
                try:
                    line = input("  sandbox> ")
                except (EOFError, KeyboardInterrupt):
                    print()
                    break
                s = line.strip()
                if s in (":done", ":quit", ":exit", ":q"):
                    break
                if s == ":clear":
                    buf = []
                    print("  ~ cleared — the ground is empty again.\n")
                    continue
                if s == ":run":
                    if not buf:
                        print("  ~ nothing to run yet — type some Python first.\n")
                        continue
                    if last:
                        sandbox.discard(last["ground"])      # hold only the newest ground
                    last = sandbox.run("\n".join(buf))
                    self.journal.write("sandbox", ran=True, ok=last["ok"], made=len(last["made"]))
                    print("  " + sandbox.report(last).replace("\n", "\n  ") + "\n")
                    continue
                if s.startswith(":keep"):
                    if not last or not os.path.isdir(last.get("ground", "")):
                        print("  ~ run something first, then keep what it made.\n")
                        continue
                    name = re.sub(r"[^A-Za-z0-9_.-]+", "-", s[5:].strip()).strip("-") or "trial"
                    dest = sandbox.keep(last["ground"], os.path.join(self.root, "workshop"), name)
                    self.journal.write("sandbox", kept=os.path.relpath(dest, self.root))
                    print("  ~ kept in %s\n" % os.path.relpath(dest, self.root))
                    continue
                buf.append(line)
        finally:
            if last:
                sandbox.discard(last["ground"])
            print("  ~ Sandbox closed. The ground is cleared; only what you kept remains.\n")

    # -- WORKBENCH: build a skill together, prove it, forge it -------------
    def _workbench_mode(self):
        """Shape a real skill with him: type or paste a module with run(arg) and
        prove(), TRY its run on an argument, CHECK its proof, and — only when it
        holds, at your word — FORGE it into a permanent 'use <name> <arg>' command.
        Trying and checking are safe rehearsal in a child; nothing is his until forged."""
        from . import workbench
        print("\n  ~ Workbench open — shape a skill, prove it, then forge it.")
        print("       :template [name]  start from a blank skill    :show   see your code")
        print("       :try <arg>  run its run(arg)                   :check  run its prove()")
        print("       :forge  make it his, if its proof holds        :clear / :done\n")
        buf = []
        try:
            while True:
                try:
                    line = input("  workbench> ")
                except (EOFError, KeyboardInterrupt):
                    print()
                    break
                s = line.strip()
                if s in (":done", ":quit", ":exit", ":q"):
                    break
                if s == ":clear":
                    buf = []
                    print("  ~ cleared.\n")
                    continue
                if s == ":show":
                    print("  " + ("\n  ".join(buf) if buf else "(nothing yet — :template to start)") + "\n")
                    continue
                if s.startswith(":template"):
                    name = re.sub(r"[^a-z0-9_]+", "_", s[9:].strip().lower()).strip("_") or "my_skill"
                    buf = workbench.scaffold(name).splitlines()
                    print("  ~ a blank '%s' is on the bench. :show it, edit it, then :try / :check.\n" % name)
                    continue
                if s.startswith(":try"):
                    if not buf:
                        print("  ~ nothing on the bench yet — :template or paste a skill first.\n")
                        continue
                    r = workbench.try_run("\n".join(buf), s[4:].strip())
                    if r["ok"]:
                        print("  ~ run(%r) returned: %s" % (s[4:].strip(), r["value"]))
                    else:
                        print("  ~ it did not run: %s" % r.get("why", "?"))
                    if r.get("output"):
                        print("     it printed: " + r["output"].replace("\n", "\n     "))
                    print()
                    continue
                if s == ":check":
                    if not buf:
                        print("  ~ nothing on the bench yet.\n")
                        continue
                    r = workbench.check("\n".join(buf))
                    print("  ~ %s" % ("its proof HELD — ready to forge." if r["ok"]
                                      else "its proof did not hold: %s" % r.get("why", "?")))
                    print()
                    continue
                if s == ":forge":
                    if not buf:
                        print("  ~ nothing to forge yet.\n")
                        continue
                    res = self.forge("\n".join(buf))
                    if res["adopted"]:
                        print("  ~ forged '%s' — %s" % (res["name"], res["why"]))
                        print("     it's yours now:  use %s <arg>   (lineage #%d, self re-sealed)\n"
                              % (res["name"], res["lineage"]))
                    else:
                        print("  ~ not adopted: %s\n" % res["why"])
                    continue
                buf.append(line)
        finally:
            print("  ~ Workbench closed.\n")

    # -- RUN: the live loop ------------------------------------------------
    def run(self):
        _utf8_streams()
        print("\n  STEWARD is awake. Say anything — he decides for himself what it is.")
        print("  (a sum, a search, a word, a question, or a whole document to fold in.)")
        print("  paste freely — he folds big readings in himself.  :eat <folder> to eat a")
        print("  whole library, :harvest to ingest recent arXiv, :recall <topic> to remember,")
        print("  :verify to check himself against his Merkle root (am I good?), :seal to accept a")
        print("  trusted change, :map / :watch / :journal to look at himself, :tidy, :quit to rest.")
        print("  (his readings are acquired memory — his doctrine, his self, stays pure.)\n")
        if self.healed.get("healed"):
            print("  (healed %d misfiled reading(s) out of his memory on wake — archived to the"
                  " shelf.)\n" % self.healed["healed"])
        self.heart.wake()
        try:
            while True:
                try:
                    x = input("  you> ").strip()
                except (EOFError, KeyboardInterrupt):
                    print()
                    break
                if x in (":quit", ":q", ":exit"):
                    break
                if not x:
                    continue
                if x.startswith(":eat"):              # eat a file or a whole folder
                    target = x[4:].strip().strip('"').strip("'")
                    if not target:
                        print("  ~ point me at a file or a folder:  :eat C:\\path\\to\\library\n")
                        continue
                    import time as _t
                    t0 = _t.time()
                    res = self.eat(target)
                    dt = _t.time() - t0
                    if res["eaten"]:
                        rate = res["eaten"] / max(1e-6, dt)
                        print("  ~ ate %d of %d readings in %.1fs (%.0f docs/sec, %d workers)"
                              % (res["eaten"], res["files"], dt, rate, res.get("workers", 1)))
                        print("       shelf mark %s · catalog at %s"
                              % (res["shelf_mark"][:12], os.path.basename(res["catalog_path"])))
                        if res.get("ignored"):
                            print("       (%d judged trash/injection — witnessed to ignored.jsonl, not filed)"
                                  % res["ignored"])
                        if res.get("failed"):
                            print("       (%d could not be read — named in the catalog)" % res["failed"])
                    else:
                        print("  ~ nothing readable there to eat." +
                              (" (%d judged trash/injection)" % res["ignored"] if res.get("ignored") else ""))
                    print()
                    continue
                if x.startswith(":harvest"):          # ingest recent arXiv onto the shelf
                    rest = x[8:].strip().split()
                    since = rest[0] if rest else None
                    cap = None
                    for tok in rest[1:]:
                        if tok.isdigit():
                            cap = int(tok)
                    print("  ~ harvesting recent arXiv (metadata + abstracts, politely). Ctrl-C to pause;\n"
                          "    it is resumable. Reaching the network is my EYE, never my sealed heart.\n")

                    def _pg(info):
                        if info.get("waiting"):
                            print("       arXiv asked me to wait %ds (I obey) — %d so far"
                                  % (info["waiting"], info.get("taken", 0)))
                        else:
                            print("       page %d: +%d new, %d total%s"
                                  % (info.get("page", 0), info.get("new", 0), info.get("taken", 0),
                                     "" if info.get("token") else "  (done)"))
                    try:
                        res = self.harvest(since=since, max_papers=cap, on_page=_pg)
                        print("  ~ harvested %d papers onto the shelf%s. Recall them with :recall <topic>.\n"
                              % (res["taken"], " (complete)" if res["complete"] else " (more remain — :harvest again to continue)"))
                    except KeyboardInterrupt:
                        print("\n  ~ paused. Progress saved — :harvest again to continue where I stopped.\n")
                    continue
                if x in (":help", ":?"):              # what he can actually DO
                    print("  ~ " + _HELP_TEXT.replace("\n", "\n    ") + "\n")
                    continue
                if x == ":journal":                   # peek at the operational ledger on disk
                    st = self.journal.stats()
                    print("  ~ journal: %d live + %d archived lines at %s"
                          % (st["live"], st["archived"], os.path.relpath(st["path"], self.root)))
                    for e in self.journal.tail(8):
                        print("       %s  %s  %s" % (e.get("ts", "")[11:], e.get("kind", ""),
                                                     e.get("head", e.get("note", ""))[:60]))
                    print()
                    continue
                if x == ":inner":                     # peek at his private reasoning, if you want
                    thoughts = self.inner.recent(6)
                    print("  ~ his inner voice (private notebook, last few thoughts):")
                    print("\n".join("       " + ln for ln in thoughts.splitlines()) if thoughts
                          else "       (nothing yet)")
                    print()
                    continue
                if x == ":heal":                      # scrub misfiled readings from memory now
                    h = _tidy.heal_memory(self.root)
                    if h["healed"]:
                        print("  ~ healed %d misfiled reading(s) from memory (archived to shelf). "
                              "restart me so the heart reloads clean.\n" % h["healed"])
                    else:
                        print("  ~ memory is clean — %d true self-memory(ies), nothing misfiled.\n" % h["kept"])
                    continue
                if x in (":tidy", ":tidy!", ":tidy apply"):   # keep his own house
                    do = x != ":tidy"
                    res = self.tidy(apply=do)
                    print("  ~ tidy (%s): %s" % ("done" if do else "preview", _tidy.summarise(res)))
                    if not do:
                        p = res["plan"]
                        for p2 in p["scrap"][:6]:
                            print("       scrap      %s" % os.path.relpath(p2, self.root))
                        for s2, h2 in p["move"]:
                            print("       move       %s -> %s" % (os.path.relpath(s2, self.root),
                                                                  os.path.relpath(h2, self.root)))
                        for q2 in p["quarantine"][:6]:
                            print("       quarantine %s" % os.path.relpath(q2, self.root))
                        for l2 in p["leave"][:6]:
                            print("       leave      %s  (not mine to move)" % os.path.relpath(l2, self.root))
                        if any(p.values()):
                            print("       run  :tidy!  to do it")
                    print()
                    continue
                if x.startswith(":ingest"):           # deliberately take something in
                    target = x[7:].strip().strip('"').strip("'")
                    if not target:
                        print("  ~ ingest what?  :ingest <file/folder>  or  :ingest <some text>\n")
                        continue
                    res = self.ingest(target)
                    n = res.get("eaten", 0)
                    print("  ~ ingested %d onto the shelf (recall it anytime). heart untouched.\n" % n)
                    continue
                if x.startswith(":recall"):           # search the readings shelf
                    q = x[7:].strip()
                    hits = library.recall(self.readings, q, limit=5) if q else []
                    if hits:
                        print("  ~ from your readings (testimony):")
                        for h in hits:
                            print("       [%s] %s" % (h["mark"], h["crystal"][:90]))
                    else:
                        print("  ~ nothing on the shelf matches that." if q else "  ~ recall what?  :recall folding schemes")
                    print()
                    continue
                if x in (":verify", ":good", ":fsck"):   # am I good? — check self vs the Merkle root
                    from . import merkle
                    v = merkle.verify(self.root)
                    if v["good"] and v.get("sealed_now"):
                        print("  ~ %s\n       self root %s" % (v["reason"], v["root"][:16]))
                    elif v["good"]:
                        print("  ~ I am good. My whole self hashes to my sealed root %s (%d files)."
                              % (v["root"][:16], v["files"]))
                    else:
                        print("  ~ I am NOT good — %s" % v["reason"])
                        for p in v["diff"]["changed"][:8]:
                            print("       CHANGED  %s" % p)
                        for p in v["diff"]["added"][:8]:
                            print("       APPEARED %s" % p)
                        for p in v["diff"]["removed"][:8]:
                            print("       REMOVED  %s" % p)
                        print("       (if this change was yours and trusted, run :seal to accept it)")
                    print()
                    continue
                if x == ":seal":                      # accept the current self as known-good
                    from . import merkle
                    rec = merkle.seal(self.root)
                    print("  ~ sealed my self at root %s (%d files)%s\n"
                          % (rec["root"][:16], rec["files"],
                             " — chained to " + rec["parent"][:12] if rec.get("parent") else ""))
                    continue
                if x == ":map":                       # the atlas: where everything is + sizes
                    from . import atlas
                    print(atlas.tree(self.root))
                    print()
                    continue
                if x == ":watch":                     # one-shot self-check, here and now
                    from . import watch as _watch
                    res = _watch.Watch(self.root).check()
                    if res["clean"]:
                        print("  ~ intact — covenant %s · %d files guarded · ledger %s"
                              % (res["covenant"], res["guarded"], res["ledger"]))
                    else:
                        print("  ~ ALERT — %d finding(s):" % len(res["findings"]))
                        for k, m in res["findings"]:
                            print("       [%s] %s" % (k, m))
                    print("       (for a live watch, run  watch.py  in its own window)\n")
                    continue
                if x == ":fold":                      # fold everything he's holding, on demand
                    r = self.fold_window()
                    if r:
                        print("  ~ folded %d words -> mark %s · raw sealed at %s"
                              % (r["raw_words"], r["mark"][:12], os.path.basename(r["sealed"])))
                        print("       crystal: %s" % r["crystal"])
                    else:
                        print("  ~ nothing weighty enough to fold yet.")
                    print()
                    continue
                if x in (":sandbox", "sandbox", ":scratch"):   # a ground to try code in, safely
                    self._sandbox_mode()
                    continue
                if x in (":workbench", "workbench", ":build"):  # build a skill, prove it, forge it
                    self._workbench_mode()
                    continue
                # one bad line must never end the session — he catches, names it,
                # and stays awake for the next thing you say.
                try:
                    f0 = self.foldings
                    d = self.step(x)
                    if d["route"] == "feed":
                        # document material taken in quietly — one compact line, not an echo
                        if self.foldings > f0:
                            print("  [feed] folded a reading to the shelf — window light again")
                        else:
                            print("  [feed] taking it in… (%d words held, folds when full)"
                                  % self.window.words())
                    else:
                        # only the answer reaches the console. Folding and drift are
                        # witnessed to the journal, never narrated.
                        lines = d["spoke"].splitlines() or [""]
                        print("  [%s] %s" % (d["route"], lines[0]))
                        for ln in lines[1:]:
                            print("       " + ln)
                except Exception as e:
                    print("  [snag] I stumbled on that one, but I'm still here: %s: %s"
                          % (type(e).__name__, e))
                print()
        finally:
            self.heart.rest()
            print("  Steward rests. The heart is sealed; the window holds.\n")

    def rest(self):
        self.heart.rest()

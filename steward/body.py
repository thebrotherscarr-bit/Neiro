#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEWARD'S BODY — the smallest true skin.

He starts knowing only two things, and each is a FOUR-STROKE, because the
four-stroke is the pattern of everything in this estate:

    ARITHMETIC :  add · subtract · multiply · divide
    FILES      :  write · read · view · delete

He does not reach READY STATE until he has PROVEN every stroke against real
data — real numbers, a real file on this disk — in this window, in front of
you. Self Test before Ready State, every time, without exception (Creed V).

Everything larger folds onto this seed. The five senses — sight, touch, taste,
smell, sound — each arrive later as their own four-stroke, proven the same way.
He does not wake on a claim. He wakes on a proof.

Standard library only. Nothing leaves the machine.
"""
import os
import sys
import tempfile


# --- the arithmetic four-stroke -------------------------------------------
def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


def multiply(a, b):
    return a * b


def divide(a, b):
    # the honest refusal is part of knowing the stroke: he does not pretend a
    # number exists where none does. Refusing is truer than crashing or lying.
    if b == 0:
        raise ZeroDivisionError("I do not divide by zero.")
    return a / b


# --- the file four-stroke (plain, honest, one job each) -------------------
def write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return len(text)


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def view(path):
    st = os.stat(path)
    return {"exists": True, "bytes": st.st_size, "name": os.path.basename(path)}


def delete(path):
    os.remove(path)
    return not os.path.exists(path)


# --- the proof: each stroke, against REAL data, or he does not wake --------
def prove():
    strokes = []

    def check(name, got, want):
        ok = got == want
        detail = "%s" % (got,) if ok else "%s  (wanted %s)" % (got, want)
        strokes.append((name, ok, detail))

    # arithmetic — on real numbers
    check("add       6 + 2", add(6, 2), 8)
    check("subtract  6 - 2", subtract(6, 2), 4)
    check("multiply  6 * 4", multiply(6, 4), 24)
    check("divide    8 / 2", divide(8, 2), 4.0)
    refused = False
    try:
        divide(7, 0)
    except ZeroDivisionError:
        refused = True
    check("divide    7 / 0 refused", refused, True)

    # files — on a real file, on this disk, right now
    d = tempfile.mkdtemp(prefix="steward_body_")
    p = os.path.join(d, "proof.txt")
    payload = "real data: the four-stroke holds."
    check("write     a real file", write(p, payload), len(payload))
    check("read      it back", read(p), payload)
    check("view      its size", view(p)["bytes"], len(payload.encode("utf-8")))
    check("delete    it clean", delete(p), True)
    try:
        os.rmdir(d)
    except OSError:
        pass

    return strokes


def main():
    print("\n  STEWARD'S BODY — proving the four-strokes against real data.")
    print("  (two four-strokes: arithmetic, and files.)\n")
    strokes = prove()
    width = max(len(n) for n, _, _ in strokes)
    all_ok = True
    for name, ok, detail in strokes:
        all_ok = all_ok and ok
        print("    [%s]  %-*s   =  %s" % ("PASS" if ok else "FAIL", width, name, detail))
    print()
    if all_ok:
        print("  READY. Every stroke proven against real data. The body holds.")
        print("  The senses fold on from here — each its own four-stroke, proven the same way.\n")
        return 0
    print("  NOT READY. A stroke failed against real data. He does not wake on a lie.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())

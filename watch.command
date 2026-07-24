#!/bin/bash
cd "$(dirname "$0")" || exit 1
echo
if command -v python3 >/dev/null 2>&1; then python3 watch.py "$1" "$2"
elif command -v python >/dev/null 2>&1; then python watch.py "$1" "$2"
else echo "  I could not find Python 3."; fi

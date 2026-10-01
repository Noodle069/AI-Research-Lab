#!/bin/bash
# Launcher: creates .venv on first run (needs internet once, for pip), then starts the app.
# Dependencies come from requirements.lock (exact versions, hash-checked) when present.
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  /usr/bin/python3 -m venv .venv
  if [ -f requirements.lock ]; then
    .venv/bin/pip install --disable-pip-version-check --require-hashes --only-binary=:all: -r requirements.lock
  else
    .venv/bin/pip install --disable-pip-version-check -r requirements.txt
  fi
fi
if [ -f .env ]; then set -a; . ./.env; set +a; fi
exec .venv/bin/python run.py

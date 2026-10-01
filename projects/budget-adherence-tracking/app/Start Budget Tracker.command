#!/bin/bash
# Double-click launcher for macOS. Starts the Budget Tracker on this Mac only (127.0.0.1)
# and opens the private link in your browser. Close the app with Control+C in this window.
cd "$(dirname "$0")" || exit 1
export BUDGET_DATA_DIR="${BUDGET_DATA_DIR:-$HOME/BudgetTrackerData}"

# First run: build the private Python environment (needs internet once, only for this step).
if [ ! -x .venv/bin/python ]; then
  echo "First run: setting up (needs internet once, takes a minute)..."
  if ! /usr/bin/python3 -m venv .venv; then
    echo "Could not create the Python environment. Install Apple's command line tools if asked, then try again."
    read -r -p "Press Return to close." _; exit 1
  fi
  if [ -f requirements.lock ]; then
    .venv/bin/pip install --disable-pip-version-check --require-hashes --only-binary=:all: -r requirements.lock
  else
    .venv/bin/pip install --disable-pip-version-check -r requirements.txt
  fi
  if [ $? -ne 0 ]; then
    rm -rf .venv
    echo "Setup failed (is the internet on?). Nothing was changed. Try again."
    read -r -p "Press Return to close." _; exit 1
  fi
fi

echo "Your data folder: $BUDGET_DATA_DIR"
echo "Starting. Keep this window open while you use the app. Press Control+C here to stop."
# Read the app's output line by line; open the one-time link (it contains a private token) in the browser.
while IFS= read -r line; do
  echo "$line"
  case "$line" in
    *"http://127.0.0.1:"*"/enter?t="*) open "$(echo "$line" | tr -d ' ')" ;;
  esac
done < <(.venv/bin/python -u run.py 2>&1)
echo
echo "The app has stopped."
read -r -p "Press Return to close." _

"""Start the app on 127.0.0.1 only. Prints a one-time link containing a per-launch token."""
import os
import sys

from werkzeug.serving import make_server

from budget_app import HOST, create_app
from budget_app.datadir import resolve_data_dir


def main():
    data_dir = resolve_data_dir(os.environ.get("BUDGET_DATA_DIR"))
    port = int(os.environ.get("BUDGET_PORT", "5055"))
    app = create_app(data_dir, port=port, backup_keep=os.environ.get("BUDGET_BACKUP_KEEP"))
    # Bind first, print the link only if that worked. An old copy still holding the port would
    # otherwise answer with "Forbidden", because the link's key belongs to this new copy.
    try:
        server = make_server(HOST, port, app, threaded=True)
    except (OSError, SystemExit):  # werkzeug exits (not raises) when the port is taken
        print(f"The Budget Tracker cannot start: port {port} is already in use.\n"
              "It is probably still running in another Terminal window. Click that window and press "
              "Control+C to stop it, then start the app again.", flush=True)
        return 1
    print(f"Open this link in your browser (valid until you stop the app):\n  http://{HOST}:{port}/enter?t={app.config['LAUNCH_TOKEN']}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    sys.exit(main())

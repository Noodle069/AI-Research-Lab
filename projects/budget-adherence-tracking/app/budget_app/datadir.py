import os
from pathlib import Path


def resolve_data_dir(raw):
    """Validate the user's data folder: must be set and not somewhere iCloud may sync."""
    if not raw:
        raise SystemExit("BUDGET_DATA_DIR is not set. Choose a folder outside ~/Documents, ~/Desktop and iCloud.")
    p = Path(raw).expanduser().resolve()
    home = Path.home().resolve()
    banned = [home / "Documents", home / "Desktop", home / "Library" / "Mobile Documents"]
    for b in banned:
        if p == b or b in p.parents:
            raise SystemExit(f"Refusing data folder inside {b.name}: it may sync to iCloud. Pick another folder.")
    p.mkdir(parents=True, exist_ok=True)
    os.chmod(p, 0o700)
    return p

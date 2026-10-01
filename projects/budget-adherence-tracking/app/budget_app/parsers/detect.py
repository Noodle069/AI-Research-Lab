"""Layout auto-detection. Exactly one layout must match; otherwise the file is rejected."""
from pathlib import Path

from . import ing_short, ing_statement, nab_card, offset_listing
from .common import ParseRejected

PARSERS = (ing_statement, ing_short, nab_card, offset_listing)


MAX_PAGES = 150          # real statements are a few pages; checked before any text extraction
PARSE_TIMEOUT_S = 30     # wall clock for the whole parse in the worker process
MAX_PARSE_BYTES = 10 * 1024 * 1024


def parse_pdf(fileobj):
    """fileobj: path or binary file-like. Raises ParseRejected on any failure."""
    import pdfplumber
    try:
        with pdfplumber.open(fileobj) as pdf:
            if len(pdf.pages) > MAX_PAGES:
                raise ParseRejected([f"The PDF has more than {MAX_PAGES} pages. Nothing imported."])
            pages_words = [p.extract_words(x_tolerance=1.5) for p in pdf.pages]
    except ParseRejected:
        raise
    except Exception:
        raise ParseRejected(["Could not read the file as a PDF with selectable text. Nothing imported."])
    hits = [p for p in PARSERS if p.detect(pages_words)]
    if not hits:
        raise ParseRejected(["Unrecognised layout: no supported statement header was found. Nothing imported."])
    if len(hits) > 1:
        raise ParseRejected(["Ambiguous layout: more than one supported layout matched. Nothing imported."])
    return hits[0].parse_pages(pages_words)


def _run_worker(cmd, data, timeout):
    """Run the worker, feed it the bytes, return its pickled result. Kills it on timeout."""
    import pickle
    import subprocess
    try:
        proc = subprocess.run(cmd, input=data, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=timeout,
                              cwd=str(Path(__file__).resolve().parents[2]))
    except subprocess.TimeoutExpired:       # subprocess.run kills the child before raising
        raise ParseRejected([f"Reading the file took longer than {timeout} seconds, so it was stopped. Nothing imported."])
    try:
        kind, payload = pickle.loads(proc.stdout)   # our own worker's output, never file content
    except Exception:
        raise ParseRejected(["Could not read the file as a PDF with selectable text. Nothing imported."])
    if kind == "rejected":
        raise ParseRejected(payload)
    return payload


def parse_pdf_bounded(data, timeout=None):
    """Parse upload bytes with cheap pre-checks and a wall-clock timeout (separate process, killed on timeout)."""
    import sys
    if len(data) > MAX_PARSE_BYTES:
        raise ParseRejected(["File is too large. Nothing imported."])
    if b"%PDF-" not in data[:1024]:
        raise ParseRejected(["This is not a PDF file. Nothing imported."])
    cmd = [sys.executable, "-m", "budget_app.parsers.worker"]
    return _run_worker(cmd, data, timeout or PARSE_TIMEOUT_S)

"""Worker process: reads PDF bytes on stdin, writes a pickled ("ok", parsed) or ("rejected", errors) to stdout."""
import io
import pickle
import sys

from .common import ParseRejected
from .detect import parse_pdf


def main():
    data = sys.stdin.buffer.read()
    try:
        out = ("ok", parse_pdf(io.BytesIO(data)))
    except ParseRejected as e:
        out = ("rejected", list(e.errors))
    sys.stdout.buffer.write(pickle.dumps(out))


if __name__ == "__main__":
    main()

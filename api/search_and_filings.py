"""Search first, then explicitly choose a reporting entity. One call per invocation."""
import argparse
from client import APIError, display, get

parser = argparse.ArgumentParser(description=__doc__)
selection = parser.add_mutually_exclusive_group(required=True)
selection.add_argument("--search", metavar="NAME")
selection.add_argument("--cik", type=int, metavar="CIK")
args = parser.parse_args()
if args.cik is not None and args.cik <= 0:
    parser.error("CIK must be positive")
try:
    if args.search is not None:
        display(get("/api/v1/search", q=args.search, limit=5))
    else:
        display(get(f"/api/v1/funds/{args.cik}/filings", limit=10))
except APIError as exc:
    parser.exit(1, str(exc) + "\n")

"""Read one bounded portfolio page, retaining citations, units and quota metadata."""
import argparse
import re
from client import APIError, display, get

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("cik", type=int)
parser.add_argument("--quarter", help="YYYYqN; omitted means latest locally available")
parser.add_argument("--page", type=int, default=1)
parser.add_argument("--limit", type=int, default=10)
args = parser.parse_args()
if args.cik <= 0 or not 1 <= args.page <= 10000 or not 1 <= args.limit <= 100:
    parser.error("Use a positive CIK, page 1–10000 and limit 1–100")
if args.quarter and not re.fullmatch(r"\d{4}q[1-4]", args.quarter):
    parser.error("quarter must be YYYYqN")
params = {"view": "summary", "limit": args.limit, "page": args.page, "sort": "value"}
if args.quarter:
    params["quarter"] = args.quarter
try:
    display(get(f"/api/v1/funds/{args.cik}/portfolio", **params))
except APIError as exc:
    parser.exit(1, str(exc) + "\n")

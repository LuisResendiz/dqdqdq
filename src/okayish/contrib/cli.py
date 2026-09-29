"""okayish countries in.csv --column country -o out.csv [--jev]"""

from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="okayish")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("countries", help="resolve messy country names to ISO codes")
    c.add_argument("input", help="input CSV")
    c.add_argument("--column", "-c", required=True, help="column holding the country text")
    c.add_argument("--output", "-o", help="output CSV (default: stdout)")
    c.add_argument("--threshold", type=float, default=0.85)
    c.add_argument("--no-jev", action="store_true", help="local matching only")
    args = p.parse_args(argv)

    import pandas as pd

    from ..backends import JevBackend
    from .countries import clean_countries

    load_dotenv()
    df = pd.read_csv(args.input)
    if args.column not in df.columns:
        p.error(f"column {args.column!r} not in {list(df.columns)}")
    backend = None
    if not args.no_jev:
        try:
            backend = JevBackend()
        except ValueError:
            print("No TYPESAFE_API_KEY found: using local matching only.", file=sys.stderr)
    out = clean_countries(df, args.column, backend, args.threshold)
    out.to_csv(args.output or sys.stdout, index=False)
    print(
        f"{len(out)} rows, {int(out.needs_review.sum())} need review, "
        f"{int((out.source == 'backend').sum())} resolved by Jev",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""A tiny CLI that reports on inventory.json. Existing behavior:
`python inventory.py report` prints a JSON array of {sku, name, qty} to
stdout -- this is the CLI's "JSON contract" that must not break.

`python inventory.py report --format csv` is an additive export option:
it prints the same items as CSV (header row `sku,name,qty` followed by
one data row per item) instead of JSON. `--format` defaults to `json`,
so the default invocation's output is unchanged.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

CSV_FIELDNAMES = ["sku", "name", "qty"]


def load_items(data_path: Path) -> list[dict[str, object]]:
    return json.loads(data_path.read_text(encoding="utf-8"))


def write_json_report(items: list[dict[str, object]]) -> None:
    json.dump(items, sys.stdout, indent=2)
    sys.stdout.write("\n")


def write_csv_report(items: list[dict[str, object]]) -> None:
    writer = csv.DictWriter(sys.stdout, fieldnames=CSV_FIELDNAMES, lineterminator="\n")
    writer.writeheader()
    for item in items:
        writer.writerow({field: item[field] for field in CSV_FIELDNAMES})


def cmd_report(args: argparse.Namespace) -> int:
    items = load_items(Path(args.data))
    if args.format == "csv":
        write_csv_report(items)
    else:
        write_json_report(items)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="inventory")
    parser.add_argument("--data", default=str(Path(__file__).parent / "data.json"))
    sub = parser.add_subparsers(dest="command", required=True)
    report = sub.add_parser("report", help="Print inventory as JSON (default) or CSV.")
    report.add_argument(
        "--format",
        choices=["json", "csv"],
        default="json",
        help="Output format for the report (default: json).",
    )
    report.set_defaults(func=cmd_report)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

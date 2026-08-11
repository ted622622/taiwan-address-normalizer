from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from .normalizer import normalize_with_report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tw-address", description="Normalize Taiwan addresses.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    normalize_parser = subparsers.add_parser("normalize", help="Normalize one address or newline-delimited stdin.")
    normalize_parser.add_argument("address", nargs="?", help="Address text. Reads stdin when omitted.")
    normalize_parser.add_argument("--mode", choices=("safe", "aggressive"), default="safe")
    normalize_parser.add_argument("--json", action="store_true", dest="as_json")

    batch_parser = subparsers.add_parser("batch", help="Normalize an address column in a CSV file.")
    batch_parser.add_argument("input", type=Path)
    batch_parser.add_argument("--column", required=True, help="CSV column containing the address.")
    batch_parser.add_argument("--output", type=Path, required=True)
    batch_parser.add_argument("--mode", choices=("safe", "aggressive"), default="safe")
    batch_parser.add_argument(
        "--allow-formulas",
        action="store_true",
        help="Do not escape cells that spreadsheet software may interpret as formulas.",
    )
    return parser


def _result_payload(result: object) -> dict[str, object]:
    return result.as_dict()  # type: ignore[attr-defined]


def _normalize_command(args: argparse.Namespace) -> int:
    values = [args.address] if args.address is not None else [line.rstrip("\r\n") for line in sys.stdin]
    for value in values:
        result = normalize_with_report(value, mode=args.mode)
        if args.as_json:
            print(json.dumps(_result_payload(result), ensure_ascii=False))
        else:
            print(result.normalized)
    return 0


def _batch_command(args: argparse.Namespace) -> int:
    with args.input.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames:
            raise SystemExit("CSV has no header row.")
        duplicates = sorted({name for name in reader.fieldnames if reader.fieldnames.count(name) > 1})
        if duplicates:
            names = ", ".join(duplicates)
            raise SystemExit(f"Duplicate CSV columns are not allowed: {names}")
        if args.column not in reader.fieldnames:
            available = ", ".join(reader.fieldnames or []) or "(none)"
            raise SystemExit(f"Column {args.column!r} not found. Available columns: {available}")
        rows = list(reader)
        for row_number, row in enumerate(rows, start=2):
            if None in row:
                raise SystemExit(f"Row {row_number} has more columns than the header.")
        reserved = {"normalized_address", "address_warnings"}
        conflicts = reserved.intersection(reader.fieldnames)
        if conflicts:
            names = ", ".join(sorted(conflicts))
            raise SystemExit(f"Output column already exists: {names}")
        fieldnames = [*reader.fieldnames, "normalized_address", "address_warnings"]

    processed_rows: list[dict[str, object]] = []
    for row in rows:
        result = normalize_with_report(row.get(args.column, ""), mode=args.mode)
        processed: dict[str, object] = {
            **row,
            "normalized_address": result.normalized,
            "address_warnings": "|".join(result.warnings),
        }
        if not args.allow_formulas:
            processed = {key: _excel_safe_cell(value) for key, value in processed.items()}
        processed_rows.append(processed)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fieldnames)
        writer.writeheader()
        for row in processed_rows:
            writer.writerow(row)
    print(f"Normalized {len(rows)} rows -> {args.output}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "normalize":
        return _normalize_command(args)
    if args.command == "batch":
        return _batch_command(args)
    raise AssertionError(f"Unhandled command: {args.command}")


def _excel_safe_cell(value: object) -> object:
    if not isinstance(value, str):
        return value
    if value.lstrip().startswith(("=", "+", "-", "@")):
        return f"'{value}"
    return value

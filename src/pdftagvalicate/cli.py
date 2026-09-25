"""Command-line interface for pdftagvalicate.

Designed to be invoked both by humans and by an LLM tool-calling loop (e.g.
Claude Code shelling out to it): pass --json to get a single machine-parsable
JSON object on stdout instead of the human-readable log, and rely on the
process exit code to know whether anything changed or any issues were found.

Two modes:

* repair (default): apply the selected repairs and write the output file.
* check (--check): report-only; count problems found, write nothing.

Exit codes: 0 = nothing to repair / no issues, 1 = repairs made (or needed,
for --dry-run) / issues found, 2 = error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pikepdf

from .checks import run_checks
from .repairs import run_repairs
from .types import CheckOptions, RepairOptions, RepairReport


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdftagvalicate",
        description="PDF/UA tag-tree validator and auto-repair tool (pikepdf-based).",
    )
    parser.add_argument("input", type=Path, help="Path to the input PDF.")
    parser.add_argument(
        "output",
        type=Path,
        nargs="?",
        help="Path to write the repaired PDF (required in repair mode unless --dry-run).",
    )

    mode = parser.add_argument_group("mode")
    mode.add_argument(
        "--check",
        action="store_true",
        help="Run report-only checks (no output file written) instead of repairs.",
    )

    repairs = parser.add_argument_group("repairs")
    repairs.add_argument("--all", action="store_true", help="Apply all safe repairs (default when no repair flag given).")
    repairs.add_argument("--metadata", action="store_true", help="Fix pdfuaid:part, /ViewerPreferences, /MarkInfo.")
    repairs.add_argument("--title", action="store_true", help="Back-fill dc:title from /Info /Title when missing.")
    repairs.add_argument("--lang", action="store_true", help="Set catalog /Lang from XMP dc:language when missing.")
    repairs.add_argument(
        "--lang-value",
        metavar="CODE",
        help="Explicit language code to use for --lang (e.g. en-US).",
    )
    repairs.add_argument("--th-scope", action="store_true", help="Add /Scope attribute to <TH> cells missing it.")
    repairs.add_argument(
        "--link-nesting", action="store_true", help="Wrap orphaned Link annotations inside <Link> struct elements."
    )
    repairs.add_argument("--fix-tbody", action="store_true", help="Dissolve fake Table->TBody->TR->TD wrapper chains.")

    checks = parser.add_argument_group("checks")
    checks.add_argument("--alt-text", action="store_true", help="Report <Figure> elements missing /Alt.")
    checks.add_argument("--fonts", action="store_true", help="Report unembedded / Type3 / missing-ToUnicode fonts.")
    checks.add_argument("--suspects", action="store_true", help="Report the /MarkInfo /Suspects flag.")

    parser.add_argument(
        "--dry-run", action="store_true", help="Report what would change without writing an output file."
    )
    parser.add_argument("--json", action="store_true", help="Print a single JSON report to stdout instead of logs.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.input.exists():
        return _fail(f"File not found: {args.input}", as_json=args.json)

    if args.check:
        return _run_check_mode(args)
    return _run_repair_mode(parser, args)


def _run_repair_mode(parser: argparse.ArgumentParser, args) -> int:
    if not args.dry_run and args.output is None:
        parser.error("output path is required unless --dry-run is given")

    options = _repair_options(args)

    if not args.json:
        print(f"pdftagvalicate: {args.input.name}")
        if options.dry_run:
            print("(dry-run - no file will be written)")
        print("=" * 72)

    try:
        reports = _run(args.input, args.output, options)
    except Exception as ex:  # noqa: BLE001
        return _fail(f"Error: {ex}", as_json=args.json)

    total_fixed = sum(r.fixed for r in reports)

    if args.json:
        print(
            json.dumps(
                {
                    "input": str(args.input),
                    "output": str(args.output) if args.output else None,
                    "mode": "repair",
                    "dry_run": options.dry_run,
                    "total_fixed": total_fixed,
                    "reports": [r.to_dict() for r in reports],
                },
                indent=2,
            )
        )
    else:
        for r in reports:
            status = "FIXED" if r.fixed > 0 else "OK   "
            print(f"[{status}] {r.name}")
            if r.detail:
                print(f"         {r.detail}")
        print()
        if options.dry_run:
            print(f"Dry-run summary: {total_fixed} item(s) would be repaired.")
        elif total_fixed > 0:
            print(f"Repaired {total_fixed} item(s). Written to: {args.output}")
        else:
            print(f"Nothing to repair. Written to: {args.output}")

    return 1 if total_fixed > 0 else 0


def _run_check_mode(args) -> int:
    options = CheckOptions(
        alt_text=args.alt_text,
        fonts=args.fonts,
        suspects=args.suspects,
    )
    if not options.any_selected:
        options = CheckOptions.all()

    if not args.json:
        print(f"pdftagvalicate: {args.input.name}")
        print("(check mode - report only, no file written)")
        print("=" * 72)

    try:
        with pikepdf.open(args.input) as pdf:
            reports = run_checks(pdf, options)
    except Exception as ex:  # noqa: BLE001
        return _fail(f"Error: {ex}", as_json=args.json)

    total_issues = sum(r.issues for r in reports)

    if args.json:
        print(
            json.dumps(
                {
                    "input": str(args.input),
                    "mode": "check",
                    "total_issues": total_issues,
                    "reports": [r.to_dict() for r in reports],
                },
                indent=2,
            )
        )
    else:
        for r in reports:
            status = "ISSUES" if r.issues > 0 else "OK    "
            print(f"[{status}] {r.name}")
            if r.detail:
                print(f"         {r.detail}")
        print()
        if total_issues > 0:
            print(f"Check summary: {total_issues} issue(s) found.")
        else:
            print("Check summary: no issues found.")

    return 1 if total_issues > 0 else 0


def _repair_options(args) -> RepairOptions:
    options = RepairOptions(
        metadata=args.metadata,
        title=args.title,
        lang=args.lang,
        lang_value=args.lang_value,
        th_scope=args.th_scope,
        link_nesting=args.link_nesting,
        fix_tbody=args.fix_tbody,
        dry_run=args.dry_run,
    )
    if args.all or not options.any_selected:
        options = RepairOptions.all(dry_run=args.dry_run)
        options.lang_value = args.lang_value
    return options


def _run(input_path: Path, output_path: Path | None, options: RepairOptions) -> list[RepairReport]:
    if options.dry_run:
        with pikepdf.open(input_path) as pdf:
            return run_repairs(pdf, options)

    with pikepdf.open(input_path) as pdf:
        reports = run_repairs(pdf, options)
        pdf.save(output_path)
        return reports


def _fail(message: str, *, as_json: bool) -> int:
    if as_json:
        print(json.dumps({"error": message}))
    else:
        print(message, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())

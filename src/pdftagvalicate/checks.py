"""Orchestrates running the selected set of checks against an open PDF."""

from __future__ import annotations

import pikepdf

from . import (
    alt_text_check,
    font_check,
    lang_check,
    link_nesting_check,
    metadata_check,
    suspects_check,
    tbody_check,
    th_scope_check,
    title_check,
)
from .types import CheckOptions, CheckReport


def run_checks(pdf: pikepdf.Pdf, options: CheckOptions) -> list[CheckReport]:
    reports: list[CheckReport] = []

    if options.metadata:
        _run_one(reports, lambda: metadata_check.check_pdf_ua_identifier(pdf))
        _run_one(reports, lambda: metadata_check.check_mark_info(pdf))
        _run_one(reports, lambda: metadata_check.check_display_doc_title(pdf))
    if options.title:
        _run_one(reports, lambda: title_check.check(pdf))
    if options.lang:
        _run_one(reports, lambda: lang_check.check(pdf))
    if options.th_scope:
        _run_one(reports, lambda: th_scope_check.check(pdf))
    if options.link_nesting:
        _run_one(reports, lambda: link_nesting_check.check(pdf))
    if options.fix_tbody:
        _run_one(reports, lambda: tbody_check.check(pdf))
    if options.alt_text:
        _run_one(reports, lambda: alt_text_check.check(pdf))
    if options.fonts:
        _run_one(reports, lambda: font_check.check(pdf))
    if options.suspects:
        _run_one(reports, lambda: suspects_check.check(pdf))

    return reports


def _run_one(reports: list[CheckReport], check) -> None:
    """Runs a single check, catching any unexpected exception so the others
    still run; surfaces the failure as a zero-issue report."""
    try:
        reports.append(check())
    except Exception as ex:  # noqa: BLE001
        reports.append(CheckReport(type(ex).__name__, 0, f"Unexpected error: {ex}"))

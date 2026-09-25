"""Orchestrates running the selected set of repairs against an open PDF."""

from __future__ import annotations

import pikepdf

from . import (
    lang_repair,
    link_nesting_repair,
    metadata_repairs,
    tbody_repair,
    th_scope_repair,
    title_repair,
)
from .types import RepairOptions, RepairReport


def run_repairs(pdf: pikepdf.Pdf, options: RepairOptions) -> list[RepairReport]:
    reports: list[RepairReport] = []

    if options.metadata:
        _run_one(reports, lambda: metadata_repairs.fix_pdf_ua_identifier(pdf))
        _run_one(reports, lambda: metadata_repairs.fix_mark_info(pdf))
        _run_one(reports, lambda: metadata_repairs.fix_display_doc_title(pdf))
    if options.title:
        _run_one(reports, lambda: title_repair.fix(pdf))
    if options.lang:
        _run_one(reports, lambda: lang_repair.fix(pdf, options.lang_value))
    if options.fix_tbody:
        _run_one(reports, lambda: tbody_repair.fix(pdf))
    if options.th_scope:
        _run_one(reports, lambda: th_scope_repair.fix(pdf))
    if options.link_nesting:
        _run_one(reports, lambda: link_nesting_repair.fix(pdf))

    return reports


def _run_one(reports: list[RepairReport], repair) -> None:
    """Runs a single repair, catching any unexpected exception so the others
    still run; surfaces the failure as a zero-fixed report."""
    try:
        reports.append(repair())
    except Exception as ex:  # noqa: BLE001
        reports.append(RepairReport(type(ex).__name__, 0, f"Unexpected error: {ex}"))

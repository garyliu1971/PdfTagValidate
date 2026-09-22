"""Dissolve fake Table -> TBody -> TR -> TD wrapper chains.

A "fake table" is a <Table> struct element that (a) has no <THead>/<TFoot>
siblings and (b) wraps exactly one <TBody> -> one <TR> -> one <TD>/<TH>, with
no actual tabular content. Such chains are sometimes produced by upstream
conversion tools and confuse assistive technology, so we dissolve them by
re-parenting the cell's children directly under the table's original parent.
"""

from __future__ import annotations

import pikepdf
from pikepdf import Array, Dictionary, Name

from .pdfutil import get_kids, replace_kid, role_of
from .types import RepairReport


def fix(pdf: pikepdf.Pdf) -> RepairReport:
    name = "Fake TBody wrappers"

    from .pdfutil import is_tagged

    if not is_tagged(pdf):
        return RepairReport(name, 0, "Document is not tagged - skipped.")

    struct_root = pdf.Root.get(Name.StructTreeRoot)
    if struct_root is None:
        return RepairReport(name, 0, "No struct tree root - skipped.")

    tables: list[Dictionary] = []
    _collect_by_role(struct_root.get(Name.K), "Table", tables, set())

    changes = 0
    for table in tables:
        try:
            if _try_fix_fake_table(table):
                changes += 1
        except Exception:  # noqa: BLE001 - one malformed table shouldn't abort the rest
            continue

    if changes > 0:
        return RepairReport(name, changes, f"Dissolved {changes} fake Table->TBody->TR->TD chain(s).")
    return RepairReport(name, 0, "No fake-table wrappers found.")


# ---- helpers ---------------------------------------------------------------


def _try_fix_fake_table(table: Dictionary) -> bool:
    if _has_kid_role(table, "THead") or _has_kid_role(table, "TFoot"):
        return False

    tbody = _get_single_kid_by_role(table, "TBody")
    if tbody is None:
        return False

    tr = _get_single_kid_by_role(tbody, "TR")
    if tr is None:
        return False

    cell = _get_single_kid_by_role(tr, "TD") or _get_single_kid_by_role(tr, "TH")
    if cell is None:
        return False

    parent = table.get(Name.P)
    if not isinstance(parent, Dictionary):
        return False

    children = get_kids(cell)
    if not children:
        return False

    for child in children:
        if isinstance(child, Dictionary):
            child[Name.P] = parent

    return replace_kid(parent, table, children)


def _collect_by_role(k, role: str, result: list, visited: set) -> None:
    if k is None:
        return
    if isinstance(k, Array):
        for item in k:
            _collect_by_role(item, role, result, visited)
        return
    if not isinstance(k, Dictionary):
        return

    visit_key = _visit_key(k)
    if visit_key in visited:
        return
    visited.add(visit_key)

    if role_of(k) == role:
        result.append(k)
    _collect_by_role(k.get(Name.K), role, result, visited)


def _get_all_dict_kids(elem: Dictionary) -> list:
    return [k for k in get_kids(elem) if isinstance(k, Dictionary)]


def _has_kid_role(elem: Dictionary, role: str) -> bool:
    if _get_single_kid_by_role(elem, role) is not None:
        return True
    return any(role_of(d) == role for d in _get_all_dict_kids(elem))


def _get_single_kid_by_role(elem: Dictionary, role: str) -> Dictionary | None:
    kids = _get_all_dict_kids(elem)
    if len(kids) == 1 and role_of(kids[0]) == role:
        return kids[0]
    return None


def _visit_key(obj):
    objgen = getattr(obj, "objgen", (0, 0))
    return objgen if objgen != (0, 0) else id(obj)

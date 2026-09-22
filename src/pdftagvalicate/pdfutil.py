"""Small helpers shared across repair modules.

pikepdf transparently dereferences indirect references when you read a
dictionary/array value, so unlike the original iText port we rarely need to
resolve references by hand. The one place identity still matters is when we
need to find *which* slot in a parent's /K array holds a particular struct
element so we can replace or remove it — for that we compare by (obj, gen)
via ``same_object``.
"""

from __future__ import annotations

from typing import Iterable, Optional

import pikepdf
from pikepdf import Array, Dictionary, Name, Object


def is_tagged(pdf: pikepdf.Pdf) -> bool:
    """Mirrors iText's PdfDocument.IsTagged(): a StructTreeRoot exists and
    /MarkInfo /Marked is true."""
    root = pdf.Root
    struct_root = root.get(Name.StructTreeRoot)
    mark_info = root.get(Name.MarkInfo)
    marked = bool(mark_info.get(Name.Marked)) if mark_info is not None else False
    return struct_root is not None and marked


def ensure_tagged(pdf: pikepdf.Pdf) -> None:
    """Mirrors iText's PdfDocument.SetTagged(): ensure /MarkInfo /Marked and a
    minimal /StructTreeRoot both exist."""
    root = pdf.Root

    mark_info = root.get(Name.MarkInfo)
    if mark_info is None:
        mark_info = pdf.make_indirect(Dictionary())
        root[Name.MarkInfo] = mark_info
    mark_info[Name.Marked] = True

    if root.get(Name.StructTreeRoot) is None:
        struct_root = pdf.make_indirect(
            Dictionary(Type=Name.StructTreeRoot, ParentTree=Dictionary(Nums=Array([])))
        )
        root[Name.StructTreeRoot] = struct_root


def get_kids(elem: Dictionary) -> list:
    """Returns the raw contents of /K as a Python list, regardless of whether
    /K is a single value or an array. Kids may be struct-element
    dictionaries, OBJR/MCR dictionaries, or bare MCIDs (ints)."""
    k = elem.get(Name.K)
    if k is None:
        return []
    if isinstance(k, Array):
        return list(k)
    return [k]


def get_struct_kids(elem: Dictionary) -> list:
    """Kids of /K that are themselves struct elements (i.e. have /S)."""
    return [k for k in get_kids(elem) if isinstance(k, Dictionary) and Name.S in k]


def role_of(elem) -> Optional[str]:
    if not isinstance(elem, Dictionary):
        return None
    name = elem.get(Name.S)
    return str(name)[1:] if name is not None else None  # strip leading '/'


def same_object(a: Object, b: Object) -> bool:
    """Identity comparison that works for both indirect and direct objects."""
    try:
        a_ref, b_ref = a.objgen, b.objgen
    except AttributeError:
        return a is b
    if a_ref != (0, 0) or b_ref != (0, 0):
        return a_ref == b_ref
    return a is b


def replace_kid(parent: Dictionary, old_kid: Dictionary, new_kids: Iterable[Object]) -> bool:
    """Replaces old_kid inside parent's /K with new_kids (0, 1 or many)."""
    new_kids = list(new_kids)
    k = parent.get(Name.K)
    if isinstance(k, Array):
        for i, item in enumerate(k):
            if same_object(item, old_kid):
                items = list(k)
                items[i:i + 1] = new_kids
                parent[Name.K] = Array(items)
                return True
        return False
    if k is not None and same_object(k, old_kid):
        if len(new_kids) == 1:
            parent[Name.K] = new_kids[0]
        else:
            parent[Name.K] = Array(new_kids)
        return True
    return False


def append_kid(parent: Dictionary, new_kid: Object) -> None:
    """Appends new_kid to parent's /K, upgrading a single value to an array
    as needed (mirrors LinkNestingRepair.AppendKid)."""
    k = parent.get(Name.K)
    if isinstance(k, Array):
        k.append(new_kid)
        return
    if k is not None:
        parent[Name.K] = Array([k, new_kid])
        return
    parent[Name.K] = new_kid

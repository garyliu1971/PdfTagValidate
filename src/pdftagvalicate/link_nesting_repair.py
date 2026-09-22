"""Wrap orphaned Link annotations in a <Link> struct element with an OBJR.

A Link annotation that has no corresponding <Link> struct element (and thus
no /StructParent back-reference) is invisible to assistive technology even
though it's visually present and clickable. This repair finds every Link
annotation not already referenced from a <Link> element, and:

  1. creates a <Link> struct element (parented under the document's
     top-level <Document> element, creating one if needed),
  2. points it at the annotation via an OBJR,
  3. registers the pair in the structure's ParentTree, and
  4. sets the annotation's own /StructParent key.
"""

from __future__ import annotations

import pikepdf
from pikepdf import Array, Dictionary, Name

from .pdfutil import append_kid, ensure_tagged, get_kids, is_tagged, role_of
from .types import RepairReport


def fix(pdf: pikepdf.Pdf) -> RepairReport:
    name = "Link annotation nesting"

    # Step 1: collect annotation obj-numbers already referenced from <Link> elements.
    tagged_obj_nums: set[int] = set()
    existing_root = pdf.Root.get(Name.StructTreeRoot)
    if existing_root is not None:
        _collect_tagged(existing_root, tagged_obj_nums, parent_is_link=False)

    # Step 2: ensure the document has a struct tree with a <Document> root element.
    if not is_tagged(pdf):
        try:
            ensure_tagged(pdf)
        except Exception as ex:  # noqa: BLE001
            return RepairReport(name, 0, f"Could not enable tagging on this document: {ex}")

    root = pdf.Root.get(Name.StructTreeRoot)

    # Step 3: find or create the <Document> struct element.
    doc_elem = _find_document_element(root) or _create_document_element(pdf, root)

    # Step 4: prepare the parent tree for new entries.
    parent_tree = _ensure_parent_tree(pdf, root)
    nums = _ensure_nums(parent_tree)
    next_key = _next_parent_tree_key(nums, root)

    fixed = 0

    for page in pdf.pages:
        annots = page.get(Name.Annots)
        if annots is None:
            continue

        for annot in annots:
            if not isinstance(annot, Dictionary):
                continue
            if annot.get(Name.Subtype) != Name.Link:
                continue

            objgen = getattr(annot, "objgen", (0, 0))
            if objgen == (0, 0) or objgen[0] in tagged_obj_nums:
                continue

            page_obj = page.obj

            obj_ref = Dictionary(Type=Name.OBJR, Pg=page_obj, Obj=annot)

            link_dict = pdf.make_indirect(
                Dictionary(Type=Name.StructElem, S=Name.Link, Pg=page_obj, P=doc_elem, K=obj_ref)
            )

            append_kid(doc_elem, link_dict)

            annot[Name.StructParent] = next_key
            nums.append(next_key)
            nums.append(link_dict)
            next_key += 1

            fixed += 1

    root[Name.ParentTreeNextKey] = next_key

    if fixed > 0:
        return RepairReport(name, fixed, f"Wrapped {fixed} Link annotation(s) inside <Link> struct elements.")
    return RepairReport(name, 0, "All Link annotations are already properly nested.")


# ---- helpers ---------------------------------------------------------------


def _collect_tagged(node, tagged: set, parent_is_link: bool) -> None:
    if not isinstance(node, Dictionary):
        return
    is_link = role_of(node) == "Link"

    for kid in get_kids(node):
        if (is_link or parent_is_link) and isinstance(kid, Dictionary) and kid.get(Name.Type) == Name.OBJR:
            annot_ref = kid.get(Name.Obj)
            if annot_ref is not None:
                objgen = getattr(annot_ref, "objgen", (0, 0))
                if objgen != (0, 0):
                    tagged.add(objgen[0])
        _collect_tagged(kid, tagged, is_link)


def _find_document_element(root: Dictionary):
    for kid in get_kids(root):
        if isinstance(kid, Dictionary) and role_of(kid) == "Document":
            return kid
    return None


def _create_document_element(pdf: pikepdf.Pdf, root: Dictionary) -> Dictionary:
    doc_dict = pdf.make_indirect(Dictionary(Type=Name.StructElem, S=Name.Document, P=root))
    append_kid(root, doc_dict)
    return doc_dict


def _ensure_parent_tree(pdf: pikepdf.Pdf, root: Dictionary) -> Dictionary:
    pt = root.get(Name.ParentTree)
    if pt is None:
        pt = Dictionary()
        root[Name.ParentTree] = pt
    return pt


def _ensure_nums(parent_tree: Dictionary) -> Array:
    nums = parent_tree.get(Name.Nums)
    if nums is None:
        nums = Array([])
        parent_tree[Name.Nums] = nums
    return nums


def _next_parent_tree_key(nums: Array, root: Dictionary) -> int:
    hint = root.get(Name.ParentTreeNextKey)
    if hint is not None:
        return int(hint)

    max_key = -1
    for i in range(0, len(nums), 2):
        key = nums[i]
        if key is not None:
            max_key = max(max_key, int(key))
    return max_key + 1

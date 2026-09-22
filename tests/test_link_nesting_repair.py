import pikepdf
from pdftagvalicate import link_nesting_repair
from pikepdf import Array, Dictionary, Name


def _add_link_annot(pdf, page_obj):
    annot = pdf.make_indirect(
        Dictionary(Type=Name.Annot, Subtype=Name.Link, Rect=Array([0, 0, 10, 10]))
    )
    annots = page_obj.get(Name.Annots)
    if annots is None:
        page_obj[Name.Annots] = Array([annot])
    else:
        annots.append(annot)
    return annot


def test_wraps_orphaned_link_annotation(tagged_pdf):
    pdf, struct_root, doc_elem = tagged_pdf
    page_obj = pdf.pages[0].obj
    annot = _add_link_annot(pdf, page_obj)

    report = link_nesting_repair.fix(pdf)

    assert report.fixed == 1
    assert Name.StructParent in annot
    nums = struct_root[Name.ParentTree][Name.Nums]
    assert len(nums) == 2
    link_elem = nums[1]
    assert link_elem[Name.S] == Name.Link
    assert link_elem[Name.K][Name.Obj].objgen == annot.objgen


def test_already_tagged_link_is_left_alone(tagged_pdf):
    pdf, struct_root, doc_elem = tagged_pdf
    page_obj = pdf.pages[0].obj
    annot = _add_link_annot(pdf, page_obj)

    # Pre-tag it exactly like the repair itself would.
    first = link_nesting_repair.fix(pdf)
    assert first.fixed == 1

    second = link_nesting_repair.fix(pdf)
    assert second.fixed == 0


def test_creates_struct_tree_for_fully_untagged_pdf(blank_pdf):
    page_obj = blank_pdf.pages[0].obj
    _add_link_annot(blank_pdf, page_obj)

    report = link_nesting_repair.fix(blank_pdf)

    assert report.fixed == 1
    assert blank_pdf.Root.get(Name.StructTreeRoot) is not None

import pikepdf
import pytest
from pikepdf import Array, Dictionary, Name


def _blank_page(pdf: pikepdf.Pdf) -> Dictionary:
    page = pdf.make_indirect(
        Dictionary(
            Type=Name.Page,
            MediaBox=Array([0, 0, 612, 792]),
            Resources=Dictionary(),
        )
    )
    pdf.pages.append(pikepdf.Page(page))
    return pdf.pages[-1].obj


@pytest.fixture
def blank_pdf():
    """A minimal, single-page, untagged PDF."""
    pdf = pikepdf.new()
    _blank_page(pdf)
    yield pdf
    pdf.close()


@pytest.fixture
def tagged_pdf():
    """A minimal single-page PDF with /MarkInfo /Marked and an empty
    <Document> struct tree, but no other content."""
    pdf = pikepdf.new()
    _blank_page(pdf)

    doc_elem = pdf.make_indirect(Dictionary(Type=Name.StructElem, S=Name.Document))
    struct_root = pdf.make_indirect(
        Dictionary(
            Type=Name.StructTreeRoot,
            K=doc_elem,
            ParentTree=Dictionary(Nums=Array([])),
        )
    )
    doc_elem[Name.P] = struct_root

    pdf.Root[Name.StructTreeRoot] = struct_root
    pdf.Root[Name.MarkInfo] = Dictionary(Marked=True)

    yield pdf, struct_root, doc_elem
    pdf.close()

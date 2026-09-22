from pdftagvalicate import tbody_repair
from pikepdf import Dictionary, Name


def _table_chain(pdf, parent):
    """Builds parent -> Table -> TBody -> TR -> TD(with content) and links it
    into parent's /K. Returns (table, td)."""
    content = pdf.make_indirect(Dictionary(Type=Name.StructElem, S=Name.P))
    td = pdf.make_indirect(Dictionary(Type=Name.StructElem, S=Name.TD, K=content))
    content[Name.P] = td
    tr = pdf.make_indirect(Dictionary(Type=Name.StructElem, S=Name.TR, K=td))
    td[Name.P] = tr
    tbody = pdf.make_indirect(Dictionary(Type=Name.StructElem, S=Name.TBody, K=tr))
    tr[Name.P] = tbody
    table = pdf.make_indirect(Dictionary(Type=Name.StructElem, S=Name.Table, K=tbody, P=parent))
    tbody[Name.P] = table
    parent[Name.K] = table
    return table, content


def test_dissolves_fake_table_chain(tagged_pdf):
    pdf, struct_root, doc_elem = tagged_pdf
    table, content = _table_chain(pdf, doc_elem)

    report = tbody_repair.fix(pdf)

    assert report.fixed == 1
    # doc_elem's /K should now point directly at the cell's content, not the table.
    assert doc_elem[Name.K].objgen == content.objgen
    assert content[Name.P].objgen == doc_elem.objgen


def test_leaves_real_table_with_thead_alone(tagged_pdf):
    pdf, struct_root, doc_elem = tagged_pdf
    table, content = _table_chain(pdf, doc_elem)
    thead = pdf.make_indirect(Dictionary(Type=Name.StructElem, S=Name.THead, P=table))
    from pikepdf import Array

    table[Name.K] = Array([thead, table[Name.K]])

    report = tbody_repair.fix(pdf)

    assert report.fixed == 0
    assert doc_elem[Name.K].objgen == table.objgen


def test_skips_untagged_document(blank_pdf):
    report = tbody_repair.fix(blank_pdf)
    assert report.fixed == 0
    assert "not tagged" in report.detail

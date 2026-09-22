from pdftagvalicate import metadata_repairs
from pikepdf import Name


def test_fix_mark_info_sets_marked_true(blank_pdf):
    report = metadata_repairs.fix_mark_info(blank_pdf)
    assert report.fixed == 1
    assert blank_pdf.Root[Name.MarkInfo][Name.Marked] is True


def test_fix_mark_info_is_idempotent(blank_pdf):
    metadata_repairs.fix_mark_info(blank_pdf)
    second = metadata_repairs.fix_mark_info(blank_pdf)
    assert second.fixed == 0


def test_fix_display_doc_title_sets_true(blank_pdf):
    report = metadata_repairs.fix_display_doc_title(blank_pdf)
    assert report.fixed == 1
    assert blank_pdf.Root[Name.ViewerPreferences][Name.DisplayDocTitle] is True


def test_fix_display_doc_title_is_idempotent(blank_pdf):
    metadata_repairs.fix_display_doc_title(blank_pdf)
    second = metadata_repairs.fix_display_doc_title(blank_pdf)
    assert second.fixed == 0


def test_fix_pdf_ua_identifier_sets_xmp(blank_pdf):
    report = metadata_repairs.fix_pdf_ua_identifier(blank_pdf)
    assert report.fixed == 1
    with blank_pdf.open_metadata() as meta:
        assert meta["pdfuaid:part"] == "1"

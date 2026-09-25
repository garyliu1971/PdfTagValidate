import json

import pikepdf
from pikepdf import Array, Dictionary, Name

from pdftagvalicate.cli import main


def _write_blank_pdf(path):
    pdf = pikepdf.new()
    page = pdf.make_indirect(Dictionary(Type=Name.Page, MediaBox=Array([0, 0, 612, 792]), Resources=Dictionary()))
    pdf.pages.append(pikepdf.Page(page))
    pdf.save(path)
    pdf.close()


def test_dry_run_reports_fixes_without_writing(tmp_path, capsys):
    src = tmp_path / "in.pdf"
    _write_blank_pdf(src)

    exit_code = main([str(src), "--dry-run", "--json"])

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["dry_run"] is True
    assert payload["total_fixed"] == 3
    assert not (tmp_path / "out.pdf").exists()


def test_writes_repaired_output(tmp_path, capsys):
    src = tmp_path / "in.pdf"
    dst = tmp_path / "out.pdf"
    _write_blank_pdf(src)

    exit_code = main([str(src), str(dst), "--json"])

    assert exit_code == 1
    assert dst.exists()
    payload = json.loads(capsys.readouterr().out)
    assert payload["total_fixed"] == 3


def test_missing_input_file_errors(tmp_path, capsys):
    missing = tmp_path / "does-not-exist.pdf"

    exit_code = main([str(missing), "--dry-run", "--json"])

    assert exit_code == 2
    payload = json.loads(capsys.readouterr().out)
    assert "error" in payload


def test_output_required_unless_dry_run(tmp_path):
    src = tmp_path / "in.pdf"
    _write_blank_pdf(src)

    try:
        main([str(src)])
        assert False, "expected SystemExit"
    except SystemExit as ex:
        assert ex.code == 2


def test_check_mode_default_runs_all_checks(tmp_path, capsys):
    src = tmp_path / "in.pdf"
    _write_blank_pdf(src)

    exit_code = main([str(src), "--check", "--json"])

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "check"
    assert payload["total_issues"] == 5
    names = {r["name"] for r in payload["reports"]}
    assert "PDF/UA identifier (pdfuaid:part)" in names
    assert "Document title (dc:title)" in names
    assert "Document language (/Lang)" in names


def test_check_mode_single_check_no_issues(tmp_path, capsys):
    src = tmp_path / "in.pdf"
    _write_blank_pdf(src)

    exit_code = main([str(src), "--check", "--fonts", "--json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "check"
    assert payload["total_issues"] == 0
    assert len(payload["reports"]) == 1


def _write_tagged_pdf_with_figure(path):
    pdf = pikepdf.new()
    page = pdf.make_indirect(
        Dictionary(Type=Name.Page, MediaBox=Array([0, 0, 612, 792]), Resources=Dictionary())
    )
    pdf.pages.append(pikepdf.Page(page))

    doc = pdf.make_indirect(Dictionary(Type=Name.StructElem, S=Name.Document))
    root = pdf.make_indirect(
        Dictionary(Type=Name.StructTreeRoot, K=doc, ParentTree=Dictionary(Nums=Array([])))
    )
    doc[Name.P] = root
    fig = pdf.make_indirect(Dictionary(Type=Name.StructElem, S=Name.Figure, P=doc))
    doc[Name.K] = fig

    pdf.Root[Name.StructTreeRoot] = root
    pdf.Root[Name.MarkInfo] = Dictionary(Marked=True)
    pdf.save(path)
    pdf.close()


def test_check_mode_reports_missing_alt(tmp_path, capsys):
    src = tmp_path / "in.pdf"
    _write_tagged_pdf_with_figure(src)

    exit_code = main([str(src), "--check", "--alt-text", "--json"])

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["total_issues"] == 1


def test_lang_value_flag(tmp_path, capsys):
    src = tmp_path / "in.pdf"
    dst = tmp_path / "out.pdf"
    _write_blank_pdf(src)

    exit_code = main([str(src), str(dst), "--lang", "--lang-value", "zh-CN", "--json"])

    assert exit_code == 1
    assert dst.exists()
    payload = json.loads(capsys.readouterr().out)
    lang_report = next(r for r in payload["reports"] if "Lang" in r["name"])
    assert lang_report["fixed"] == 1

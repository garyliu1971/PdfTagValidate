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

"""
pdf_export.py
-------------
Optional PPTX to PDF: LibreOffice headless (all platforms), or PowerPoint COM via comtypes on Windows.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

# PowerPoint ppSaveAsPDF
_PP_SAVE_AS_PDF = 32


def _pptx_to_pdf_windows_powerpoint(pptx_path: Path, pdf_path: Path) -> Path:
    """Use installed Microsoft PowerPoint through COM (``pip install comtypes``)."""
    try:
        import comtypes.client  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError(
            "Windows PDF via PowerPoint requires comtypes: pip install comtypes"
        ) from exc

    pptx_path = pptx_path.resolve()
    pdf_path = pdf_path.resolve()
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    app = comtypes.client.CreateObject("PowerPoint.Application")
    try:
        app.Visible = 0
        presentation = app.Presentations.Open(str(pptx_path), WithWindow=False)
        try:
            presentation.SaveAs(str(pdf_path), FileFormat=_PP_SAVE_AS_PDF)
        finally:
            presentation.Close()
    finally:
        app.Quit()

    if not pdf_path.is_file():
        raise RuntimeError("PowerPoint did not produce a PDF file.")
    return pdf_path


def pptx_to_pdf(pptx_path: str | Path, pdf_path: str | Path | None = None) -> Path:
    """
    Convert ``pptx_path`` to PDF.

    Tries ``soffice`` / ``libreoffice`` first, then on Windows PowerPoint COM if comtypes is installed.
    """
    pptx_path = Path(pptx_path).resolve()
    if not pptx_path.is_file():
        raise FileNotFoundError(pptx_path)

    if pdf_path is None:
        out_dir = pptx_path.parent
        expected_pdf = out_dir / f"{pptx_path.stem}.pdf"
    else:
        expected_pdf = Path(pdf_path).resolve()
        out_dir = expected_pdf.parent

    out_dir.mkdir(parents=True, exist_ok=True)

    for binary in ("soffice", "libreoffice"):
        exe = shutil.which(binary)
        if not exe:
            continue
        cmd = [
            exe,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(out_dir),
            str(pptx_path),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                f"{binary} failed to convert {pptx_path}: {exc.stderr or exc.stdout}"
            ) from exc

        produced = out_dir / f"{pptx_path.stem}.pdf"
        if produced.is_file():
            if produced.resolve() != expected_pdf.resolve():
                shutil.move(str(produced), str(expected_pdf))
            return expected_pdf

    detail: str | None = None
    if sys.platform == "win32":
        try:
            return _pptx_to_pdf_windows_powerpoint(pptx_path, expected_pdf)
        except Exception as exc:
            detail = str(exc)

    msg = (
        "No PDF converter available. Install LibreOffice (soffice or libreoffice on PATH), "
        "or on Windows use Microsoft PowerPoint with pip install comtypes, or skip --pdf."
    )
    if detail:
        msg = f"{msg} ({detail})"
    raise RuntimeError(msg)

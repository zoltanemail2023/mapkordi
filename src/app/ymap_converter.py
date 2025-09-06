# app/ymap_converter.py
import os
import sys
import shutil
import tempfile
import subprocess
from typing import Tuple

class ConversionError(Exception):
    pass

def find_codewalker(prefer_path: str | None) -> str | None:
    """
    Megpróbálja megtalálni a CodeWalker.exe-t.
    Visszaadja az abszolút elérési utat, ha megtalálta, különben None.
    """
    candidates: list[str] = []

    # 1) kézzel megadott út
    if prefer_path:
        candidates.append(prefer_path)

    # 2) környezeti változó
    env = os.environ.get("CODEWALKER_EXE_PATH")
    if env:
        candidates.append(env)

    # 3) gyakori helyek
    home = os.path.expanduser("~")
    common_dirs = [
        os.getcwd(),
        os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.abspath("."),
        os.path.join(home, "Desktop", "CodeWalker"),
        os.path.join(home, "CodeWalker"),
        os.path.join("C:\\", "Program Files", "CodeWalker"),
        os.path.join("C:\\", "Program Files (x86)", "CodeWalker"),
    ]
    for d in common_dirs:
        candidates.append(os.path.join(d, "CodeWalker.exe"))

    for p in candidates:
        if p and os.path.isfile(p):
            return os.path.abspath(p)
    return None


def _is_xml_text(path: str) -> bool:
    try:
        with open(path, "rb") as f:
            head = f.read(256)
        return head.lstrip().startswith(b"<")
    except Exception:
        return False


def ensure_xml_from_ymap(input_path: str, codewalker_path: str | None) -> Tuple[str, str]:
    """
    Ha input XML (ymap.xml vagy sima xml), visszaadjuk.
    Ha bináris .ymap: CodeWalker -> XML export (rejtve).
    Visszatérés: (xml_path, status_message)
    """
    if not os.path.isfile(input_path):
        raise ConversionError(f"Nem található: {input_path}")

    # Ha már XML-nek látszik, vagy .xml a kiterjesztés – nem indítunk CW-t.
    ext = os.path.splitext(input_path)[1].lower()
    if ext == ".xml" or _is_xml_text(input_path):
        return input_path, "Forrás már XML volt – CW nem kellett."

    # Bináris .ymap eset -> CodeWalker export szükséges
    if not codewalker_path or not os.path.isfile(codewalker_path):
        raise ConversionError(
            "Bináris .ymap és nincs beállítva érvényes CodeWalker.exe.\n"
            "Beállítások gomb → válaszd ki a CodeWalker.exe-t."
        )

    out_xml = os.path.join(
        tempfile.gettempdir(),
        os.path.splitext(os.path.basename(input_path))[0] + ".xml",
    )

    # A CW sok mindent relatív elérési úttal keres – ezért a cwd legyen a CW mappája.
    cw_dir = os.path.dirname(codewalker_path)

    # 1) Parancssori export megkísérlése rejtve
    args = [codewalker_path, "-exportxml", input_path, out_xml]
    try:
        creation = 0x08000000  # CREATE_NO_WINDOW
        subprocess.run(args, cwd=cw_dir, check=False, creationflags=creation)
    except Exception:
        pass

    # 2) PowerShell-es rejtett indítás, ha még nincs kimenet
    if not (os.path.exists(out_xml) and os.path.getsize(out_xml) > 100):
        ps = (
            f'Start-Process -FilePath "{codewalker_path}" '
            f'-ArgumentList \'-exportxml\',\'{input_path}\',\'{out_xml}\' '
            f'-WorkingDirectory "{cw_dir}" -WindowStyle Hidden -Wait'
        )
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                cwd=cw_dir,
                check=False,
                creationflags=0x08000000
            )
        except Exception:
            pass

    if not (os.path.exists(out_xml) and os.path.getsize(out_xml) > 100):
        raise ConversionError(
            "CodeWalker export sikertelen (nem jött létre használható XML).\n"
            "Ellenőrizd, hogy a CodeWalker legfrissebb, és hogy a -exportxml működik."
        )

    return out_xml, "Bináris .ymap → CodeWalker export (rejtve) sikerült."

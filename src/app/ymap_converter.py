# app/ymap_converter.py
import os
import shutil
import tempfile
import subprocess
from typing import Tuple

class ConversionError(Exception):
    pass

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

    # 1) Megpróbáljuk a (létező) parancssoros exportot: -exportxml <in> <out>
    # Rejtett módon, és megvárjuk a végét.
    # Ha a CW nem támogatná, esünk a 2) PowerShell hívásra (szintén rejtve).
    args = [codewalker_path, "-exportxml", input_path, out_xml]

    try:
        # Windows alatt teljesen rejtett futtatás
        creation = 0x08000000  # CREATE_NO_WINDOW
        subprocess.run(
            args,
            cwd=cw_dir,
            check=False,
            creationflags=creation
        )
    except Exception:
        pass  # megyünk a PS-es útra

    # Ha még nincs kimentve, próbáljuk PowerShell-lel rejtve indítani és kivárni
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
                creationflags=0x08000000  # CREATE_NO_WINDOW
            )
        except Exception:
            pass

    if not (os.path.exists(out_xml) and os.path.getsize(out_xml) > 100):
        raise ConversionError(
            "CodeWalker export sikertelen (nem jött létre használható XML).\n"
            "Ellenőrizd, hogy a CodeWalker legfrissebb, és hogy a -exportxml működik ennél a verziónál."
        )

    return out_xml, "Bináris .ymap → CodeWalker export (rejtve) sikerült."

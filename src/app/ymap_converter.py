# app/ymap_converter.py
import os, tempfile, time, subprocess
from typing import Tuple

class ConversionError(Exception):
    pass

def _is_xml_text(path: str) -> bool:
    try:
        with open(path, "rb") as f:
            return f.read(256).lstrip().startswith(b"<")
    except Exception:
        return False

def _run_cw_hidden(cw_path: str, args: list[str], cwd: str, out_xml: str, timeout: float = 120.0) -> bool:
    # Indítás teljesen rejtve
    CREATE_NO_WINDOW       = 0x08000000
    DETACHED_PROCESS       = 0x00000008
    STARTF_USESHOWWINDOW   = 0x00000001
    SW_HIDE                = 0

    si = subprocess.STARTUPINFO()
    si.dwFlags |= STARTF_USESHOWWINDOW
    si.wShowWindow = SW_HIDE

    try:
        proc = subprocess.Popen(
            [cw_path, *args],
            cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW | DETACHED_PROCESS,
            startupinfo=si
        )
    except Exception:
        return False

    # Fájl létrejöttének figyelése (UI nem blokkol, mert ezt háttérszál hívja)
    t0 = time.time()
    while time.time() - t0 < timeout:
        if os.path.exists(out_xml) and os.path.getsize(out_xml) > 100:
            break
        time.sleep(0.4)

    # Ha még fut, lezárjuk
    try:
        if proc.poll() is None:
            proc.terminate()
            time.sleep(0.5)
            if proc.poll() is None:
                proc.kill()
    except Exception:
        pass

    return os.path.exists(out_xml) and os.path.getsize(out_xml) > 100

def ensure_xml_from_ymap(input_path: str, codewalker_path: str | None) -> Tuple[str, str]:
    """
    XML-t ad vissza. Ha a forrás már XML, azt használjuk.
    Ha bináris .ymap, CodeWalkerrel exportálunk – láthatatlanul, háttérben, timeouttal.
    """
    if not os.path.isfile(input_path):
        raise ConversionError(f"Nem található: {input_path}")

    ext = os.path.splitext(input_path)[1].lower()
    if ext == ".xml" or _is_xml_text(input_path):
        return input_path, "Forrás már XML volt – CW nem kellett."

    if not codewalker_path or not os.path.isfile(codewalker_path):
        raise ConversionError(
            "Bináris .ymap és nincs beállítva érvényes CodeWalker.exe.\n"
            "Beállítások → válaszd ki a CodeWalker.exe-t."
        )

    out_xml = os.path.join(
        tempfile.gettempdir(),
        os.path.splitext(os.path.basename(input_path))[0] + ".xml"
    )
    cw_dir = os.path.dirname(codewalker_path)

    # Először a dokumentált CLI kapcsolóval próbáljuk
    ok = _run_cw_hidden(codewalker_path, ["-exportxml", input_path, out_xml], cw_dir, out_xml, timeout=180.0)
    if not ok:
        raise ConversionError(
            "A CodeWalker export nem hozott létre használható XML-t (timeout vagy hiba).\n"
            "Friss CW ajánlott. Végső esetben exportálj kézzel .ymap.xml-re, és azt add meg."
        )

    return out_xml, "Bináris .ymap → CodeWalker export (rejtve) sikerült."

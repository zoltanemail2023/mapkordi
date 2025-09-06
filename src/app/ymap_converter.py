import os
import re
import shutil
import subprocess
import tempfile

from typing import Tuple

class ConversionError(Exception):
    pass


def _looks_like_xml_text(data: bytes) -> bool:
    head = data.lstrip()[:100].lower()
    return head.startswith(b"<") or b"<map" in head or b"<cmap" in head or b"<?xml" in head


def _read_file_bytes(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def _write_utf8(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _cw_headless_run(args: list, cwd: str | None = None) -> tuple[int, str, str]:
    """
    Futtat egy külső programot teljesen ablak nélkül.
    """
    # Rejtett indulás Windows alatt
    startupinfo = None
    creationflags = 0
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        creationflags = subprocess.CREATE_NO_WINDOW  # nincs konzolablak
    except Exception:
        pass

    completed = subprocess.run(
        args,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=False,
        startupinfo=startupinfo,
        creationflags=creationflags,
    )
    return completed.returncode, completed.stdout, completed.stderr


def find_codewalker(explicit_path: str | None) -> str | None:
    """
    Ha nincs megadva, próbálunk ésszerű helyeken keresni.
    """
    candidates: list[str] = []
    if explicit_path:
        candidates.append(explicit_path)

    # Gyakori telepítési helyek
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    local_appdata = os.environ.get("LOCALAPPDATA", "")

    for base in [program_files, program_files_x86, local_appdata]:
        if not base:
            continue
        for name in ["CodeWalker", "CodeWalkerGTAV", "CodeWalker-Release", "CodeWalker RPF Explorer"]:
            exe = os.path.join(base, name, "CodeWalker.exe")
            if os.path.isfile(exe):
                candidates.append(exe)

    # A PATH-on is megpróbáljuk
    for p in os.environ.get("PATH", "").split(os.pathsep):
        exe = os.path.join(p, "CodeWalker.exe")
        if os.path.isfile(exe):
            candidates.append(exe)

    # Dedup & ellenőrzés
    seen = set()
    for c in candidates:
        c = os.path.normpath(c)
        if c.lower() in seen:
            continue
        seen.add(c.lower())
        if os.path.isfile(c):
            return c
    return None


def _try_cw_export(cw_exe: str, src: str, dst: str) -> tuple[bool, str]:
    """
    Több lehetséges CodeWalker CLI szintaxist is megpróbálunk.
    Minden hívás NÉMA (ablak nélkül) történik.
    """
    cwd = os.path.dirname(cw_exe) or None

    # 1) Régebbi/újabb build-ek között eltérhet a flag; végigpróbáljuk.
    candidates = [
        [cw_exe, "-exportxml", src, dst],
        [cw_exe, "/exportxml", src, dst],
        [cw_exe, "-convertxml", src, dst],
        [cw_exe, "/convertxml", src, dst],
        # Biztonsági „convert” variánsok (ha az XML-t automatikusan kitalálja)
        [cw_exe, "-convert", src, dst],
        [cw_exe, "/convert", src, dst],
    ]

    last_stdout = ""
    last_stderr = ""

    for cmd in candidates:
        rc, out, err = _cw_headless_run(cmd, cwd=cwd)
        last_stdout, last_stderr = out, err

        if rc == 0 and os.path.isfile(dst):
            try:
                # Nézzük meg, tényleg XML-t kaptunk-e
                with open(dst, "rb") as f:
                    if _looks_like_xml_text(f.read(400)):
                        return True, ""
            except Exception:
                pass

        # Ha a kimenet jelzi, hogy ismeretlen flag, megyünk a következőre
        if any(k in (out + err).lower() for k in ["unknown option", "invalid", "usage"]):
            continue

    # semelyik forma nem jött be
    msg = (last_stdout + "\n" + last_stderr).strip()
    return False, msg


def ensure_xml_from_ymap(src_path: str, cw_path: str | None) -> Tuple[str, str]:
    """
    Bemenet: .ymap vagy .ymap.xml
    Kimenet: (xml_path, info_message)  — mindent ablak nélkül végez.
    """
    if not os.path.isfile(src_path):
        raise ConversionError(f"Nincs ilyen fájl: {src_path}")

    data = _read_file_bytes(src_path)

    # 1) Ha már XML (vagy .ymap.xml), visszaadjuk.
    if _looks_like_xml_text(data) or src_path.lower().endswith((".xml", ".ymap.xml")):
        return src_path, "Forrás már XML; nincs konverzió."

    # 2) Bináris .ymap → próbáljuk CodeWalkerrel némán konvertálni
    cw = find_codewalker(cw_path)
    if not cw:
        raise ConversionError(
            "Bináris .ymap és nem találom a CodeWalkert. "
            "Állíts be CodeWalkert a Beállításokban, vagy adj meg .ymap.xml-t."
        )

    tmp_dir = tempfile.mkdtemp(prefix="cw_xml_")
    dst_xml = os.path.join(tmp_dir, os.path.splitext(os.path.basename(src_path))[0] + ".xml")

    ok, msg = _try_cw_export(cw, src_path, dst_xml)
    if not ok or not os.path.isfile(dst_xml):
        raise ConversionError(
            "CodeWalker export sikertelen (némán futott). "
            "Próbáld friss CodeWalkerrel, vagy adj meg .ymap.xml fájlt.\n\n"
            f"Utolsó üzenet:\n{msg}"
        )

    return dst_xml, "CodeWalker headless export kész."

# src/app/ymap_converter.py

import os
import time
import shutil
import subprocess
from typing import Tuple, Optional

class ConversionError(Exception):
    pass


def find_codewalker(user_path: Optional[str]) -> Optional[str]:
    """
    Visszaadja a CodeWalker.exe teljes elérési útját ha megtalálja.
    - Először a felhasználó által megadott útvonalat ellenőrzi.
    - Ha nincs, tipikus helyeken próbálkozik.
    """
    candidates = []
    if user_path:
        candidates.append(user_path)

    # Tipikus telepítési helyek – ha nálad máshol van, Beállításokban tallózd be.
    candidates += [
        r"C:\CodeWalker\CodeWalker.exe",
        r"C:\Program Files\CodeWalker\CodeWalker.exe",
        r"C:\Program Files (x86)\CodeWalker\CodeWalker.exe",
    ]

    for p in candidates:
        if p and os.path.isfile(p):
            return os.path.abspath(p)
    return None


def _try_run_codewalker_once(exe: str, ymap_path: str, out_xml: str) -> None:
    """
    Egyszeri kísérlet a CodeWalker indítására olyan cwd-vel, hogy a relatív erőforrások (icons\...) megtalálódjanak.
    Többféle CLI kapcsolót is megpróbálunk, mert egyes build-ek más flaget várhatnak.
    """
    exe = os.path.abspath(exe)
    exe_dir = os.path.dirname(exe)

    # Lehetséges parancssorok – az első működő fog nyerni.
    candidates = [
        [exe, "-exportxml", ymap_path, out_xml],
        [exe, "/exportxml", ymap_path, out_xml],
    ]

    # Biztonság kedvéért a PATH elejére tesszük a CodeWalker mappát.
    env = os.environ.copy()
    env["PATH"] = exe_dir + os.pathsep + env.get("PATH", "")

    last_err = None
    for cmd in candidates:
        try:
            # FONTOS: cwd=exe_dir → így látja az icons\... mappát is
            subprocess.run(
                cmd,
                cwd=exe_dir,
                env=env,
                check=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
            return
        except Exception as e:
            last_err = e
            # Megpróbáljuk a következő kapcsolóval is
            continue
    if last_err:
        raise ConversionError(f"CodeWalker indítás sikertelen. Részlet: {last_err}")


def _export_with_codewalker(exe: str, ymap_path: str) -> str:
    """
    CodeWalker-rel XML export. Visszaadja az elkészült XML útvonalát.
    Várakozik az elkészült fájlra (max ~30s), különben hibát dob.
    """
    if not os.path.isfile(ymap_path):
        raise ConversionError(f"Fájl nem található: {ymap_path}")

    base, ext = os.path.splitext(ymap_path)
    out_xml = base + ".xml"

    # Ha már létezik régi export, töröljük, hogy biztosan az újra várjunk
    try:
        if os.path.isfile(out_xml):
            os.remove(out_xml)
    except Exception:
        pass

    _try_run_codewalker_once(exe, ymap_path, out_xml)

    # Várunk, amíg valóban megjelenik a fájl (CodeWalker néha késleltetve ír)
    timeout_s = 30
    waited = 0
    while waited < timeout_s:
        if os.path.isfile(out_xml) and os.path.getsize(out_xml) > 0:
            return out_xml
        time.sleep(0.5)
        waited += 0.5

    raise ConversionError("A CodeWalker nem hozta létre az XML fájlt időben.")


def ensure_xml_from_ymap(input_path: str, codewalker_path: Optional[str]) -> Tuple[str, str]:
    """
    Ha az input már XML: visszaadjuk. Ha .ymap: CodeWalker-rel exportáljuk.
    return: (xml_path, emberi üzenet)
    """
    if not os.path.isfile(input_path):
        raise ConversionError(f"Fájl nem található: {input_path}")

    # Ha már XML (vagy .ymap.xml), nincs teendő
    low = input_path.lower()
    if low.endswith(".xml") and not low.endswith(".ymap"):
        return os.path.abspath(input_path), "Már XML-t kaptam, konverzió nem kellett."

    # .ymap vagy .ymap.xml → export
    exe = find_codewalker(codewalker_path)
    if not exe:
        raise ConversionError(
            "CodeWalker.exe nem található. A Beállítások gombbal add meg a helyét."
        )

    xml_path = _export_with_codewalker(exe, input_path)
    return xml_path, f"Sikeres export a CodeWalker-rel: {xml_path}"

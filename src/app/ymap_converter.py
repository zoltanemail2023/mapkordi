\
import os, subprocess

class ConversionError(Exception):
    pass

def find_codewalker(candidate: str | None = None) -> str | None:
    if candidate and os.path.isfile(candidate):
        return candidate
    env_path = os.environ.get("CODEWALKER_EXE_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path
    guesses = [
        os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "CodeWalker", "CodeWalker.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "CodeWalker", "CodeWalker.exe"),
        os.path.join(os.environ.get("USERPROFILE", "C:\\"), "Desktop", "CodeWalker.exe"),
        os.path.join(os.environ.get("USERPROFILE", "C:\\"), "Downloads", "CodeWalker.exe"),
    ]
    for g in guesses:
        if os.path.isfile(g):
            return g
    return None

def ensure_xml_from_ymap(input_path: str, codewalker_path: str | None):
    base, ext = os.path.splitext(input_path)
    try:
        with open(input_path, "rb") as f:
            b = f.read(256)
        if b.lstrip().startswith(b"<"):
            out_xml = base + ".xml" if not input_path.lower().endswith(".xml") else input_path
            if out_xml != input_path:
                with open(input_path, "rb") as src, open(out_xml, "wb") as dst:
                    dst.write(src.read())
            return out_xml, "Input already XML; copied."
    except Exception:
        pass

    cw = find_codewalker(codewalker_path)
    if not cw:
        raise ConversionError("CodeWalker.exe not found. Set it in Beállítások.")

    out_xml = base + ".xml"
    variants = [
        [cw, "-exportxml", input_path, out_xml],
        [cw, "-rpfexportxml", input_path, out_xml],
    ]
    last_rc = None; last_out=""; last_err=""
    for cmd in variants:
        try:
            p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180, creationflags=0x08000000)
            last_rc = p.returncode
            last_out = p.stdout.decode("utf-8", errors="ignore")
            last_err = p.stderr.decode("utf-8", errors="ignore")
            if p.returncode == 0 and os.path.isfile(out_xml) and os.path.getsize(out_xml) > 0:
                return out_xml, "Converted with CodeWalker."
        except subprocess.TimeoutExpired:
            last_rc = -1; last_err = "Timeout"
        except Exception as e:
            last_rc = -2; last_err = str(e)
    raise ConversionError(f"CodeWalker export failed. RC={last_rc} OUT={last_out[:200]} ERR={last_err[:200]}")

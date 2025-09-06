\
import os, json, tkinter as tk
from tkinter import ttk, filedialog, messagebox
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except Exception:
    TkinterDnD = tk.Tk
    DND_AVAILABLE = False

from app.ymap_converter import ensure_xml_from_ymap, find_codewalker, ConversionError
from app.xml_parser import extract_positions_from_xml, summarize

APP_TITLE = "MapKordi – YMAP → Koordináta"
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "app", "config.json")

def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"codewalker_path": ""}

def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass

class App:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE); self.root.geometry("720x500")
        self.cfg = load_config()

        frm = ttk.Frame(root, padding=12); frm.pack(fill="both", expand=True)
        head = ttk.Frame(frm); head.pack(fill="x")
        ttk.Label(head, text="Húzd ide a .ymap / .ymap.xml fájlt, vagy kattints a Böngészés gombra.", font=("Segoe UI", 11)).pack(side="left")
        ttk.Button(head, text="Beállítások", command=self.open_settings).pack(side="right", padx=6)

        self.drop = tk.Text(frm, height=6, relief="ridge", borderwidth=2)
        self.drop.insert("1.0", "\n\n\n     ⤵ Ide dobd a fájlt ⤵\n\n")
        self.drop.config(state="disabled"); self.drop.pack(fill="both", expand=True, pady=10)

        if DND_AVAILABLE:
            self.drop.drop_target_register(DND_FILES); self.drop.dnd_bind("<<Drop>>", self.on_drop)

        btm = ttk.Frame(frm); btm.pack(fill="x")
        ttk.Button(btm, text="Böngészés…", command=self.browse).pack(side="left")
        self.status = ttk.Label(btm, text="Készen áll.", anchor="w"); self.status.pack(side="left", padx=12)

        self.out = tk.Text(frm, height=12, wrap="word"); self.out.pack(fill="both", expand=True)
        self.out.insert("1.0", "Eredmény itt fog megjelenni…"); self.out.config(state="disabled")

        if not self.cfg.get("codewalker_path"):
            auto = find_codewalker(None)
            if auto:
                self.cfg["codewalker_path"] = auto; save_config(self.cfg)

    def set_status(self, text): self.status.config(text=text); self.root.update_idletasks()

    def open_settings(self):
        path = filedialog.askopenfilename(title="Válaszd ki a CodeWalker.exe-t",
                                          filetypes=[("CodeWalker", "CodeWalker.exe"), ("EXE", "*.exe"), ("All files", "*.*")])
        if path:
            self.cfg["codewalker_path"] = path; save_config(self.cfg); messagebox.showinfo("Mentve", f"CodeWalker: {path}")

    def browse(self):
        f = filedialog.askopenfilename(title="Válassz .ymap / .ymap.xml fájlt",
                                       filetypes=[("YMAP or XML", "*.ymap *.xml *.ymap.xml"), ("All files", "*.*")])
        if f: self.process_file(f)

    def on_drop(self, event):
        raw = event.data
        if raw.startswith("{") and raw.endswith("}"):
            raw = raw[1:-1]
        f = raw.split("} {")[0] if "} {" in raw else raw
        self.process_file(f)

    def append_out(self, text):
        self.out.config(state="normal"); self.out.delete("1.0", "end"); self.out.insert("1.0", text); self.out.config(state="disabled")

    def process_file(self, path):
        try:
            self.set_status("Feldolgozás…")
            xml_path, msg = ensure_xml_from_ymap(path, self.cfg.get("codewalker_path"))
            coords = extract_positions_from_xml(xml_path)
            summary = summarize(coords)
            base = os.path.splitext(path)[0]
            if xml_path.lower() != (base + ".xml").lower():
                try:
                    import shutil; shutil.copyfile(xml_path, base + ".xml")
                except Exception: pass
            self.append_out(f"XML: {xml_path}\n\n{summary}")
            self.set_status("Kész.")
        except ConversionError as e:
            self.append_out(f"Konverziós hiba: {e}"); self.set_status("Hiba.")
        except Exception as e:
            self.append_out(f"Hiba: {type(e).__name__}: {e}"); self.set_status("Hiba.")

def main():
    try:
        from tkinterdnd2 import TkinterDnD
        root = TkinterDnD()
    except Exception:
        root = tk.Tk()
    try:
        ttk.Style(root).theme_use("vista")
    except Exception: pass
    App(root); root.mainloop()

if __name__ == "__main__":
    main()

# main.py
import os, json, threading, tkinter as tk
from tkinter import ttk, filedialog, messagebox

# DnD EXE-ben ki van kapcsolva, hogy ne kelljen tkdnd
DND_AVAILABLE = False

from app.ymap_converter import ensure_xml_from_ymap, ConversionError
from app.xml_parser import extract_positions_from_xml, summarize

APP_TITLE   = "MapKordi – YMAP → Koordináta"
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "app", "config.json")

def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"codewalker_path": ""}

def save_config(cfg):
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass

class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("720x500")
        self.cfg = load_config()

        frm = ttk.Frame(root, padding=12); frm.pack(fill="both", expand=True)
        head = ttk.Frame(frm); head.pack(fill="x")
        ttk.Label(
            head,
            text="Válassz .ymap / .ymap.xml fájlt a Böngészés gombbal. (DnD EXE-ben ki van kapcsolva.)",
            font=("Segoe UI", 10)
        ).pack(side="left", padx=(0,8))
        ttk.Button(head, text="Beállítások", command=self.open_settings).pack(side="right")

        self.drop = tk.Text(frm, height=6, relief="groove", borderwidth=2, state="disabled")
        self.drop.pack(fill="both", expand=True, pady=8)
        self.drop.config(state="normal")
        self.drop.delete("1.0","end")
        self.drop.insert("1.0", "  } Ide dobnád a fájlt }\n\n( EXE-ben használd a Böngészés gombot )")
        self.drop.config(state="disabled")

        bar = ttk.Frame(frm); bar.pack(fill="x", pady=(4,2))
        self.btn_browse = ttk.Button(bar, text="Böngészés…", command=self.browse)
        self.btn_browse.pack(side="left")
        self.status = ttk.Label(bar, text="Készen áll."); self.status.pack(side="left", padx=12)

        self.out = tk.Text(frm, height=12, wrap="word"); self.out.pack(fill="both", expand=True)
        self.out.insert("1.0", "Eredmény itt fog megjelenni…")
        self.out.config(state="disabled")

    # UI helpers
    def set_status(self, txt): self.status.config(text=txt); self.root.update_idletasks()
    def set_out(self, txt):
        self.out.config(state="normal"); self.out.delete("1.0","end"); self.out.insert("1.0", txt); self.out.config(state="disabled")

    # Settings
    def open_settings(self):
        p = filedialog.askopenfilename(
            title="Válaszd ki a CodeWalker.exe-t",
            filetypes=[("CodeWalker", "CodeWalker.exe"), ("EXE", "*.exe"), ("All files", "*.*")]
        )
        if p:
            self.cfg["codewalker_path"] = p
            save_config(self.cfg)
            messagebox.showinfo("Mentve", f"CodeWalker: {p}")

    # Browse + worker
    def browse(self):
        f = filedialog.askopenfilename(
            title="Válassz .ymap / .ymap.xml fájlt",
            filetypes=[("YMAP vagy XML", "*.ymap *.xml *.ymap.xml"), ("All files", "*.*")]
        )
        if f:
            self.start_worker(f)

    def start_worker(self, path: str):
        # Gomb letilt, státusz
        self.btn_browse.config(state="disabled")
        self.set_status("Feldolgozás…")
        self.set_out("Feldolgozás…\n\nEz eltarthat pár másodpercig nagyobb fájloknál.")

        t = threading.Thread(target=self._worker, args=(path,), daemon=True)
        t.start()

    def _worker(self, path: str):
        try:
            xml_path, msg = ensure_xml_from_ymap(path, self.cfg.get("codewalker_path"))
            coords = extract_positions_from_xml(xml_path)
            text = f"{msg}\n\n{summarize(coords)}"

            # UI frissítés a főszálon
            self.root.after(0, lambda: (self.set_out(text), self.set_status("Kész.")))
        except ConversionError as e:
            self.root.after(0, lambda: (self.set_out(f"Konverziós hiba: {e}"), self.set_status("Hiba.")))
        except Exception as e:
            self.root.after(0, lambda: (self.set_out(f"Hiba: {type(e).__name__}: {e}"), self.set_status("Hiba.")))
        finally:
            self.root.after(0, lambda: self.btn_browse.config(state="normal"))

def main():
    root = tk.Tk()
    try:
        ttk.Style(root).theme_use("vista")
    except Exception:
        pass
    App(root)
    root.mainloop()

if __name__ == "__main__":
    main()

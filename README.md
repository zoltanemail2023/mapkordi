# MapKordi (Windows EXE via GitHub Actions)

One-click build of a **single-file EXE** (no Python needed on your PC).  
The EXE includes Python runtime; you only download the artifact and run it.

## How to use
1. Create a new **private GitHub repo**, upload these files.
2. Go to **Actions** tab — the `Build-Windows-EXE` workflow will run automatically.
3. When it finishes, open the run → **Artifacts** → download `MapKordi-Windows-zip`.
4. Inside you'll find `MapKordi.exe`. Run it.
   - If you drop raw `.ymap`, set **CodeWalker.exe** in the app (Beállítások).
   - For `.ymap.xml`, CodeWalker is not needed.

## Dev notes
- Built with PyInstaller (`--onefile`).
- tkinter (built-in) + tkinterdnd2 + defusedxml.

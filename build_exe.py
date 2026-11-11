"""
Script de Compilación Automatizada con PyInstaller para generar MarkdownTransformer.exe
Empaqueta todos los recursos (plantillas CSS/HTML, ejemplos, iconos) en un único ejecutable.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def build():
    print("=" * 60)
    print("Iniciando compilación de MarkdownTransformer.exe con PyInstaller...")
    print("=" * 60)

    # Rutas clave
    main_script = BASE_DIR / "main.py"
    icon_path = BASE_DIR / "assets" / "app_icon.ico"
    dist_dir = BASE_DIR / "dist"
    build_dir = BASE_DIR / "build"

    # Argumentos de PyInstaller
    # En Windows el separador de add-data es ';'
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name=MarkdownTransformer",
        "--onefile",
        "--windowed",
        f"--icon={icon_path}",
        f"--add-data={BASE_DIR / 'templates'};templates",
        f"--add-data={BASE_DIR / 'assets'};assets",
        f"--add-data={BASE_DIR / 'examples'};examples",
        "--hidden-import=aiohttp",
        "--hidden-import=yaml",
        "--hidden-import=markdown",
        "--hidden-import=markdown.extensions",
        "--hidden-import=markdown.extensions.tables",
        "--hidden-import=markdown.extensions.fenced_code",
        "--hidden-import=markdown.extensions.codehilite",
        "--hidden-import=markdown.extensions.sane_lists",
        "--hidden-import=markdown.extensions.attr_list",
        "--hidden-import=markdown.extensions.def_list",
        "--hidden-import=markdown.extensions.footnotes",
        "--hidden-import=pygments",
        "--hidden-import=pygments.lexers",
        "--hidden-import=pygments.formatters",
        "--exclude-module=pymupdf",
        "--exclude-module=fitz",
        "--exclude-module=numpy",
        str(main_script)
    ]

    print("Ejecutando comando:")
    print(" ".join(cmd))
    print("-" * 60)

    res = subprocess.run(cmd, cwd=str(BASE_DIR))
    if res.returncode != 0:
        print(f"\n[ERROR] Falló la compilación con código {res.returncode}")
        sys.exit(res.returncode)

    exe_path = dist_dir / "MarkdownTransformer.exe"
    if exe_path.is_file():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print("\n" + "=" * 60)
        print("[OK] COMPILACION EXITOSA!")
        print(f"Ejecutable generado en: {exe_path}")
        print(f"Tamano del archivo: {size_mb:.2f} MB")
        print("=" * 60)
    else:
        print(f"\n[ERROR] No se encontró el archivo generado en {exe_path}")
        sys.exit(1)

if __name__ == "__main__":
    build()

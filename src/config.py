"""
Módulo de Configuración y Constantes del Sistema de Transformación Markdown.
Define valores predeterminados para documentos académicos (UPeU) y detección del navegador.
Compatible con entornos de desarrollo y empaquetado PyInstaller (.exe).
"""

import os
import shutil
import sys
from pathlib import Path

# Detección de ruta base compatible con PyInstaller (_MEIPASS)
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

TEMPLATES_DIR = BASE_DIR / "templates"
EXAMPLES_DIR = BASE_DIR / "examples"
ASSETS_DIR = BASE_DIR / "assets"

CSS_TEMPLATE_PATH = TEMPLATES_DIR / "academic.css"
HTML_TEMPLATE_PATH = TEMPLATES_DIR / "academic_template.html"

# Autor y ciclo predeterminados cuando el documento no especifica autor ni grupo
DEFAULT_AUTHOR_NAME = "William David Ortiz Mamani"
DEFAULT_CYCLE_SUFFIX = "Ciclo VIII · 2026-2"
DEFAULT_AUTHOR_FOOTER = f"{DEFAULT_AUTHOR_NAME} — {DEFAULT_CYCLE_SUFFIX}"

# Metadatos institucionales base (solo valores institucionales por defecto)
# NO se definen títulos ni datos de proyectos hardcodeados para evitar duplicación.
DEFAULT_METADATA = {
    "institucion": "Universidad Peruana Unión",
    "escuela": "Escuela Prof. de Ingeniería de Sistemas",
    "autor_pie": DEFAULT_AUTHOR_FOOTER,
    "titulo": "",
    "subtitulo": "Cabecera de Control del Entregable",
    "mostrar_cabecera_control": False
}

def find_browser_executable() -> str | None:
    """
    Localiza automáticamente el ejecutable de Microsoft Edge o Google Chrome en Windows.
    Microsoft Edge viene preinstalado en todas las versiones modernas de Windows 10/11.
    """
    candidates = [
        # Microsoft Edge (estándar Windows 10/11)
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Microsoft\Edge\Application\msedge.exe"),
        # Google Chrome
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Google\Chrome\Application\chrome.exe"),
    ]

    for path in candidates:
        if path and os.path.isfile(path):
            return path

    # Buscar en el PATH del sistema
    for cmd in ["msedge", "chrome", "msedge.exe", "chrome.exe"]:
        found = shutil.which(cmd)
        if found:
            return found

    return None

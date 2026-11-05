"""
Punto de Entrada Principal (CLI & GUI) del Transformador Markdown a PDF y HTML.
Si se ejecuta sin parámetros (doble clic), abre la interfaz gráfica limpia.
Si se ejecuta con argumentos desde la consola, opera como herramienta CLI conectándose a la terminal.
"""

import argparse
import ctypes
import os
import sys
from pathlib import Path

# Si se ejecuta desde consola con argumentos, adjuntar salida a la terminal de Windows
if len(sys.argv) > 1 and not any(arg in sys.argv for arg in ("--gui", "-g")):
    try:
        if ctypes.windll.kernel32.AttachConsole(-1):
            sys.stdout = open("CONOUT$", "w", encoding="utf-8", errors="replace")
            sys.stderr = open("CONOUT$", "w", encoding="utf-8", errors="replace")
    except Exception:
        pass

# Configurar codificación UTF-8 en consola
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Asegurar que el directorio raíz esté en sys.path tanto en script como en PyInstaller
if getattr(sys, "frozen", False):
    APP_ROOT = Path(sys._MEIPASS)
else:
    APP_ROOT = Path(__file__).resolve().parent

if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from src.converter import MarkdownConverter
from src.gui import launch_gui


def main_cli():
    parser = argparse.ArgumentParser(
        description="Transformador de Markdown a PDF y HTML con formato académico institucional (UPeU)."
    )
    parser.add_argument("input", nargs="?", help="Ruta al archivo Markdown (.md) o carpeta para modo lote.")
    parser.add_argument("-o", "--output", help="Ruta del archivo PDF de salida.")
    parser.add_argument("--html-output", help="Ruta del archivo HTML de salida.")
    parser.add_argument(
        "-f", "--format",
        choices=["pdf", "html", "both"],
        default="both",
        help="Formato de exportación: pdf, html o both (predeterminado: both)."
    )
    parser.add_argument("--institucion", help="Nombre institucional para la cabecera izquierda.")
    parser.add_argument("--escuela", help="Nombre de escuela/facultad para la cabecera derecha.")
    parser.add_argument("--autor", help="Nombre de autor o ciclo para el pie de página.")
    parser.add_argument("--titulo", help="Título del documento.")
    parser.add_argument("--gui", action="store_true", help="Forzar apertura de la interfaz gráfica.")

    args = parser.parse_args()

    # Si se invoca sin argumentos o con --gui, abrir la interfaz gráfica
    if args.gui or not args.input:
        launch_gui()
        return

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: La ruta de entrada no existe: {input_path}", file=sys.stderr)
        sys.exit(1)

    converter = MarkdownConverter()
    overrides = {}
    if args.institucion:
        overrides["institucion"] = args.institucion
    if args.escuela:
        overrides["escuela"] = args.escuela
    if args.autor:
        overrides["autor_pie"] = args.autor
    if args.titulo:
        overrides["titulo"] = args.titulo

    gen_pdf = args.format in ("pdf", "both")
    gen_html = args.format in ("html", "both")

    if input_path.is_file():
        print(f"Procesando archivo: {input_path.name}...")
        try:
            html_out, pdf_out = converter.convert(
                input_md_path=input_path,
                output_pdf_path=args.output,
                output_html_path=args.html_output,
                generate_pdf=gen_pdf,
                generate_html=gen_html,
                custom_metadata=overrides
            )
            print("[OK] Transformación completada exitosamente:")
            if html_out and html_out.is_file():
                print(f"  -> HTML: {html_out}")
            if pdf_out and pdf_out.is_file():
                print(f"  -> PDF:  {pdf_out} ({pdf_out.stat().st_size:,} bytes)")
        except Exception as e:
            print(f"Error durante la conversión: {e}", file=sys.stderr)
            sys.exit(1)

    elif input_path.is_dir():
        # Modo lote para carpeta
        md_files = list(input_path.glob("*.md")) + list(input_path.glob("*.markdown"))
        if not md_files:
            print(f"No se encontraron archivos Markdown en la carpeta: {input_path}")
            return

        print(f"Modo lote: procesando {len(md_files)} archivos en {input_path}...")
        for f in md_files:
            print(f" - Convirtiendo {f.name}...")
            try:
                converter.convert(
                    input_md_path=f,
                    generate_pdf=gen_pdf,
                    generate_html=gen_html,
                    custom_metadata=overrides
                )
            except Exception as e:
                print(f"   Error en {f.name}: {e}", file=sys.stderr)

        print("Lote completado.")


if __name__ == "__main__":
    main_cli()

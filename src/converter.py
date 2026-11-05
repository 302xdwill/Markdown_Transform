"""
Controlador de Conversión Markdown a HTML y PDF.
Orquesta el preprocesamiento, renderizado HTML y exportación estricta según el formato solicitado.
"""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from src.pdf_generator import convert_html_to_pdf
from src.template_engine import render_html_document


class MarkdownConverter:
    """Clase principal para transformar documentos Markdown en HTML y PDF académicos."""

    def __init__(self, default_overrides: Optional[Dict[str, Any]] = None):
        self.default_overrides = default_overrides or {}

    def convert(
        self,
        input_md_path: str | Path,
        output_pdf_path: Optional[str | Path] = None,
        output_html_path: Optional[str | Path] = None,
        generate_pdf: bool = True,
        generate_html: bool = False,
        custom_metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[Path], Optional[Path]]:
        """
        Ejecuta la transformación de un archivo Markdown.
        - Si generate_html es False, NO genera ningún archivo .html en la carpeta de destino.
        - Si generate_pdf es False, NO invoca el motor de renderizado PDF.
        Retorna una tupla (ruta_html, ruta_pdf) con los archivos generados.
        """
        md_file = Path(input_md_path).resolve()
        if not md_file.is_file():
            raise FileNotFoundError(f"El archivo markdown no existe: {md_file}")

        target_dir = md_file.parent
        stem = md_file.stem

        final_html_path = Path(output_html_path).resolve() if output_html_path else (target_dir / f"{stem}.html")
        final_pdf_path = Path(output_pdf_path).resolve() if output_pdf_path else (target_dir / f"{stem}.pdf")

        # Fusionar opciones de metadatos
        merged_meta = dict(self.default_overrides)
        if custom_metadata:
            merged_meta.update({k: v for k, v in custom_metadata.items() if v is not None and v != ""})

        # 1. Renderizar contenido HTML en memoria
        html_content, meta = render_html_document(md_file, merged_meta)

        result_html = None
        result_pdf = None

        # 2. Si el usuario solicitó HTML, guardar en la ruta final
        if generate_html:
            final_html_path.parent.mkdir(parents=True, exist_ok=True)
            with open(final_html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            result_html = final_html_path

        # 3. Si el usuario solicitó PDF, usar el HTML final o uno temporal
        if generate_pdf:
            if generate_html and final_html_path.is_file():
                source_html = final_html_path
                temp_html_created = False
            else:
                # Crear archivo temporal en AppData/Temp para que NO aparezca en la carpeta del usuario
                temp_fd, temp_path_str = tempfile.mkstemp(suffix=".html", prefix="md2pdf_")
                os.close(temp_fd)
                source_html = Path(temp_path_str)
                with open(source_html, "w", encoding="utf-8") as f:
                    f.write(html_content)
                temp_html_created = True

            try:
                final_pdf_path.parent.mkdir(parents=True, exist_ok=True)
                convert_html_to_pdf(source_html, final_pdf_path, meta)
                result_pdf = final_pdf_path
            finally:
                if temp_html_created and source_html.exists():
                    try:
                        source_html.unlink()
                    except Exception:
                        pass

        return result_html, result_pdf

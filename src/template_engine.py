"""
Motor de Plantillas y Procesamiento de Markdown para Documentos Académicos UPeU.
Procesa metadatos YAML, detecta tablas de control existentes para evitar duplicados,
aplica estilos institucionales automáticos y genera HTML autocontenido.
"""

import base64
import mimetypes
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import markdown
import yaml

from src.config import (
    CSS_TEMPLATE_PATH,
    DEFAULT_AUTHOR_FOOTER,
    DEFAULT_AUTHOR_NAME,
    DEFAULT_CYCLE_SUFFIX,
    DEFAULT_METADATA,
    HTML_TEMPLATE_PATH,
)


def parse_frontmatter(md_content: str) -> Tuple[Dict[str, Any], str]:
    """
    Extrae el bloque YAML frontmatter superior (entre '---' y '---') si existe.
    Retorna un diccionario de metadatos y el cuerpo markdown sin el frontmatter.
    """
    frontmatter: Dict[str, Any] = {}
    # Eliminar marca BOM de UTF-8 (\ufeff) si estuviera presente
    md_content = md_content.lstrip('\ufeff')
    body = md_content

    # Coincidencia con frontmatter estándar: ^---\s*\n(.*?)\n---\s*\n
    pattern = r"^---\s*\r?\n(.*?)\r?\n---\s*\r?\n"
    match = re.match(pattern, md_content, re.DOTALL)
    if match:
        yaml_str = match.group(1)
        body = md_content[match.end():]
        try:
            parsed = yaml.safe_load(yaml_str)
            if isinstance(parsed, dict):
                frontmatter = parsed
        except Exception:
            # Fallback simple línea por línea si yaml falla
            for line in yaml_str.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    frontmatter[k.strip().lower()] = v.strip().strip('"\'')

    return frontmatter, body


def preprocess_markdown(md_text: str, base_dir: Path) -> str:
    """
    Preprocesa la sintaxis markdown antes de la conversión a HTML:
    - Transforma comandos de salto de página a <div class="page-break"></div>
    - Incrusta imágenes relativas en formato base64 para total portabilidad
    - Soporta alertas tipo GitHub (> [!NOTE])
    """
    # 1. Saltos de página (con doble salto de línea para que Markdown los trate como bloque independiente)
    page_break_tag = '\n\n<div class="page-break"></div>\n\n'
    md_text = re.sub(
        r'(\\pagebreak|\\newpage|<!--\s*pagebreak\s*-->|---pagebreak---|<div\s+class=["\']page-break["\']\s*>\s*</div>|<div\s+style=["\'][^"\']*(?:page-break|break)-(?:after|before)\s*:\s*(?:always|page)[^"\']*["\']\s*>\s*</div>)',
        page_break_tag,
        md_text,
        flags=re.IGNORECASE
    )

    # 2. Reemplazo de imágenes locales por Data URI (Base64) para portabilidad total
    def replace_img_src(match):
        alt = match.group(1)
        src = match.group(2).strip()

        # Si ya es URL remota o base64, dejar intacto
        if src.startswith(('http://', 'https://', 'data:')):
            return match.group(0)

        img_path = (base_dir / src).resolve() if not os.path.isabs(src) else Path(src)
        if img_path.is_file():
            mime_type, _ = mimetypes.guess_type(str(img_path))
            mime_type = mime_type or 'image/png'
            try:
                with open(img_path, 'rb') as f:
                    b64_data = base64.b64encode(f.read()).decode('ascii')
                return f'![{alt}](data:{mime_type};base64,{b64_data})'
            except Exception:
                pass
        return match.group(0)

    md_text = re.sub(r'!\[(.*?)\]\((.*?)\)', replace_img_src, md_text)

    # 3. Alertas / Callouts (> [!NOTE], etc.)
    def replace_callout(match):
        callout_type = match.group(1).upper()
        content = match.group(2).strip()
        # Limpiar los prefijos '>' dentro del bloque de alerta
        content = re.sub(r'^>\s?', '', content, flags=re.MULTILINE)

        type_class = {
            'NOTE': 'callout-note',
            'TIP': 'callout-tip',
            'IMPORTANT': 'callout-important',
            'WARNING': 'callout-warning',
            'CAUTION': 'callout-important'
        }.get(callout_type, 'callout-note')

        title_text = {
            'NOTE': 'Nota',
            'TIP': 'Consejo',
            'IMPORTANT': 'Importante',
            'WARNING': 'Advertencia',
            'CAUTION': 'Precaución'
        }.get(callout_type, callout_type)

        return f'<div class="callout {type_class}"><div class="callout-title">{title_text}</div>\n\n{content}\n\n</div>'

    md_text = re.sub(
        r'>\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*\n((?:>[^\n]*\n?)*)',
        replace_callout,
        md_text
    )

    return md_text


def postprocess_html(html_content: str, has_header_control: bool = False) -> str:
    """
    Aplica mejoras estilísticas al HTML resultante:
    - Transforma menciones de papers como [P01], [P02], [S01] en badges elegantes
    - Reconoce tablas de 'Metadatos / Cabecera de Control' escritas en Markdown y les aplica la clase 'metadata-table'
    - Permite corte de página limpio en filas de tabla extremadamente largas (evita páginas en blanco)
    - Estiliza el título 'Índice de Contenido' con la barra azul institucional
    - Normaliza saltos de página aplicando break-before al siguiente bloque para eliminar páginas en blanco intermedias
    """
    # 1. Envolver etiquetas de citas como [P01], [P02], [S01], [S02] en <span class="paper-tag">[P01]</span>
    def wrap_paper_tag(m):
        tag = m.group(1)
        return f'<span class="paper-tag">[{tag}]</span>'

    html_content = re.sub(r'(?<!=["\'>])\[([PS]\d+)\](?![^<]*>|</a>)', wrap_paper_tag, html_content)

    # 2. Si hay una tabla escrita directamente en el markdown con 'Metadatos' y 'Detalle Institucional',
    # convertirla en la tabla institucional oficial con clases para columnas
    def enhance_metadata_table(match):
        table_html = match.group(0)
        if "Metadatos" in table_html and "Detalle Institucional" in table_html:
            # Reemplazar etiqueta <table> por <table class="metadata-table">
            table_html = re.sub(r'<table(?:\s+[^>]*)?>', '<table class="metadata-table">', table_html, count=1)
            # Asignar clases a td: primera columna meta-key, segunda meta-val
            def add_cell_classes(tr_match):
                tr_content = tr_match.group(0)
                td_parts = re.split(r'(</?td[^>]*>)', tr_content)
                td_count = 0
                new_parts = []
                for p in td_parts:
                    if p.startswith('<td'):
                        td_count += 1
                        if td_count % 2 == 1:
                            new_parts.append('<td class="meta-key">')
                        else:
                            new_parts.append('<td class="meta-val">')
                    else:
                        new_parts.append(p)
                return "".join(new_parts)

            table_html = re.sub(r'<tr>\s*<td.*?</tr>', add_cell_classes, table_html, flags=re.DOTALL)
        return table_html

    html_content = re.sub(r'<table.*?>.*?</table>', enhance_metadata_table, html_content, flags=re.DOTALL)

    # 2b. Marcar filas de tabla muy extensas con class="allow-break" para evitar que dejen páginas en blanco
    def allow_break_on_huge_rows(tr_match):
        tr_html = tr_match.group(0)
        plain_text = re.sub(r'<[^>]+>', ' ', tr_html)
        plain_text = re.sub(r'\s+', ' ', plain_text).strip()
        br_or_li_count = len(re.findall(r'<(?:br|li|/p)\b', tr_html, flags=re.IGNORECASE))
        td_count = len(re.findall(r'<td\b', tr_html, flags=re.IGNORECASE))
        if len(plain_text) > 420 or br_or_li_count >= 4 or (td_count >= 6 and len(plain_text) > 300):
            return re.sub(r'^<tr\b', '<tr class="allow-break"', tr_html, count=1)
        return tr_html

    html_content = re.sub(r'<tr\b[^>]*>.*?</tr>', allow_break_on_huge_rows, html_content, flags=re.DOTALL)

    # 3. Estilizar encabezados de Cabecera de Control del Entregable
    html_content = re.sub(
        r'<h[234]>\s*(Cabecera de Control del Entregable)\s*</h[234]>',
        r'<div class="control-header-title">\1</div>',
        html_content,
        flags=re.IGNORECASE
    )

    # 4. Estilizar encabezado del Índice de Contenido si se escribió como h2 en Markdown
    def style_toc_heading(match):
        title = match.group(1)
        return f'<div class="toc-header"><h2 class="toc-title">{title}</h2></div>'

    html_content = re.sub(
        r'<h2>\s*(ÍNDICE DE CONTENIDO|INDICE DE CONTENIDO)\s*</h2>',
        style_toc_heading,
        html_content,
        flags=re.IGNORECASE
    )

    # 5. Limpieza y optimización de saltos de página para evitar páginas en blanco
    # Desenvolver <div class="page-break"></div> si quedó dentro de un <p>
    html_content = re.sub(
        r'<p>\s*(<div class="page-break"></div>)\s*</p>',
        r'\1',
        html_content,
        flags=re.IGNORECASE
    )
    # Eliminar <hr> adyacentes a un salto de página (evita líneas huérfanas en hojas en blanco)
    html_content = re.sub(
        r'(?:<hr\s*/?>\s*)+(<div class="page-break"></div>)',
        r'\1',
        html_content,
        flags=re.IGNORECASE
    )
    html_content = re.sub(
        r'(<div class="page-break"></div>)(?:\s*<hr\s*/?>)+',
        r'\1',
        html_content,
        flags=re.IGNORECASE
    )
    # Colapsar múltiples saltos de página consecutivos en uno solo
    html_content = re.sub(
        r'(<div class="page-break"></div>\s*){2,}',
        '<div class="page-break"></div>\n',
        html_content,
        flags=re.IGNORECASE
    )
    # Si no hay cabecera sintética previa, eliminar saltos de página al inicio del documento
    if not has_header_control:
        html_content = re.sub(
            r'^\s*(?:<div class="page-break"></div>\s*)+',
            '',
            html_content,
            flags=re.IGNORECASE
        )
    # Eliminar saltos de página al final del documento
    html_content = re.sub(
        r'(?:\s*<div class="page-break"></div>)+\s*$',
        '',
        html_content,
        flags=re.IGNORECASE
    )

    # Transferir el salto de página como clase 'page-break-before' al siguiente elemento HTML real
    # (elimina el nodo vacío <div class="page-break"></div> que en Chromium genera páginas en blanco
    # cuando el elemento anterior termina justo al borde inferior de la hoja)
    def attach_page_break_to_next_tag(match):
        tag_name = match.group(1)
        attrs = match.group(2) or ""
        if re.search(r'\bclass\s*=\s*["\']', attrs, flags=re.IGNORECASE):
            attrs = re.sub(
                r'\bclass\s*=\s*(["\'])(.*?)\1',
                lambda m: f'class={m.group(1)}{m.group(2)} page-break-before{m.group(1)}',
                attrs,
                count=1,
                flags=re.IGNORECASE
            )
            return f'<{tag_name}{attrs}>'
        else:
            return f'<{tag_name} class="page-break-before"{attrs}>'

    html_content = re.sub(
        r'<div class="page-break"></div>\s*<([a-zA-Z0-9]+)\b([^>]*)>',
        attach_page_break_to_next_tag,
        html_content
    )

    return html_content


def clean_author_text(raw_val: Any) -> str:
    """
    Limpia y normaliza un texto de autor o lista de integrantes grupales extraído
    de YAML o del cuerpo Markdown (tablas, listas o texto en negrita).
    """
    if raw_val is None:
        return ""

    if isinstance(raw_val, (list, tuple)):
        items = [clean_author_text(x) for x in raw_val if clean_author_text(x)]
        if not items:
            return ""
        if len(items) == 2:
            return f"{items[0]} & {items[1]}"
        return ", ".join(items)

    text = str(raw_val).strip()
    if not text:
        return ""

    # Reemplazar saltos <br> por separador limpio
    parts = [p.strip() for p in re.split(r'<br\s*/?>|\r?\n', text, flags=re.IGNORECASE) if p.strip()]
    if len(parts) > 1:
        cleaned_parts = []
        for p in parts:
            p_clean = re.sub(r'^[ \t]*(?:[-*+•]|\d+[\.\)])\s*', '', p).strip()
            if p_clean:
                cleaned_parts.append(p_clean)
        if len(cleaned_parts) == 2:
            text = f"{cleaned_parts[0]} & {cleaned_parts[1]}"
        elif cleaned_parts:
            text = ", ".join(cleaned_parts)

    # Eliminar etiquetas HTML residuales y formato Markdown (**, *, __, `)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'(\*{1,2}|_{1,2}|`)', '', text)
    text = re.sub(r'\s+', ' ', text).strip(" \t,-:;•")
    return text


def format_author_footer(author_str: str, cycle_str: str = DEFAULT_CYCLE_SUFFIX) -> str:
    """
    Formatea el texto final para el pie de página izquierdo (Autor / Grupo + Ciclo).
    Si no se detecta autor, utiliza el nombre predeterminado de William David Ortiz Mamani.
    """
    cleaned = clean_author_text(author_str)
    if not cleaned:
        return DEFAULT_AUTHOR_FOOTER

    # Si ya contiene el ciclo o el semestre (ej. 'Ciclo VIII · 2026-2' o '2026-'), mantenerlo
    if re.search(r'\bciclo\b|\b202\d\b', cleaned, flags=re.IGNORECASE):
        return cleaned

    cycle_clean = clean_author_text(cycle_str) or DEFAULT_CYCLE_SUFFIX
    # Si el nombre (individual o grupal corto) no es excesivamente largo, anexar el ciclo
    if len(cleaned) <= 75:
        return f"{cleaned} — {cycle_clean}"
    return cleaned


def extract_metadata_from_body(body_md: str) -> Dict[str, str]:
    """
    Extrae datos clave (título, autor individual o equipo/integrantes grupales,
    institución, escuela, ciclo) del cuerpo Markdown (tablas, listas o cabeceras).
    """
    extracted: Dict[str, str] = {}

    # 1. Detectar título principal (# TITULO)
    m_title = re.search(r"^#\s+(.+)$", body_md, re.MULTILINE)
    if m_title:
        extracted["titulo"] = clean_author_text(m_title.group(1))

    # 2. Detectar autor individual o grupal en tablas Markdown:
    # Soporta: Equipo Investigador, Integrantes, Autor(es), Estudiante(s), Alumno(s), Grupo, Presentado por, etc.
    table_author_regex = (
        r"\|\s*\*{0,2}\s*"
        r"(?:Equipo(?:\s+Investigador|\s+de\s+Investigaci[oó]n|\s+de\s+Trabajo)?|"
        r"Integrantes?|Autores?|Autor(?:a|es|as)?|Authors?|Estudiantes?|Alumnos?|Alumnas?|"
        r"Miembros?|Grupo(?:\s+de\s+Trabajo)?|Investigador(?:es|a|as)?|"
        r"Responsables?|Presentado\s+por|Elaborado\s+por)"
        r"\s*:?\s*\*{0,2}\s*\|\s*([^|\n]+)\|"
    )
    m_table_author = re.search(table_author_regex, body_md, re.IGNORECASE)
    detected_author = ""
    if m_table_author:
        candidate = clean_author_text(m_table_author.group(1))
        # Evitar falsos positivos con cabeceras de tablas de literatura (ej. 'Problema Específico Abordado')
        if candidate and not re.search(
            r"^(?:Problema|Detalle|Descripci[oó]n|Nombre|Apellidos|Rol|C[oó]digo|Actividad|Paper|M[eé]todo)\b",
            candidate,
            re.IGNORECASE
        ):
            detected_author = candidate

    # 3. Si no está en tabla, buscar en las primeras ~90 líneas del documento en formato texto/negrita o lista
    if not detected_author:
        head_lines = "\n".join(body_md.splitlines()[:90])

        # 3a. Formato de línea directa: **Autor(es):** Nombre / **Integrantes:** Nombre1, Nombre2
        line_author_regex = (
            r"^[ \t]*(?:[-*+•]\s+|\d+[\.\)]\s+)?\*{0,2}"
            r"(?:Equipo(?:\s+Investigador|\s+de\s+Investigaci[oó]n|\s+de\s+Trabajo)?|"
            r"Integrantes?|Autores?|Autor(?:a|es|as)?|Authors?|Estudiantes?|Alumnos?|Alumnas?|"
            r"Grupo(?:\s+de\s+Trabajo)?|Investigador(?:es)?|Responsables?|Presentado\s+por|Elaborado\s+por)"
            r"\*{0,2}[ \t]*:[ \t]*\*{0,2}[ \t]*([^\r\n|]+)"
        )
        m_line_author = re.search(line_author_regex, head_lines, re.IGNORECASE | re.MULTILINE)
        if m_line_author:
            candidate = clean_author_text(m_line_author.group(1))
            if candidate:
                detected_author = candidate

        # 3b. Formato de bloque con lista debajo de 'Integrantes:' / 'Autores:' / '### Integrantes'
        if not detected_author:
            block_author_regex = (
                r"(?:^|\n)[ \t]*(?:#{1,4}[ \t]+|\*{1,2})?"
                r"(?:Equipo(?:\s+Investigador|\s+de\s+Investigaci[oó]n|\s+de\s+Trabajo)?|"
                r"Integrantes?|Autores?|Estudiantes?|Alumnos?|Presentado\s+por|Elaborado\s+por)"
                r"\*{0,2}[ \t]*:?[ \t]*\r?\n"
                r"((?:[ \t]*(?:[-*+•]|\d+[\.\)])[ \t]+[^\r\n]+\r?\n?){1,8})"
            )
            m_block = re.search(block_author_regex, head_lines, re.IGNORECASE)
            if m_block:
                bullet_lines = m_block.group(1).strip().splitlines()
                cleaned_bullets = []
                for bl in bullet_lines:
                    item = re.sub(r"^[ \t]*(?:[-*+•]|\d+[\.\)])[ \t]+", "", bl).strip()
                    item = clean_author_text(item)
                    if item:
                        cleaned_bullets.append(item)
                if len(cleaned_bullets) == 2:
                    detected_author = f"{cleaned_bullets[0]} & {cleaned_bullets[1]}"
                elif cleaned_bullets:
                    detected_author = ", ".join(cleaned_bullets)

    if detected_author:
        extracted["autor_detectado"] = detected_author
        extracted["equipo"] = detected_author

    # 4. Detectar institución y escuela
    m_inst = re.search(r"\|\s*\*{0,2}Instituci[oó]n:?\*{0,2}\s*\|\s*([^|\n]+)\|", body_md, re.IGNORECASE)
    if m_inst:
        val = clean_author_text(m_inst.group(1))
        if "—" in val or "-" in val:
            parts = re.split(r"\s*[—-]\s*", val, 1)
            extracted["institucion"] = parts[0].strip()
            extracted["escuela"] = parts[1].strip()

    return extracted


def resolve_author_metadata(frontmatter: Dict[str, Any], in_body_meta: Dict[str, str]) -> Tuple[str, bool]:
    """
    Determina el autor o grupo de autores del documento revisando el frontmatter YAML
    y el cuerpo del Markdown.
    Retorna (autor_pie_formateado, fue_detectado_en_archivo).
    Si el archivo no especifica autor ni grupo, retorna el valor predeterminado
    de William David Ortiz Mamani.
    """
    # Normalizar claves de frontmatter a minúsculas para búsqueda flexible
    fm_lower = {str(k).strip().lower(): v for k, v in frontmatter.items() if v is not None and str(v).strip() != ""}

    # Si existe un diccionario anidado 'metadatos' en el frontmatter, incluir sus claves también
    nested_meta = fm_lower.get("metadatos")
    if isinstance(nested_meta, dict):
        for nk, nv in nested_meta.items():
            nk_low = str(nk).strip().lower()
            if nk_low not in fm_lower and nv is not None and str(nv).strip() != "":
                fm_lower[nk_low] = nv

    # Buscar ciclo/semestre si el documento lo menciona, o usar el predeterminado
    cycle_str = DEFAULT_CYCLE_SUFFIX
    if fm_lower.get("ciclo"):
        cycle_str = str(fm_lower["ciclo"]).strip()

    # Claves grupales e individuales en el frontmatter
    group_keys = [
        "equipo", "equipo_investigador", "integrantes", "autores",
        "authors", "grupo", "estudiantes", "alumnos", "miembros"
    ]
    single_keys = [
        "autor", "author", "estudiante", "alumno", "responsable",
        "responsables", "presentado_por", "elaborado_por"
    ]

    fm_group_val = ""
    for gk in group_keys:
        if gk in fm_lower:
            fm_group_val = clean_author_text(fm_lower[gk])
            if fm_group_val:
                break

    fm_single_val = ""
    for sk in single_keys:
        if sk in fm_lower:
            fm_single_val = clean_author_text(fm_lower[sk])
            if fm_single_val:
                break

    fm_autor_pie = clean_author_text(fm_lower.get("autor_pie", ""))

    # Si el frontmatter tiene un equipo grupal (ej. con '&' o ',') pero autor_pie tenía solo a Uhziel por plantilla antigua,
    # priorizar el equipo grupal completo o si autor_pie es explícito y válido, usarlo.
    if fm_group_val:
        if fm_autor_pie and not (
            "uhziel" in fm_autor_pie.lower() and "william" not in fm_autor_pie.lower() and "william" in fm_group_val.lower()
        ):
            # Si autor_pie ya incluye a todos o fue personalizado pero el grupo tiene varios integrantes y autor_pie no:
            if ("&" in fm_group_val or "," in fm_group_val) and not ("&" in fm_autor_pie or "," in fm_autor_pie):
                return format_author_footer(fm_group_val, cycle_str), True
            return format_author_footer(fm_autor_pie, cycle_str), True
        return format_author_footer(fm_group_val, cycle_str), True

    if fm_autor_pie:
        # Reemplazar el antiguo valor por defecto de Uhziel en plantillas individuales por William David Ortiz Mamani
        if "uhziel" in fm_autor_pie.lower() and "william" not in fm_autor_pie.lower():
            fm_autor_pie = re.sub(
                r"Uhziel\s+El[ií]\s+Condori\s+Rojas",
                DEFAULT_AUTHOR_NAME,
                fm_autor_pie,
                flags=re.IGNORECASE
            )
        return format_author_footer(fm_autor_pie, cycle_str), True

    if fm_single_val:
        return format_author_footer(fm_single_val, cycle_str), True

    # Buscar en los datos extraídos del cuerpo del Markdown
    body_author = in_body_meta.get("autor_detectado") or in_body_meta.get("equipo") or ""
    if body_author:
        return format_author_footer(body_author, cycle_str), True

    # Valor predeterminado: William David Ortiz Mamani — Ciclo VIII · 2026-2
    return DEFAULT_AUTHOR_FOOTER, False


def inspect_markdown_metadata(md_path: Path) -> Dict[str, Any]:
    """
    Inspecciona rápidamente un archivo Markdown y retorna sus metadatos detectados
    (incluyendo 'autor_pie', 'autor_detectado_en_archivo', 'titulo', 'institucion', 'escuela').
    Útil para actualizar automáticamente la interfaz gráfica al seleccionar un archivo.
    """
    with open(md_path, "r", encoding="utf-8") as f:
        raw_content = f.read()

    frontmatter, body = parse_frontmatter(raw_content)
    in_body_meta = extract_metadata_from_body(body)
    autor_pie, was_detected = resolve_author_metadata(frontmatter, in_body_meta)

    meta = dict(DEFAULT_METADATA)
    meta.update(in_body_meta)
    meta.update(frontmatter)
    meta["autor_pie"] = autor_pie
    meta["autor_detectado_en_archivo"] = was_detected
    return meta


def build_metadata_rows(meta: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Construye las filas de la tabla 'Cabecera de Control del Entregable'
    utilizando los campos institucionales del documento si fueron definidos.
    """
    rows = []

    # Si el usuario define un diccionario 'metadatos' explícito en el frontmatter
    custom_dict = meta.get("metadatos")
    if isinstance(custom_dict, dict):
        for k, v in custom_dict.items():
            rows.append({"key": str(k), "val": str(v)})
        return rows

    field_mappings = [
        ("Asignatura", meta.get("asignatura")),
        ("Evaluación", meta.get("evaluacion")),
        ("Tema del Proyecto", meta.get("tema") or meta.get("tema_del_proyecto")),
        ("Equipo Investigador", meta.get("equipo") or meta.get("equipo_investigador") or meta.get("autores")),
        ("Docente Asesor", meta.get("docente") or meta.get("docente_asesor") or meta.get("asesor")),
        ("Institución", meta.get("institucion_detalle") or (
            f"{meta.get('institucion')} — {meta.get('escuela')}" if meta.get("institucion") and meta.get("escuela") else None
        )),
        ("Fecha de Entrega", meta.get("fecha") or meta.get("fecha_de_entrega")),
        ("Estado", meta.get("estado")),
    ]

    for key, val in field_mappings:
        if val:
            rows.append({"key": key, "val": str(val)})

    return rows


def render_html_document(md_path: Path, custom_overrides: Dict[str, Any] = None) -> Tuple[str, Dict[str, Any]]:
    """
    Lee un archivo Markdown, aplica estilos académicos y devuelve el código HTML completo
    y el diccionario consolidado de metadatos.
    Previene la duplicación de cabeceras de control si ya están presentes en el cuerpo.
    """
    with open(md_path, "r", encoding="utf-8") as f:
        raw_content = f.read()

    frontmatter, body = parse_frontmatter(raw_content)

    # Detectar si el cuerpo Markdown YA contiene su propia cabecera o tabla de control
    has_in_body_control = bool(
        re.search(r"\|\s*Metadatos\s*\|\s*Detalle\s+Institucional\s*\|", body, re.IGNORECASE) or
        re.search(r"Cabecera\s+de\s+Control\s+del\s+Entregable", body, re.IGNORECASE)
    )

    # Extraer metadatos auxiliares del cuerpo siempre (para detectar autor individual/grupal o título)
    in_body_meta = extract_metadata_from_body(body)
    resolved_author_pie, was_author_detected = resolve_author_metadata(frontmatter, in_body_meta)

    # Fusionar metadatos: Defaults <- Datos en cuerpo <- Frontmatter <- Autor resuelto <- Sobrescrituras manuales
    meta = dict(DEFAULT_METADATA)
    meta.update(in_body_meta)
    meta.update(frontmatter)
    meta["autor_pie"] = resolved_author_pie
    meta["autor_detectado_en_archivo"] = was_author_detected
    if custom_overrides:
        meta.update({k: v for k, v in custom_overrides.items() if v is not None and v != ""})

    # Decidir si generar bloque sintético de cabecera de control:
    # SOLO se genera si:
    # 1. El usuario lo pidió explícitamente (mostrar_cabecera_control: true) Y
    # 2. El cuerpo NO tiene ya su propia tabla de control
    show_control = meta.get("mostrar_cabecera_control", False)
    if isinstance(show_control, str):
        show_control = show_control.lower() in ("true", "1", "si", "sí", "yes")

    # Si el cuerpo ya tiene la tabla, NUNCA inyectar una segunda cabecera duplicada
    if has_in_body_control:
        show_control = False

    metadata_rows = build_metadata_rows(meta) if show_control else []
    has_synthetic_header = bool(show_control and metadata_rows)

    # Preprocesamiento de Markdown
    processed_md = preprocess_markdown(body, md_path.parent)

    # Conversión con extensiones avanzadas
    md_extensions = [
        'tables',
        'fenced_code',
        'codehilite',
        'sane_lists',
        'attr_list',
        'def_list',
        'footnotes'
    ]
    raw_html = markdown.markdown(processed_md, extensions=md_extensions)
    body_html = postprocess_html(raw_html, has_header_control=has_synthetic_header)

    # Cargar CSS
    with open(CSS_TEMPLATE_PATH, "r", encoding="utf-8") as f:
        inline_css = f.read()

    # Cargar Plantilla HTML
    with open(HTML_TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template_html = f.read()

    doc_title = meta.get("titulo") or "Documento Académico"
    main_title = meta.get("titulo", "")
    control_subtitle = meta.get("subtitulo", "Cabecera de Control del Entregable")

    if has_synthetic_header:
        rows_html = ""
        for item in metadata_rows:
            rows_html += f'            <tr>\n              <td class="meta-key">{item["key"]}:</td>\n              <td class="meta-val">{item["val"]}</td>\n            </tr>\n'

        title_h1 = f'<h1 class="main-title">{main_title}</h1>\n' if main_title else ''
        header_control_block = f"""    <header class="doc-header">
      {title_h1}      <div class="control-header-section">
        <div class="control-header-title">{control_subtitle}</div>
        <table class="metadata-table">
          <thead>
            <tr>
              <th style="width: 25%;">Metadatos</th>
              <th style="width: 75%;">Detalle Institucional</th>
            </tr>
          </thead>
          <tbody>
{rows_html}          </tbody>
        </table>
      </div>
    </header>"""
    else:
        header_control_block = ""

    # Inyección final en plantilla
    final_html = template_html.replace("{{ doc_title }}", doc_title)
    final_html = final_html.replace("{{ inline_css }}", inline_css)
    final_html = final_html.replace("{{ header_control_block }}", header_control_block)
    final_html = final_html.replace("{{ content }}", body_html)

    return final_html, meta

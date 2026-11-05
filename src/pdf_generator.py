"""
Generador de PDF de Alta Fidelidad mediante Microsoft Edge / Chromium CDP.
Permite maquetación A4 con cabeceras y pies de página dinámicos numerados (Página X de Y)
y prevención inteligente de páginas en blanco.
"""

import asyncio
import base64
import html
import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp

from src.config import DEFAULT_AUTHOR_FOOTER, find_browser_executable


def _strip_blank_pdf_pages(pdf_bytes: bytes) -> bytes:
    """
    Verifica el PDF generado y elimina cualquier página que haya quedado en blanco
    en medio o al final del documento (es decir, páginas que solo contienen la cabecera
    y el pie de página corridos, sin texto, tablas ni imágenes en el área de cuerpo).
    """
    try:
        import pymupdf
    except ImportError:
        try:
            import fitz as pymupdf
        except ImportError:
            return pdf_bytes

    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        if len(doc) <= 1:
            doc.close()
            return pdf_bytes

        blank_indices: List[int] = []
        for idx, page in enumerate(doc):
            h = page.rect.height
            # La cabecera está en y < 50pt y el pie de página en y > (h - 54pt) (~788pt en A4)
            top_bound = 50.0
            bottom_bound = h - 54.0

            # 1. Revisar palabras dentro del área del cuerpo
            words = page.get_text_words()
            body_words = [w for w in words if w[3] > top_bound and w[1] < bottom_bound and str(w[4]).strip()]
            if body_words:
                continue

            # 2. Revisar imágenes dentro del área del cuerpo
            has_body_image = False
            for img_info in page.get_images(full=True):
                xref = img_info[0]
                for rect in page.get_image_rects(xref):
                    if rect.y1 > top_bound and rect.y0 < bottom_bound and rect.width > 5 and rect.height > 5:
                        has_body_image = True
                        break
                if has_body_image:
                    break
            if has_body_image:
                continue

            # 3. Revisar gráficos vectoriales / tablas significativas en el área del cuerpo
            has_body_drawing = False
            for d in page.get_drawings():
                r = d.get("rect")
                if r and r.y1 > top_bound and r.y0 < bottom_bound and (r.width > 10 or r.height > 10):
                    has_body_drawing = True
                    break
            if has_body_drawing:
                continue

            blank_indices.append(idx)

        # Si no hay páginas en blanco o todas parecieran en blanco, devolver intacto
        if not blank_indices or len(blank_indices) >= len(doc):
            doc.close()
            return pdf_bytes

        # Eliminar páginas en blanco en orden inverso
        for idx in reversed(blank_indices):
            doc.delete_page(idx)

        out_bytes = doc.tobytes(garbage=3, deflate=True)
        doc.close()
        return out_bytes
    except Exception:
        return pdf_bytes


def get_free_port() -> int:
    """Obtiene un puerto TCP libre disponible en la máquina."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


async def _generate_pdf_via_cdp(
    browser_exe: str,
    html_file_path: Path,
    output_pdf_path: Path,
    meta: Dict[str, Any],
    timeout: float = 30.0
) -> None:
    """
    Controla el navegador mediante Chrome DevTools Protocol para renderizar
    el PDF con las cabeceras y pies de página exactos solicitados.
    """
    port = get_free_port()
    user_data_dir = tempfile.mkdtemp(prefix="md_to_pdf_")
    
    cmd = [
        browser_exe,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-extensions",
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_data_dir}",
        "about:blank"
    ]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    try:
        # Esperar a que el puerto de depuración esté listo
        ws_url = None
        start_time = time.time()
        while time.time() - start_time < 10.0:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1.0) as resp:
                    data = json.loads(resp.read().decode())
                    ws_url = data.get("webSocketDebuggerUrl")
                    if ws_url:
                        break
            except Exception:
                await asyncio.sleep(0.15)

        if not ws_url:
            raise RuntimeError("No se pudo establecer conexión con el puerto CDP del navegador.")

        # Textos para cabecera y pie de página escapados para HTML seguro
        institucion = html.escape(str(meta.get("institucion", "Universidad Peruana Unión")))
        escuela = html.escape(str(meta.get("escuela", "Escuela Prof. de Ingeniería de Sistemas")))
        autor_pie = html.escape(
            str(meta.get("autor_pie") or meta.get("autor") or meta.get("equipo") or DEFAULT_AUTHOR_FOOTER)
        )

        # Plantillas Chromium de Header y Footer
        header_template = f"""
        <div style="font-size: 8pt; font-family: 'Segoe UI', Arial, sans-serif; color: #64748b; width: 100%; display: flex; justify-content: space-between; padding: 0 42px; margin-top: 4px;">
            <span>{institucion}</span>
            <span>{escuela}</span>
        </div>
        """

        footer_template = f"""
        <div style="font-size: 8pt; font-family: 'Segoe UI', Arial, sans-serif; color: #64748b; width: 100%; display: flex; justify-content: space-between; padding: 0 42px; margin-bottom: 4px;">
            <span>{autor_pie}</span>
            <span>Página <span class="pageNumber"></span> de <span class="totalPages"></span></span>
        </div>
        """

        file_url = html_file_path.resolve().as_uri()

        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(ws_url, max_msg_size=100 * 1024 * 1024) as ws:
                # 1. Crear nuevo objetivo
                await ws.send_json({"id": 1, "method": "Target.createTarget", "params": {"url": "about:blank"}})
                target_resp = await ws.receive_json()
                target_id = target_resp["result"]["targetId"]

                # 2. Conectar al objetivo creado
                await ws.send_json({"id": 2, "method": "Target.attachToTarget", "params": {"targetId": target_id, "flatten": True}})
                attach_resp = await ws.receive_json()
                session_id = attach_resp["params"]["sessionId"]

                # 3. Habilitar eventos de página
                await ws.send_json({"sessionId": session_id, "id": 3, "method": "Page.enable"})
                await ws.receive_json()

                # 4. Navegar al archivo HTML
                await ws.send_json({
                    "sessionId": session_id,
                    "id": 4,
                    "method": "Page.navigate",
                    "params": {"url": file_url}
                })
                await ws.receive_json()

                # Esperar que los recursos, fuentes y estilos terminen de asentarse
                await asyncio.sleep(0.8)

                # 4b. Limpieza DOM en vivo previa a impresión para evitar saltos de página redundantes o huérfanos
                cleanup_js = """
                (() => {
                    const body = document.querySelector('.doc-body');
                    if (!body) return;
                    // Convertir cualquier .page-break remanente en clase page-break-before del siguiente hermano
                    body.querySelectorAll('.page-break').forEach(pb => {
                        let next = pb.nextElementSibling;
                        if (next) {
                            next.classList.add('page-break-before');
                        }
                        pb.remove();
                    });
                    // Si no hay cabecera de control antes de .doc-body, el primer hijo nunca debe forzar salto de página
                    const header = document.querySelector('.doc-header');
                    if (!header && body.firstElementChild) {
                        body.firstElementChild.classList.remove('page-break-before');
                    }
                })();
                """
                await ws.send_json({
                    "sessionId": session_id,
                    "id": 45,
                    "method": "Runtime.evaluate",
                    "params": {"expression": cleanup_js}
                })
                await ws.receive_json()

                # 5. Generar PDF con parámetros A4
                await ws.send_json({
                    "sessionId": session_id,
                    "id": 5,
                    "method": "Page.printToPDF",
                    "params": {
                        "landscape": False,
                        "displayHeaderFooter": True,
                        "headerTemplate": header_template,
                        "footerTemplate": footer_template,
                        "printBackground": True,
                        "paperWidth": 8.27,    # A4: 210mm
                        "paperHeight": 11.69,  # A4: 297mm
                        "marginTop": 0.75,     # ~19mm
                        "marginBottom": 0.75,  # ~19mm
                        "marginLeft": 0.7,     # ~17mm
                        "marginRight": 0.7,    # ~17mm
                        "preferCSSPageSize": True
                    }
                })

                # 6. Recibir datos en Base64
                pdf_data_b64 = None
                while True:
                    msg = await ws.receive_json()
                    if msg.get("id") == 5:
                        if "error" in msg:
                            raise RuntimeError(f"Error al imprimir PDF: {msg['error']}")
                        pdf_data_b64 = msg["result"]["data"]
                        break

                if not pdf_data_b64:
                    raise RuntimeError("No se recibieron datos de PDF desde el motor de renderizado.")

                pdf_bytes = base64.b64decode(pdf_data_b64)
                pdf_bytes = _strip_blank_pdf_pages(pdf_bytes)
                with open(output_pdf_path, "wb") as f:
                    f.write(pdf_bytes)

    finally:
        # Asegurar terminación del proceso y limpieza de temporales
        proc.terminate()
        try:
            proc.wait(timeout=3.0)
        except Exception:
            proc.kill()

        shutil.rmtree(user_data_dir, ignore_errors=True)


def convert_html_to_pdf(
    html_file_path: Path,
    output_pdf_path: Path,
    meta: Dict[str, Any]
) -> None:
    """
    Función de entrada principal para convertir un HTML a PDF con
    cabecera y pie de página institucionales numerados.
    """
    browser_exe = find_browser_executable()
    if not browser_exe:
        raise FileNotFoundError(
            "No se encontró Microsoft Edge ni Google Chrome en el sistema. "
            "Por favor asegúrese de tener Microsoft Edge instalado."
        )

    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(_generate_pdf_via_cdp(browser_exe, html_file_path, output_pdf_path, meta))

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
from typing import Any, Dict, Optional

import aiohttp

from src.config import DEFAULT_AUTHOR_FOOTER, find_browser_executable


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
                        while (next && next.tagName === 'HR') {
                            const toRemove = next;
                            next = next.nextElementSibling;
                            toRemove.remove();
                        }
                        if (next) {
                            next.classList.add('page-break-before');
                        }
                        pb.remove();
                    });
                    // Eliminar nodos vacíos al final de .doc-body que pudieran causar una hoja final en blanco
                    while (body.lastElementChild && !body.lastElementChild.textContent.trim() && !body.lastElementChild.querySelector('img, svg, table, hr')) {
                        body.lastElementChild.remove();
                    }
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

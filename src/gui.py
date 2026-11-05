"""
Interfaz Gráfica de Usuario (GUI) Moderna en Tkinter / ttk
Permite transformar archivos Markdown a PDF y HTML con selección estricta de formato y control total.
"""

import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from src.config import ASSETS_DIR, BASE_DIR, DEFAULT_METADATA, EXAMPLES_DIR
from src.converter import MarkdownConverter
from src.template_engine import inspect_markdown_metadata


class ModernApp(tk.Tk):
    """Ventana principal de la aplicación de transformación de Markdown a PDF/HTML."""

    def __init__(self):
        super().__init__()

        self.title("Transformador Markdown a PDF & HTML — UPeU Académico")
        self.geometry("880x730")
        self.minsize(780, 640)
        self.configure(bg="#f8fafc")

        # Establecer icono si existe
        icon_path = ASSETS_DIR / "app_icon.ico"
        if icon_path.is_file():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

        # Variables de estado
        self.var_md_path = tk.StringVar()
        self.var_out_dir = tk.StringVar()
        # Formato de exportación: 'pdf', 'html', 'both' (Por defecto: Solo PDF)
        self.var_export_format = tk.StringVar(value="pdf")
        self.var_auto_open = tk.BooleanVar(value=True)

        # Variables de metadatos rápidos
        self.var_institucion = tk.StringVar(value=DEFAULT_METADATA["institucion"])
        self.var_escuela = tk.StringVar(value=DEFAULT_METADATA["escuela"])
        self.var_autor = tk.StringVar(value=DEFAULT_METADATA["autor_pie"])
        self.var_titulo = tk.StringVar(value="")

        # Rutas de los últimos resultados
        self.last_pdf_path: Optional[Path] = None
        self.last_html_path: Optional[Path] = None
        self._last_inspected_md: Optional[Path] = None

        self._setup_styles()
        self._build_ui()

    def _setup_styles(self):
        self.style = ttk.Style(self)
        self.style.theme_use("clam")

        # Configuración de colores
        bg_card = "#ffffff"
        text_dark = "#1e293b"
        accent_blue = "#164e87"

        self.style.configure(".", background="#f8fafc", foreground=text_dark, font=("Segoe UI", 9))
        self.style.configure("TLabel", background="#f8fafc", foreground=text_dark, font=("Segoe UI", 9))
        self.style.configure("Card.TFrame", background=bg_card, relief="solid", borderwidth=1)
        self.style.configure("CardLabel.TLabel", background=bg_card, foreground=text_dark, font=("Segoe UI", 9))
        self.style.configure("CardTitle.TLabel", background=bg_card, foreground=accent_blue, font=("Segoe UI", 10, "bold"))

        # Radiobutton institucional
        self.style.configure("TRadiobutton", background=bg_card, foreground=text_dark, font=("Segoe UI", 9, "bold"))

        # Botón primario de transformación
        self.style.configure(
            "Primary.TButton",
            background="#164e87",
            foreground="#ffffff",
            font=("Segoe UI", 10, "bold"),
            padding=(16, 8),
            borderwidth=0
        )
        self.style.map(
            "Primary.TButton",
            background=[("active", "#0f3966"), ("disabled", "#94a3b8")]
        )

        # Botón de acción secundaria
        self.style.configure(
            "Secondary.TButton",
            background="#e2e8f0",
            foreground="#1e293b",
            font=("Segoe UI", 9, "bold"),
            padding=(10, 5),
            borderwidth=0
        )
        self.style.map(
            "Secondary.TButton",
            background=[("active", "#cbd5e1")]
        )

        # Checkbutton
        self.style.configure("TCheckbutton", background=bg_card, foreground=text_dark, font=("Segoe UI", 9))

    def _build_ui(self):
        # 1. Header Banner Superior
        header_frame = tk.Frame(self, bg="#164e87", height=75)
        header_frame.pack(fill="x", side="top")
        header_frame.pack_propagate(False)

        header_content = tk.Frame(header_frame, bg="#164e87")
        header_content.pack(fill="both", expand=True, padx=25, pady=12)

        lbl_app_title = tk.Label(
            header_content,
            text="Transformador Markdown a PDF & HTML",
            font=("Segoe UI", 14, "bold"),
            bg="#164e87",
            fg="#ffffff"
        )
        lbl_app_title.pack(anchor="w")

        lbl_app_sub = tk.Label(
            header_content,
            text="Formato Académico Profesional de Alta Fidelidad (UPeU / Ing. de Sistemas)",
            font=("Segoe UI", 9),
            bg="#164e87",
            fg="#cbd5e1"
        )
        lbl_app_sub.pack(anchor="w")

        # 2. Contenedor Principal
        main_body = tk.Frame(self, bg="#f8fafc")
        main_body.pack(fill="both", expand=True, padx=20, pady=12)

        # --- SECCIÓN 1: Seleccionar archivo Markdown ---
        card_file = tk.Frame(main_body, bg="#ffffff", bd=1, relief="solid")
        card_file.pack(fill="x", pady=(0, 10), ipady=8, ipadx=12)

        lbl_file_title = ttk.Label(card_file, text="📄 1. Archivo Markdown de Entrada (.md)", style="CardTitle.TLabel")
        lbl_file_title.pack(anchor="w", padx=10, pady=(6, 4))

        row_file = tk.Frame(card_file, bg="#ffffff")
        row_file.pack(fill="x", padx=10, pady=2)

        self.entry_md = tk.Entry(
            row_file,
            textvariable=self.var_md_path,
            font=("Segoe UI", 9),
            relief="solid",
            bd=1,
            bg="#f8fafc"
        )
        self.entry_md.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 8))

        btn_browse = ttk.Button(row_file, text="Explorar...", style="Secondary.TButton", command=self._browse_md)
        btn_browse.pack(side="left", padx=(0, 6))

        btn_sample = ttk.Button(row_file, text="Cargar Ejemplo UPeU", style="Secondary.TButton", command=self._load_sample)
        btn_sample.pack(side="left")

        # --- SECCIÓN 2: Opciones de Formato y Destino ---
        card_opts = tk.Frame(main_body, bg="#ffffff", bd=1, relief="solid")
        card_opts.pack(fill="x", pady=(0, 10), ipady=8, ipadx=12)

        lbl_opts_title = ttk.Label(card_opts, text="⚙️ 2. ¿Qué formato deseas exportar?", style="CardTitle.TLabel")
        lbl_opts_title.pack(anchor="w", padx=10, pady=(6, 4))

        row_format = tk.Frame(card_opts, bg="#ffffff")
        row_format.pack(fill="x", padx=10, pady=4)

        rb_pdf = ttk.Radiobutton(
            row_format,
            text="📕 Solo PDF (.pdf)",
            variable=self.var_export_format,
            value="pdf",
            style="TRadiobutton"
        )
        rb_pdf.pack(side="left", padx=(0, 20))

        rb_html = ttk.Radiobutton(
            row_format,
            text="🌐 Solo HTML (.html)",
            variable=self.var_export_format,
            value="html",
            style="TRadiobutton"
        )
        rb_html.pack(side="left", padx=(0, 20))

        rb_both = ttk.Radiobutton(
            row_format,
            text="📦 Ambos formatos (PDF y HTML)",
            variable=self.var_export_format,
            value="both",
            style="TRadiobutton"
        )
        rb_both.pack(side="left", padx=(0, 25))

        chk_open = ttk.Checkbutton(row_format, text="Abrir archivo al terminar", variable=self.var_auto_open)
        chk_open.pack(side="left")

        # Carpeta de salida personalizada (opcional)
        row_out = tk.Frame(card_opts, bg="#ffffff")
        row_out.pack(fill="x", padx=10, pady=(8, 2))

        lbl_out = ttk.Label(row_out, text="Carpeta de Salida:", style="CardLabel.TLabel")
        lbl_out.pack(side="left", padx=(0, 8))

        self.entry_out = tk.Entry(
            row_out,
            textvariable=self.var_out_dir,
            font=("Segoe UI", 9),
            relief="solid",
            bd=1,
            bg="#f8fafc"
        )
        self.entry_out.pack(side="left", fill="x", expand=True, ipady=3, padx=(0, 8))

        btn_browse_out = ttk.Button(row_out, text="Cambiar...", style="Secondary.TButton", command=self._browse_out)
        btn_browse_out.pack(side="left")

        # --- SECCIÓN 3: Metadatos Rápidos Institucionales ---
        card_meta = tk.Frame(main_body, bg="#ffffff", bd=1, relief="solid")
        card_meta.pack(fill="x", pady=(0, 10), ipady=8, ipadx=12)

        lbl_meta_title = ttk.Label(card_meta, text="🏛️ 3. Encabezados y Pie de Página Institucionales", style="CardTitle.TLabel")
        lbl_meta_title.pack(anchor="w", padx=10, pady=(6, 4))

        grid_meta = tk.Frame(card_meta, bg="#ffffff")
        grid_meta.pack(fill="x", padx=10, pady=2)

        # Fila 1: Institución y Escuela
        tk.Label(grid_meta, text="Institución (Header Izq):", bg="#ffffff", font=("Segoe UI", 8, "bold")).grid(row=0, column=0, sticky="w", pady=2)
        tk.Entry(grid_meta, textvariable=self.var_institucion, font=("Segoe UI", 9), relief="solid", bd=1, bg="#f8fafc").grid(row=0, column=1, sticky="ew", padx=(5, 15), pady=2)

        tk.Label(grid_meta, text="Escuela (Header Der):", bg="#ffffff", font=("Segoe UI", 8, "bold")).grid(row=0, column=2, sticky="w", pady=2)
        tk.Entry(grid_meta, textvariable=self.var_escuela, font=("Segoe UI", 9), relief="solid", bd=1, bg="#f8fafc").grid(row=0, column=3, sticky="ew", padx=(5, 0), pady=2)

        # Fila 2: Autor / Ciclo y Título opcional
        tk.Label(grid_meta, text="Autor / Ciclo (Footer Izq):", bg="#ffffff", font=("Segoe UI", 8, "bold")).grid(row=1, column=0, sticky="w", pady=2)
        tk.Entry(grid_meta, textvariable=self.var_autor, font=("Segoe UI", 9), relief="solid", bd=1, bg="#f8fafc").grid(row=1, column=1, sticky="ew", padx=(5, 15), pady=2)

        tk.Label(grid_meta, text="Título (Opcional):", bg="#ffffff", font=("Segoe UI", 8, "bold")).grid(row=1, column=2, sticky="w", pady=2)
        tk.Entry(grid_meta, textvariable=self.var_titulo, font=("Segoe UI", 9), relief="solid", bd=1, bg="#f8fafc").grid(row=1, column=3, sticky="ew", padx=(5, 0), pady=2)

        grid_meta.columnconfigure(1, weight=1)
        grid_meta.columnconfigure(3, weight=1)

        # --- SECCIÓN 4: Botón de Transformación y Consola ---
        action_bar = tk.Frame(main_body, bg="#f8fafc")
        action_bar.pack(fill="x", pady=(2, 6))

        self.btn_convert = ttk.Button(
            action_bar,
            text="⚡ Transformar Markdown Ahora",
            style="Primary.TButton",
            command=self._start_conversion
        )
        self.btn_convert.pack(side="left", padx=(0, 12))

        self.progress_bar = ttk.Progressbar(action_bar, mode="indeterminate", length=200)

        # Botones de apertura rápida (ocultos hasta completar)
        self.btn_open_pdf = ttk.Button(action_bar, text="📄 Ver PDF", style="Secondary.TButton", command=self._open_pdf)
        self.btn_open_html = ttk.Button(action_bar, text="🌐 Ver HTML", style="Secondary.TButton", command=self._open_html)
        self.btn_open_folder = ttk.Button(action_bar, text="📁 Abrir Carpeta", style="Secondary.TButton", command=self._open_folder)

        # Consola de estado / log
        card_log = tk.Frame(main_body, bg="#ffffff", bd=1, relief="solid")
        card_log.pack(fill="both", expand=True, pady=(4, 0))

        lbl_log = ttk.Label(card_log, text="📋 Registro de Transformación:", style="CardLabel.TLabel")
        lbl_log.pack(anchor="w", padx=10, pady=(6, 2))

        self.txt_log = tk.Text(
            card_log,
            height=5,
            font=("Consolas", 9),
            bg="#0f172a",
            fg="#f8fafc",
            relief="flat",
            padx=10,
            pady=8
        )
        self.txt_log.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # Mensaje de bienvenida
        self._log("Listo. Seleccione un archivo Markdown (.md) y el formato deseado (Solo PDF, Solo HTML o Ambos).")

    def _log(self, text: str):
        self.txt_log.insert(tk.END, f"{text}\n")
        self.txt_log.see(tk.END)

    def _sync_metadata_from_file(self, md_file: Path):
        """
        Lee el archivo Markdown seleccionado para identificar automáticamente
        si tiene un autor individual o grupal, o aplicar por defecto
        William David Ortiz Mamani.
        """
        try:
            if not md_file.is_file():
                return
            meta = inspect_markdown_metadata(md_file)
            self._last_inspected_md = md_file.resolve()

            autor_pie = meta.get("autor_pie") or DEFAULT_METADATA["autor_pie"]
            was_detected = meta.get("autor_detectado_en_archivo", False)
            self.var_autor.set(autor_pie)

            if meta.get("institucion"):
                self.var_institucion.set(str(meta["institucion"]))
            if meta.get("escuela"):
                self.var_escuela.set(str(meta["escuela"]))

            if was_detected:
                self._log(f"  👤 Autor/Grupo identificado en archivo: {autor_pie}")
            else:
                self._log(f"  👤 Autor predeterminado aplicado: {autor_pie}")
        except Exception:
            self.var_autor.set(DEFAULT_METADATA["autor_pie"])

    def _browse_md(self):
        f = filedialog.askopenfilename(
            title="Seleccionar archivo Markdown",
            filetypes=[("Archivos Markdown", "*.md *.markdown *.mdown"), ("Todos los archivos", "*.*")]
        )
        if f:
            md_path = Path(f)
            self.var_md_path.set(f)
            if not self.var_out_dir.get():
                self.var_out_dir.set(str(md_path.parent))
            self._log(f"Seleccionado: {f}")
            self._sync_metadata_from_file(md_path)

    def _browse_out(self):
        d = filedialog.askdirectory(title="Seleccionar carpeta de salida")
        if d:
            self.var_out_dir.set(d)
            self._log(f"Carpeta de salida: {d}")

    def _load_sample(self):
        sample_path = EXAMPLES_DIR / "ejemplo_articulo_investigacion.md"
        if sample_path.is_file():
            self.var_md_path.set(str(sample_path))
            self.var_out_dir.set(str(sample_path.parent))
            self._log(f"Ejemplo oficial UPeU cargado: {sample_path.name}")
            self._sync_metadata_from_file(sample_path)
        else:
            messagebox.showwarning("Aviso", "No se encontró el archivo de ejemplo.")

    def _start_conversion(self):
        md_path_str = self.var_md_path.get().strip()
        if not md_path_str:
            messagebox.showwarning("Atención", "Por favor seleccione un archivo Markdown (.md).")
            return

        md_file = Path(md_path_str)
        if not md_file.is_file():
            messagebox.showerror("Error", f"El archivo no existe:\n{md_file}")
            return

        # Si el usuario escribió la ruta manualmente y no se había inspeccionado aún
        if self._last_inspected_md != md_file.resolve():
            self._sync_metadata_from_file(md_file)

        # Deshabilitar botón durante conversión
        self.btn_convert.config(state="disabled")
        self.btn_open_pdf.pack_forget()
        self.btn_open_html.pack_forget()
        self.btn_open_folder.pack_forget()

        self.progress_bar.pack(side="left", padx=10)
        self.progress_bar.start(10)

        fmt = self.var_export_format.get()
        fmt_label = "Solo PDF" if fmt == "pdf" else ("Solo HTML" if fmt == "html" else "Ambos formatos")
        self._log(f"Iniciando transformación ({fmt_label}): {md_file.name}...")

        # Ejecutar en hilo de fondo para no bloquear la interfaz
        thread = threading.Thread(target=self._run_conversion_worker, args=(md_file,), daemon=True)
        thread.start()

    def _run_conversion_worker(self, md_file: Path):
        try:
            out_dir = Path(self.var_out_dir.get().strip()) if self.var_out_dir.get().strip() else md_file.parent
            stem = md_file.stem

            fmt = self.var_export_format.get()
            gen_pdf = fmt in ("pdf", "both")
            gen_html = fmt in ("html", "both")

            out_html = (out_dir / f"{stem}.html") if gen_html else None
            out_pdf = (out_dir / f"{stem}.pdf") if gen_pdf else None

            # Metadatos personalizados si el usuario los especificó
            overrides = {}
            if self.var_institucion.get().strip():
                overrides["institucion"] = self.var_institucion.get().strip()
            if self.var_escuela.get().strip():
                overrides["escuela"] = self.var_escuela.get().strip()
            if self.var_autor.get().strip():
                overrides["autor_pie"] = self.var_autor.get().strip()
            if self.var_titulo.get().strip():
                overrides["titulo"] = self.var_titulo.get().strip()

            converter = MarkdownConverter()
            html_res, pdf_res = converter.convert(
                input_md_path=md_file,
                output_pdf_path=out_pdf,
                output_html_path=out_html,
                generate_pdf=gen_pdf,
                generate_html=gen_html,
                custom_metadata=overrides
            )

            self.last_pdf_path = pdf_res
            self.last_html_path = html_res

            self.after(0, self._on_conversion_success)

        except Exception as e:
            self.after(0, lambda: self._on_conversion_error(str(e)))

    def _on_conversion_success(self):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.btn_convert.config(state="normal")

        self._log("✔ ¡Transformación completada con éxito!")
        if self.last_pdf_path and self.last_pdf_path.is_file():
            self._log(f"  → PDF generado: {self.last_pdf_path.name} ({self.last_pdf_path.stat().st_size:,} bytes)")
            self.btn_open_pdf.pack(side="left", padx=(0, 6))

        if self.last_html_path and self.last_html_path.is_file():
            self._log(f"  → HTML generado: {self.last_html_path.name}")
            self.btn_open_html.pack(side="left", padx=(0, 6))

        self.btn_open_folder.pack(side="left")

        # Apertura automática según el formato generado
        if self.var_auto_open.get():
            if self.last_pdf_path and self.last_pdf_path.is_file():
                self._open_pdf()
            elif self.last_html_path and self.last_html_path.is_file():
                self._open_html()

    def _on_conversion_error(self, err_msg: str):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.btn_convert.config(state="normal")
        self._log(f"❌ Error durante la conversión: {err_msg}")
        messagebox.showerror("Error en Conversión", f"Ocurrió un error al procesar el documento:\n\n{err_msg}")

    def _open_pdf(self):
        if self.last_pdf_path and self.last_pdf_path.is_file():
            os.startfile(str(self.last_pdf_path))

    def _open_html(self):
        if self.last_html_path and self.last_html_path.is_file():
            os.startfile(str(self.last_html_path))

    def _open_folder(self):
        target = self.last_pdf_path or self.last_html_path
        if target and target.parent.is_dir():
            os.startfile(str(target.parent))


def launch_gui():
    app = ModernApp()
    app.mainloop()


if __name__ == "__main__":
    launch_gui()

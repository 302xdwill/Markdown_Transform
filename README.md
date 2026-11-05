# 🎓 Transformador de Markdown a PDF y HTML — Formato Académico Institucional (UPeU)

Software profesional desarrollado en **Python** para transformar archivos Markdown (`.md`) en documentos **PDF** de alta fidelidad para impresión y entregas académicas, y en archivos **HTML** interactivos y autocontenidos.

El formato visual reproduce con exactitud la maquetación y tipografía de los entregables académicos oficiales de la **Universidad Peruana Unión (UPeU)** — Escuela Profesional de Ingeniería de Sistemas (cabecera institucional, pie de página numerado *Página X de Y*, tabla de metadatos de control, tablas de papers y matrices de síntesis comparativa).

---

## 🚀 Ejecución Inmediata (.exe listo para usar)

El ejecutable se encuentra en:
📁 **`dist/MarkdownTransformer.exe`**

### Modo Gráfico (GUI):
- Simplemente haz **doble clic** sobre `MarkdownTransformer.exe`.
- Selecciona tu archivo `.md` (o presiona el botón **"Cargar Ejemplo UPeU"** para ver la plantilla de muestra).
- Elige si deseas generar **PDF**, **HTML** o ambos.
- Presiona **"⚡ Transformar Markdown a PDF y HTML"**.
- Al terminar, se habilitarán botones directos para **Ver PDF**, **Ver HTML** y **Abrir Carpeta**.

### Modo Consola / Terminal (CLI):
También puedes usar el `.exe` desde PowerShell o CMD:
```bash
# Transformar a PDF y HTML
.\dist\MarkdownTransformer.exe documento.md

# Especificar archivo de salida
.\dist\MarkdownTransformer.exe documento.md -o "Entregable_Final.pdf"

# Exportar únicamente HTML o únicamente PDF
.\dist\MarkdownTransformer.exe documento.md -f pdf
.\dist\MarkdownTransformer.exe documento.md -f html

# Conversión por lote de toda una carpeta
.\dist\MarkdownTransformer.exe .\mis_entregables\
```

---

## 📋 Estructura de un Documento Markdown Académico

Para generar el documento con el mismo formato que el ejemplo, tu archivo Markdown puede incluir un bloque de metadatos **YAML frontmatter** al inicio:

```markdown
---
institucion: Universidad Peruana Unión
escuela: Escuela Prof. de Ingeniería de Sistemas
titulo: PRODUCTO ACADÉMICO 1 (PA1) — ESTADO DEL ARTE DE LA INVESTIGACIÓN
subtitulo: Cabecera de Control del Entregable
asignatura: Investigación III (Ciclo 8 – Semestre 2026-2)
evaluacion: Producto Académico 1 (PA1 — 15%) / Cierre de Unidad 1
tema: Sistema Inteligente para la Prevención Temprana de Deuda Técnica en la Fase de Planificación (Shift-Left) en Equipos Ágiles Pequeños
equipo: William David Ortiz Mamani & Uhziel Elí Condori Rojas
docente: Mg. Fredy Abel Huanca Torres
institucion_detalle: Universidad Peruana Unión (UPeU) — Escuela Profesional de Ingeniería de Sistemas
fecha: 2026-09-06
estado: 🟢 Completado / Listo para Revisión y Entrega Final
autor_pie: William David Ortiz Mamani — Ciclo VIII · 2026-2
mostrar_cabecera_control: true
---

\pagebreak

<div class="toc-card">
  <div class="toc-header">
    <div class="toc-title">ÍNDICE DE CONTENIDO</div>
  </div>
  <div class="toc-list">
    <div class="toc-item level-1">
      <span>Actividad 1: Plantilla de Análisis y Catalogación de Papers</span>
      <span class="toc-page">pág. 3</span>
    </div>
  </div>
</div>

\pagebreak

# ACTIVIDAD 1: PLANTILLA DE ANÁLISIS Y CATALOGACIÓN DE PAPERS

## 1. Descripción e Instrucciones
Texto del contenido con enlaces y formato normal...

## 2. Tabla de Catalogación
| N° | Paper | Tipo | Ranking |
| :-: | :--- | :--- | :---: |
| 01 | Paper 1 | Experimental | Scimago Q1 |
```

---

## ✨ Características Principales

1. **Fidelidad Visual Idéntica al Documento Modelo:**
   - **Cabecera corrida (Running Header):** Con el nombre de la institución a la izquierda (`Universidad Peruana Unión`) y escuela/facultad a la derecha (`Escuela Prof. de Ingeniería de Sistemas`).
   - **Pie de página corrido (Running Footer):** Con el autor/ciclo a la izquierda y paginación dinámica (`Página X de Y`) a la derecha.
   - **Cabecera de Control del Entregable:** Tabla con estilo institucional azul (`#164e87`) y filas alternadas con todos los metadatos académicos.
   - **Índice de Contenido:** Con barra vertical de acento azul y alineación de números de página.
   - **Tablas de Alta Densidad:** Cabeceras sólidas en azul marino, filas con alternancia de color suave (`#f8fafc`) y bordes nítidos. Las filas nunca se parten por la mitad entre saltos de página.
   - **Badges para Citas:** Reconocimiento y resaltado de códigos de artículos como `[P01]`, `[P02]` con estilo badge moderno.
   - **Saltos de página:** Soporte para `\pagebreak`, `\newpage` y `---pagebreak---`.
   - **Imágenes incrustadas:** Las imágenes locales relativas se empaquetan en base64 para que el archivo HTML sea 100% independiente y portable.

2. **Motor de Renderizado:**
   - Emplea el motor Chromium de **Microsoft Edge** (preinstalado en Windows 10 y 11) a través de Chrome DevTools Protocol (CDP).
   - No requiere descargar navegadores adicionales de cientos de megabytes ni instalar dependencias pesadas de GTK.
   - Genera tipografía vectorial nítida y respetando exactamente el tamaño de página A4 estándar.

---

## 🛠️ Recompilación del Proyecto (Desarrolladores)

Si deseas modificar el código fuente en Python o añadir nuevos estilos:

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar la aplicación en modo desarrollo
python main.py

# Recompilar el ejecutable .exe
python build_exe.py
```

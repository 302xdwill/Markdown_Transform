# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:/Documentos/Trabajos upeu/Codigos/Transform/main.py'],
    pathex=[],
    binaries=[],
    datas=[('D:/Documentos/Trabajos upeu/Codigos/Transform/templates', 'templates'), ('D:/Documentos/Trabajos upeu/Codigos/Transform/assets', 'assets'), ('D:/Documentos/Trabajos upeu/Codigos/Transform/examples', 'examples')],
    hiddenimports=['aiohttp', 'yaml', 'markdown', 'markdown.extensions', 'markdown.extensions.tables', 'markdown.extensions.fenced_code', 'markdown.extensions.codehilite', 'markdown.extensions.sane_lists', 'markdown.extensions.attr_list', 'markdown.extensions.def_list', 'markdown.extensions.footnotes', 'pygments', 'pygments.lexers', 'pygments.formatters'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pymupdf', 'fitz', 'numpy'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MarkdownTransformer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['D:/Documentos/Trabajos upeu/Codigos/Transform/assets/app_icon.ico'],
)

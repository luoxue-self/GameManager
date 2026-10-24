# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置（onedir：启动快、路径稳定）。"""
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = [
    ("templates", "templates"),
    ("assets", "assets"),
]
datas += collect_data_files("webview")
datas += collect_data_files("pypinyin")

hiddenimports = [
    "webview.platforms.edgechromium",
    "webview.platforms.winforms",
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan.on",
]
hiddenimports += collect_submodules("webview")
hiddenimports += collect_submodules("uvicorn")
hiddenimports += collect_submodules("pypinyin")

a = Analysis(
    ["desktop.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "pandas"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="游戏库管理器",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon="assets/icon.ico",
)
coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False, upx=True, upx_exclude=[],
    name="游戏库管理器",
)

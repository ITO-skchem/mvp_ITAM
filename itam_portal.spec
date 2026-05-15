# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onefile spec: Django portal + REST + optional AI (torch/sentence-transformers)."""
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files

ROOT = Path(SPEC).resolve().parent

block_cipher = None

datas: list = []
binaries: list = []
hiddenimports: list = []


def merge_all(package: str) -> None:
    global datas, binaries, hiddenimports
    try:
        d, b, h = collect_all(package)
    except Exception:
        return
    datas += d
    binaries += b
    hiddenimports += h


for pkg in (
    "django",
    "jazzmin",
    "rest_framework",
    "django_filters",
    "pandas",
    "openpyxl",
    "psycopg2",
):
    merge_all(pkg)

for pkg in ("web", "masters", "assets", "core", "ai_search", "api", "itam_portal"):
    try:
        datas += collect_data_files(pkg, include_py_files=True)
    except Exception:
        pass

for pkg in (
    "sentence_transformers",
    "torch",
    "transformers",
    "tokenizers",
    "sklearn",
    "huggingface_hub",
):
    merge_all(pkg)

hiddenimports += [
    "faiss",
    "faiss._swigfaiss",
    "ai_search.services",
    "ai_search.indexer",
    "itam_portal.settings",
    "itam_portal.urls",
    "itam_portal.wsgi",
    "itam_portal.django_compat",
]

a = Analysis(
    [str(ROOT / "launcher.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib.tests"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="ITAM_Portal",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

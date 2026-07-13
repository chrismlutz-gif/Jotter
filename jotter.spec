# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Jotter

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# tkinterdnd2 ships native DLLs that must be bundled
_dnd_datas = collect_data_files('tkinterdnd2')

a = Analysis(
    ['editor.py'],
    pathex=[],
    binaries=[],
    datas=_dnd_datas,
    hiddenimports=['tkinter', 'tkinter.filedialog', 'tkinter.messagebox',
                   'tkinter.colorchooser', 'tkinter.simpledialog', 'rtf_io',
                   'tkinterdnd2'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='Jotter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,   # was True
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # no console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='jotter.ico',
    version_info=None,
)

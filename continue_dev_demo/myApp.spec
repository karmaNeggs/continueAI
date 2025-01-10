# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        ('prompts', 'prompts'),
        ],
    hiddenimports=['cryptography','pdfminer.six', 'python-pptx', 'python-docx', 'pandas','pywebview'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=None,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main',
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
    icon='static/icon.ico',
)
app = BUNDLE(
    exe,
    name='continue.app',
    icon='static/icon.icns',
    bundle_identifier='com.yourdomain.main',
    datas=[
        ('templates', 'templates'),  # Explicitly include templates
        ('static', 'static'),        # Explicitly include static files
        ('prompts', 'prompts'),
    ],
    plist={
        'CFBundleName': 'MainApp',
        'CFBundleIdentifier': 'com.yourdomain.main',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0',
    },
)





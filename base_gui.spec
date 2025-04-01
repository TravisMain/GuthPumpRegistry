# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

a = Analysis(
    ['gui\\base_gui.py'],
    pathex=['C:\\Users\\travism\\source\\repos\\GuthPumpRegistry'],
    binaries=[('C:\\Program Files\\Python311\\python311.dll', '.')],
    datas=[
        ('assets\\*.ttf', 'assets'),  # Explicitly include font files
        ('assets\\*.json', 'assets'),  # Explicitly include JSON files
        ('assets', 'assets'),  # Include the entire assets directory
        ('gui', 'gui'),
        ('utils', 'utils'),
        ('database.py', '.'),
        ('export_utils.py', '.'),
        ('config.json', '.')
    ],
    hiddenimports=[
        'reportlab',
        'reportlab.lib.pagesizes',
        'reportlab.lib.units',
        'reportlab.lib.styles',
        'reportlab.lib.colors',
        'reportlab.platypus',
        'reportlab.graphics',
        'ttkbootstrap',
        'pyodbc',
        'smtplib',
        'email.mime.multipart',
        'email.mime.text',
        'email.mime.application',
        'PIL',
        'os',
        'json',
        'datetime',
        'sys',
        'traceback',
        'logging',
        'bcrypt',
        'pandas',
        'tkinter.filedialog',
        'matplotlib',  # Added for matplotlib.pyplot in approval_gui.py
        'matplotlib.backends.backend_tkagg'  # Added for FigureCanvasTkAgg
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    optimize=0
)

a.hiddenimports.extend(collect_submodules('reportlab'))

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='base_gui',
    debug=False,  # Disable debug since no console
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Changed to False for no console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.ico'  # Ensure this path is correct
)
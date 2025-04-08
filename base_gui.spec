# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

a = Analysis(
    ['gui\\base_gui.py'],
    pathex=['C:\\Users\\travism\\source\\repos\\GuthPumpRegistry'],
    binaries=[('C:\\Program Files\\Python311\\python311.dll', '.')],
    datas=[
        ('assets\\bom.json', 'assets'),
        ('assets\\pump_options.json', 'assets'),
        ('assets\\assembly_part_numbers.json', 'assets'),
        ('assets\\logo.png', 'assets'),
        ('gui', 'gui'),
        ('utils', 'utils'),
        ('database.py', '.'),
        ('export_utils.py', '.'),  # Main PDF/email utility
        ('doc_utils.py', '.'),     # Added if distinct from export_utils.py
        ('config.json', '.'),
        ('README.md', '.'),
        ('USER_GUIDE.md', '.')
    ],
    hiddenimports=[
        'ttkbootstrap',                  # GUI framework
        'pyodbc',                        # Database connectivity
        'bcrypt',                        # Password hashing
        'reportlab',                     # PDF generation
        'reportlab.lib.pagesizes',
        'reportlab.lib.units',
        'reportlab.lib.styles',
        'reportlab.lib.colors',
        'reportlab.platypus',
        'reportlab.graphics',
        'PIL',                           # Image processing
        'threading',                     # Thread safety
        'matplotlib',                    # Graphing in approval_gui.py
        'matplotlib.backends.backend_tkagg',  # Tkinter canvas for graphs
        'pandas',                        # Added back if used elsewhere
        'tkinter.filedialog'             # Added back if used elsewhere
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
    name='GuthPumpRegistry',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console for GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.ico'  # Verify this exists at project root
)
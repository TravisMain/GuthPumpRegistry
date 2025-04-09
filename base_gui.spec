# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

a = Analysis(
    ['gui\\base_gui.py'],
    pathex=['C:\\Users\\travism\\source\\repos\\GuthPumpRegistry'],
    binaries=[
        ('C:\\Program Files\\Python311\\python311.dll', '.'),
        # Adjust this path based on your system
        ('C:\\Program Files\\Microsoft SQL Server\\Client SDK\\ODBC\\170\\Tools\\Binn\\msodbcsql17.dll', '.')
    ],
    datas=[
        ('assets\\bom.json', 'assets'),
        ('assets\\pump_options.json', 'assets'),
        ('assets\\assembly_part_numbers.json', 'assets'),
        ('assets\\logo.png', 'assets'),
        ('assets\\guth_logo.png', 'assets'),
        ('assets\\Roboto-Regular.ttf', 'assets'),
        ('assets\\Roboto-Black.ttf', 'assets'),
        ('gui', 'gui'),
        ('utils', 'utils'),
        ('database.py', '.'),
        ('export_utils.py', '.'),
        ('config.json', '.'),
        ('README.md', '.'),
        ('USER_GUIDE.md', '.'),
        ('app_icon.ico', '.'),
        *collect_data_files('ttkbootstrap')  # ttkbootstrap themes
    ],
    hiddenimports=[
        'ttkbootstrap',
        'ttkbootstrap.style',
        'ttkbootstrap.themes',
        'ttkbootstrap.window',
        'pyodbc',
        'pyodbc.drivers',
        'bcrypt',
        'reportlab',
        'reportlab.lib.pagesizes',
        'reportlab.lib.units',
        'reportlab.lib.styles',
        'reportlab.lib.colors',
        'reportlab.platypus',
        'reportlab.graphics',
        'PIL',
        'threading',
        'matplotlib',
        'matplotlib.backends.backend_tkagg',
        'pandas',
        'tkinter.filedialog'
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
a.hiddenimports.extend(collect_submodules('ttkbootstrap'))
a.hiddenimports.extend(collect_submodules('pyodbc'))

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='GuthPumpWorks',
    debug=True,
    console=False,  # Keep True for now to debug
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    onefile=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.ico'
)
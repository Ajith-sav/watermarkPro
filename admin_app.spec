# admin_app.spec — PyInstaller spec for WatermarkProAdmin.exe
# Usage:  pyinstaller admin_app.spec

block_cipher = None

# Assets folder is only included if it exists.
extra_datas = []
if os.path.isdir('assets'):
    extra_datas.append(('assets', 'assets'))

a = Analysis(
    ['admin_app/main.py'],
    pathex=['.'],
    binaries=[],
    datas=extra_datas,
    hiddenimports=[
        'shared.database', 'shared.config_file',
        'shared.config_manager', 'shared.models',
        'admin_app.dashboard',
        'user_app.autostart',      # used by settings panel
        'win32gui', 'win32api', 'win32con', 'pywintypes', 'winreg',
        'PIL._tkinter_finder', 'PIL.Image', 'PIL.ImageDraw', 'PIL.ImageFont',
        'tkinter', 'tkinter.messagebox', 'tkinter.filedialog',
        'tkinter.colorchooser',
        'psycopg2', 'psycopg2.extras', 'psycopg2.pool',
        'psutil',
    ],
    hookspath=[],
    excludes=['matplotlib','numpy','pandas','scipy','unittest'],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name='WatermarkProAdmin',
    debug=False,
    strip=False,
    upx=True,
    console=False,          # ← NO terminal window
    icon='assets\\icon.ico',
    version='version_admin.txt',
)

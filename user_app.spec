# user_app.spec — PyInstaller spec for WatermarkPro.exe (user watermark)
# Usage:  pyinstaller user_app.spec

block_cipher = None

# Assets folder is only included if it exists.
extra_datas = []
if os.path.isdir('assets'):
    extra_datas.append(('assets', 'assets'))

a = Analysis(
    ['user_app/main.py'],
    pathex=['.'],
    binaries=[],
    datas=extra_datas,
    hiddenimports=[
        # shared layer
        'shared.database', 'shared.config_file',
        'shared.config_manager', 'shared.models',
        # user app
        'user_app.overlay', 'user_app.monitor', 'user_app.tray',
        'user_app.autostart', 'user_app.credential_guard', 'user_app._icon',
        # Windows API
        'win32gui', 'win32api', 'win32con', 'win32process',
        'win32ts', 'win32security', 'win32event', 'pywintypes',
        # pystray Windows backend
        'pystray._win32',
        # Pillow
        'PIL._tkinter_finder', 'PIL.Image', 'PIL.ImageDraw', 'PIL.ImageFont',
        # stdlib
        'tkinter', 'tkinter.messagebox', 'sqlite3',
        'psycopg2', 'psycopg2.extras', 'psycopg2.pool',
        'psutil', 'winreg', 'ctypes', 'ctypes.wintypes',
    ],
    hookspath=[],
    excludes=['matplotlib','numpy','pandas','scipy','unittest','test'],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name='WatermarkPro',
    debug=False,
    strip=False,
    upx=True,
    console=False,          # ← NO terminal window
    icon='assets\\icon.ico',
    version='version_user.txt',
)

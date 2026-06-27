# service.spec — PyInstaller spec for WatermarkProService.exe (Guardian)
# Usage:  pyinstaller service.spec

block_cipher = None

a = Analysis(
    ['guardian/service.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'win32serviceutil', 'win32service', 'win32event',
        'servicemanager', 'win32ts', 'win32security',
        'win32process', 'win32api', 'pywintypes',
        'psutil','win32timezone',
    ],
    hookspath=[],
    excludes=['tkinter','matplotlib','numpy'],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name='WatermarkProService',
    debug=False,
    strip=False,
    upx=True,
    console=True,           # Service needs console for SCM interaction
    icon='assets\\icon.ico',
)

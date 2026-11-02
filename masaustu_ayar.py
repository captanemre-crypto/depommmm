"""Select an existing OpenJarvis project and create a desktop shortcut."""
import json, os, subprocess, sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageDraw

rootdir = Path(__file__).resolve().parent
root = tk.Tk(); root.withdraw()
config = rootdir / 'openjarvis_yol.json'
messagebox.showinfo('EMRE kurulumu', 'Şimdi daha önce kurduğun OpenJarvis proje klasörünü seç. Bu klasörde pyproject.toml bulunmalı. İptal edersen otomatik başlatma ayarlanmaz.')
folder = filedialog.askdirectory(title='OpenJarvis proje klasörünü seç')
if folder:
    if not (Path(folder) / 'pyproject.toml').is_file():
        messagebox.showwarning('EMRE', 'Bu klasörde pyproject.toml bulunamadı. OpenJarvis otomatik başlatma ayarlanmadı. Kurulumu tekrar çalıştırabilirsin.')
    else:
        config.write_text(json.dumps({'klasor':folder}, ensure_ascii=False, indent=2), encoding='utf-8')
image=Image.new('RGBA',(64,64),(5,14,18,255)); d=ImageDraw.Draw(image)
d.ellipse((5,5,59,59),outline=(81,224,207,255),width=3)
d.ellipse((15,15,49,49),outline=(255,139,79,255),width=2)
d.ellipse((25,25,39,39),fill=(255,174,111,255))
icon=rootdir/'emre.ico'; image.save(icon, format='ICO', sizes=[(16,16),(32,32),(64,64)])
env=os.environ.copy(); env.update(EMRE_PYTHONW=str(Path(sys.executable).with_name('pythonw.exe')), EMRE_START=str(rootdir/'masaustu_ac.pyw'), EMRE_DIR=str(rootdir), EMRE_ICON=str(icon))
script="""$ErrorActionPreference='Stop'; $d=[Environment]::GetFolderPath('Desktop'); if (!$d) { throw 'Masaüstü klasörü bulunamadı' }; $s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $d 'EMRE.lnk')); $s.TargetPath=$env:EMRE_PYTHONW; $s.Arguments='"'+$env:EMRE_START+'"'; $s.WorkingDirectory=$env:EMRE_DIR; $s.IconLocation=$env:EMRE_ICON; $s.Save()"""
try:
    subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script], env=env, check=True, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    messagebox.showinfo('EMRE kurulumu', 'Masaüstüne EMRE kısayolu oluşturuldu. Ayarlar > OpenJarvis bölümünden OpenJarvis seçimini kaydet.')
except Exception as exc:
    messagebox.showerror('EMRE kurulumu', 'Kısayol oluşturulamadı: '+str(exc))
    sys.exit(1)
finally:
    root.destroy()

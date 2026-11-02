"""Show startup errors even when launched without a console."""
import ctypes, runpy, traceback
from pathlib import Path
try:
    runpy.run_path(str(Path(__file__).resolve().with_name('masaustu.py')), run_name='__main__')
except BaseException as exc:
    try:
        Path(__file__).resolve().with_name('masaustu_hata.log').write_text(traceback.format_exc(), encoding='utf-8')
        ctypes.windll.user32.MessageBoxW(None, 'EMRE açılamadı: '+str(exc)+'\nAyrıntı: masaustu_hata.log', 'EMRE', 0x10)
    except Exception:
        pass

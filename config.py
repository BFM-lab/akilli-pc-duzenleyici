import os
import sys
from pathlib import Path

APP_NAME = "Akıllı Bilgisayar Düzenleyici"
APP_VERSION = "1.0.0"
APP_AUTHOR = "BFM CORE"
FILE_CATEGORIES = {
    "Görseller": {
        "extensions": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".heic"},
        "by_date": True,
    },
    "Belgeler": {
        "extensions": {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".txt", ".csv"},
        "by_sub_type": True,
    },
    "Arşivler": {
        "extensions": {".zip", ".rar", ".7z", ".tar", ".gz"},
        "by_date": False,
    },
    "Kurulum Dosyaları": {
        "extensions": {".exe", ".msi"},
        "by_date": False,
    },
    "Videolar": {
        "extensions": {".mp4", ".mkv", ".avi", ".mov", ".wmv"},
        "by_date": True,
    },
}

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
    LOGS_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "AkilliPCDuzenleyici" / "logs"
else:
    BASE_DIR = Path(__file__).resolve().parent
    LOGS_DIR = BASE_DIR / "logs"

HISTORY_FILE = LOGS_DIR / "history.json"


def resource_path(relative_path: str) -> Path:
    """Hem Python'dan hem de .exe içinden gömülü logo/dosya yolunu doğru bulur."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).resolve().parent / relative_path
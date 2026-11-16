import os
import winreg
from pathlib import Path
from typing import Dict


def get_windows_special_folders() -> Dict[str, Path]:
    """
    Windows Registry üzerinden kullanıcının gerçek İndirilenler, Masaüstü
    ve Belgeler klasör yollarını (OneDrive yönlendirmeleri dahil) döndürür.
    """
    home = Path.home()
    defaults = {
        "Masaüstü": home / "Desktop",
        "İndirilenler": home / "Downloads",
        "Belgeler": home / "Documents",
    }

    reg_keys = {
        "Masaüstü": "Desktop",
        "Belgeler": "Personal",
        "İndirilenler": "{374DE290-123F-4565-9164-39C4925E467B}",
    }

    resolved_folders: Dict[str, Path] = {}

    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            for label, reg_name in reg_keys.items():
                try:
                    raw_value, _ = winreg.QueryValueEx(key, reg_name)
                    expanded = Path(os.path.expandvars(raw_value))
                    resolved_folders[label] = expanded if expanded.exists() else defaults[label]
                except OSError:
                    resolved_folders[label] = defaults[label]
    except OSError:
        resolved_folders = defaults

    return resolved_folders


def get_safe_trash_path() -> Path:
    """Masaüstündeki 'Güvenli Çöp Kutusu' klasörünün yolunu döndürür."""
    desktop = get_windows_special_folders()["Masaüstü"]
    return desktop / "Güvenli Çöp Kutusu"
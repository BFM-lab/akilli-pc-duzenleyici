import os
import subprocess
import winreg
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from core.path_helper import get_safe_trash_path
from core.safe_trash import move_to_safe_trash
from core.undo_manager import UndoManager


@dataclass
class InstallerFile:
    path: Path
    name: str
    size_bytes: int
    modified_date: datetime
    age_days: int


@dataclass
class InstalledApp:
    name: str
    publisher: str
    version: str
    size_mb: float
    uninstall_string: str
    last_used_date: Optional[datetime]
    inactive_days: Optional[int]
    source_note: str


class AppCleaner:
    """Kurulum dosyalarını (.exe, .msi) ve uzun süredir kullanılmayan programları tespit eder."""

    INSTALLER_EXTS = {".exe", ".msi"}

    PROTECTED_DIRS = {
        ".git", ".svn", ".hg", "node_modules", "venv", ".venv",
        "env", "__pycache__", ".idea", ".vscode", ".vs", "site-packages"
    }

    # Kaldırılmaması gereken donanım sürücüleri ve sistem kütüphaneleri
    DRIVER_AND_RUNTIME_KEYWORDS = (
        "redistributable", "visual c++", ".net ", "webview2", "directx", "vulkan",
        "realtek", "intel(r)", "intel ", "amd ", "nvidia physx", "nvidia graphics",
        "chipset", "driver", "sürücü", "hotplug", "monitor control",
        "smart display control", "ms control", "system control interface",
        "windows sdk", "app runtime"
    )

    def scan_installers(self, selected_folders: List[Path], min_age_days: int = 0) -> List[InstallerFile]:
        """Yalnızca seçilen klasörlerdeki .exe ve .msi kurulum dosyalarını tarar (proje klasörlerini atlar)."""
        results: List[InstallerFile] = []
        safe_trash = get_safe_trash_path().resolve()
        now = datetime.now()

        for folder in selected_folders:
            if not folder.exists() or not folder.is_dir():
                continue

            for root, dirs, files in os.walk(folder, onerror=lambda _e: None):
                root_path = Path(root)
                dirs[:] = [
                    d for d in dirs
                    if (root_path / d).resolve() != safe_trash
                    and not d.startswith("$")
                    and not d.startswith(".")
                    and d.lower() not in self.PROTECTED_DIRS
                ]

                for fname in files:
                    item = root_path / fname
                    if not item.is_file() or item.is_symlink():
                        continue
                    if item.suffix.lower() in self.INSTALLER_EXTS:
                        try:
                            stat = item.stat()
                            mtime = datetime.fromtimestamp(stat.st_mtime)
                            age_days = max(0, (now - mtime).days)
                            if age_days >= min_age_days:
                                results.append(
                                    InstallerFile(
                                        path=item,
                                        name=item.name,
                                        size_bytes=stat.st_size,
                                        modified_date=mtime,
                                        age_days=age_days,
                                    )
                                )
                        except OSError:
                            continue

        results.sort(key=lambda x: (x.age_days, x.size_bytes), reverse=True)
        return results

    def trash_installers(self, files: List[InstallerFile], undo_manager: UndoManager) -> Tuple[int, List[str]]:
        """Seçilen kurulum dosyalarını Güvenli Çöp Kutusuna taşır ve Undo kaydı oluşturur."""
        moved: List[Tuple[Path, Path]] = []
        errors: List[str] = []

        for item in files:
            try:
                dest = move_to_safe_trash(item.path)
                moved.append((item.path, dest))
            except Exception as e:
                errors.append(f"{item.name}: {e}")

        if moved:
            undo_manager.record_batch(
                action_type="safe_trash",
                description=f"{len(moved)} kurulum dosyası Güvenli Çöp Kutusuna taşındı",
                moves=moved,
            )

        return len(moved), errors

    def scan_installed_apps(self, min_inactive_days: int = 0) -> List[InstalledApp]:
        """Windows Kayıt Defteri üzerinden kurulu programları ve tahmini pasiflik süresini okur."""
        uninstall_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]

        seen_names = set()
        apps: List[InstalledApp] = []
        now = datetime.now()

        for root_key, subkey_path in uninstall_paths:
            try:
                with winreg.OpenKey(root_key, subkey_path) as root:
                    num_subkeys = winreg.QueryInfoKey(root)[0]
                    for i in range(num_subkeys):
                        try:
                            sub_name = winreg.EnumKey(root, i)
                            with winreg.OpenKey(root, sub_name) as app_key:
                                app = self._parse_app_key(app_key, now)
                                if not app:
                                    continue

                                key_id = app.name.lower()
                                if key_id in seen_names:
                                    continue
                                seen_names.add(key_id)

                                if min_inactive_days > 0:
                                    if app.inactive_days is None or app.inactive_days < min_inactive_days:
                                        continue

                                apps.append(app)
                        except OSError:
                            continue
            except OSError:
                continue

        apps.sort(key=lambda a: (a.inactive_days if a.inactive_days is not None else -1), reverse=True)
        return apps

    def _parse_app_key(self, app_key, now: datetime) -> Optional[InstalledApp]:
        def get_val(name: str, default=None):
            try:
                val, _ = winreg.QueryValueEx(app_key, name)
                return val
            except OSError:
                return default

        if get_val("SystemComponent", 0) == 1 or get_val("ParentKeyName"):
            return None

        name = get_val("DisplayName")
        uninstall_str = get_val("UninstallString")
        if not name or not uninstall_str:
            return None

        # Kritik donanım sürücülerini ve sistem bileşenlerini koru
        low_name = str(name).lower()
        if any(kw in low_name for kw in self.DRIVER_AND_RUNTIME_KEYWORDS):
            return None

        publisher = get_val("Publisher", "Bilinmiyor")
        version = get_val("DisplayVersion", "-")
        est_size_kb = get_val("EstimatedSize", 0)
        size_mb = round(est_size_kb / 1024, 1) if isinstance(est_size_kb, int) and est_size_kb > 0 else 0.0

        last_used, source_note = self._estimate_last_activity(
            display_icon=get_val("DisplayIcon", ""),
            install_location=get_val("InstallLocation", ""),
            install_date_str=get_val("InstallDate", ""),
        )

        inactive_days = max(0, (now - last_used).days) if last_used else None

        return InstalledApp(
            name=str(name).strip(),
            publisher=str(publisher).strip(),
            version=str(version).strip(),
            size_mb=size_mb,
            uninstall_string=str(uninstall_str).strip(),
            last_used_date=last_used,
            inactive_days=inactive_days,
            source_note=source_note,
        )

    @staticmethod
    def _estimate_last_activity(
        display_icon: str, install_location: str, install_date_str: str
    ) -> Tuple[Optional[datetime], str]:
        candidates: List[Path] = []

        if display_icon:
            raw_icon = str(display_icon).split(",")[0].strip().strip('"')
            if raw_icon.lower().endswith(".exe"):
                candidates.append(Path(raw_icon))

        if install_location:
            loc = Path(str(install_location).strip().strip('"'))
            if loc.exists() and loc.is_dir():
                try:
                    exes = [p for p in loc.iterdir() if p.is_file() and p.suffix.lower() == ".exe"]
                    candidates.extend(exes[:3])
                except OSError:
                    pass

        latest_ts = None
        for exe_path in candidates:
            try:
                if exe_path.exists():
                    st = exe_path.stat()
                    ts = max(st.st_atime, st.st_mtime)
                    if latest_ts is None or ts > latest_ts:
                        latest_ts = ts
            except OSError:
                continue

        if latest_ts:
            return datetime.fromtimestamp(latest_ts), "Dosya Erişimi"

        if install_date_str and len(str(install_date_str)) == 8 and str(install_date_str).isdigit():
            try:
                dt = datetime.strptime(str(install_date_str), "%Y%m%d")
                return dt, "Kurulum Tarihi"
            except ValueError:
                pass

        return None, "Tarih Bilinmiyor"

    @staticmethod
    def launch_uninstaller(uninstall_string: str):
        cmd = uninstall_string.strip()
        if not cmd.startswith('"') and cmd.lower().endswith(".exe"):
            try:
                if Path(cmd).exists():
                    subprocess.Popen([cmd])
                    return
            except OSError:
                pass
        subprocess.Popen(cmd, shell=True)
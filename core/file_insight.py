import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set, Tuple

from core.app_cleaner import AppCleaner
from core.path_helper import get_windows_special_folders

KNOWN_APP_NAMES = {
    "vscode": "Visual Studio Code",
    "freecad": "FreeCAD",
    "arduino": "Arduino IDE",
    "warp": "Cloudflare WARP",
    "cloudflare": "Cloudflare WARP",
    "medal": "Medal.tv",
    "ftb": "FTB App",
    "anylabeling": "X-AnyLabeling",
    "chrome": "Google Chrome",
    "firefox": "Mozilla Firefox",
    "discord": "Discord",
    "spotify": "Spotify",
    "steam": "Steam",
    "epic": "Epic Games Launcher",
    "python": "Python",
    "git": "Git",
    "nodejs": "Node.js",
    "node": "Node.js",
    "vlc": "VLC Media Player",
    "winrar": "WinRAR",
    "7z": "7-Zip",
    "obs": "OBS Studio",
    "zoom": "Zoom",
    "whatsapp": "WhatsApp",
    "telegram": "Telegram",
    "blender": "Blender",
    "figma": "Figma",
    "notion": "Notion",
}

NOISE_TOKENS = {
    "setup", "installer", "install", "win", "win32", "win64", "windows",
    "x64", "x86", "amd64", "64bit", "32bit", "user", "usersetup", "conda", "cpu", "gpu"
}


@dataclass
class FileInsight:
    friendly_title: str
    category_badge: str
    badge_variant: str  # success, warning, danger, info, neutral
    advice: str
    short_location: str


def load_installed_app_names() -> Set[str]:
    """Kurulu programların isimlerini küçük harfli küme olarak döndürür."""
    try:
        apps = AppCleaner().scan_installed_apps(min_inactive_days=0)
        return {a.name.lower() for a in apps}
    except Exception:
        return set()


def format_short_location(path: Path) -> str:
    """Uzun C:\\Users\\... yolunu okunaklı 'İndirilenler > ...' biçimine çevirir."""
    specials = get_windows_special_folders()
    parent = path.parent.resolve()

    for label, spath in specials.items():
        s_res = spath.resolve()
        if parent == s_res:
            return f"📁 {label}"
        if s_res in parent.parents:
            rel = parent.relative_to(s_res)
            parts = " › ".join(rel.parts)
            return f"📁 {label} › {parts}"

    return f"📁 {parent.parent.name} › {parent.name}" if parent.parent.name else f"📁 {parent}"


def _humanize_filename(stem: str) -> str:
    # Rastgele base64 benzeri uzun tokenları (örn. .NTI1NDc4...) temizle
    cleaned = re.sub(r"\.[A-Za-z0-9+/=]{12,}", "", stem)
    low = cleaned.lower()

    # Bilinen uygulamaları doğrudan yakala
    version_match = re.search(r"(\d+\.\d+(?:\.\d+)?)", cleaned)
    ver_str = f" v{version_match.group(1)}" if version_match else ""

    for key, pretty in KNOWN_APP_NAMES.items():
        if key in low:
            return f"{pretty}{ver_str}"

    # Genel temizlik: alt çizgi / tire ayır ve gürültü kelimeleri at
    tokens = re.split(r"[_\-.]+", cleaned)
    kept: List[str] = []
    for tok in tokens:
        t_low = tok.lower()
        if not tok or t_low in NOISE_TOKENS:
            continue
        if len(tok) > 16 and not tok.isalpha():
            continue
        kept.append(tok)

    result = " ".join(kept).strip()
    return result if result else stem


def analyze_file(path: Path, age_days: int, installed_names: Set[str]) -> FileInsight:
    ext = path.suffix.lower()
    friendly = _humanize_filename(path.stem)
    short_loc = format_short_location(path)

    # Bilgisayarda kurulu eşleşmesi var mı?
    is_installed = False
    first_word = friendly.split()[0].lower().replace("v", "")
    if len(first_word) >= 3:
        is_installed = any(first_word in app_name for app_name in installed_names)

    if ext in {".exe", ".msi"}:
        if is_installed:
            return FileInsight(
                friendly_title=f"{friendly} (Kurulum Dosyası)",
                category_badge="✅ Bilgisayarda Kurulu",
                badge_variant="success",
                advice="Program zaten kurulu. Bu kurulum dosyasını güvenle Güvenli Çöp Kutusu'na atabilirsiniz.",
                short_location=short_loc,
            )
        elif age_days >= 90:
            return FileInsight(
                friendly_title=f"{friendly} (Kurulum Dosyası)",
                category_badge=f"⏳ {age_days} Günlük Eski Kurulum",
                badge_variant="warning",
                advice="Uzun süredir bekleyen kurulum paketi. Artık kurmayacaksanız temizleyebilirsiniz.",
                short_location=short_loc,
            )
        else:
            return FileInsight(
                friendly_title=f"{friendly} (Kurulum Dosyası)",
                category_badge="🔧 Kurulum Paketi",
                badge_variant="info",
                advice="Yakın zamanda indirilmiş kurulum dosyası.",
                short_location=short_loc,
            )

    if ext in {".zip", ".rar", ".7z", ".tar", ".gz"}:
        return FileInsight(
            friendly_title=f"{friendly} (Sıkıştırılmış Arşiv)",
            category_badge="📦 Arşiv Dosyası",
            badge_variant="neutral",
            advice="İçindeki dosyaları çıkardıysanız bu arşivi silmeyi düşünebilirsiniz.",
            short_location=short_loc,
        )

    if ext in {".iso", ".img"}:
        return FileInsight(
            friendly_title=f"{friendly} (Disk Kalıbı)",
            category_badge="💿 Disk İmajı (.iso)",
            badge_variant="warning",
            advice="Genellikle format/kurulum sonrası unutulan büyük disk imajı.",
            short_location=short_loc,
        )

    if ext in {".mp4", ".mkv", ".avi", ".mov", ".wmv"}:
        return FileInsight(
            friendly_title=f"{friendly} (Video)",
            category_badge="🎬 Video Dosyası",
            badge_variant="info",
            advice="Ekran kaydı veya indirilmiş video dosyası.",
            short_location=short_loc,
        )

    return FileInsight(
        friendly_title=friendly,
        category_badge=f"📄 {ext.upper().lstrip('.')} Dosyası",
        badge_variant="neutral",
        advice="Büyük boyutlu dosya. Silmeden önce içeriğini kontrol edin.",
        short_location=short_loc,
    )
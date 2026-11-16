import ctypes
import json
from ctypes import wintypes
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageOps
from config import LOGS_DIR

BACKUP_FILE = LOGS_DIR / "desktop_backup.json"
GENERATED_WALLPAPER = LOGS_DIR / "desktop_fences_wallpaper.png"

# Windows API Sabitleri
LVM_FIRST = 0x1000
LVM_GETITEMCOUNT = LVM_FIRST + 4
LVM_SETITEMPOSITION = LVM_FIRST + 15
LVM_GETITEMPOSITION = LVM_FIRST + 16
LVM_GETITEMSPACING = LVM_FIRST + 51
LVM_GETITEMTEXTW = LVM_FIRST + 115

MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
MEM_RELEASE = 0x8000
PAGE_READWRITE = 0x04
PROCESS_VM_OPERATION = 0x0008
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020

GWL_STYLE = -16
LVS_AUTOARRANGE = 0x0100

SPI_GETDESKWALLPAPER = 0x0073
SPI_SETDESKWALLPAPER = 0x0014
SPI_GETWORKAREA = 0x0030
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDCHANGE = 0x02

CATEGORY_KEYWORDS = {
    "Oyunlar": [
        "steam", "epic", "valorant", "riot", "league", "minecraft", "roblox",
        "cs2", "gta", "ubisoft", "origin", "ea ", "battle.net", "xbox", "oyun", "game"
    ],
    "Tarayıcı & İletişim": [
        "chrome", "edge", "firefox", "opera", "brave", "discord", "whatsapp",
        "telegram", "zoom", "teams", "skype", "slack", "spotify"
    ],
    "İş & Geliştirme": [
        "word", "excel", "powerpoint", "outlook", "code", "visual studio",
        "pycharm", "git", "notion", "obsidian", "photoshop", "figma", "acrobat", "pdf"
    ],
    "Sistem & Araçlar": [
        "bu bilgisayar", "this pc", "geri dönüşüm", "recycle bin", "denetim masası",
        "control panel", "winrar", "7-zip", "vlc", "ayarlar", "ağ"
    ],
}

ZONE_COLORS = {
    "Mavi": (52, 152, 219),
    "Mor": (155, 89, 182),
    "Yeşil": (46, 204, 113),
    "Turuncu": (230, 126, 34),
    "Kırmızı": (231, 76, 60),
    "Gri": (149, 165, 166),
}


class LVITEMW(ctypes.Structure):
    _fields_ = [
        ("mask", wintypes.UINT),
        ("iItem", ctypes.c_int),
        ("iSubItem", ctypes.c_int),
        ("state", wintypes.UINT),
        ("stateMask", wintypes.UINT),
        ("pszText", ctypes.c_void_p),
        ("cchTextMax", ctypes.c_int),
        ("iImage", ctypes.c_int),
        ("lParam", ctypes.c_void_p),
        ("iIndent", ctypes.c_int),
        ("iGroupId", ctypes.c_int),
        ("cColumns", wintypes.UINT),
        ("puColumns", ctypes.c_void_p),
        ("piColFmt", ctypes.c_void_p),
        ("iGroup", ctypes.c_int),
    ]


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


@dataclass
class DesktopIcon:
    index: int
    name: str
    x: int
    y: int


@dataclass
class DesktopZone:
    zone_id: str
    title: str
    color_name: str
    x1: int
    y1: int
    x2: int
    y2: int
    assigned_icons: List[str] = field(default_factory=list)


class DesktopLayoutManager:
    """Windows masaüstü simgelerini okur ve çizilen kutu sınırları dışına taşırmadan hizalar."""

    def __init__(self):
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        self._configure_ctypes()

    def _configure_ctypes(self):
        self.kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.kernel32.OpenProcess.restype = wintypes.HANDLE

        self.kernel32.VirtualAllocEx.argtypes = [
            wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD
        ]
        self.kernel32.VirtualAllocEx.restype = ctypes.c_void_p

        self.kernel32.WriteProcessMemory.argtypes = [
            wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)
        ]
        self.kernel32.WriteProcessMemory.restype = wintypes.BOOL

        self.kernel32.ReadProcessMemory.argtypes = [
            wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)
        ]
        self.kernel32.ReadProcessMemory.restype = wintypes.BOOL

        self.kernel32.VirtualFreeEx.argtypes = [
            wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD
        ]
        self.kernel32.VirtualFreeEx.restype = wintypes.BOOL

        self.user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        self.user32.SendMessageW.restype = ctypes.c_ssize_t

    def get_screen_and_workarea(self) -> Tuple[int, int, Tuple[int, int, int, int]]:
        sw = self.user32.GetSystemMetrics(0)
        sh = self.user32.GetSystemMetrics(1)
        rect = wintypes.RECT()
        self.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0)
        return sw, sh, (rect.left, rect.top, rect.right, rect.bottom)

    def _find_desktop_listview(self) -> Optional[int]:
        progman = self.user32.FindWindowW("Progman", None)
        shell_view = self.user32.FindWindowExW(progman, 0, "SHELLDLL_DefView", None)

        if not shell_view:
            found_views = []

            @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            def enum_cb(hwnd, _lparam):
                sv = self.user32.FindWindowExW(hwnd, 0, "SHELLDLL_DefView", None)
                if sv:
                    found_views.append(sv)
                    return False
                return True

            self.user32.EnumWindows(enum_cb, 0)
            if found_views:
                shell_view = found_views[0]

        if not shell_view:
            return None

        return self.user32.FindWindowExW(shell_view, 0, "SysListView32", "FolderView")

    def get_icon_spacing(self) -> Tuple[int, int]:
        """Windows masaüstündeki gerçek simge hücre genişlik ve yüksekliğini (DPI dahil) döndürür."""
        lv = self._find_desktop_listview()
        if lv:
            spacing = self.user32.SendMessageW(lv, LVM_GETITEMSPACING, 0, 0)
            if spacing > 0:
                cx = spacing & 0xFFFF
                cy = (spacing >> 16) & 0xFFFF
                if cx >= 60 and cy >= 60:
                    return cx, cy
        return 104, 112

    def compute_zone_slots(
        self, zone: DesktopZone, draw_on_wallpaper: bool = False
    ) -> List[Tuple[int, int]]:
        """
        Çizilen kutunun sınırları (x1, y1, x2, y2) içinde kalacak şekilde
        taşma yapmayan kesin (x, y) simge slotlarını hesaplar.
        """
        cell_w, cell_h = self.get_icon_spacing()
        _, _, (work_left, work_top, work_right, work_bottom) = self.get_screen_and_workarea()

        x1 = max(work_left, min(zone.x1, zone.x2))
        x2 = min(work_right, max(zone.x1, zone.x2))
        y1 = max(work_top, min(zone.y1, zone.y2))
        y2 = min(work_bottom, max(zone.y1, zone.y2))

        top_pad = 42 if draw_on_wallpaper else 8
        inner_x1 = x1 + 8
        inner_y1 = y1 + top_pad
        inner_x2 = x2 - 8
        inner_y2 = y2 - 8

        # Windows'un 'Kılavuz çizgisine hizala' ızgarasına tam oturan sütun/satırları bul
        xs = []
        gx = work_left
        while gx + cell_w <= inner_x2:
            if gx >= inner_x1 - 12:
                xs.append(gx)
            gx += cell_w

        ys = []
        gy = work_top
        while gy + cell_h <= inner_y2:
            if gy >= inner_y1 - 12:
                ys.append(gy)
            gy += cell_h

        # Kutu dar olduğu için global ızgara çizgisine denk gelmezse kutu içi koordinat üret
        if not xs and (inner_x2 - inner_x1) >= cell_w:
            cx = inner_x1
            while cx + cell_w <= inner_x2:
                xs.append(cx)
                cx += cell_w
        if not ys and (inner_y2 - inner_y1) >= cell_h:
            cy = inner_y1
            while cy + cell_h <= inner_y2:
                ys.append(cy)
                cy += cell_h

        if not xs:
            xs = [min(inner_x1, max(work_left, x2 - cell_w))]
        if not ys:
            ys = [min(inner_y1, max(work_top, y2 - cell_h))]

        slots: List[Tuple[int, int]] = []
        for py in ys:
            for px in xs:
                slots.append((px, py))
        return slots

    def is_auto_arrange_enabled(self) -> bool:
        lv = self._find_desktop_listview()
        if not lv:
            return False
        style = self.user32.GetWindowLongW(lv, GWL_STYLE)
        return bool(style & LVS_AUTOARRANGE)

    def get_desktop_icons(self) -> List[DesktopIcon]:
        lv = self._find_desktop_listview()
        if not lv:
            return []

        count = self.user32.SendMessageW(lv, LVM_GETITEMCOUNT, 0, 0)
        if count <= 0:
            return []

        pid = wintypes.DWORD()
        self.user32.GetWindowThreadProcessId(lv, ctypes.byref(pid))
        proc = self.kernel32.OpenProcess(PROCESS_VM_OPERATION | PROCESS_VM_READ | PROCESS_VM_WRITE, False, pid.value)
        if not proc:
            return []

        icons: List[DesktopIcon] = []
        text_buf_size = 520
        remote_text = self.kernel32.VirtualAllocEx(proc, None, text_buf_size, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE)
        remote_item = self.kernel32.VirtualAllocEx(proc, None, ctypes.sizeof(LVITEMW), MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE)
        remote_pt = self.kernel32.VirtualAllocEx(proc, None, ctypes.sizeof(POINT), MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE)

        try:
            for i in range(count):
                lvitem = LVITEMW()
                lvitem.mask = 0x0001
                lvitem.iItem = i
                lvitem.iSubItem = 0
                lvitem.pszText = remote_text
                lvitem.cchTextMax = 260

                written = ctypes.c_size_t()
                self.kernel32.WriteProcessMemory(proc, remote_item, ctypes.byref(lvitem), ctypes.sizeof(LVITEMW), ctypes.byref(written))
                self.user32.SendMessageW(lv, LVM_GETITEMTEXTW, i, int(remote_item))

                local_text = ctypes.create_unicode_buffer(260)
                read_bytes = ctypes.c_size_t()
                self.kernel32.ReadProcessMemory(proc, remote_text, local_text, text_buf_size, ctypes.byref(read_bytes))

                self.user32.SendMessageW(lv, LVM_GETITEMPOSITION, i, int(remote_pt))
                pt = POINT()
                self.kernel32.ReadProcessMemory(proc, remote_pt, ctypes.byref(pt), ctypes.sizeof(POINT), ctypes.byref(read_bytes))

                name = local_text.value.strip()
                if name:
                    icons.append(DesktopIcon(index=i, name=name, x=pt.x, y=pt.y))
        finally:
            if remote_text:
                self.kernel32.VirtualFreeEx(proc, remote_text, 0, MEM_RELEASE)
            if remote_item:
                self.kernel32.VirtualFreeEx(proc, remote_item, 0, MEM_RELEASE)
            if remote_pt:
                self.kernel32.VirtualFreeEx(proc, remote_pt, 0, MEM_RELEASE)
            self.kernel32.CloseHandle(proc)

        return icons

    def get_current_wallpaper_path(self) -> Optional[Path]:
        buf = ctypes.create_unicode_buffer(260)
        self.user32.SystemParametersInfoW(SPI_GETDESKWALLPAPER, 260, buf, 0)
        if buf.value and Path(buf.value).exists():
            return Path(buf.value)
        return None

    def get_base_wallpaper_image(self) -> Image.Image:
        sw, sh, _ = self.get_screen_and_workarea()
        wp_path = self.get_current_wallpaper_path()

        if BACKUP_FILE.exists():
            try:
                with open(BACKUP_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                orig = data.get("original_wallpaper")
                if orig and Path(orig).exists():
                    wp_path = Path(orig)
            except (json.JSONDecodeError, OSError):
                pass

        if wp_path and wp_path.resolve() != GENERATED_WALLPAPER.resolve():
            try:
                img = Image.open(wp_path).convert("RGB")
                return ImageOps.fit(img, (sw, sh), method=Image.Resampling.LANCZOS)
            except Exception:
                pass

        return Image.new("RGB", (sw, sh), (24, 32, 48))

    def auto_assign_icons(self, zones: List[DesktopZone], icons: List[DesktopIcon], draw_on_wallpaper: bool = False):
        """Simgeleri kutu isimlerine ve kutuların alabileceği maksimum kapasiteye göre dağıtır."""
        if not zones:
            return

        capacities = {z.zone_id: len(self.compute_zone_slots(z, draw_on_wallpaper)) for z in zones}
        for z in zones:
            z.assigned_icons.clear()

        def match_category(icon_name: str) -> str:
            low = icon_name.lower()
            for cat, kws in CATEGORY_KEYWORDS.items():
                if any(kw in low for kw in kws):
                    return cat
            return "Diğer"

        def has_space(z: DesktopZone) -> bool:
            return len(z.assigned_icons) < capacities[z.zone_id]

        for icon in icons:
            cat = match_category(icon.name)
            placed = False

            for z in zones:
                if not has_space(z):
                    continue
                zt = z.title.lower()
                if cat == "Oyunlar" and any(k in zt for k in ["oyun", "game"]):
                    z.assigned_icons.append(icon.name)
                    placed = True
                    break
                if cat == "Tarayıcı & İletişim" and any(k in zt for k in ["tarayıcı", "internet", "iletişim", "sosyal"]):
                    z.assigned_icons.append(icon.name)
                    placed = True
                    break
                if cat == "İş & Geliştirme" and any(k in zt for k in ["iş", "ofis", "geliştir", "çalışma", "kod", "okul"]):
                    z.assigned_icons.append(icon.name)
                    placed = True
                    break
                if cat == "Sistem & Araçlar" and any(k in zt for k in ["sistem", "araç", "bilgisayar"]):
                    z.assigned_icons.append(icon.name)
                    placed = True
                    break

            if not placed:
                # Boş yeri olan uygun bir kutuya koy (taşma yapma)
                for z in zones:
                    if has_space(z):
                        z.assigned_icons.append(icon.name)
                        break

    def _backup_if_needed(self, icons: List[DesktopIcon]):
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        current_wp = self.get_current_wallpaper_path()

        if BACKUP_FILE.exists() and current_wp and current_wp.resolve() == GENERATED_WALLPAPER.resolve():
            return

        backup = {
            "original_wallpaper": str(current_wp) if current_wp else None,
            "icons": [{"name": ic.name, "x": ic.x, "y": ic.y} for ic in icons],
        }
        with open(BACKUP_FILE, "w", encoding="utf-8") as f:
            json.dump(backup, f, ensure_ascii=False, indent=2)

    def _restore_original_wallpaper_only(self):
        current_wp = self.get_current_wallpaper_path()
        if BACKUP_FILE.exists() and current_wp and current_wp.resolve() == GENERATED_WALLPAPER.resolve():
            try:
                with open(BACKUP_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                orig_wp = data.get("original_wallpaper")
                if orig_wp and Path(orig_wp).exists():
                    self.user32.SystemParametersInfoW(
                        SPI_SETDESKWALLPAPER, 0, str(orig_wp), SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
                    )
            except (json.JSONDecodeError, OSError):
                pass

    def apply_layout(self, zones: List[DesktopZone], draw_on_wallpaper: bool = False) -> Tuple[int, int, Optional[str]]:
        """
        Simgeleri çizilen kutu sınırlarını aşmadan yan yana dizer.
        Dönüş: (yerleştirilen_sayı, kapasite_yüzünden_sığmayan_sayı, uyarı_mesajı)
        """
        icons = self.get_desktop_icons()
        if not icons:
            return 0, 0, "Masaüstü simgeleri okunamadı."

        auto_warn = None
        if self.is_auto_arrange_enabled():
            auto_warn = (
                "Masaüstünüzde 'Simgeleri otomatik düzenle' ayarı açık!\n"
                "Simgelerin kutular içinde kalması için Masaüstüne Sağ Tık > Görünüm > "
                "'Simgeleri otomatik düzenle' işaretini kaldırıp tekrar 'Uygula'ya basın."
            )

        self._backup_if_needed(icons)

        if draw_on_wallpaper:
            self._apply_wallpaper_boxes(zones)
        else:
            # Duvar kağıdında kutu istenmiyorsa varsa eski üretilmiş çerçeveli duvar kağıdını temizle
            self._restore_original_wallpaper_only()

        lv = self._find_desktop_listview()
        if not lv:
            return 0, 0, "Masaüstü penceresi bulunamadı."

        name_to_indices: Dict[str, List[int]] = {}
        for ic in icons:
            name_to_indices.setdefault(ic.name, []).append(ic.index)

        moved_count = 0
        overflow_count = 0

        for z in zones:
            slots = self.compute_zone_slots(z, draw_on_wallpaper=draw_on_wallpaper)
            for slot_idx, icon_name in enumerate(z.assigned_icons):
                if slot_idx >= len(slots):
                    overflow_count += 1
                    continue

                idx_list = name_to_indices.get(icon_name, [])
                if not idx_list:
                    continue
                icon_idx = idx_list.pop(0)
                px, py = slots[slot_idx]

                lparam = ((py & 0xFFFF) << 16) | (px & 0xFFFF)
                self.user32.SendMessageW(lv, LVM_SETITEMPOSITION, icon_idx, lparam)
                moved_count += 1

        return moved_count, overflow_count, auto_warn

    def _apply_wallpaper_boxes(self, zones: List[DesktopZone]):
        base_img = self.get_base_wallpaper_image().convert("RGBA")
        overlay = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        try:
            font = ImageFont.truetype("segoeui.ttf", 19)
        except OSError:
            font = ImageFont.load_default()

        for z in zones:
            r, g, b = ZONE_COLORS.get(z.color_name, (52, 152, 219))
            x1, y1, x2, y2 = min(z.x1, z.x2), min(z.y1, z.y2), max(z.x1, z.x2), max(z.y1, z.y2)
            if (x2 - x1) < 60 or (y2 - y1) < 60:
                continue

            draw.rounded_rectangle(
                [x1, y1, x2, y2], radius=14, fill=(18, 22, 32, 145), outline=(r, g, b, 230), width=3
            )
            header_h = min(36, (y2 - y1) // 2)
            draw.rounded_rectangle([x1, y1, x2, y1 + header_h], radius=14, fill=(r, g, b, 195))
            draw.rectangle([x1, y1 + header_h - 10, x2, y1 + header_h], fill=(r, g, b, 195))
            draw.text((x1 + 14, y1 + 6), z.title, fill=(255, 255, 255, 255), font=font)

        final_img = Image.alpha_composite(base_img, overlay).convert("RGB")
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        final_img.save(GENERATED_WALLPAPER, "PNG")

        self.user32.SystemParametersInfoW(
            SPI_SETDESKWALLPAPER, 0, str(GENERATED_WALLPAPER.resolve()), SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
        )

    def restore_backup(self) -> Tuple[bool, str]:
        if not BACKUP_FILE.exists():
            return False, "Geri yüklenecek masaüstü yedeği bulunamadı."

        try:
            with open(BACKUP_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            return False, f"Yedek okunamadı: {e}"

        orig_wp = data.get("original_wallpaper")
        if orig_wp and Path(orig_wp).exists():
            self.user32.SystemParametersInfoW(
                SPI_SETDESKWALLPAPER, 0, str(orig_wp), SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
            )

        lv = self._find_desktop_listview()
        current_icons = self.get_desktop_icons()
        if lv and current_icons:
            name_to_indices: Dict[str, List[int]] = {}
            for ic in current_icons:
                name_to_indices.setdefault(ic.name, []).append(ic.index)

            for saved in data.get("icons", []):
                idx_list = name_to_indices.get(saved["name"], [])
                if idx_list:
                    icon_idx = idx_list.pop(0)
                    lparam = ((int(saved["y"]) & 0xFFFF) << 16) | (int(saved["x"]) & 0xFFFF)
                    self.user32.SendMessageW(lv, LVM_SETITEMPOSITION, icon_idx, lparam)

        return True, "Orijinal duvar kağıdı ve simge konumları geri yüklendi."
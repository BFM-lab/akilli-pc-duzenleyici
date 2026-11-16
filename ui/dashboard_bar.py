import os
import shutil
from pathlib import Path
from tkinter import messagebox
import customtkinter as ctk

from core.path_helper import get_safe_trash_path
from core.undo_manager import UndoManager
from ui.icon_helper import get_icon
from ui.theme import SHADCN


class DashboardBar(ctk.CTkFrame):
    """shadcn/ui tarzı ince kenarlıklı disk, çöp kutusu ve geçmiş özet kartları."""

    def __init__(self, master, undo_manager: UndoManager, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.undo_manager = undo_manager
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        self.grid_columnconfigure((0, 1, 2), weight=1)

        # Kart 1: Disk Durumu
        c1 = ctk.CTkFrame(
            self, fg_color=SHADCN["card"], border_width=1, border_color=SHADCN["border"], corner_radius=12
        )
        c1.grid(row=0, column=0, padx=(0, 8), sticky="nsew")
        c1.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            c1, text=" Sistem Diski", image=get_icon("disk", 17), compound="left",
            text_color=SHADCN["muted_text"], font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=0, padx=14, pady=(12, 4), sticky="w")

        self.disk_label = ctk.CTkLabel(c1, text="...", font=ctk.CTkFont(size=13, weight="bold"))
        self.disk_label.grid(row=1, column=0, padx=14, pady=(0, 6), sticky="w")

        self.disk_progress = ctk.CTkProgressBar(c1, height=6, progress_color=SHADCN["accent_blue"])
        self.disk_progress.grid(row=2, column=0, padx=14, pady=(0, 12), sticky="ew")

        # Kart 2: Güvenli Çöp Kutusu
        c2 = ctk.CTkFrame(
            self, fg_color=SHADCN["card"], border_width=1, border_color=SHADCN["border"], corner_radius=12
        )
        c2.grid(row=0, column=1, padx=4, sticky="nsew")
        c2.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            c2, text=" Güvenli Çöp Kutusu", image=get_icon("trash", 17), compound="left",
            text_color=SHADCN["muted_text"], font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=0, columnspan=2, padx=14, pady=(12, 4), sticky="w")

        self.trash_label = ctk.CTkLabel(c2, text="0 öğe (0 MB)", font=ctk.CTkFont(size=13, weight="bold"))
        self.trash_label.grid(row=1, column=0, padx=14, pady=(0, 12), sticky="w")

        self.empty_trash_btn = ctk.CTkButton(
            c2, text="Boşalt", width=65, height=26, corner_radius=6,
            fg_color=SHADCN["danger"], hover_color=SHADCN["danger_hover"],
            font=ctk.CTkFont(size=11, weight="bold"), command=self._empty_safe_trash
        )
        self.empty_trash_btn.grid(row=1, column=1, padx=12, pady=(0, 12), sticky="e")

        # Kart 3: Kayıtlı İşlem / Geri Al
        c3 = ctk.CTkFrame(
            self, fg_color=SHADCN["card"], border_width=1, border_color=SHADCN["border"], corner_radius=12
        )
        c3.grid(row=0, column=2, padx=(8, 0), sticky="nsew")
        c3.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            c3, text=" İşlem Geçmişi", image=get_icon("history", 17), compound="left",
            text_color=SHADCN["muted_text"], font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=0, padx=14, pady=(12, 4), sticky="w")

        self.history_label = ctk.CTkLabel(c3, text="0 kayıtlı işlem", font=ctk.CTkFont(size=13, weight="bold"))
        self.history_label.grid(row=1, column=0, padx=14, pady=(0, 12), sticky="w")

    def refresh(self):
        try:
            drive = Path.home().anchor or "C:\\"
            usage = shutil.disk_usage(drive)
            free_gb = usage.free / (1024 ** 3)
            total_gb = usage.total / (1024 ** 3)
            ratio = usage.used / usage.total
            self.disk_label.configure(text=f"{drive}  {free_gb:.1f} GB boş / {total_gb:.0f} GB")
            self.disk_progress.set(ratio)
        except OSError:
            self.disk_label.configure(text="Disk bilgisi alınamadı")

        trash_dir = get_safe_trash_path()
        file_count = 0
        total_bytes = 0
        if trash_dir.exists():
            for root, _dirs, files in os.walk(trash_dir):
                for fname in files:
                    file_count += 1
                    try:
                        total_bytes += (Path(root) / fname).stat().st_size
                    except OSError:
                        pass
        mb = total_bytes / (1024 ** 2)
        self.trash_label.configure(text=f"{file_count} öğe ({mb:.1f} MB)")
        self.empty_trash_btn.configure(state="normal" if file_count > 0 else "disabled")

        history = self.undo_manager.get_history()
        self.history_label.configure(text=f"{len(history)} geri alınabilir işlem")

    def _empty_safe_trash(self):
        trash_dir = get_safe_trash_path()
        if not trash_dir.exists():
            return

        if not messagebox.askyesno(
            "Kalıcı Silme Onayı",
            "Masaüstündeki 'Güvenli Çöp Kutusu' içindeki tüm dosyalar KALICI olarak silinecek.\n"
            "Bu işlem geri alınamaz! Emin misiniz?",
        ):
            return

        for item in trash_dir.iterdir():
            try:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
            except OSError:
                pass
        self.refresh()
        messagebox.showinfo("Tamamlandı", "Güvenli Çöp Kutusu boşaltıldı.")
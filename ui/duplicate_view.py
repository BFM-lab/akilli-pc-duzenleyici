import subprocess
import threading
from pathlib import Path
from tkinter import messagebox
from typing import Callable, Dict, List, Set
import customtkinter as ctk

from core.duplicate_finder import DuplicateAndLargeFinder, DuplicateGroup, LargeFile
from core.file_insight import analyze_file, format_short_location, load_installed_app_names
from core.undo_manager import UndoManager
from ui.theme import SHADCN, ShadcnBadge


def format_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


class DuplicateView(ctk.CTkFrame):
    """shadcn/ui Zinc estetiğinde ve insan diliyle açıklamalı Kopya & Büyük Dosya ekranı."""

    def __init__(
        self,
        master,
        get_selected_folders: Callable[[], List[Path]],
        undo_manager: UndoManager,
        on_data_changed: Callable[[], None],
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.get_selected_folders = get_selected_folders
        self.undo_manager = undo_manager
        self.on_data_changed = on_data_changed
        self.finder = DuplicateAndLargeFinder()

        self.dup_checks: Dict[Path, ctk.BooleanVar] = {}
        self.large_checks: Dict[Path, ctk.BooleanVar] = {}
        self.installed_names: Set[str] = set()

        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(
            self,
            fg_color=SHADCN["card"],
            border_width=1,
            border_color=SHADCN["border"],
            corner_radius=12,
        )
        self.tabview.grid(row=0, column=0, padx=20, pady=(8, 20), sticky="nsew")

        self.tab_dups = self.tabview.add("Çift (Kopya) Dosyalar")
        self.tab_large = self.tabview.add("Büyük Dosyalar")

        self._build_dups_tab()
        self._build_large_tab()

    @staticmethod
    def _reveal_in_explorer(path: Path):
        if path.exists():
            subprocess.Popen(["explorer", "/select,", str(path)])
        else:
            messagebox.showinfo("Bilgi", "Dosya artık bu konumda bulunmuyor.")

    # --- SEKME 1: KOPYA DOSYALAR ---
    def _build_dups_tab(self):
        self.tab_dups.grid_columnconfigure(0, weight=1)
        self.tab_dups.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(self.tab_dups, fg_color=SHADCN["muted"], corner_radius=10)
        top.grid(row=0, column=0, padx=10, pady=(10, 8), sticky="ew")
        top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top,
            text="Aynı içeriğe sahip kopyaları bulur. Orijinal dosya otomatik korunur.",
            font=ctk.CTkFont(size=12),
            text_color=SHADCN["muted_text"],
        ).grid(row=0, column=0, padx=14, pady=12, sticky="w")

        self.scan_dup_btn = ctk.CTkButton(
            top, text="Kopyaları Tara", height=34, corner_radius=8, command=self._start_dup_scan
        )
        self.scan_dup_btn.grid(row=0, column=1, padx=12, pady=10)

        self.dup_list = ctk.CTkScrollableFrame(self.tab_dups, fg_color="transparent")
        self.dup_list.grid(row=1, column=0, padx=6, pady=4, sticky="nsew")
        self.dup_list.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.dup_list,
            text="Seçili klasörlerde kopya aramak için 'Kopyaları Tara' butonuna tıklayın.",
            text_color=SHADCN["muted_text"],
            font=ctk.CTkFont(size=12, slant="italic"),
        ).pack(pady=60)

        bottom = ctk.CTkFrame(self.tab_dups, fg_color=SHADCN["muted"], corner_radius=10)
        bottom.grid(row=2, column=0, padx=10, pady=(8, 10), sticky="ew")
        bottom.grid_columnconfigure(0, weight=1)

        self.dup_status = ctk.CTkLabel(bottom, text="Hazır.", font=ctk.CTkFont(size=12))
        self.dup_status.grid(row=0, column=0, padx=14, pady=12, sticky="w")

        self.trash_dup_btn = ctk.CTkButton(
            bottom,
            text="Seçilen Kopyaları Çöp Kutusu'na Taşı",
            height=34,
            corner_radius=8,
            fg_color=SHADCN["danger"],
            hover_color=SHADCN["danger_hover"],
            state="disabled",
            command=self._trash_duplicates,
        )
        self.trash_dup_btn.grid(row=0, column=1, padx=12, pady=10)

    def _start_dup_scan(self):
        folders = self.get_selected_folders()
        if not folders:
            messagebox.showwarning("Uyarı", "Lütfen 'Dosya Düzenleyici' sekmesinden en az bir klasör seçin!")
            return

        self.scan_dup_btn.configure(state="disabled", text="Taranıyor...")
        self.dup_status.configure(text="Dosya içerikleri (SHA-256) karşılaştırılıyor...")

        def worker():
            groups = self.finder.find_duplicates(folders)
            self.after(0, lambda: self._render_duplicates(groups))

        threading.Thread(target=worker, daemon=True).start()

    def _render_duplicates(self, groups: List[DuplicateGroup]):
        self.scan_dup_btn.configure(state="normal", text="Kopyaları Tara")
        for w in self.dup_list.winfo_children():
            w.destroy()
        self.dup_checks.clear()

        if not groups:
            self.trash_dup_btn.configure(state="disabled")
            self.dup_status.configure(text="Kopya dosya bulunamadı.")
            ctk.CTkLabel(self.dup_list, text="Harika! Seçili klasörlerde kopya dosya yok.").pack(pady=50)
            return

        recoverable = sum(g.size_bytes * (len(g.files) - 1) for g in groups)
        self.dup_status.configure(
            text=f"{len(groups)} kopya grubu bulundu • Kazanılabilir Alan: {format_size(recoverable)}"
        )
        self.trash_dup_btn.configure(state="normal")

        for idx, grp in enumerate(groups):
            card = ctk.CTkFrame(
                self.dup_list,
                fg_color=SHADCN["card"],
                border_width=1,
                border_color=SHADCN["border"],
                corner_radius=10,
            )
            card.grid(row=idx, column=0, padx=4, pady=5, sticky="ew")
            card.grid_columnconfigure(0, weight=1)

            hdr = ctk.CTkFrame(card, fg_color="transparent")
            hdr.grid(row=0, column=0, padx=14, pady=(10, 6), sticky="ew")
            ctk.CTkLabel(
                hdr,
                text=grp.files[0].name,
                font=ctk.CTkFont(size=13, weight="bold"),
            ).pack(side="left")
            ShadcnBadge(hdr, text=f"{format_size(grp.size_bytes)} × {len(grp.files)} adet", variant="warning").pack(
                side="right"
            )

            for f_idx, fpath in enumerate(grp.files):
                is_duplicate = f_idx > 0
                var = ctk.BooleanVar(value=is_duplicate)
                self.dup_checks[fpath] = var

                row = ctk.CTkFrame(card, fg_color="transparent")
                row.grid(row=f_idx + 1, column=0, padx=14, pady=3, sticky="ew")
                row.grid_columnconfigure(1, weight=1)

                ctk.CTkCheckBox(row, text="", variable=var, width=22).grid(row=0, column=0, padx=(0, 6))
                badge_txt = "KOPYA (Silinebilir)" if is_duplicate else "ORİJİNAL (Korunacak)"
                badge_var = "danger" if is_duplicate else "success"
                ShadcnBadge(row, text=badge_txt, variant=badge_var).grid(row=0, column=1, padx=(0, 8), sticky="w")

                ctk.CTkLabel(
                    row,
                    text=f"{format_short_location(fpath)} › {fpath.name}",
                    font=ctk.CTkFont(size=12),
                    text_color=SHADCN["muted_text"],
                    anchor="w",
                ).grid(row=0, column=2, sticky="ew")
                row.grid_columnconfigure(2, weight=1)

                ctk.CTkButton(
                    row,
                    text="Göster",
                    width=60,
                    height=24,
                    fg_color=SHADCN["muted"],
                    text_color=SHADCN["text"],
                    hover_color=SHADCN["border_strong"],
                    font=ctk.CTkFont(size=11),
                    command=lambda p=fpath: self._reveal_in_explorer(p),
                ).grid(row=0, column=3, padx=(8, 0))

            ctk.CTkFrame(card, height=8, fg_color="transparent").grid(row=len(grp.files) + 1, column=0)

    def _trash_duplicates(self):
        selected = [p for p, var in self.dup_checks.items() if var.get()]
        if not selected:
            messagebox.showwarning("Uyarı", "Taşınacak kopya dosya seçilmedi.")
            return

        if not messagebox.askyesno(
            "Onay",
            f"{len(selected)} kopya dosya Masaüstündeki 'Güvenli Çöp Kutusu'na taşınacak.\nDevam edilsin mi?",
        ):
            return

        count, errors = self.finder.move_files_to_trash(selected, "kopya dosya", self.undo_manager)
        self.on_data_changed()
        msg = f"{count} kopya dosya Güvenli Çöp Kutusuna taşındı."
        if errors:
            msg += "\n\nHatalar:\n" + "\n".join(errors[:5])
        messagebox.showinfo("Tamamlandı", msg)
        self._start_dup_scan()

    # --- SEKME 2: BÜYÜK DOSYALAR (ANLAŞILIR KART TASARIMI) ---
    def _build_large_tab(self):
        self.tab_large.grid_columnconfigure(0, weight=1)
        self.tab_large.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(self.tab_large, fg_color=SHADCN["muted"], corner_radius=10)
        top.grid(row=0, column=0, padx=10, pady=(10, 8), sticky="ew")
        top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top,
            text="Büyük dosyaları tarar, ne olduklarını ve bilgisayarda kurulu olup olmadıklarını açıklar.",
            font=ctk.CTkFont(size=12),
            text_color=SHADCN["muted_text"],
        ).grid(row=0, column=0, padx=14, pady=12, sticky="w")

        self.size_filter = ctk.CTkOptionMenu(top, values=["50 MB+", "100 MB+", "500 MB+", "1 GB+"], width=110)
        self.size_filter.set("100 MB+")
        self.size_filter.grid(row=0, column=1, padx=6, pady=10)

        self.scan_large_btn = ctk.CTkButton(
            top, text="Büyük Dosyaları Tara", height=34, corner_radius=8, command=self._start_large_scan
        )
        self.scan_large_btn.grid(row=0, column=2, padx=12, pady=10)

        self.large_list = ctk.CTkScrollableFrame(self.tab_large, fg_color="transparent")
        self.large_list.grid(row=1, column=0, padx=6, pady=4, sticky="nsew")
        self.large_list.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.large_list,
            text="Tarama başlatmak için 'Büyük Dosyaları Tara' butonuna tıklayın.",
            text_color=SHADCN["muted_text"],
            font=ctk.CTkFont(size=12, slant="italic"),
        ).pack(pady=60)

        bottom = ctk.CTkFrame(self.tab_large, fg_color=SHADCN["muted"], corner_radius=10)
        bottom.grid(row=2, column=0, padx=10, pady=(8, 10), sticky="ew")
        bottom.grid_columnconfigure(0, weight=1)

        self.large_status = ctk.CTkLabel(bottom, text="Hazır.", font=ctk.CTkFont(size=12))
        self.large_status.grid(row=0, column=0, padx=14, pady=12, sticky="w")

        self.trash_large_btn = ctk.CTkButton(
            bottom,
            text="Seçilenleri Güvenli Çöp Kutusuna Taşı",
            height=34,
            corner_radius=8,
            fg_color=SHADCN["danger"],
            hover_color=SHADCN["danger_hover"],
            state="disabled",
            command=self._trash_large_files,
        )
        self.trash_large_btn.grid(row=0, column=1, padx=12, pady=10)

    def _start_large_scan(self):
        folders = self.get_selected_folders()
        if not folders:
            messagebox.showwarning("Uyarı", "Lütfen 'Dosya Düzenleyici' sekmesinden en az bir klasör seçin!")
            return

        val = self.size_filter.get()
        min_mb = 1024 if "1 GB" in val else int(val.split()[0])

        self.scan_large_btn.configure(state="disabled", text="Analiz Ediliyor...")
        self.large_status.configure(text="Dosyalar ve kurulu program eşleşmeleri taranıyor...")

        def worker():
            installed = load_installed_app_names()
            items = self.finder.find_large_files(folders, min_size_mb=min_mb)
            self.after(0, lambda: self._render_large_files(items, installed))

        threading.Thread(target=worker, daemon=True).start()

    def _render_large_files(self, items: List[LargeFile], installed: Set[str]):
        self.scan_large_btn.configure(state="normal", text="Büyük Dosyaları Tara")
        self.installed_names = installed

        for w in self.large_list.winfo_children():
            w.destroy()
        self.large_checks.clear()

        if not items:
            self.trash_large_btn.configure(state="disabled")
            self.large_status.configure(text="Belirtilen boyutun üzerinde dosya bulunamadı.")
            ctk.CTkLabel(self.large_list, text="Eşleşen büyük dosya yok.").pack(pady=50)
            return

        total = sum(i.size_bytes for i in items)
        self.large_status.configure(text=f"{len(items)} dosya analiz edildi • Toplam: {format_size(total)}")
        self.trash_large_btn.configure(state="normal")

        for idx, item in enumerate(items):
            insight = analyze_file(item.path, item.age_days, installed)
            var = ctk.BooleanVar(value=False)
            self.large_checks[item.path] = var

            card = ctk.CTkFrame(
                self.large_list,
                fg_color=SHADCN["card"],
                border_width=1,
                border_color=SHADCN["border"],
                corner_radius=10,
            )
            card.grid(row=idx, column=0, padx=4, pady=5, sticky="ew")
            card.grid_columnconfigure(1, weight=1)

            # Sol: Checkbox
            ctk.CTkCheckBox(card, text="", variable=var, width=22).grid(
                row=0, column=0, rowspan=3, padx=(14, 6), pady=12
            )

            # Üst Satır: İnsan dostu başlık + Durum Rozeti
            title_row = ctk.CTkFrame(card, fg_color="transparent")
            title_row.grid(row=0, column=1, padx=(4, 10), pady=(10, 2), sticky="ew")
            ctk.CTkLabel(
                title_row,
                text=insight.friendly_title,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=SHADCN["text"],
            ).pack(side="left")
            ShadcnBadge(title_row, text=insight.category_badge, variant=insight.badge_variant).pack(
                side="left", padx=(10, 0)
            )

            # Orta Satır: Ne işe yaradığı / Tavsiye
            ctk.CTkLabel(
                card,
                text=insight.advice,
                font=ctk.CTkFont(size=12),
                text_color=SHADCN["text"],
                anchor="w",
            ).grid(row=1, column=1, padx=(4, 10), pady=2, sticky="w")

            # Alt Satır: Kısa Konum + Ham dosya adı
            ctk.CTkLabel(
                card,
                text=f"{insight.short_location}   •   Dosya: {item.name}",
                font=ctk.CTkFont(size=11),
                text_color=SHADCN["muted_text"],
                anchor="w",
            ).grid(row=2, column=1, padx=(4, 10), pady=(2, 10), sticky="w")

            # Sağ Sütun: Boyut Rozeti + Klasörde Göster
            right_col = ctk.CTkFrame(card, fg_color="transparent")
            right_col.grid(row=0, column=2, rowspan=3, padx=(6, 14), pady=10, sticky="e")

            ShadcnBadge(right_col, text=format_size(item.size_bytes), variant="neutral").pack(anchor="e", pady=(0, 6))
            ctk.CTkButton(
                right_col,
                text="Klasörde Göster",
                width=110,
                height=26,
                fg_color=SHADCN["muted"],
                text_color=SHADCN["text"],
                hover_color=SHADCN["border_strong"],
                font=ctk.CTkFont(size=11),
                command=lambda p=item.path: self._reveal_in_explorer(p),
            ).pack(anchor="e")

    def _trash_large_files(self):
        selected = [p for p, var in self.large_checks.items() if var.get()]
        if not selected:
            messagebox.showwarning("Uyarı", "Lütfen en az bir dosya işaretleyin.")
            return

        if not messagebox.askyesno(
            "Onay",
            f"{len(selected)} dosya Masaüstündeki 'Güvenli Çöp Kutusu'na taşınacak.\nDevam edilsin mi?",
        ):
            return

        count, errors = self.finder.move_files_to_trash(selected, "büyük dosya", self.undo_manager)
        self.on_data_changed()
        msg = f"{count} dosya Güvenli Çöp Kutusuna taşındı."
        if errors:
            msg += "\n\nHatalar:\n" + "\n".join(errors[:5])
        messagebox.showinfo("Tamamlandı", msg)
        self._start_large_scan()
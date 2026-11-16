import threading
from pathlib import Path
from tkinter import messagebox
from typing import Callable, List
import customtkinter as ctk

from core.app_cleaner import AppCleaner, InstalledApp, InstallerFile
from core.undo_manager import UndoManager


def format_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


class CleanerView(ctk.CTkFrame):
    """Kurulum (.exe/.msi) temizliği ve kullanılmayan program kaldırma ekranı."""

    def __init__(
        self,
        master,
        get_selected_folders: Callable[[], List[Path]],
        undo_manager: UndoManager,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.get_selected_folders = get_selected_folders
        self.undo_manager = undo_manager
        self.cleaner = AppCleaner()

        self.found_installers: List[InstallerFile] = []
        self.installer_vars: List[ctk.BooleanVar] = []
        self.all_apps: List[InstalledApp] = []

        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        self.tab_installers = self.tabview.add("Kurulum Dosyaları (.exe / .msi)")
        self.tab_apps = self.tabview.add("Kurulu Uygulamalar")

        self._build_installers_tab()
        self._build_apps_tab()

    # ---------------------------------------------------------
    # SEKME 1: KURULUM DOSYALARI (.exe / .msi)
    # ---------------------------------------------------------
    def _build_installers_tab(self):
        self.tab_installers.grid_columnconfigure(0, weight=1)
        self.tab_installers.grid_rowconfigure(1, weight=1)

        top_bar = ctk.CTkFrame(self.tab_installers)
        top_bar.grid(row=0, column=0, padx=10, pady=(10, 8), sticky="ew")
        top_bar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top_bar,
            text="Seçili klasörlerdeki gereksiz kurulum dosyalarını tarar.",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray70"),
        ).grid(row=0, column=0, padx=12, pady=10, sticky="w")

        self.installer_age_filter = ctk.CTkOptionMenu(
            top_bar,
            values=["Tümü", "30+ gün", "90+ gün"],
            width=110,
        )
        self.installer_age_filter.grid(row=0, column=1, padx=6, pady=10)

        self.scan_inst_btn = ctk.CTkButton(
            top_bar,
            text="Kurulum Dosyalarını Tara",
            command=self._start_installer_scan,
        )
        self.scan_inst_btn.grid(row=0, column=2, padx=12, pady=10)

        self.installer_list_frame = ctk.CTkScrollableFrame(self.tab_installers)
        self.installer_list_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        self.installer_list_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.installer_list_frame,
            text="Tarama başlatmak için sağ üstteki butona tıklayın.",
            text_color=("gray50", "gray60"),
            font=ctk.CTkFont(size=12, slant="italic"),
        ).pack(pady=50)

        bottom_bar = ctk.CTkFrame(self.tab_installers)
        bottom_bar.grid(row=2, column=0, padx=10, pady=(8, 10), sticky="ew")
        bottom_bar.grid_columnconfigure(0, weight=1)

        self.installer_status = ctk.CTkLabel(bottom_bar, text="Hazır.", font=ctk.CTkFont(size=12))
        self.installer_status.grid(row=0, column=0, padx=12, pady=10, sticky="w")

        self.trash_inst_btn = ctk.CTkButton(
            bottom_bar,
            text="Seçilenleri Güvenli Çöp Kutusuna Taşı",
            fg_color="#C0392B",
            hover_color="#922B21",
            state="disabled",
            command=self._trash_selected_installers,
        )
        self.trash_inst_btn.grid(row=0, column=1, padx=12, pady=10)

    def _start_installer_scan(self):
        folders = self.get_selected_folders()
        if not folders:
            messagebox.showwarning("Uyarı", "Lütfen 'Dosya Düzenleyici' sekmesinden en az bir klasör seçin!")
            return

        filter_val = self.installer_age_filter.get()
        min_days = 30 if "30" in filter_val else (90 if "90" in filter_val else 0)

        self.scan_inst_btn.configure(state="disabled", text="Taranıyor...")
        self.installer_status.configure(text="Seçili klasörler taranıyor...")

        def worker():
            results = self.cleaner.scan_installers(folders, min_age_days=min_days)
            self.after(0, lambda: self._render_installers(results))

        threading.Thread(target=worker, daemon=True).start()

    def _render_installers(self, results: List[InstallerFile]):
        self.scan_inst_btn.configure(state="normal", text="Kurulum Dosyalarını Tara")
        for w in self.installer_list_frame.winfo_children():
            w.destroy()

        self.found_installers = results
        self.installer_vars.clear()

        if not results:
            self.trash_inst_btn.configure(state="disabled")
            self.installer_status.configure(text="Kurulum dosyası bulunamadı.")
            ctk.CTkLabel(
                self.installer_list_frame,
                text="Kriterlere uygun .exe veya .msi dosyası bulunamadı.",
                text_color=("gray50", "gray60"),
            ).pack(pady=50)
            return

        total_size = sum(f.size_bytes for f in results)
        self.installer_status.configure(
            text=f"{len(results)} kurulum dosyası bulundu (Toplam: {format_size(total_size)})"
        )
        self.trash_inst_btn.configure(state="normal")

        for idx, item in enumerate(results):
            var = ctk.BooleanVar(value=True)
            self.installer_vars.append(var)

            row = ctk.CTkFrame(self.installer_list_frame, fg_color=("gray88", "gray20"), corner_radius=6)
            row.grid(row=idx, column=0, padx=4, pady=3, sticky="ew")
            row.grid_columnconfigure(1, weight=1)

            ctk.CTkCheckBox(row, text="", variable=var, width=24).grid(row=0, column=0, padx=(10, 4), pady=8)

            info = f"{item.name}  ({format_size(item.size_bytes)}  |  {item.age_days} gün önce)\n{item.path}"
            ctk.CTkLabel(row, text=info, justify="left", anchor="w", font=ctk.CTkFont(size=12)).grid(
                row=0, column=1, padx=6, pady=6, sticky="ew"
            )

    def _trash_selected_installers(self):
        selected = [item for item, var in zip(self.found_installers, self.installer_vars) if var.get()]
        if not selected:
            messagebox.showwarning("Uyarı", "Lütfen en az bir dosya işaretleyin.")
            return

        if not messagebox.askyesno(
            "Güvenli Silme Onayı",
            f"{len(selected)} kurulum dosyası kalıcı olarak silinmeyecek, "
            f"Masaüstündeki 'Güvenli Çöp Kutusu' klasörüne taşınacak.\n\nDevam edilsin mi?",
        ):
            return

        count, errors = self.cleaner.trash_installers(selected, self.undo_manager)
        msg = f"{count} dosya 'Güvenli Çöp Kutusu'na taşındı."
        if errors:
            msg += "\n\nHatalar:\n" + "\n".join(errors[:5])
        messagebox.showinfo("Tamamlandı", msg)
        self._start_installer_scan()

    # ---------------------------------------------------------
    # SEKME 2: KURULU VE KULLANILMAYAN UYGULAMALAR
    # ---------------------------------------------------------
    def _build_apps_tab(self):
        self.tab_apps.grid_columnconfigure(0, weight=1)
        self.tab_apps.grid_rowconfigure(1, weight=1)

        top_bar = ctk.CTkFrame(self.tab_apps)
        top_bar.grid(row=0, column=0, padx=10, pady=(10, 8), sticky="ew")
        top_bar.grid_columnconfigure(0, weight=1)

        self.app_search_entry = ctk.CTkEntry(top_bar, placeholder_text="Program adı ara...")
        self.app_search_entry.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.app_search_entry.bind("<KeyRelease>", lambda _e: self._filter_displayed_apps())

        self.app_age_filter = ctk.CTkOptionMenu(
            top_bar,
            values=["90+ gün pasif", "30+ gün pasif", "Tümü"],
            width=130,
        )
        self.app_age_filter.grid(row=0, column=1, padx=6, pady=10)

        self.scan_apps_btn = ctk.CTkButton(
            top_bar,
            text="Uygulamaları Tara",
            command=self._start_apps_scan,
        )
        self.scan_apps_btn.grid(row=0, column=2, padx=10, pady=10)

        self.apps_list_frame = ctk.CTkScrollableFrame(self.tab_apps)
        self.apps_list_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        self.apps_list_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.apps_list_frame,
            text="Bilgisayarınızdaki programları analiz etmek için 'Uygulamaları Tara' butonuna basın.",
            text_color=("gray50", "gray60"),
            font=ctk.CTkFont(size=12, slant="italic"),
        ).pack(pady=50)

        self.apps_status = ctk.CTkLabel(self.tab_apps, text="Hazır.", font=ctk.CTkFont(size=12))
        self.apps_status.grid(row=2, column=0, padx=15, pady=(4, 10), sticky="w")

    def _start_apps_scan(self):
        filter_val = self.app_age_filter.get()
        min_days = 90 if "90" in filter_val else (30 if "30" in filter_val else 0)

        self.scan_apps_btn.configure(state="disabled", text="Taranıyor...")
        self.apps_status.configure(text="Kayıt defteri ve program erişim tarihleri analiz ediliyor...")

        def worker():
            apps = self.cleaner.scan_installed_apps(min_inactive_days=min_days)
            self.after(0, lambda: self._on_apps_scanned(apps))

        threading.Thread(target=worker, daemon=True).start()

    def _on_apps_scanned(self, apps: List[InstalledApp]):
        self.scan_apps_btn.configure(state="normal", text="Uygulamaları Tara")
        self.all_apps = apps
        self._filter_displayed_apps()

    def _filter_displayed_apps(self):
        query = self.app_search_entry.get().strip().lower()
        filtered = [a for a in self.all_apps if query in a.name.lower() or query in a.publisher.lower()]

        for w in self.apps_list_frame.winfo_children():
            w.destroy()

        if not filtered:
            self.apps_status.configure(text="Eşleşen uygulama bulunamadı.")
            ctk.CTkLabel(
                self.apps_list_frame,
                text="Seçilen kriterlere uygun uygulama bulunamadı.",
                text_color=("gray50", "gray60"),
            ).pack(pady=50)
            return

        self.apps_status.configure(text=f"{len(filtered)} uygulama listeleniyor.")

        # Arayüz akıcılığı için ilk 100 sonucu göster
        for idx, app in enumerate(filtered[:100]):
            card = ctk.CTkFrame(self.apps_list_frame, fg_color=("gray88", "gray20"), corner_radius=6)
            card.grid(row=idx, column=0, padx=4, pady=4, sticky="ew")
            card.grid_columnconfigure(0, weight=1)

            size_txt = f"{app.size_mb} MB" if app.size_mb > 0 else "Boyut bilinmiyor"
            if app.inactive_days is not None and app.last_used_date:
                age_txt = f"{app.inactive_days} gün önce ({app.last_used_date.strftime('%d.%m.%Y')} - {app.source_note})"
            else:
                age_txt = "Aktivite tarihi bilinmiyor"

            ctk.CTkLabel(
                card,
                text=f"{app.name}  (v{app.version})",
                font=ctk.CTkFont(size=13, weight="bold"),
                anchor="w",
            ).grid(row=0, column=0, padx=12, pady=(8, 2), sticky="w")

            ctk.CTkLabel(
                card,
                text=f"Yayıncı: {app.publisher}  |  {size_txt}  |  Son Aktivite: {age_txt}",
                font=ctk.CTkFont(size=11),
                text_color=("gray40", "gray70"),
                anchor="w",
            ).grid(row=1, column=0, padx=12, pady=(0, 8), sticky="w")

            ctk.CTkButton(
                card,
                text="Kaldır",
                width=90,
                height=30,
                fg_color="#D35400",
                hover_color="#A04000",
                command=lambda a=app: self._uninstall_app(a),
            ).grid(row=0, column=1, rowspan=2, padx=12, pady=8)

    def _uninstall_app(self, app: InstalledApp):
        if not messagebox.askyesno(
            "Uygulama Kaldırma",
            f"'{app.name}' uygulamasının resmi kaldırma sihirbazı başlatılacak.\nDevam etmek istiyor musunuz?",
        ):
            return
        try:
            self.cleaner.launch_uninstaller(app.uninstall_string)
        except Exception as e:
            messagebox.showerror("Hata", f"Kaldırma sihirbazı başlatılamadı:\n{e}")
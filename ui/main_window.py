from tkinter import messagebox
from typing import List
from PIL import Image
import customtkinter as ctk

from config import APP_AUTHOR, APP_NAME, APP_VERSION, resource_path
from core.file_organizer import FileOrganizer, PlannedMove
from core.undo_manager import UndoManager
from ui.cleaner_view import CleanerView
from ui.dashboard_bar import DashboardBar
from ui.desktop_layout_view import DesktopLayoutView
from ui.duplicate_view import DuplicateView
from ui.folder_selector import FolderSelectorFrame
from ui.history_view import HistoryView
from ui.icon_helper import get_icon
from ui.preview_modal import PreviewModal
from ui.theme import SHADCN


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"{APP_NAME} v{APP_VERSION} - {APP_AUTHOR}")
        self.geometry("1040x720")
        self.minsize(880, 620)
        self.configure(fg_color=SHADCN["bg"])

        # CustomTkinter'ın varsayılan ikonunu ezmemek için 250ms sonra kendi logomuzu uygula
        self.after(250, self._apply_window_icon)

        self.undo_manager = UndoManager()
        self.organizer = FileOrganizer()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._create_sidebar()
        self._create_dashboard()
        self._create_pages()
        self.show_page("organizer")

    def _apply_window_icon(self):
        icon_file = resource_path("app_icon.ico")
        if icon_file.exists():
            try:
                self.iconbitmap(str(icon_file))
            except Exception:
                pass

    def _create_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=230, corner_radius=0, fg_color=SHADCN["sidebar"])
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar.grid_rowconfigure(7, weight=1)

        # Üst Logo + Başlık
        brand_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_frame.grid(row=0, column=0, padx=18, pady=(22, 20), sticky="ew")

        icon_file = resource_path("app_icon.ico")
        if icon_file.exists():
            try:
                logo_img = Image.open(icon_file)
                self._sidebar_logo = ctk.CTkImage(light_image=logo_img, dark_image=logo_img, size=(42, 42))
                ctk.CTkLabel(brand_frame, text="", image=self._sidebar_logo).pack(pady=(0, 8))
            except Exception:
                pass

        ctk.CTkLabel(
            brand_frame,
            text="Akıllı PC\nDüzenleyici",
            font=ctk.CTkFont(size=19, weight="bold"),
        ).pack()

        self.nav_buttons = {}
        menu_items = [
            ("organizer", " Dosya Düzenleyici", "folder"),
            ("duplicates", " Kopya & Büyük Dosya", "duplicate"),
            ("desktop", " Masaüstü Tasarımcısı", "desktop"),
            ("cleaner", " Uygulama Temizleyici", "broom"),
            ("history", " Geri Al / Geçmiş", "history"),
        ]

        for idx, (key, title, icon_name) in enumerate(menu_items, start=1):
            btn = ctk.CTkButton(
                self.sidebar,
                text=title,
                image=get_icon(icon_name, 19),
                compound="left",
                height=42,
                anchor="w",
                corner_radius=8,
                fg_color="transparent",
                text_color=SHADCN["text"],
                hover_color=SHADCN["muted"],
                command=lambda k=key: self.show_page(k),
            )
            btn.grid(row=idx, column=0, padx=14, pady=4, sticky="ew")
            self.nav_buttons[key] = btn

        theme_label = ctk.CTkLabel(
            self.sidebar, text="Görünüm Teması:", font=ctk.CTkFont(size=12), text_color=SHADCN["muted_text"]
        )
        theme_label.grid(row=8, column=0, padx=20, pady=(10, 0), sticky="w")

        self.theme_menu = ctk.CTkOptionMenu(
            self.sidebar, values=["System", "Dark", "Light"], command=self._change_theme
        )
        self.theme_menu.grid(row=9, column=0, padx=20, pady=(5, 10), sticky="ew")

        # Geliştirici İmzası (En alt kısım)
        ctk.CTkLabel(
            self.sidebar,
            text=f"Geliştirici: {APP_AUTHOR}\nv{APP_VERSION}",
            font=ctk.CTkFont(size=11),
            text_color=SHADCN["muted_text"],
            justify="center",
        ).grid(row=10, column=0, padx=16, pady=(4, 16))

    def _create_dashboard(self):
        self.dashboard = DashboardBar(self, undo_manager=self.undo_manager)
        self.dashboard.grid(row=0, column=1, padx=20, pady=(15, 5), sticky="ew")

    def _create_pages(self):
        self.pages = {}

        # 1. Dosya Düzenleyici
        organizer_page = ctk.CTkFrame(self, fg_color="transparent")
        organizer_page.grid_columnconfigure(0, weight=1)
        organizer_page.grid_rowconfigure(0, weight=1)

        self.folder_selector = FolderSelectorFrame(organizer_page)
        self.folder_selector.grid(row=0, column=0, padx=20, pady=(10, 10), sticky="nsew")

        action_bar = ctk.CTkFrame(organizer_page)
        action_bar.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")
        action_bar.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            action_bar, text="Hazır. Taranacak klasörleri seçip analiz başlatabilirsiniz.", font=ctk.CTkFont(size=12)
        )
        self.status_label.grid(row=0, column=0, padx=15, pady=15, sticky="w")

        ctk.CTkButton(
            action_bar,
            text="Taramayı Başlat (Önizleme)",
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_start_scan,
        ).grid(row=0, column=1, padx=15, pady=15, sticky="e")

        self.pages["organizer"] = organizer_page

        # 2. Kopya & Büyük Dosya
        self.duplicate_view = DuplicateView(
            self,
            get_selected_folders=self.folder_selector.get_selected_folders,
            undo_manager=self.undo_manager,
            on_data_changed=self.dashboard.refresh,
        )
        self.pages["duplicates"] = self.duplicate_view

        # 3. Görsel Masaüstü Tasarımcısı
        self.desktop_layout_view = DesktopLayoutView(self, on_data_changed=self.dashboard.refresh)
        self.pages["desktop"] = self.desktop_layout_view

        # 4. Uygulama Temizleyici
        self.cleaner_view = CleanerView(
            self,
            get_selected_folders=self.folder_selector.get_selected_folders,
            undo_manager=self.undo_manager,
        )
        self.pages["cleaner"] = self.cleaner_view

        # 5. Geçmiş / Geri Al
        self.history_view = HistoryView(self, undo_manager=self.undo_manager)
        self.pages["history"] = self.history_view

    def show_page(self, page_key: str):
        for key, page in self.pages.items():
            page.grid_forget()
            self.nav_buttons[key].configure(fg_color="transparent")

        self.pages[page_key].grid(row=1, column=1, sticky="nsew")
        self.nav_buttons[page_key].configure(fg_color=SHADCN["muted"])
        self.dashboard.refresh()

        if page_key == "history":
            self.history_view.refresh()
        elif page_key == "desktop":
            self.desktop_layout_view.reload_desktop_state()

    def _change_theme(self, new_theme: str):
        ctk.set_appearance_mode(new_theme)

    def _on_start_scan(self):
        selected_folders = self.folder_selector.get_selected_folders()
        if not selected_folders:
            messagebox.showwarning("Uyarı", "Lütfen taramak için en az bir klasör seçin!")
            return

        self.status_label.configure(text="Klasörler analiz ediliyor...")
        self.update_idletasks()

        planned_moves = self.organizer.analyze(selected_folders)
        if not planned_moves:
            self.status_label.configure(text="Düzenlenecek dağınık dosya bulunamadı.")
            messagebox.showinfo("Bilgi", "Seçili klasörlerde düzenlenecek yeni dosya bulunamadı.")
            return

        self.status_label.configure(text=f"{len(planned_moves)} dosya bulundu. Önizleme açılıyor...")
        PreviewModal(self, planned_moves=planned_moves, on_confirm=self._execute_organization)

    def _execute_organization(self, approved_moves: List[PlannedMove]):
        count, errors = self.organizer.execute_plan(approved_moves, self.undo_manager)
        self.status_label.configure(text=f"Tamamlandı: {count} dosya düzenlendi.")
        self.dashboard.refresh()

        msg = f"{count} dosya başarıyla hiyerarşik klasörlere taşındı."
        if errors:
            msg += "\n\nHatalar:\n" + "\n".join(errors[:5])
        messagebox.showinfo("İşlem Tamamlandı", msg)
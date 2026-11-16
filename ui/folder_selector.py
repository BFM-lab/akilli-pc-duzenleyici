import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import Dict, List
import customtkinter as ctk

from core.path_helper import get_windows_special_folders


class FolderSelectorFrame(ctk.CTkFrame):
    """Kullanıcının taranacak klasörleri seçmesini ve yönetmesini sağlayan arayüz bileşeni."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.special_folders = get_windows_special_folders()
        # Seçim durumlarını tutan sözlükler: {Path: ctk.BooleanVar}
        self.default_vars: Dict[Path, ctk.BooleanVar] = {}
        self.custom_folders: Dict[Path, dict] = {}  # {Path: {"var": BooleanVar, "row": CTkFrame}}

        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)

        # Başlık
        header = ctk.CTkLabel(
            self,
            text="1. Taranacak Klasörleri Seçin",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        header.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")

        desc = ctk.CTkLabel(
            self,
            text="Tarama yalnızca aşağıda işaretlediğiniz klasörler içerisinde gerçekleştirilir.",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray70")
        )
        desc.grid(row=1, column=0, padx=15, pady=(0, 10), sticky="w")

        # --- Varsayılan Sistem Klasörleri Bölümü ---
        default_frame = ctk.CTkFrame(self, fg_color=("gray90", "gray17"))
        default_frame.grid(row=2, column=0, padx=15, pady=5, sticky="ew")
        default_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            default_frame,
            text="Sistem Klasörleri",
            font=ctk.CTkFont(size=13, weight="bold")
        ).grid(row=0, column=0, padx=12, pady=(10, 5), sticky="w")

        for idx, (label, path) in enumerate(self.special_folders.items(), start=1):
            resolved_path = path.resolve()
            # Güvenlik için varsayılan olarak sadece İndirilenler seçili gelsin
            is_checked = (label == "İndirilenler")
            var = ctk.BooleanVar(value=is_checked)
            self.default_vars[resolved_path] = var

            row_frame = ctk.CTkFrame(default_frame, fg_color="transparent")
            row_frame.grid(row=idx, column=0, padx=12, pady=4, sticky="ew")

            cb = ctk.CTkCheckBox(
                row_frame,
                text=f"{label}  ({resolved_path})",
                variable=var,
                font=ctk.CTkFont(size=13)
            )
            cb.pack(side="left", fill="x")

            if not resolved_path.exists():
                cb.configure(state="disabled")
                var.set(False)

        # Alt boşluk
        ctk.CTkFrame(default_frame, height=6, fg_color="transparent").grid(row=len(self.special_folders) + 1, column=0)

        # --- Özel Klasörler Bölümü ---
        custom_header_frame = ctk.CTkFrame(self, fg_color="transparent")
        custom_header_frame.grid(row=3, column=0, padx=15, pady=(15, 5), sticky="ew")
        custom_header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            custom_header_frame,
            text="Özel Klasörler",
            font=ctk.CTkFont(size=13, weight="bold")
        ).grid(row=0, column=0, sticky="w")

        add_btn = ctk.CTkButton(
            custom_header_frame,
            text="+ Özel Klasör Ekle",
            width=150,
            height=30,
            command=self._add_custom_folder
        )
        add_btn.grid(row=0, column=1, sticky="e")

        # Eklenen özel klasörlerin listeleneceği kaydırılabilir alan
        self.custom_list_frame = ctk.CTkScrollableFrame(
            self,
            height=130,
            fg_color=("gray90", "gray17")
        )
        self.custom_list_frame.grid(row=4, column=0, padx=15, pady=(0, 15), sticky="nsew")
        self.custom_list_frame.grid_columnconfigure(0, weight=1)

        self.empty_label = ctk.CTkLabel(
            self.custom_list_frame,
            text="Henüz özel klasör eklenmedi.",
            text_color=("gray50", "gray60"),
            font=ctk.CTkFont(size=12, slant="italic")
        )
        self.empty_label.grid(row=0, column=0, pady=40)

    def _add_custom_folder(self):
        selected_dir = filedialog.askdirectory(title="Taranacak Klasörü Seçin")
        if not selected_dir:
            return

        folder_path = Path(selected_dir).resolve()

        # Zaten varsayılanlarda veya özel listede var mı kontrolü
        if folder_path in self.default_vars:
            self.default_vars[folder_path].set(True)
            messagebox.showinfo("Bilgi", "Bu klasör zaten Sistem Klasörleri listesinde mevcut ve işaretlendi.")
            return

        if folder_path in self.custom_folders:
            self.custom_folders[folder_path]["var"].set(True)
            messagebox.showinfo("Bilgi", "Bu klasör zaten eklenmiş.")
            return

        # Boş durum uyarısını gizle
        if self.empty_label.winfo_ismapped():
            self.empty_label.grid_forget()

        var = ctk.BooleanVar(value=True)
        row_frame = ctk.CTkFrame(self.custom_list_frame, fg_color=("gray85", "gray22"), corner_radius=6)
        row_frame.pack(fill="x", padx=5, pady=4)

        cb = ctk.CTkCheckBox(
            row_frame,
            text=str(folder_path),
            variable=var,
            font=ctk.CTkFont(size=12)
        )
        cb.pack(side="left", padx=10, pady=6, fill="x", expand=True)

        remove_btn = ctk.CTkButton(
            row_frame,
            text="Kaldır",
            width=60,
            height=24,
            fg_color="#C0392B",
            hover_color="#922B21",
            command=lambda p=folder_path: self._remove_custom_folder(p)
        )
        remove_btn.pack(side="right", padx=8, pady=6)

        self.custom_folders[folder_path] = {"var": var, "row": row_frame}

    def _remove_custom_folder(self, folder_path: Path):
        if folder_path in self.custom_folders:
            self.custom_folders[folder_path]["row"].destroy()
            del self.custom_folders[folder_path]

        if not self.custom_folders:
            self.empty_label.grid(row=0, column=0, pady=40)

    def get_selected_folders(self) -> List[Path]:
        """Kullanıcının işaretlediği tüm geçerli klasör yollarını liste olarak döndürür."""
        selected: List[Path] = []

        for path, var in self.default_vars.items():
            if var.get() and path.exists():
                selected.append(path)

        for path, data in self.custom_folders.items():
            if data["var"].get() and path.exists():
                selected.append(path)

        return selected
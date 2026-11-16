import os
from tkinter import messagebox
import customtkinter as ctk

from core.safe_trash import ensure_safe_trash_exists
from core.undo_manager import UndoManager


class HistoryView(ctk.CTkFrame):
    """İşlem geçmişini listeleyen, Geri Al ve Güvenli Çöp Kutusu erişimi sunan sayfa."""

    def __init__(self, master, undo_manager: UndoManager, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.undo_manager = undo_manager
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Üst Başlık ve Güvenli Çöp Kutusu Butonu
        header = ctk.CTkFrame(self)
        header.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="İşlem Geçmişi ve Geri Alma (Undo)",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, padx=15, pady=12, sticky="w")

        ctk.CTkButton(
            header,
            text="Güvenli Çöp Kutusunu Aç",
            width=180,
            command=self._open_safe_trash
        ).grid(row=0, column=1, padx=10, pady=12)

        ctk.CTkButton(
            header,
            text="Yenile",
            width=80,
            command=self.refresh
        ).grid(row=0, column=2, padx=(0, 15), pady=12)

        # Kayıt Listesi
        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.list_frame.grid_columnconfigure(0, weight=1)

        self.refresh()

    def refresh(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        history = self.undo_manager.get_history()
        if not history:
            ctk.CTkLabel(
                self.list_frame,
                text="Henüz geri alınabilecek bir işlem kaydı yok.",
                text_color=("gray50", "gray60"),
                font=ctk.CTkFont(size=13, slant="italic")
            ).pack(pady=60)
            return

        for idx, batch in enumerate(history):
            card = ctk.CTkFrame(self.list_frame, fg_color=("gray88", "gray20"), corner_radius=8)
            card.grid(row=idx, column=0, padx=6, pady=6, sticky="ew")
            card.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                card,
                text=batch["description"],
                font=ctk.CTkFont(size=14, weight="bold")
            ).grid(row=0, column=0, padx=15, pady=(10, 2), sticky="w")

            ctk.CTkLabel(
                card,
                text=f"Tarih: {batch['timestamp']}  |  Taşınan Öğe: {len(batch['moves'])}",
                font=ctk.CTkFont(size=12),
                text_color=("gray40", "gray70")
            ).grid(row=1, column=0, padx=15, pady=(0, 10), sticky="w")

            ctk.CTkButton(
                card,
                text="Geri Al",
                width=100,
                fg_color="#D35400",
                hover_color="#A04000",
                command=lambda b_id=batch["id"]: self._undo_action(b_id)
            ).grid(row=0, column=1, rowspan=2, padx=15, pady=10)

    def _undo_action(self, batch_id: str):
        if not messagebox.askyesno("Onay", "Bu işlemdeki dosyalar eski konumlarına geri taşınacak. Devam edilsin mi?"):
            return

        count, errors = self.undo_manager.undo_batch(batch_id)
        self.refresh()

        msg = f"{count} dosya orijinal konumuna geri taşındı."
        if errors:
            msg += "\n\nUyarılar:\n" + "\n".join(errors[:5])
        messagebox.showinfo("Geri Alma Tamamlandı", msg)

    @staticmethod
    def _open_safe_trash():
        trash_path = ensure_safe_trash_exists()
        os.startfile(str(trash_path))
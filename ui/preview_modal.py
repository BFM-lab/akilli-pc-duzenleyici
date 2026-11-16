from collections import defaultdict
from typing import Callable, Dict, List
import customtkinter as ctk
from core.file_organizer import PlannedMove


def format_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


class PreviewModal(ctk.CTkToplevel):
    """Kategori başlıklarıyla gruplanmış Dry-Run önizleme ve onay penceresi."""

    def __init__(self, master, planned_moves: List[PlannedMove], on_confirm: Callable[[List[PlannedMove]], None]):
        super().__init__(master)
        self.planned_moves = planned_moves
        self.on_confirm = on_confirm
        self.move_vars: List[ctk.BooleanVar] = []
        self.category_groups: Dict[str, List[ctk.BooleanVar]] = defaultdict(list)

        self.title("Önizleme (Dry-Run) - Kategori Bazlı Taşıma Planı")
        self.geometry("880x580")
        self.minsize(740, 460)
        self.transient(master)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        total_size = sum(m.size_bytes for m in self.planned_moves)
        top_frame = ctk.CTkFrame(self)
        top_frame.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="ew")
        top_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top_frame,
            text=f"Toplam {len(self.planned_moves)} dosya düzenlenmeye hazır ({format_size(total_size)})",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=0, column=0, padx=15, pady=(10, 2), sticky="w")

        ctk.CTkLabel(
            top_frame,
            text="Kategori başlığından tüm grubu veya tek tek dosyaları seçip çıkarabilirsiniz.",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray70"),
        ).grid(row=1, column=0, padx=15, pady=(0, 10), sticky="w")

        self.select_all_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(top_frame, text="Tümünü Seç", variable=self.select_all_var, command=self._toggle_all).grid(
            row=0, column=1, rowspan=2, padx=15
        )

        # Kategorilere göre grupla
        grouped: Dict[str, List[PlannedMove]] = defaultdict(list)
        for m in self.planned_moves:
            grouped[m.category].append(m)

        list_frame = ctk.CTkScrollableFrame(self)
        list_frame.grid(row=1, column=0, padx=15, pady=5, sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)

        row_cursor = 0
        for cat, moves in grouped.items():
            cat_size = sum(m.size_bytes for m in moves)
            cat_var = ctk.BooleanVar(value=True)

            cat_header = ctk.CTkFrame(list_frame, fg_color=("#DCE6F2", "#2B3A4A"), corner_radius=6)
            cat_header.grid(row=row_cursor, column=0, padx=4, pady=(10, 4), sticky="ew")
            row_cursor += 1

            ctk.CTkCheckBox(
                cat_header,
                text=f"{cat}  ({len(moves)} dosya  •  {format_size(cat_size)})",
                variable=cat_var,
                font=ctk.CTkFont(size=13, weight="bold"),
                command=lambda c=cat, v=cat_var: self._toggle_category(c, v.get()),
            ).pack(side="left", padx=12, pady=7)

            for move in moves:
                var = ctk.BooleanVar(value=True)
                self.move_vars.append(var)
                self.category_groups[cat].append(var)

                row = ctk.CTkFrame(list_frame, fg_color=("gray90", "gray20"), corner_radius=6)
                row.grid(row=row_cursor, column=0, padx=(18, 4), pady=2, sticky="ew")
                row.grid_columnconfigure(1, weight=1)
                row_cursor += 1

                ctk.CTkCheckBox(row, text="", variable=var, width=24).grid(row=0, column=0, padx=(10, 4), pady=6)

                try:
                    rel_dest = move.destination.relative_to(move.source.parent)
                except ValueError:
                    rel_dest = move.destination

                info_text = f"{move.source.name}  →  {move.source.parent.name}\\{rel_dest}"
                ctk.CTkLabel(row, text=info_text, justify="left", anchor="w", font=ctk.CTkFont(size=12)).grid(
                    row=0, column=1, padx=6, pady=6, sticky="ew"
                )
                ctk.CTkLabel(
                    row, text=format_size(move.size_bytes), font=ctk.CTkFont(size=11), text_color=("gray40", "gray70")
                ).grid(row=0, column=2, padx=12, pady=6)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=2, column=0, padx=15, pady=15, sticky="ew")
        btn_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            btn_frame, text="İptal", width=120, fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"), command=self.destroy
        ).grid(row=0, column=1, padx=(0, 10))

        ctk.CTkButton(
            btn_frame, text="Onayla ve Düzenle", width=180, fg_color="#2E8B57", hover_color="#236B43",
            font=ctk.CTkFont(size=13, weight="bold"), command=self._confirm
        ).grid(row=0, column=2)

    def _toggle_category(self, category: str, state: bool):
        for var in self.category_groups[category]:
            var.set(state)

    def _toggle_all(self):
        state = self.select_all_var.get()
        for var in self.move_vars:
            var.set(state)

    def _confirm(self):
        approved = [m for m, var in zip(self.planned_moves, self.move_vars) if var.get()]
        self.destroy()
        if approved:
            self.on_confirm(approved)
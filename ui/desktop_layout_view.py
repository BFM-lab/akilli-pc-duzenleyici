import tkinter as tk
from tkinter import messagebox
from typing import Callable, Dict, List, Optional
import uuid
import customtkinter as ctk
from PIL import ImageTk

from core.desktop_layout import DesktopIcon, DesktopLayoutManager, DesktopZone, ZONE_COLORS


class DesktopLayoutView(ctk.CTkFrame):
    """Kullanıcının masaüstü önizlemesi üzerinde bölgeler çizip uygulamaları hizaladığı ekran."""

    CANVAS_W = 540
    CANVAS_H = 304

    def __init__(self, master, on_data_changed: Optional[Callable[[], None]] = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_data_changed = on_data_changed
        self.manager = DesktopLayoutManager()

        self.screen_w, self.screen_h, self.work_area = self.manager.get_screen_and_workarea()
        self.desktop_icons: List[DesktopIcon] = []
        self.zones: List[DesktopZone] = []
        self.selected_zone_id: Optional[str] = None

        self._bg_photo = None
        self._drag_start = None
        self._temp_rect = None
        self.app_checks: Dict[str, ctk.BooleanVar] = {}

        self._build_ui()
        self.reload_desktop_state()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)

        # Üst Başlık & Hızlı İşlemler
        top = ctk.CTkFrame(self)
        top.grid(row=0, column=0, columnspan=2, padx=20, pady=(10, 10), sticky="ew")
        top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top,
            text="Önizleme üzerinde kutular çizin; uygulamalar gerçek masaüstünde o bölgelere taşmadan sıralansın.",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray70"),
        ).grid(row=0, column=0, padx=14, pady=12, sticky="w")

        ctk.CTkButton(
            top, text="✨ Akıllı Otomatik Dağıt", width=170, fg_color="#8E44AD", hover_color="#6C3483",
            command=self._auto_distribute
        ).grid(row=0, column=1, padx=6, pady=10)

        ctk.CTkButton(
            top, text="Masaüstünü Yenile", width=130, command=self.reload_desktop_state
        ).grid(row=0, column=2, padx=(4, 12), pady=10)

        # Sol Panel: Etkileşimli Masaüstü Tuvali
        canvas_card = ctk.CTkFrame(self)
        canvas_card.grid(row=1, column=0, padx=(20, 8), pady=(0, 10), sticky="nsew")
        canvas_card.grid_columnconfigure(0, weight=1)
        canvas_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            canvas_card,
            text="Masaüstü Önizlemesi (Sol tık + sürükle ile bölge çizin)",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, padx=14, pady=(10, 6), sticky="w")

        self.canvas = tk.Canvas(
            canvas_card,
            width=self.CANVAS_W,
            height=self.CANVAS_H,
            bg="#182030",
            highlightthickness=2,
            highlightbackground="#3B82F6",
            cursor="crosshair",
        )
        self.canvas.grid(row=1, column=0, padx=14, pady=(4, 6))

        # Duvar kağıdında kutuların görünüp görünmeyeceği seçeneği (Varsayılan: Gizli)
        self.draw_wallpaper_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            canvas_card,
            text="Duvar kağıdımda kutu çerçevelerini görünür yap (İsteğe bağlı)",
            variable=self.draw_wallpaper_var,
            font=ctk.CTkFont(size=12),
            command=self._on_draw_mode_changed,
        ).grid(row=2, column=0, padx=14, pady=(2, 12), sticky="w")

        self.canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)

        # Sağ Panel: Seçili Kutu Ayarları ve Uygulama Seçimi
        right_card = ctk.CTkFrame(self)
        right_card.grid(row=1, column=1, padx=(8, 20), pady=(0, 10), sticky="nsew")
        right_card.grid_columnconfigure(0, weight=1)
        right_card.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(
            right_card, text="Çizilen Bölgeler & Kapasite", font=ctk.CTkFont(size=13, weight="bold")
        ).grid(row=0, column=0, columnspan=2, padx=14, pady=(10, 6), sticky="w")

        self.zone_selector = ctk.CTkOptionMenu(
            right_card, values=["Henüz kutu çizilmedi"], command=self._on_zone_selected
        )
        self.zone_selector.grid(row=1, column=0, columnspan=2, padx=14, pady=(0, 8), sticky="ew")

        edit_row = ctk.CTkFrame(right_card, fg_color="transparent")
        edit_row.grid(row=2, column=0, columnspan=2, padx=14, pady=4, sticky="ew")
        edit_row.grid_columnconfigure(0, weight=1)

        self.zone_title_entry = ctk.CTkEntry(edit_row, placeholder_text="Bölge Adı (Örn: Oyunlar)")
        self.zone_title_entry.grid(row=0, column=0, padx=(0, 6), sticky="ew")
        self.zone_title_entry.bind("<KeyRelease>", lambda _e: self._update_selected_zone_meta())

        self.zone_color_menu = ctk.CTkOptionMenu(
            edit_row, values=list(ZONE_COLORS.keys()), width=90, command=lambda _c: self._update_selected_zone_meta()
        )
        self.zone_color_menu.grid(row=0, column=1)

        del_row = ctk.CTkFrame(right_card, fg_color="transparent")
        del_row.grid(row=3, column=0, columnspan=2, padx=14, pady=(2, 6), sticky="ew")
        del_row.grid_columnconfigure(0, weight=1)

        self.capacity_label = ctk.CTkLabel(
            del_row, text="Uygulamalar:", font=ctk.CTkFont(size=12, weight="bold")
        )
        self.capacity_label.grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            del_row, text="Bölgeyi Sil", width=85, height=24, fg_color="#C0392B", hover_color="#922B21",
            command=self._delete_selected_zone
        ).grid(row=0, column=1, sticky="e")

        self.apps_checklist = ctk.CTkScrollableFrame(right_card, fg_color=("gray90", "gray17"))
        self.apps_checklist.grid(row=4, column=0, columnspan=2, padx=14, pady=(0, 14), sticky="nsew")
        self.apps_checklist.grid_columnconfigure(0, weight=1)

        # Alt İşlem Çubuğu
        bottom = ctk.CTkFrame(self)
        bottom.grid(row=2, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="ew")
        bottom.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(bottom, text="Hazır.", font=ctk.CTkFont(size=12))
        self.status_label.grid(row=0, column=0, padx=14, pady=14, sticky="w")

        ctk.CTkButton(
            bottom, text="Eski Masaüstüne Geri Dön", width=180, fg_color="#D35400", hover_color="#A04000",
            command=self._restore_desktop
        ).grid(row=0, column=1, padx=8, pady=12)

        ctk.CTkButton(
            bottom, text="Uygula ve Sırala", width=180, height=36,
            fg_color="#2E8B57", hover_color="#236B43", font=ctk.CTkFont(size=13, weight="bold"),
            command=self._apply_to_desktop
        ).grid(row=0, column=2, padx=(4, 14), pady=12)

    def _to_screen(self, cx: int, cy: int):
        sx = int(cx * (self.screen_w / self.CANVAS_W))
        sy = int(cy * (self.screen_h / self.CANVAS_H))
        return max(0, min(self.screen_w, sx)), max(0, min(self.screen_h, sy))

    def _to_canvas(self, sx: int, sy: int):
        cx = int(sx * (self.CANVAS_W / self.screen_w))
        cy = int(sy * (self.CANVAS_H / self.screen_h))
        return cx, cy

    def _on_draw_mode_changed(self):
        self._update_capacity_label()
        self._redraw_canvas()

    def reload_desktop_state(self):
        self.screen_w, self.screen_h, self.work_area = self.manager.get_screen_and_workarea()
        self.desktop_icons = self.manager.get_desktop_icons()

        base_img = self.manager.get_base_wallpaper_image()
        preview_img = base_img.resize((self.CANVAS_W, self.CANVAS_H))
        self._bg_photo = ImageTk.PhotoImage(preview_img)

        self._redraw_canvas()
        self._refresh_app_checklist()
        cell_w, cell_h = self.manager.get_icon_spacing()
        self.status_label.configure(
            text=f"Ekran: {self.screen_w}x{self.screen_h}  |  Simge boyutu: {cell_w}x{cell_h}px  |  Simge: {len(self.desktop_icons)}"
        )

    def _redraw_canvas(self):
        self.canvas.delete("all")
        if self._bg_photo:
            self.canvas.create_image(0, 0, anchor="nw", image=self._bg_photo)

        _, _, _, work_bottom = self.work_area
        _, cy_taskbar = self._to_canvas(0, work_bottom)
        self.canvas.create_line(0, cy_taskbar, self.CANVAS_W, cy_taskbar, fill="#94A3B8", dash=(4, 4))

        for ic in self.desktop_icons:
            cx, cy = self._to_canvas(ic.x, ic.y)
            self.canvas.create_oval(cx, cy, cx + 5, cy + 5, fill="#CBD5E1", outline="#0F172A")

        show_wp = self.draw_wallpaper_var.get()
        cell_w, cell_h = self.manager.get_icon_spacing()

        for z in self.zones:
            cx1, cy1 = self._to_canvas(z.x1, z.y1)
            cx2, cy2 = self._to_canvas(z.x2, z.y2)
            r, g, b = ZONE_COLORS.get(z.color_name, (52, 152, 219))
            hex_col = f"#{r:02x}{g:02x}{b:02x}"
            outline_w = 3 if z.zone_id == self.selected_zone_id else 2

            slots = self.manager.compute_zone_slots(z, draw_on_wallpaper=show_wp)
            cap = len(slots)

            self.canvas.create_rectangle(
                cx1, cy1, cx2, cy2,
                outline=hex_col, width=outline_w, fill=hex_col, stipple="gray25"
            )
            self.canvas.create_rectangle(cx1, cy1, cx2, min(cy2, cy1 + 18), fill=hex_col, outline="")
            self.canvas.create_text(
                cx1 + 6, cy1 + 9, anchor="w",
                text=f"{z.title} ({len(z.assigned_icons)}/{cap} yer)",
                fill="white", font=("Segoe UI", 8, "bold")
            )

            # Kutunun içindeki her yerleştirilmiş simgeyi minik kare olarak göster (taşmayacağını önceden gör)
            sw_icon = max(8, int(cell_w * (self.CANVAS_W / self.screen_w)) - 6)
            sh_icon = max(8, int(cell_h * (self.CANVAS_H / self.screen_h)) - 6)
            for idx, _name in enumerate(z.assigned_icons):
                if idx >= len(slots):
                    break
                px, py = slots[idx]
                ix, iy = self._to_canvas(px, py)
                self.canvas.create_rectangle(
                    ix + 2, iy + 2, ix + sw_icon, iy + sh_icon,
                    fill="#F8FAFC", outline=hex_col, width=1
                )

    def _on_mouse_down(self, event):
        sx, sy = self._to_screen(event.x, event.y)
        self._drag_start = (event.x, event.y)
        self._clicked_zone_candidate = None
        for z in reversed(self.zones):
            if z.x1 <= sx <= z.x2 and z.y1 <= sy <= z.y2:
                self._clicked_zone_candidate = z.zone_id
                break

    def _on_mouse_drag(self, event):
        if not self._drag_start:
            return
        if self._temp_rect:
            self.canvas.delete(self._temp_rect)
        x0, y0 = self._drag_start
        self._temp_rect = self.canvas.create_rectangle(
            x0, y0, event.x, event.y, outline="#38BDF8", width=2, dash=(4, 2)
        )

    def _on_mouse_up(self, event):
        if self._temp_rect:
            self.canvas.delete(self._temp_rect)
            self._temp_rect = None

        if not self._drag_start:
            return

        x0, y0 = self._drag_start
        self._drag_start = None

        if abs(event.x - x0) < 25 or abs(event.y - y0) < 25:
            if self._clicked_zone_candidate:
                self._select_zone(self._clicked_zone_candidate)
            return

        sx1, sy1 = self._to_screen(min(x0, event.x), min(y0, event.y))
        sx2, sy2 = self._to_screen(max(x0, event.x), max(y0, event.y))

        _, _, _, work_bottom = self.work_area
        sy2 = min(sy2, work_bottom - 4)

        cell_w, cell_h = self.manager.get_icon_spacing()
        if (sx2 - sx1) < cell_w + 16 or (sy2 - sy1) < cell_h + 16:
            messagebox.showinfo(
                "Kutu Çok Küçük",
                f"En az 1 simge sığabilmesi için kutuyu biraz daha büyük çizin (en az {cell_w + 20}x{cell_h + 20} px).",
            )
            return

        preset_names = ["Oyunlar", "İş & Geliştirme", "Tarayıcı & İletişim", "Klasörler & Diğer"]
        color_names = list(ZONE_COLORS.keys())
        idx = len(self.zones)
        title = preset_names[idx] if idx < len(preset_names) else f"Bölge {idx + 1}"
        color = color_names[idx % len(color_names)]

        new_zone = DesktopZone(
            zone_id=str(uuid.uuid4())[:8],
            title=title,
            color_name=color,
            x1=sx1, y1=sy1, x2=sx2, y2=sy2,
        )
        self.zones.append(new_zone)
        self._refresh_zone_dropdown(select_id=new_zone.zone_id)
        self._redraw_canvas()

    def _refresh_zone_dropdown(self, select_id: Optional[str] = None):
        if not self.zones:
            self.zone_selector.configure(values=["Henüz kutu çizilmedi"])
            self.zone_selector.set("Henüz kutu çizilmedi")
            self.selected_zone_id = None
            self.zone_title_entry.delete(0, "end")
            self._update_capacity_label()
            self._refresh_app_checklist()
            return

        labels = [f"{z.title} [#{z.zone_id}]" for z in self.zones]
        self.zone_selector.configure(values=labels)
        target_id = select_id or self.selected_zone_id or self.zones[0].zone_id
        self._select_zone(target_id)

    def _select_zone(self, zone_id: str):
        zone = next((z for z in self.zones if z.zone_id == zone_id), None)
        if not zone:
            return
        self.selected_zone_id = zone.zone_id
        self.zone_selector.set(f"{zone.title} [#{zone.zone_id}]")

        self.zone_title_entry.delete(0, "end")
        self.zone_title_entry.insert(0, zone.title)
        self.zone_color_menu.set(zone.color_name)

        self._update_capacity_label()
        self._refresh_app_checklist()
        self._redraw_canvas()

    def _update_capacity_label(self):
        zone = next((z for z in self.zones if z.zone_id == self.selected_zone_id), None)
        if not zone:
            self.capacity_label.configure(text="Uygulamalar:")
            return
        cap = len(self.manager.compute_zone_slots(zone, draw_on_wallpaper=self.draw_wallpaper_var.get()))
        used = len(zone.assigned_icons)
        self.capacity_label.configure(text=f"Uygulamalar ({used} / {cap} yer):")

    def _on_zone_selected(self, value: str):
        if "[#" in value:
            zid = value.split("[#")[-1].rstrip("]")
            self._select_zone(zid)

    def _update_selected_zone_meta(self):
        zone = next((z for z in self.zones if z.zone_id == self.selected_zone_id), None)
        if not zone:
            return
        zone.title = self.zone_title_entry.get().strip() or "Bölge"
        zone.color_name = self.zone_color_menu.get()

        labels = [f"{z.title} [#{z.zone_id}]" for z in self.zones]
        self.zone_selector.configure(values=labels)
        self.zone_selector.set(f"{zone.title} [#{zone.zone_id}]")
        self._redraw_canvas()

    def _delete_selected_zone(self):
        if not self.selected_zone_id:
            return
        self.zones = [z for z in self.zones if z.zone_id != self.selected_zone_id]
        self.selected_zone_id = self.zones[0].zone_id if self.zones else None
        self._refresh_zone_dropdown(self.selected_zone_id)
        self._redraw_canvas()

    def _refresh_app_checklist(self):
        for w in self.apps_checklist.winfo_children():
            w.destroy()
        self.app_checks.clear()

        zone = next((z for z in self.zones if z.zone_id == self.selected_zone_id), None)
        if not zone:
            ctk.CTkLabel(
                self.apps_checklist,
                text="Önce soldaki önizleme üzerinde bir bölge çizin.",
                text_color=("gray50", "gray60"),
                font=ctk.CTkFont(size=12, slant="italic"),
            ).pack(pady=35)
            return

        if not self.desktop_icons:
            ctk.CTkLabel(self.apps_checklist, text="Masaüstü simgesi bulunamadı.").pack(pady=35)
            return

        assigned_set = set(zone.assigned_icons)
        for idx, ic in enumerate(self.desktop_icons):
            var = ctk.BooleanVar(value=(ic.name in assigned_set))
            self.app_checks[ic.name] = var
            cb = ctk.CTkCheckBox(
                self.apps_checklist,
                text=ic.name,
                variable=var,
                font=ctk.CTkFont(size=12),
                command=lambda n=ic.name, v=var: self._on_toggle_icon(n, v.get()),
            )
            cb.grid(row=idx, column=0, padx=8, pady=3, sticky="w")

    def _on_toggle_icon(self, icon_name: str, checked: bool):
        zone = next((z for z in self.zones if z.zone_id == self.selected_zone_id), None)
        if not zone:
            return

        if checked:
            cap = len(self.manager.compute_zone_slots(zone, draw_on_wallpaper=self.draw_wallpaper_var.get()))
            if len(zone.assigned_icons) >= cap:
                self.app_checks[icon_name].set(False)
                messagebox.showwarning(
                    "Kutu Dolu",
                    f"Bu kutuya en fazla {cap} uygulama sığabilir. Daha fazla eklemek için kutuyu daha büyük çizin.",
                )
                return

            for z in self.zones:
                if icon_name in z.assigned_icons:
                    z.assigned_icons.remove(icon_name)
            zone.assigned_icons.append(icon_name)
        else:
            if icon_name in zone.assigned_icons:
                zone.assigned_icons.remove(icon_name)

        self._update_capacity_label()
        self._redraw_canvas()

    def _auto_distribute(self):
        if not self.zones:
            messagebox.showwarning("Uyarı", "Önce sol taraftaki önizlemede en az 1 bölge çizin!")
            return
        self.manager.auto_assign_icons(
            self.zones, self.desktop_icons, draw_on_wallpaper=self.draw_wallpaper_var.get()
        )
        self._update_capacity_label()
        self._refresh_app_checklist()
        self._redraw_canvas()
        self.status_label.configure(text="Uygulamalar kutuların kapasitesine göre otomatik dağıtıldı.")

    def _apply_to_desktop(self):
        if not self.zones:
            messagebox.showwarning("Uyarı", "Lütfen önce masaüstünde en az bir bölge çizin.")
            return

        total_assigned = sum(len(z.assigned_icons) for z in self.zones)
        if total_assigned == 0:
            if messagebox.askyesno(
                "Uygulamalar Seçilmedi",
                "Bölgelere henüz uygulama atanmadı. Akıllı Otomatik Dağıtım yapıp uygulayayım mı?",
            ):
                self._auto_distribute()
            else:
                return

        count, overflow, warn = self.manager.apply_layout(
            self.zones, draw_on_wallpaper=self.draw_wallpaper_var.get()
        )
        self.reload_desktop_state()
        if self.on_data_changed:
            self.on_data_changed()

        msg = f"{count} simge çizdiğiniz bölgelerin içine taşmadan yan yana hizalandı!"
        if overflow > 0:
            msg += f"\n\nNot: {overflow} uygulama kutu kapasitesini aştığı için taşınmadı."
        if warn:
            msg += f"\n\n⚠️ ÖNEMLİ NOT:\n{warn}"
        messagebox.showinfo("Masaüstü Düzenlendi", msg)

    def _restore_desktop(self):
        if not messagebox.askyesno("Onay", "Eski duvar kağıdınız ve simge konumlarınız geri yüklensin mi?"):
            return
        ok, msg = self.manager.restore_backup()
        self.reload_desktop_state()
        if ok:
            messagebox.showinfo("Geri Yüklendi", msg)
        else:
            messagebox.showwarning("Bilgi", msg)
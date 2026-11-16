import customtkinter as ctk

# shadcn/ui Zinc Paleti: (Light Mode, Dark Mode)
SHADCN = {
    "bg": ("#FFFFFF", "#09090B"),
    "sidebar": ("#F4F4F5", "#111114"),
    "card": ("#FAFAFA", "#18181B"),
    "card_hover": ("#F4F4F5", "#202024"),
    "muted": ("#F4F4F5", "#27272A"),
    "border": ("#E4E4E7", "#27272A"),
    "border_strong": ("#D4D4D8", "#3F3F46"),
    "text": ("#09090B", "#FAFAFA"),
    "muted_text": ("#71717A", "#A1A1AA"),
    "primary": ("#18181B", "#FAFAFA"),
    "primary_text": ("#FAFAFA", "#09090B"),
    "accent_blue": ("#2563EB", "#3B82F6"),
    "danger": ("#DC2626", "#EF4444"),
    "danger_hover": ("#B91C1C", "#DC2626"),
    "success": ("#16A34A", "#22C55E"),
    "success_hover": ("#15803D", "#16A34A"),
}

BADGE_STYLES = {
    "success": (("#DCFCE7", "#14532D"), ("#166534", "#86EFAC")),
    "warning": (("#FEF3C7", "#451A03"), ("#92400E", "#FCD34D")),
    "danger": (("#FEE2E2", "#450A0A"), ("#991B1B", "#FCA5A5")),
    "info": (("#DBEAFE", "#172554"), ("#1E40AF", "#93C5FD")),
    "neutral": (("#F4F4F5", "#27272A"), ("#3F3F46", "#D4D4D8")),
}


class ShadcnBadge(ctk.CTkFrame):
    """shadcn/ui tarzı yuvarlak kenarlı küçük durum rozeti."""

    def __init__(self, master, text: str, variant: str = "neutral", **kwargs):
        bg_col, txt_col = BADGE_STYLES.get(variant, BADGE_STYLES["neutral"])
        super().__init__(
            master,
            fg_color=bg_col,
            corner_radius=999,
            border_width=0,
            **kwargs,
        )
        ctk.CTkLabel(
            self,
            text=text,
            text_color=txt_col,
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(padx=9, pady=2)
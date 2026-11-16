from typing import Dict, Tuple
from PIL import Image, ImageDraw
import customtkinter as ctk

_ICON_CACHE: Dict[Tuple[str, int], ctk.CTkImage] = {}


def _draw_icon(name: str, color: str, size: int) -> Image.Image:
    # Yüksek çözünürlüklü çizip küçülterek pürüzsüz (anti-aliased) görünüm elde et
    scale = 3
    s = size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = max(2, int(s * 0.09))

    if name == "folder":
        d.rounded_rectangle([s * 0.12, s * 0.28, s * 0.88, s * 0.82], radius=s * 0.08, outline=color, width=w)
        d.polygon(
            [(s * 0.12, s * 0.28), (s * 0.18, s * 0.18), (s * 0.44, s * 0.18), (s * 0.50, s * 0.28)],
            outline=color,
            width=w,
        )
    elif name == "broom":
        d.line([(s * 0.78, s * 0.16), (s * 0.44, s * 0.50)], fill=color, width=w + 1)
        d.polygon(
            [(s * 0.36, s * 0.44), (s * 0.54, s * 0.62), (s * 0.24, s * 0.86), (s * 0.14, s * 0.72)],
            outline=color,
            width=w,
        )
    elif name == "duplicate":
        d.rounded_rectangle([s * 0.16, s * 0.26, s * 0.66, s * 0.82], radius=s * 0.07, outline=color, width=w)
        d.rounded_rectangle([s * 0.34, s * 0.14, s * 0.84, s * 0.70], radius=s * 0.07, outline=color, width=w)
    elif name == "desktop":
        d.rounded_rectangle([s * 0.12, s * 0.18, s * 0.88, s * 0.70], radius=s * 0.06, outline=color, width=w)
        d.line([(s * 0.50, s * 0.70), (s * 0.50, s * 0.84)], fill=color, width=w)
        d.line([(s * 0.32, s * 0.84), (s * 0.68, s * 0.84)], fill=color, width=w)
    elif name == "history":
        d.arc([s * 0.18, s * 0.18, s * 0.84, s * 0.84], start=40, end=330, fill=color, width=w)
        d.polygon([(s * 0.14, s * 0.34), (s * 0.32, s * 0.24), (s * 0.28, s * 0.44)], fill=color)
        d.line([(s * 0.50, s * 0.34), (s * 0.50, s * 0.52), (s * 0.64, s * 0.58)], fill=color, width=w)
    elif name == "trash":
        d.line([(s * 0.20, s * 0.26), (s * 0.80, s * 0.26)], fill=color, width=w)
        d.rectangle([s * 0.38, s * 0.16, s * 0.62, s * 0.26], outline=color, width=w)
        d.rounded_rectangle([s * 0.26, s * 0.26, s * 0.74, s * 0.84], radius=s * 0.06, outline=color, width=w)
        d.line([(s * 0.42, s * 0.40), (s * 0.42, s * 0.72)], fill=color, width=w)
        d.line([(s * 0.58, s * 0.40), (s * 0.58, s * 0.72)], fill=color, width=w)
    elif name == "disk":
        d.rounded_rectangle([s * 0.14, s * 0.28, s * 0.86, s * 0.74], radius=s * 0.08, outline=color, width=w)
        d.line([(s * 0.14, s * 0.54), (s * 0.86, s * 0.54)], fill=color, width=w)
        d.ellipse([s * 0.68, s * 0.60, s * 0.76, s * 0.68], fill=color)

    return img.resize((size, size), Image.Resampling.LANCZOS)


def get_icon(name: str, size: int = 20) -> ctk.CTkImage:
    key = (name, size)
    if key not in _ICON_CACHE:
        light_img = _draw_icon(name, "#1F2937", size)
        dark_img = _draw_icon(name, "#F3F4F6", size)
        _ICON_CACHE[key] = ctk.CTkImage(light_image=light_img, dark_image=dark_img, size=(size, size))
    return _ICON_CACHE[key]
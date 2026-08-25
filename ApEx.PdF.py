#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════╗
║                              A p E x   P d F   v3                         ║
║        Advanced PDF Editor · Converter · Annotator — single file app      ║
║                        by StRaNgErDrEaMeR                                 ║
╚══════════════════════════════════════════════════════════════════════════╝

WHAT'S NEW IN v3
  • FIXED: crash when a RoundButton's own command rebuilds/destroys the
    toolbar (theme toggle, tool switch, dialog close) — button no longer
    touches itself after being destroyed mid-click
  • New animated Apple-style launch screen: dual-ring spinner, soft
    gradient glow, macOS traffic-light chrome, fade transition
  • Command Palette (Ctrl+K) — fuzzy-search every action, keyboard driven
  • Find in Document (Ctrl+F) — search text, jump + highlight matches
  • Page context menu on thumbnails — rotate, duplicate, delete, insert
    blank page, move up / move down (annotations remap automatically)
  • Dashed stroke style toggle for pen/line/arrow/rect/ellipse
  • Document Properties dialog (title / author / subject / keywords)
  • Open in system PDF viewer / print
  • Everything from v2 kept: real select/move/resize tool, progress
    dialogs, opacity + font-size sliders, recent files, fit/actual zoom

DEPENDENCIES  (install once)
    pip install PyMuPDF Pillow --break-system-packages
    (drop --break-system-packages on Windows / regular venvs)

RUN
    python3 apple_pdf_studio.py
"""

import os
import sys
import copy
import math
import time
import subprocess
import threading
import traceback
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

# ────────────────────────────────────────────────────────────────────────
#  Dependency check — fail with a friendly, actionable message
# ────────────────────────────────────────────────────────────────────────
_MISSING = []
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, simpledialog, colorchooser
except Exception:
    print("Tkinter is required and should ship with your Python install.")
    raise

try:
    import pymupdf as fitz          # PyMuPDF — new import name
except Exception:
    try:
        import fitz                 # fallback to legacy import name
    except Exception:
        _MISSING.append("PyMuPDF")
        fitz = None

try:
    from PIL import Image, ImageTk
except Exception:
    _MISSING.append("Pillow")
    Image = ImageTk = None

if _MISSING:
    msg = (
        "Missing required package(s): " + ", ".join(_MISSING) + "\n\n"
        "Install them with:\n\n"
        "    pip install PyMuPDF Pillow --break-system-packages\n\n"
        "(remove --break-system-packages if you're on Windows or a venv)"
    )
    try:
        _r = tk.Tk(); _r.withdraw()
        messagebox.showerror("ApEx PdF — missing dependencies", msg)
    except Exception:
        pass
    print(msg)
    sys.exit(1)


# ════════════════════════════════════════════════════════════════════════
#  THEME
# ════════════════════════════════════════════════════════════════════════
LIGHT = dict(
    bg="#F5F5F7", sidebar="#FBFBFD", panel="#FFFFFF", toolbar="#FBFBFD",
    text="#1D1D1F", subtext="#6E6E73", accent="#007AFF", accent_hover="#0066D6",
    border="#D6D6DA", canvas_bg="#E5E5EA", button="#FFFFFF", button_hover="#EFEFF3",
    button_active="#E2E2E8", danger="#FF3B30", success="#34C759", warn="#FF9500",
)
DARK = dict(
    bg="#1E1E1E", sidebar="#252526", panel="#2C2C2E", toolbar="#252526",
    text="#F5F5F7", subtext="#98989D", accent="#0A84FF", accent_hover="#409CFF",
    border="#3A3A3C", canvas_bg="#0B0B0C", button="#3A3A3C", button_hover="#48484A",
    button_active="#55555A", danger="#FF453A", success="#30D158", warn="#FF9F0A",
)
FONT_UI = ("SF Pro Display", "Helvetica Neue", "Segoe UI", "Arial")

CURSORS = {
    "select": "arrow", "pen": "pencil", "highlighter": "pencil",
    "line": "crosshair", "arrow": "crosshair", "rect": "crosshair",
    "ellipse": "crosshair", "balloon": "crosshair", "text": "xterm",
    "eraser": "circle", "edittext": "xterm",
}


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def spancolor_to_hex(colorint):
    """PyMuPDF span['color'] is a packed sRGB int — convert to '#rrggbb'."""
    try:
        colorint = int(colorint)
    except Exception:
        return "#1D1D1F"
    r = (colorint >> 16) & 255
    g = (colorint >> 8) & 255
    b = colorint & 255
    return f"#{r:02x}{g:02x}{b:02x}"


def blend_hex(hexcolor, opacity, bg="#E5E5EA"):
    """Approximate an alpha-blended preview color for the Tk canvas."""
    if opacity >= 0.999:
        return hexcolor
    hexcolor = hexcolor.lstrip("#")
    bg = bg.lstrip("#")
    r, g, b = (int(hexcolor[i:i + 2], 16) for i in (0, 2, 4))
    br, bgc, bb = (int(bg[i:i + 2], 16) for i in (0, 2, 4))
    nr = int(r * opacity + br * (1 - opacity))
    ng = int(g * opacity + bgc * (1 - opacity))
    nb = int(b * opacity + bb * (1 - opacity))
    return f"#{nr:02x}{ng:02x}{nb:02x}"


def round_rect_pts(x1, y1, x2, y2, r):
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    return [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]


def lerp_hex(a, b, t):
    a = a.lstrip("#"); b = b.lstrip("#")
    ar, ag, ab = (int(a[i:i + 2], 16) for i in (0, 2, 4))
    br, bg, bb = (int(b[i:i + 2], 16) for i in (0, 2, 4))
    r = int(ar + (br - ar) * t); g = int(ag + (bg - ag) * t); bl = int(ab + (bb - ab) * t)
    return f"#{r:02x}{g:02x}{bl:02x}"


# ════════════════════════════════════════════════════════════════════════
#  Splash screen — Apple-style animated launcher
# ════════════════════════════════════════════════════════════════════════
class Splash(tk.Tk):
    def __init__(self):
        super().__init__()
        self.overrideredirect(True)
        w, h = 520, 320
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        self.configure(bg="#0A0A0C")
        self.w, self.h = w, h
        self.attributes("-alpha", 0.0)

        c = tk.Canvas(self, width=w, height=h, bg="#0A0A0C", highlightthickness=0)
        c.pack(fill="both", expand=True)
        self.canvas = c

        # soft radial-ish glow behind the logo (concentric fading ovals)
        cx, cy = w / 2, h / 2 - 40
        for i, rad in enumerate(range(140, 20, -12)):
            t = i / 10
            col = lerp_hex("#0A0A0C", "#0A84FF", 0.05 + t * 0.10)
            c.create_oval(cx - rad, cy - rad, cx + rad, cy + rad, outline="", fill=col)

        # macOS traffic-light chrome, top-left, purely decorative
        for i, col in enumerate(("#FF5F57", "#FEBC2E", "#28C840")):
            c.create_oval(18 + i * 20, 16, 30 + i * 20, 28, fill=col, outline="")

        # dual ring spinner
        self.ring_r1, self.ring_r2 = 42, 30
        self.ring_cx, self.ring_cy = cx, cy
        c.create_text(cx, cy, text="PDF", font=(FONT_UI[0], 16, "bold"), fill="white")
        self.arc1 = c.create_arc(cx - self.ring_r1, cy - self.ring_r1, cx + self.ring_r1, cy + self.ring_r1,
                                   start=0, extent=110, style="arc", outline="#0A84FF", width=3)
        self.arc2 = c.create_arc(cx - self.ring_r2, cy - self.ring_r2, cx + self.ring_r2, cy + self.ring_r2,
                                   start=180, extent=70, style="arc", outline="#409CFF", width=2)

        c.create_text(w / 2, h / 2 + 66, text="ApEx PdF",
                       font=(FONT_UI[0], 20, "bold"), fill="white")
        c.create_text(w / 2, h / 2 + 92, text="by StRaNgErDrEaMeR",
                       font=(FONT_UI[0], 10), fill="#8E8E93")

        c.create_rectangle(w / 2 - 130, h / 2 + 122, w / 2 + 130, h / 2 + 128,
                            fill="#2C2C2E", outline="")
        self.bar_bg_x0 = w / 2 - 130
        self.bar_full_w = 260
        self.bar = c.create_rectangle(self.bar_bg_x0, h / 2 + 122, self.bar_bg_x0, h / 2 + 128,
                                        fill="#0A84FF", outline="")
        self.status = c.create_text(w / 2, h / 2 + 146, text="Starting…",
                                      font=(FONT_UI[0], 9), fill="#8E8E93")

        self.progress = 0
        self.spin_angle = 0
        self._steps = ["Loading engine…", "Preparing canvas…", "Warming up tools…", "Ready."]
        self._fade_in()

    def _fade_in(self, a=0.0):
        a = min(1.0, a + 0.08)
        self.attributes("-alpha", a)
        if a < 1.0:
            self.after(12, lambda: self._fade_in(a))
        else:
            self.after(30, self._animate)

    def _animate(self):
        # spinner rotation
        self.spin_angle = (self.spin_angle + 9) % 360
        self.canvas.itemconfigure(self.arc1, start=self.spin_angle)
        self.canvas.itemconfigure(self.arc2, start=(self.spin_angle * -1.4) % 360)

        self.progress = min(100, self.progress + 3)
        x1 = self.bar_bg_x0 + self.bar_full_w * (self.progress / 100)
        y0, y1 = self.h / 2 + 122, self.h / 2 + 128
        self.canvas.coords(self.bar, self.bar_bg_x0, y0, x1, y1)
        step = self._steps[min(len(self._steps) - 1, self.progress // 26)]
        self.canvas.itemconfigure(self.status, text=step)

        if self.progress < 100:
            self.after(16, self._animate)
        else:
            self._fade_out()

    def _fade_out(self, a=1.0):
        a = max(0.0, a - 0.08)
        self.attributes("-alpha", a)
        if a > 0:
            self.after(10, lambda: self._fade_out(a))
        else:
            self.destroy()


# ════════════════════════════════════════════════════════════════════════
#  Progress dialog for long-running / multi-page operations
# ════════════════════════════════════════════════════════════════════════
class ProgressDialog(tk.Toplevel):
    def __init__(self, app, title="Working…", determinate=True):
        super().__init__(app)
        t = app.theme
        self.overrideredirect(True)
        w, h = 360, 130
        x = app.winfo_rootx() + (app.winfo_width() - w) // 2
        y = app.winfo_rooty() + (app.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.configure(bg=t["panel"])
        self.transient(app)
        frame = tk.Frame(self, bg=t["panel"], highlightbackground=t["border"], highlightthickness=1)
        frame.pack(fill="both", expand=True)
        self.label = tk.Label(frame, text=title, bg=t["panel"], fg=t["text"],
                                font=(FONT_UI[0], 12, "bold"))
        self.label.pack(pady=(22, 10))
        self.pbar = ttk.Progressbar(frame, orient="horizontal", length=280,
                                      mode="determinate" if determinate else "indeterminate")
        self.pbar.pack(pady=4)
        self.sub = tk.Label(frame, text="", bg=t["panel"], fg=t["subtext"], font=(FONT_UI[0], 9))
        self.sub.pack(pady=(6, 0))
        if not determinate:
            self.pbar.start(12)
        self.update()

    def set_progress(self, current, total, text=""):
        try:
            self.pbar["maximum"] = max(1, total)
            self.pbar["value"] = current
            if text:
                self.sub.configure(text=text)
            self.update()
        except Exception:
            pass

    def close(self):
        try:
            self.pbar.stop()
            self.destroy()
        except Exception:
            pass


# ════════════════════════════════════════════════════════════════════════
#  Reusable Apple-style widgets
# ════════════════════════════════════════════════════════════════════════
class Tooltip:
    def __init__(self, widget, text):
        self.widget, self.text, self.tip = widget, text, None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, _e=None):
        if self.tip or not self.text:
            return
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        tk.Label(self.tip, text=self.text, bg="#111116", fg="white",
                  font=(FONT_UI[0], 9), padx=8, pady=4, bd=0).pack()

    def _hide(self, _e=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


class RoundButton(tk.Canvas):
    """A soft, rounded, macOS-flavoured button drawn on a Canvas."""

    def __init__(self, parent, theme, text="", icon="", command=None,
                 width=92, height=32, radius=9, kind="normal",
                 tooltip=None, toggle=False, fontsize=12):
        bg = parent["bg"]
        super().__init__(parent, width=width, height=height, bg=bg,
                          highlightthickness=0, bd=0, cursor="hand2")
        self.theme, self.command, self.kind = theme, command, kind
        self.text, self.icon, self.w, self.h, self.r = text, icon, width, height, radius
        self.toggle, self.active, self.hover = toggle, False, False
        self.fontsize = fontsize
        self.bind("<Button-1>", self._click)
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        if tooltip:
            Tooltip(self, tooltip)
        self.redraw()

    def _set_hover(self, v):
        if not self.winfo_exists():
            return
        self.hover = v
        self.redraw()

    def _click(self, _e=None):
        if self.toggle:
            self.active = not self.active
        if self.command:
            self.command()
        # FIX (v3): the command above may rebuild the UI and destroy this
        # very widget (theme toggle, tool switch, dialog close, etc). Never
        # touch self again once that's happened.
        if self.winfo_exists():
            self.redraw()

    def set_active(self, v):
        if not self.winfo_exists():
            return
        self.active = v
        self.redraw()

    def redraw(self):
        if not self.winfo_exists():
            return
        self.delete("all")
        t = self.theme
        if self.kind == "accent":
            base = t["accent"]
        elif self.active:
            base = t["accent"]
        elif self.hover:
            base = t["button_hover"]
        else:
            base = t["button"]
        fg = "#FFFFFF" if (self.kind == "accent" or self.active) else t["text"]
        pts = round_rect_pts(1, 1, self.w - 1, self.h - 1, self.r)
        outline = "" if (self.kind == "accent" or self.active) else t["border"]
        self.create_polygon(pts, smooth=True, fill=base, outline=outline, width=1)
        label = f"{self.icon}  {self.text}".strip() if self.icon and self.text else (self.icon or self.text)
        self.create_text(self.w / 2, self.h / 2, text=label, fill=fg,
                          font=(FONT_UI[0], self.fontsize))


class ToolIconButton(RoundButton):
    def __init__(self, parent, theme, icon, tool_id, command, tooltip=None, size=40):
        self.tool_id = tool_id
        super().__init__(parent, theme, text="", icon=icon, command=command,
                          width=size, height=size, radius=11, toggle=False,
                          tooltip=tooltip, fontsize=15)


# ════════════════════════════════════════════════════════════════════════
#  Data model
# ════════════════════════════════════════════════════════════════════════
@dataclass
class Annotation:
    kind: str
    points: List[Tuple[float, float]] = field(default_factory=list)   # PDF-space
    color: str = "#FF3B30"
    width: float = 2.5
    fill: Optional[str] = None
    text: str = ""
    fontsize: float = 13
    opacity: float = 1.0
    dashed: bool = False


# ════════════════════════════════════════════════════════════════════════
#  PDF ENGINE — pure logic, no Tk. Independently testable / reusable.
# ════════════════════════════════════════════════════════════════════════
class PDFEngine:

    @staticmethod
    def render_page(doc, index, zoom) -> "Image.Image":
        page = doc[index]
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

    @staticmethod
    def flatten(doc, annotations: dict, out_path: str):
        out = fitz.open()
        out.insert_pdf(doc)
        for idx, items in annotations.items():
            if idx >= len(out) or not items:
                continue
            page = out[idx]

            # ── "Edit existing text" annotations are applied FIRST, as real
            # redactions: the original PDF text is erased (white box) and the
            # replacement is baked into the page content stream in its place.
            edits = [a for a in items if a.kind == "edit_text" and len(a.points) == 2]
            for a in edits:
                r = fitz.Rect(*a.points[0], *a.points[1])
                col = hexrgb(a.color)
                page.add_redact_annot(
                    r, text=a.text or "", fontsize=a.fontsize, fontname="helv",
                    text_color=col, fill=(1, 1, 1), align=0,
                )
            if edits:
                page.apply_redactions()

            shape = page.new_shape()
            for a in items:
                if a.kind == "edit_text":
                    continue  # already applied above via redaction
                col = hexrgb(a.color)
                fillc = hexrgb(a.fill) if a.fill else None
                op = max(0.05, min(1.0, getattr(a, "opacity", 1.0)))
                dashes = "[4 3] 0" if getattr(a, "dashed", False) else None
                if a.kind in ("pen", "highlighter") and len(a.points) >= 2:
                    shape.draw_polyline(a.points)
                    hop = 0.35 if a.kind == "highlighter" else op
                    shape.finish(color=col, width=a.width, closePath=False,
                                 lineCap=1, lineJoin=1, stroke_opacity=hop, dashes=dashes)
                elif a.kind == "line" and len(a.points) == 2:
                    shape.draw_line(a.points[0], a.points[1])
                    shape.finish(color=col, width=a.width, lineCap=1, stroke_opacity=op, dashes=dashes)
                elif a.kind == "arrow" and len(a.points) == 2:
                    p0, p1 = a.points
                    shape.draw_line(p0, p1)
                    shape.finish(color=col, width=a.width, lineCap=1, stroke_opacity=op, dashes=dashes)
                    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
                    head = max(8, a.width * 4)
                    for da in (0.5, -0.5):
                        hx = p1[0] - head * math.cos(ang - da)
                        hy = p1[1] - head * math.sin(ang - da)
                        shape.draw_line(p1, (hx, hy))
                        shape.finish(color=col, width=a.width, lineCap=1, stroke_opacity=op)
                elif a.kind == "rect" and len(a.points) == 2:
                    r = fitz.Rect(*a.points[0], *a.points[1]); r.normalize()
                    shape.draw_rect(r)
                    shape.finish(color=col, width=a.width, fill=fillc,
                                  stroke_opacity=op, fill_opacity=op if fillc else 1.0, dashes=dashes)
                elif a.kind == "ellipse" and len(a.points) == 2:
                    r = fitz.Rect(*a.points[0], *a.points[1]); r.normalize()
                    shape.draw_oval(r)
                    shape.finish(color=col, width=a.width, fill=fillc,
                                  stroke_opacity=op, fill_opacity=op if fillc else 1.0, dashes=dashes)
                elif a.kind == "balloon" and len(a.points) == 2:
                    anchor, body_pt = a.points
                    bw, bh = 150, 60
                    bx0, by0 = body_pt[0] - bw / 2, body_pt[1] - bh / 2
                    bx1, by1 = bx0 + bw, by0 + bh
                    r = fitz.Rect(bx0, by0, bx1, by1)
                    cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
                    dx, dy = anchor[0] - cx, anchor[1] - cy
                    dist = max(1.0, math.hypot(dx, dy))
                    tx, ty = cx + dx / dist * (bw * 0.28), cy + dy / dist * (bh * 0.28)
                    shape.draw_polyline([(tx - 6, ty), (anchor[0], anchor[1]), (tx + 6, ty)])
                    shape.finish(color=col, width=a.width, fill=(1, 1, 1), closePath=True, stroke_opacity=op)
                    shape.draw_rect(r)
                    shape.finish(color=col, width=a.width, fill=(1, 1, 1), stroke_opacity=op)
                    page.insert_textbox(fitz.Rect(bx0 + 6, by0 + 4, bx1 - 6, by1 - 4),
                                         a.text or "", fontsize=a.fontsize,
                                         color=(0, 0, 0), align=1)
                elif a.kind == "text" and a.points:
                    # BUGFIX: the canvas preview anchors text at its TOP-LEFT
                    # corner ("nw"), but page.insert_text() places its point at
                    # the text BASELINE. That mismatch (roughly one line-height)
                    # is exactly why text typed "inside" a circle/rect on screen
                    # could drift outside that shape once exported. insert_textbox
                    # anchors from the top of the given rect, matching the canvas
                    # preview exactly, so the text stays put relative to any
                    # shape it was placed over.
                    x, y = a.points[0]
                    fs = a.fontsize
                    lines = (a.text or "").split("\n")
                    max_len = max((len(ln) for ln in lines), default=0)
                    box_w = max(60.0, max_len * fs * 0.62 + 10)
                    box_h = fs * 1.35 * max(1, len(lines)) + 6
                    rect = fitz.Rect(x, y, x + box_w, y + box_h)
                    page.insert_textbox(rect, a.text or "", fontsize=fs, color=col,
                                         fontname="helv", align=0)
            shape.commit(overlay=True)
        out.save(out_path, garbage=4, deflate=True)
        out.close()

    @staticmethod
    def pdf_to_images(path, out_dir, fmt="PNG", zoom=2.0, progress=None):
        doc = fitz.open(path)
        stem = os.path.splitext(os.path.basename(path))[0]
        out_files = []
        for i in range(len(doc)):
            img = PDFEngine.render_page(doc, i, zoom)
            ext = fmt.lower() if fmt.lower() != "jpeg" else "jpg"
            out_path = os.path.join(out_dir, f"{stem}_page{i + 1}.{ext}")
            if fmt.upper() in ("JPG", "JPEG"):
                img.convert("RGB").save(out_path, "JPEG", quality=95)
            else:
                img.save(out_path, fmt.upper())
            out_files.append(out_path)
            if progress:
                progress(i + 1, len(doc))
        doc.close()
        return out_files

    @staticmethod
    def images_to_pdf(image_paths, out_path):
        doc = fitz.open()
        for p in image_paths:
            im = Image.open(p).convert("RGB")
            w, h = im.size
            page = doc.new_page(width=w, height=h)
            page.insert_image(page.rect, filename=p)
        doc.save(out_path)
        doc.close()

    @staticmethod
    def pdf_to_text(path, out_path):
        doc = fitz.open(path)
        with open(out_path, "w", encoding="utf-8") as f:
            for i, page in enumerate(doc):
                f.write(f"\n\n===== Page {i + 1} =====\n\n")
                f.write(page.get_text())
        doc.close()

    @staticmethod
    def convert_image(path, out_path, fmt):
        im = Image.open(path)
        if fmt.upper() in ("JPG", "JPEG"):
            im = im.convert("RGB")
            im.save(out_path, "JPEG", quality=95)
        else:
            im.save(out_path, fmt.upper())

    @staticmethod
    def merge_pdfs(paths, out_path, progress=None):
        out = fitz.open()
        for i, p in enumerate(paths):
            d = fitz.open(p)
            out.insert_pdf(d)
            d.close()
            if progress:
                progress(i + 1, len(paths))
        out.save(out_path)
        out.close()

    @staticmethod
    def split_pdf(path, out_dir, progress=None):
        doc = fitz.open(path)
        stem = os.path.splitext(os.path.basename(path))[0]
        files = []
        for i in range(len(doc)):
            single = fitz.open()
            single.insert_pdf(doc, from_page=i, to_page=i)
            out_path = os.path.join(out_dir, f"{stem}_p{i + 1}.pdf")
            single.save(out_path)
            single.close()
            files.append(out_path)
            if progress:
                progress(i + 1, len(doc))
        doc.close()
        return files

    @staticmethod
    def extract_pages(path, start, end, out_path):
        doc = fitz.open(path)
        n = len(doc)
        start = max(0, min(start, n - 1))
        end = max(start, min(end, n - 1))
        out = fitz.open()
        out.insert_pdf(doc, from_page=start, to_page=end)
        out.save(out_path)
        out.close()
        doc.close()

    @staticmethod
    def rotate_pages(path, angle, out_path, pages=None):
        doc = fitz.open(path)
        idxs = pages if pages is not None else range(len(doc))
        for i in idxs:
            p = doc[i]
            p.set_rotation((p.rotation + angle) % 360)
        doc.save(out_path)
        doc.close()

    @staticmethod
    def add_watermark(path, text, out_path, size=46, color="#808080"):
        doc = fitz.open(path)
        col = hexrgb(color)
        for page in doc:
            r = page.rect
            cx, cy = r.width / 2, r.height / 2
            shape = page.new_shape()
            pos = fitz.Point(cx - size * len(text) * 0.28, cy)
            mat = fitz.Matrix(45)
            try:
                shape.insert_text(pos, text, fontsize=size, color=col,
                                   morph=(pos, mat), fontname="helv")
            except Exception:
                shape.insert_text(fitz.Point(cx - size * len(text) * 0.28, cy),
                                   text, fontsize=size, color=col)
            shape.commit(overlay=True)
        doc.save(out_path)
        doc.close()

    @staticmethod
    def set_password(path, user_pw, owner_pw, out_path):
        doc = fitz.open(path)
        doc.save(out_path, encryption=fitz.PDF_ENCRYPT_AES_256,
                  user_pw=user_pw, owner_pw=owner_pw or user_pw)
        doc.close()

    @staticmethod
    def remove_password(path, pw, out_path):
        doc = fitz.open(path)
        if doc.needs_pass:
            doc.authenticate(pw)
        doc.save(out_path, encryption=fitz.PDF_ENCRYPT_NONE)
        doc.close()


# ════════════════════════════════════════════════════════════════════════
#  Small modal dialog helper — Apple styled Toplevel
# ════════════════════════════════════════════════════════════════════════
class StudioDialog(tk.Toplevel):
    def __init__(self, app, title, width=440, height=260):
        super().__init__(app)
        self.app = app
        t = app.theme
        self.configure(bg=t["panel"])
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.resizable(False, False)
        self.transient(app)
        self.update_idletasks()
        try:
            self.grab_set()
        except tk.TclError:
            self.after(50, self._safe_grab)
        header = tk.Frame(self, bg=t["panel"])
        header.pack(fill="x", padx=20, pady=(18, 6))
        tk.Label(header, text=title, bg=t["panel"], fg=t["text"],
                  font=(FONT_UI[0], 15, "bold")).pack(anchor="w")
        self.body = tk.Frame(self, bg=t["panel"])
        self.body.pack(fill="both", expand=True, padx=20, pady=6)
        self.footer = tk.Frame(self, bg=t["panel"])
        self.footer.pack(fill="x", padx=20, pady=16)

    def _safe_grab(self):
        if self.winfo_exists():
            try:
                self.grab_set()
            except tk.TclError:
                pass

    def add_buttons(self, ok_text, on_ok, cancel_text="Cancel"):
        t = self.app.theme
        RoundButton(self.footer, t, text=cancel_text, command=self.destroy,
                    width=100).pack(side="right", padx=(8, 0))
        RoundButton(self.footer, t, text=ok_text, kind="accent",
                    command=on_ok, width=140).pack(side="right")

    def labeled_entry(self, label, default=""):
        t = self.app.theme
        tk.Label(self.body, text=label, bg=t["panel"], fg=t["subtext"],
                  font=(FONT_UI[0], 11)).pack(anchor="w", pady=(6, 2))
        var = tk.StringVar(value=default)
        e = tk.Entry(self.body, textvariable=var, font=(FONT_UI[0], 12),
                      bg=t["bg"], fg=t["text"], relief="flat", insertbackground=t["text"])
        e.pack(fill="x", ipady=6)
        return var


# ════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ════════════════════════════════════════════════════════════════════════
class AppleStudio(tk.Tk):
    TOOLS = [
        ("select", "⬚", "Select / move / resize (V)"), ("pen", "✎", "Pen"),
        ("highlighter", "🖊", "Highlighter"), ("line", "╱", "Line"),
        ("arrow", "➤", "Arrow"), ("rect", "▭", "Rectangle"),
        ("ellipse", "◯", "Ellipse"), ("balloon", "💬", "Balloon callout"),
        ("text", "T", "Text"),
        ("edittext", "Aa", "Edit existing PDF text — click a line of text to change it"),
        ("eraser", "␡", "Eraser"),
    ]
    COLORS = ["#FF3B30", "#FF9500", "#FFCC00", "#34C759", "#007AFF",
              "#5856D6", "#AF52DE", "#1D1D1F", "#FFFFFF"]
    HANDLE_R = 6

    def __init__(self):
        super().__init__()
        self.title("ApEx PdF")
        self.geometry("1380x870")
        self.minsize(1040, 640)
        self.dark = False
        self.theme = LIGHT
        self.configure(bg=self.theme["bg"])

        # document state
        self.doc = None
        self.doc_path = None
        self.page_index = 0
        self.zoom = 1.6
        self.annotations = {}
        self.undo_stack = []
        self.redo_stack = []
        self.recent_files = []

        # drawing state
        self.current_tool = "select"
        self.draw_color = "#FF3B30"
        self.stroke_width = 3.0
        self.fill_shapes = False
        self.opacity = 1.0
        self.dashed = False
        self.text_fontsize = 14.0
        self.tk_page_image = None
        self.thumb_images = []
        self._drag_start = None
        self._live_stroke_points = []
        self._temp_canvas_ids = []
        self._balloon_anchor = None

        # selection state
        self.selected_ann = None
        self._drag_mode = None            # None | 'move' | 'resize'
        self._resize_index = None
        self._orig_points = None

        # search state
        self._search_hits = []
        self._search_hit_index = -1

        self._build_menu()
        self._build_layout()
        self._bind_shortcuts()
        self._refresh_tool_highlight()

    # ─────────────────────────────────────────── layout
    def _build_layout(self):
        t = self.theme
        self.toolbar = tk.Frame(self, bg=t["toolbar"], height=56)
        self.toolbar.pack(side="top", fill="x")
        self.toolbar.pack_propagate(False)
        self._build_toolbar()
        self.toolbar_shadow = tk.Frame(self, bg=t["border"], height=1)
        self.toolbar_shadow.pack(side="top", fill="x")

        mid = tk.Frame(self, bg=t["bg"])
        mid.pack(side="top", fill="both", expand=True)

        self.sidebar = tk.Frame(mid, bg=t["sidebar"], width=170)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        tk.Label(self.sidebar, text="PAGES", bg=t["sidebar"], fg=t["subtext"],
                  font=(FONT_UI[0], 10, "bold")).pack(anchor="w", padx=14, pady=(14, 4))
        self.thumb_canvas = tk.Canvas(self.sidebar, bg=t["sidebar"], highlightthickness=0)
        self.thumb_scroll = ttk.Scrollbar(self.sidebar, orient="vertical", command=self.thumb_canvas.yview)
        self.thumb_frame = tk.Frame(self.thumb_canvas, bg=t["sidebar"])
        self.thumb_frame.bind("<Configure>", lambda e: self.thumb_canvas.configure(
            scrollregion=self.thumb_canvas.bbox("all")))
        self.thumb_canvas.create_window((0, 0), window=self.thumb_frame, anchor="nw")
        self.thumb_canvas.configure(yscrollcommand=self.thumb_scroll.set)
        self.thumb_canvas.pack(side="left", fill="both", expand=True, padx=(6, 0))
        self.thumb_scroll.pack(side="right", fill="y")
        self.thumb_canvas.bind("<MouseWheel>", self._on_thumb_mousewheel)
        self.thumb_canvas.bind("<Button-4>", self._on_thumb_mousewheel)
        self.thumb_canvas.bind("<Button-5>", self._on_thumb_mousewheel)

        center = tk.Frame(mid, bg=t["canvas_bg"])
        center.pack(side="left", fill="both", expand=True)
        self.hbar = ttk.Scrollbar(center, orient="horizontal")
        self.vbar = ttk.Scrollbar(center, orient="vertical")
        self.page_canvas = tk.Canvas(center, bg=t["canvas_bg"], highlightthickness=0,
                                      xscrollcommand=self.hbar.set, yscrollcommand=self.vbar.set,
                                      cursor="arrow")
        self.hbar.config(command=self.page_canvas.xview)
        self.vbar.config(command=self.page_canvas.yview)
        self.vbar.pack(side="right", fill="y")
        self.hbar.pack(side="bottom", fill="x")
        self.page_canvas.pack(side="left", fill="both", expand=True)
        self.page_canvas.bind("<ButtonPress-1>", self._on_down)
        self.page_canvas.bind("<B1-Motion>", self._on_drag)
        self.page_canvas.bind("<ButtonRelease-1>", self._on_up)
        self.page_canvas.bind("<Motion>", self._on_motion)
        self.page_canvas.bind("<Double-Button-1>", self._on_double_click)
        self.page_canvas.bind("<Delete>", self._delete_selected)
        self.page_canvas.bind("<BackSpace>", self._delete_selected)
        self.page_canvas.bind("<Escape>", lambda e: self._deselect())

        # ── Full mouse-wheel PDF navigation ────────────────────────────
        # Plain wheel  : scroll the page vertically; hitting the top/bottom
        #                edge rolls straight into the previous/next page,
        #                like a real PDF viewer's continuous scroll.
        # Shift+wheel  : scroll horizontally (for zoomed-in / wide pages).
        # Ctrl+wheel   : zoom in/out, centered under the cursor.
        # Trackpads and Linux (Button-4/5) are supported too.
        self.page_canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.page_canvas.bind("<Shift-MouseWheel>", self._on_mousewheel_shift)
        self.page_canvas.bind("<Control-MouseWheel>", self._on_mousewheel_zoom)
        self.page_canvas.bind("<Button-4>", self._on_mousewheel)      # Linux scroll up
        self.page_canvas.bind("<Button-5>", self._on_mousewheel)      # Linux scroll down
        self.page_canvas.bind("<Shift-Button-4>", self._on_mousewheel_shift)
        self.page_canvas.bind("<Shift-Button-5>", self._on_mousewheel_shift)
        self.page_canvas.bind("<Control-Button-4>", self._on_mousewheel_zoom)
        self.page_canvas.bind("<Control-Button-5>", self._on_mousewheel_zoom)

        self.right_panel = tk.Frame(mid, bg=t["panel"], width=220)
        self.right_panel.pack(side="right", fill="y")
        self.right_panel.pack_propagate(False)
        self._build_right_panel()

        self.status = tk.Frame(self, bg=t["toolbar"], height=30)
        self.status.pack(side="bottom", fill="x")
        self.status.pack_propagate(False)
        self.status_label = tk.Label(self.status, text="Open a PDF to begin — File ▸ Open",
                                       bg=t["toolbar"], fg=t["subtext"], font=(FONT_UI[0], 10))
        self.status_label.pack(side="left", padx=12)
        self.coord_label = tk.Label(self.status, text="", bg=t["toolbar"], fg=t["subtext"],
                                      font=(FONT_UI[0], 10))
        self.coord_label.pack(side="right", padx=12)
        self.zoom_label = tk.Label(self.status, text="", bg=t["toolbar"], fg=t["subtext"],
                                     font=(FONT_UI[0], 10))
        self.zoom_label.pack(side="right", padx=12)

    def _build_toolbar(self):
        for w in self.toolbar.winfo_children():
            w.destroy()
        t = self.theme
        left = tk.Frame(self.toolbar, bg=t["toolbar"])
        left.pack(side="left", padx=12, pady=10)
        RoundButton(left, t, icon="📂", text="Open", command=self.open_pdf, width=100,
                    tooltip="Open a PDF (Ctrl+O)").pack(side="left", padx=3)
        RoundButton(left, t, icon="💾", text="Save", command=self.save_pdf, width=100,
                    tooltip="Save annotated PDF (Ctrl+S)").pack(side="left", padx=3)
        RoundButton(left, t, icon="↩", text="", command=self.undo, width=42,
                    tooltip="Undo (Ctrl+Z)").pack(side="left", padx=3)
        RoundButton(left, t, icon="↪", text="", command=self.redo, width=42,
                    tooltip="Redo (Ctrl+Y)").pack(side="left", padx=3)

        mid = tk.Frame(self.toolbar, bg=t["toolbar"])
        mid.pack(side="left", padx=16)
        self.tool_buttons = {}
        for tid, icon, tip in self.TOOLS:
            b = ToolIconButton(mid, t, icon, tid, command=lambda x=tid: self.set_tool(x), tooltip=tip)
            b.pack(side="left", padx=2)
            self.tool_buttons[tid] = b

        right = tk.Frame(self.toolbar, bg=t["toolbar"])
        right.pack(side="right", padx=12)
        RoundButton(right, t, icon="🌙" if not self.dark else "☀", text="",
                    command=self.toggle_theme, width=42,
                    tooltip="Toggle light / dark").pack(side="left", padx=3)
        RoundButton(right, t, icon="⌘K", text="", command=self.open_command_palette, width=44,
                    tooltip="Command Palette (Ctrl+K)").pack(side="left", padx=3)
        RoundButton(right, t, icon="🔍", text="", command=self.open_find, width=42,
                    tooltip="Find in document (Ctrl+F)").pack(side="left", padx=3)
        RoundButton(right, t, icon="🧰", text="Tools", command=self.open_tools_menu, width=100,
                    tooltip="PDF tools & convert").pack(side="left", padx=3)

        nav = tk.Frame(self.toolbar, bg=t["toolbar"])
        nav.pack(side="right", padx=8)
        RoundButton(nav, t, icon="⤢", text="Fit", command=self.zoom_fit_width, width=54,
                    tooltip="Fit width").pack(side="left", padx=2)
        RoundButton(nav, t, icon="⛶", text="Page", command=self.zoom_fit_page, width=60,
                    tooltip="Fit whole page").pack(side="left", padx=2)
        RoundButton(nav, t, icon="1:1", text="", command=self.zoom_actual, width=44,
                    tooltip="Actual size (100%)").pack(side="left", padx=2)
        RoundButton(nav, t, icon="－", text="", command=self.zoom_out, width=36).pack(side="left", padx=2)
        RoundButton(nav, t, icon="＋", text="", command=self.zoom_in, width=36).pack(side="left", padx=2)
        RoundButton(nav, t, icon="◀", text="", command=self.prev_page, width=36).pack(side="left", padx=2)
        RoundButton(nav, t, icon="▶", text="", command=self.next_page, width=36).pack(side="left", padx=2)

    def _build_right_panel(self):
        for w in self.right_panel.winfo_children():
            w.destroy()
        t = self.theme
        p = self.right_panel
        tk.Label(p, text="COLOR", bg=t["panel"], fg=t["subtext"],
                  font=(FONT_UI[0], 10, "bold")).pack(anchor="w", padx=16, pady=(18, 6))
        grid = tk.Frame(p, bg=t["panel"])
        grid.pack(padx=16, anchor="w")
        for i, c in enumerate(self.COLORS):
            sw = tk.Canvas(grid, width=26, height=26, bg=t["panel"], highlightthickness=0, cursor="hand2")
            border = t["accent"] if c == self.draw_color else t["border"]
            sw.create_oval(3, 3, 23, 23, fill=c, outline=border, width=2)
            sw.bind("<Button-1>", lambda e, col=c: self._pick_color(col))
            sw.grid(row=i // 5, column=i % 5, padx=3, pady=3)
        RoundButton(p, t, text="Custom…", command=self._pick_custom_color, width=180, height=28
                    ).pack(padx=16, pady=(8, 0))

        tk.Label(p, text="STROKE WIDTH", bg=t["panel"], fg=t["subtext"],
                  font=(FONT_UI[0], 10, "bold")).pack(anchor="w", padx=16, pady=(18, 6))
        self.width_var = tk.DoubleVar(value=self.stroke_width)
        ttk.Scale(p, from_=1, to=16, variable=self.width_var, orient="horizontal",
                  command=lambda v: self._set_width(float(v))).pack(padx=16, fill="x")

        tk.Label(p, text="OPACITY", bg=t["panel"], fg=t["subtext"],
                  font=(FONT_UI[0], 10, "bold")).pack(anchor="w", padx=16, pady=(18, 6))
        self.opacity_var = tk.DoubleVar(value=self.opacity)
        ttk.Scale(p, from_=0.1, to=1.0, variable=self.opacity_var, orient="horizontal",
                  command=lambda v: self._set_opacity(float(v))).pack(padx=16, fill="x")

        tk.Label(p, text="TEXT / BALLOON SIZE", bg=t["panel"], fg=t["subtext"],
                  font=(FONT_UI[0], 10, "bold")).pack(anchor="w", padx=16, pady=(18, 6))
        self.fontsize_var = tk.DoubleVar(value=self.text_fontsize)
        ttk.Scale(p, from_=8, to=40, variable=self.fontsize_var, orient="horizontal",
                  command=lambda v: self._set_fontsize(float(v))).pack(padx=16, fill="x")

        self.fill_var = tk.BooleanVar(value=self.fill_shapes)
        tk.Checkbutton(p, text="Fill shapes", variable=self.fill_var, command=self._toggle_fill,
                         bg=t["panel"], fg=t["text"], selectcolor=t["panel"],
                         activebackground=t["panel"], font=(FONT_UI[0], 11)
                         ).pack(anchor="w", padx=14, pady=(14, 0))

        self.dash_var = tk.BooleanVar(value=self.dashed)
        tk.Checkbutton(p, text="Dashed stroke", variable=self.dash_var, command=self._toggle_dash,
                         bg=t["panel"], fg=t["text"], selectcolor=t["panel"],
                         activebackground=t["panel"], font=(FONT_UI[0], 11)
                         ).pack(anchor="w", padx=14, pady=(4, 0))

        tk.Label(p, text="PAGE", bg=t["panel"], fg=t["subtext"],
                  font=(FONT_UI[0], 10, "bold")).pack(anchor="w", padx=16, pady=(22, 6))
        self.page_info_label = tk.Label(p, text="—", bg=t["panel"], fg=t["text"], font=(FONT_UI[0], 12))
        self.page_info_label.pack(anchor="w", padx=16)

        tk.Label(p, text="CURRENT TOOL", bg=t["panel"], fg=t["subtext"],
                  font=(FONT_UI[0], 10, "bold")).pack(anchor="w", padx=16, pady=(18, 6))
        self.tool_info_label = tk.Label(p, text="Select", bg=t["panel"], fg=t["accent"],
                                          font=(FONT_UI[0], 13, "bold"))
        self.tool_info_label.pack(anchor="w", padx=16)

        self.selection_frame = tk.Frame(p, bg=t["panel"])
        self.selection_frame.pack(fill="x", padx=16, pady=(18, 0))
        self._update_selection_panel()

    def _build_menu(self):
        m = tk.Menu(self)
        self.config(menu=m)
        filem = tk.Menu(m, tearoff=0)
        filem.add_command(label="Open PDF…              Ctrl+O", command=self.open_pdf)
        self.recent_menu = tk.Menu(filem, tearoff=0, postcommand=self._rebuild_recent_menu)
        filem.add_cascade(label="Open Recent", menu=self.recent_menu)
        filem.add_command(label="Save Annotated PDF As…  Ctrl+S", command=self.save_pdf)
        filem.add_separator()
        filem.add_command(label="Document Properties…", command=self.dlg_doc_properties)
        filem.add_command(label="Open in System Viewer / Print…", command=self.open_in_system_viewer)
        filem.add_command(label="Add to Windows 'Open With' Menu…", command=self.register_windows_pdf_app)
        filem.add_separator()
        filem.add_command(label="Export Current Page as Image…", command=self.export_current_page_image)
        filem.add_command(label="Export All Pages as Images…", command=self.export_all_pages_images)
        filem.add_command(label="Export as Text…", command=self.export_text)
        filem.add_separator()
        filem.add_command(label="Quit", command=self.quit)
        m.add_cascade(label="File", menu=filem)

        editm = tk.Menu(m, tearoff=0)
        editm.add_command(label="Undo               Ctrl+Z", command=self.undo)
        editm.add_command(label="Redo               Ctrl+Y", command=self.redo)
        editm.add_command(label="Duplicate Selection  Ctrl+D", command=self._duplicate_selected)
        editm.add_command(label="Delete Selection     Del", command=self._delete_selected)
        editm.add_command(label="Clear Page Annotations", command=self.clear_page_annotations)
        editm.add_separator()
        editm.add_command(label="Find in Document…   Ctrl+F", command=self.open_find)
        editm.add_command(label="Command Palette…    Ctrl+K", command=self.open_command_palette)
        m.add_cascade(label="Edit", menu=editm)

        convm = tk.Menu(m, tearoff=0)
        convm.add_command(label="Images → PDF…", command=self.dlg_images_to_pdf)
        convm.add_command(label="Convert Image Format…", command=self.dlg_convert_image)
        m.add_cascade(label="Convert", menu=convm)

        toolm = tk.Menu(m, tearoff=0)
        toolm.add_command(label="Merge PDFs…", command=self.dlg_merge)
        toolm.add_command(label="Split PDF…", command=self.dlg_split)
        toolm.add_command(label="Extract Page Range…", command=self.dlg_extract)
        toolm.add_command(label="Rotate Pages…", command=self.dlg_rotate)
        toolm.add_command(label="Add Watermark…", command=self.dlg_watermark)
        toolm.add_command(label="Add Password…", command=self.dlg_add_password)
        toolm.add_command(label="Remove Password…", command=self.dlg_remove_password)
        m.add_cascade(label="PDF Tools", menu=toolm)

        pagem = tk.Menu(m, tearoff=0)
        pagem.add_command(label="Rotate Current Page 90°", command=lambda: self.page_rotate(self.page_index, 90))
        pagem.add_command(label="Duplicate Current Page", command=lambda: self.page_duplicate(self.page_index))
        pagem.add_command(label="Insert Blank Page After", command=lambda: self.page_insert_blank(self.page_index))
        pagem.add_command(label="Delete Current Page", command=lambda: self.page_delete(self.page_index))
        pagem.add_separator()
        pagem.add_command(label="Move Page Up", command=lambda: self.page_move(self.page_index, -1))
        pagem.add_command(label="Move Page Down", command=lambda: self.page_move(self.page_index, 1))
        m.add_cascade(label="Page", menu=pagem)

        viewm = tk.Menu(m, tearoff=0)
        viewm.add_command(label="Zoom In           Ctrl++", command=self.zoom_in)
        viewm.add_command(label="Zoom Out          Ctrl+-", command=self.zoom_out)
        viewm.add_command(label="Fit Width", command=self.zoom_fit_width)
        viewm.add_command(label="Fit Page", command=self.zoom_fit_page)
        viewm.add_command(label="Actual Size (100%)", command=self.zoom_actual)
        viewm.add_separator()
        viewm.add_command(label="Next Page         PgDn / Scroll Down", command=self.next_page)
        viewm.add_command(label="Previous Page     PgUp / Scroll Up", command=self.prev_page)
        viewm.add_command(label="First Page        Home", command=lambda: self.go_to_page(0))
        viewm.add_command(label="Last Page         End", command=lambda: self.go_to_page(len(self.doc) - 1) if self.doc else None)
        viewm.add_separator()
        viewm.add_command(label="Toggle Dark Mode", command=self.toggle_theme)
        m.add_cascade(label="View", menu=viewm)

        helpm = tk.Menu(m, tearoff=0)
        helpm.add_command(label="Keyboard Shortcuts", command=self._show_shortcuts)
        m.add_cascade(label="Help", menu=helpm)

    def _bind_shortcuts(self):
        self.bind("<Control-o>", lambda e: self.open_pdf())
        self.bind("<Control-s>", lambda e: self.save_pdf())
        self.bind("<Control-z>", lambda e: self.undo())
        self.bind("<Control-y>", lambda e: self.redo())
        self.bind("<Control-d>", lambda e: self._duplicate_selected())
        self.bind("<Control-plus>", lambda e: self.zoom_in())
        self.bind("<Control-minus>", lambda e: self.zoom_out())
        self.bind("<Control-0>", lambda e: self.zoom_actual())
        self.bind("<Control-k>", lambda e: self.open_command_palette())
        self.bind("<Control-f>", lambda e: self.open_find())
        self.bind("<Left>", lambda e: self.prev_page())
        self.bind("<Right>", lambda e: self.next_page())
        self.bind("<Prior>", lambda e: self.prev_page())   # Page Up
        self.bind("<Next>", lambda e: self.next_page())    # Page Down
        self.bind("<Home>", lambda e: self.go_to_page(0))
        self.bind("<End>", lambda e: self.go_to_page(len(self.doc) - 1) if self.doc else None)
        self.bind("v", lambda e: self.set_tool("select"))

    def _show_shortcuts(self):
        text = (
            "Ctrl+O  Open PDF\nCtrl+S  Save annotated PDF\n"
            "Ctrl+Z / Ctrl+Y  Undo / Redo\nCtrl+D  Duplicate selection\n"
            "Delete / Backspace  Delete selection\nV  Select tool\n"
            "Ctrl + / Ctrl -  Zoom in / out\nCtrl+0  Actual size\n"
            "Ctrl+K  Command palette\nCtrl+F  Find in document\n"
            "← / → , Page Up / Page Down  Previous / next page\n"
            "Home / End  First / last page\n"
            "Double-click text or balloon  Edit its text\n"
            "Right-click a thumbnail  Page menu (rotate/duplicate/delete/insert/move)\n\n"
            "MOUSE — full scroll & zoom support:\n"
            "Scroll wheel  Scroll the page up/down; scrolling past the\n"
            "   top/bottom edge moves you straight to the previous/next page\n"
            "Shift + Scroll  Scroll left/right\n"
            "Ctrl + Scroll  Zoom in/out, centered on the cursor\n"
            "Scroll over the page list  Scroll through thumbnails"
        )
        messagebox.showinfo("Keyboard Shortcuts", text)

    # ─────────────────────────────────────────── theme
    def toggle_theme(self):
        self.dark = not self.dark
        self.theme = DARK if self.dark else LIGHT
        t = self.theme
        self.configure(bg=t["bg"])
        self.toolbar.configure(bg=t["toolbar"])
        self.toolbar_shadow.configure(bg=t["border"])
        self.sidebar.configure(bg=t["sidebar"])
        self.thumb_canvas.configure(bg=t["sidebar"])
        self.thumb_frame.configure(bg=t["sidebar"])
        self.page_canvas.configure(bg=t["canvas_bg"])
        self.right_panel.configure(bg=t["panel"])
        self.status.configure(bg=t["toolbar"])
        self.status_label.configure(bg=t["toolbar"], fg=t["subtext"])
        self.coord_label.configure(bg=t["toolbar"], fg=t["subtext"])
        self.zoom_label.configure(bg=t["toolbar"], fg=t["subtext"])
        self._build_toolbar()
        self._build_right_panel()
        self._refresh_tool_highlight()
        if self.doc:
            self._render_thumbnails()
            self._render_current_page()

    # ─────────────────────────────────────────── document
    def open_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if path:
            self._open_path(path)

    def _open_path(self, path):
        try:
            self.doc = fitz.open(path)
            self.doc_path = path
            self.page_index = 0
            self.annotations = {}
            self.undo_stack.clear()
            self.redo_stack.clear()
            self.selected_ann = None
            self.zoom = 1.6
            n = len(self.doc)
            dlg = ProgressDialog(self, title="Opening PDF…", determinate=True) if n > 3 else None
            self._render_current_page()
            self._render_thumbnails(progress_dialog=dlg)
            if dlg:
                dlg.close()
            if path in self.recent_files:
                self.recent_files.remove(path)
            self.recent_files.insert(0, path)
            self.recent_files = self.recent_files[:6]
            self._set_status(f"Opened {os.path.basename(path)} · {n} pages")
        except Exception as e:
            messagebox.showerror("Open failed", str(e))

    def _rebuild_recent_menu(self):
        self.recent_menu.delete(0, "end")
        if not self.recent_files:
            self.recent_menu.add_command(label="(empty)", state="disabled")
            return
        for p in self.recent_files:
            self.recent_menu.add_command(label=os.path.basename(p), command=lambda pp=p: self._open_path(pp))

    def save_pdf(self):
        if not self.doc:
            messagebox.showinfo("No document", "Open a PDF first.")
            return
        out = filedialog.asksaveasfilename(defaultextension=".pdf",
                                            filetypes=[("PDF files", "*.pdf")],
                                            initialfile="annotated.pdf")
        if not out:
            return
        try:
            PDFEngine.flatten(self.doc, self.annotations, out)
            self._set_status(f"Saved → {out}")
            messagebox.showinfo("Saved", f"Annotated PDF saved:\n{out}")
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Save failed", str(e))

    def open_in_system_viewer(self):
        if not self.doc_path:
            messagebox.showinfo("No document", "Open a PDF first.")
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(self.doc_path)  # noqa
            elif sys.platform == "darwin":
                subprocess.Popen(["open", self.doc_path])
            else:
                subprocess.Popen(["xdg-open", self.doc_path])
        except Exception as e:
            messagebox.showerror("Couldn't open", str(e))

    def register_windows_pdf_app(self):
        """Register ApEx PdF with Windows so it shows up in Explorer's
        right-click 'Open with' list for .pdf files (and can be picked as the
        default). Only touches HKEY_CURRENT_USER, so no admin rights needed,
        and it never forces itself as the default — the user still confirms
        that choice in Explorer."""
        if not sys.platform.startswith("win"):
            messagebox.showinfo(
                "Windows only",
                "This adds ApEx PdF to Explorer's 'Open with' menu, which only "
                "applies on Windows. On macOS/Linux, use your file manager's "
                "'Open with' / 'set default application' option and point it at "
                "this script instead."
            )
            return
        try:
            import winreg
        except Exception as ex:
            messagebox.showerror("Unavailable", f"winreg module not available: {ex}")
            return
        try:
            py = sys.executable
            pyw_candidate = os.path.join(os.path.dirname(py), "pythonw.exe")
            if os.path.isfile(pyw_candidate):
                py = pyw_candidate
            script = os.path.abspath(__file__)
            app_id = "ApExPdF.Document"
            command = f'"{py}" "{script}" "%1"'

            # Application entry -> shows up under "Open with -> More apps"
            key = winreg.CreateKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Classes\Applications\ApExPdF.exe\shell\open\command")
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)
            winreg.CloseKey(key)
            key = winreg.CreateKey(
                winreg.HKEY_CURRENT_USER, r"Software\Classes\Applications\ApExPdF.exe")
            winreg.SetValueEx(key, "FriendlyAppName", 0, winreg.REG_SZ, "ApEx PdF")
            winreg.CloseKey(key)

            # ProgID Windows can associate with .pdf
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{app_id}")
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "ApEx PdF Document")
            winreg.CloseKey(key)
            key = winreg.CreateKey(
                winreg.HKEY_CURRENT_USER, rf"Software\Classes\{app_id}\shell\open\command")
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)
            winreg.CloseKey(key)

            # Let Explorer know .pdf can be opened with this ProgID
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\.pdf\OpenWithProgids")
            winreg.SetValueEx(key, app_id, 0, winreg.REG_NONE, b"")
            winreg.CloseKey(key)

            messagebox.showinfo(
                "Added to Windows",
                "ApEx PdF is now registered.\n\n"
                "Right-click any PDF → Open with → More apps, and pick "
                "\"ApEx PdF\" (check \"Always use this app\" if you want it as "
                "your default PDF viewer)."
            )
        except Exception as ex:
            messagebox.showerror(
                "Registration failed", f"{ex}\n\nTry running this app as your normal "
                "user (not elevated) — HKEY_CURRENT_USER doesn't need admin rights.")

    def dlg_doc_properties(self):
        if not self.doc:
            messagebox.showinfo("No document", "Open a PDF first.")
            return
        md = self.doc.metadata or {}
        d = StudioDialog(self, "Document Properties", height=340)
        title_v = d.labeled_entry("Title", md.get("title", "") or "")
        author_v = d.labeled_entry("Author", md.get("author", "") or "")
        subject_v = d.labeled_entry("Subject", md.get("subject", "") or "")
        kw_v = d.labeled_entry("Keywords", md.get("keywords", "") or "")

        def go():
            new_md = dict(md)
            new_md.update(title=title_v.get(), author=author_v.get(),
                           subject=subject_v.get(), keywords=kw_v.get())
            self.doc.set_metadata(new_md)
            out = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile="metadata.pdf")
            if out:
                try:
                    self.doc.save(out, garbage=4, deflate=True)
                    messagebox.showinfo("Saved", f"Metadata saved to:\n{out}")
                except Exception as ex:
                    messagebox.showerror("Failed", str(ex))
            d.destroy()
        d.add_buttons("Save As…", go)

    def _render_thumbnails(self, progress_dialog=None):
        for w in self.thumb_frame.winfo_children():
            w.destroy()
        self.thumb_images = []
        if not self.doc:
            return
        t = self.theme
        n = len(self.doc)
        for i in range(n):
            img = PDFEngine.render_page(self.doc, i, 0.22)
            tkimg = ImageTk.PhotoImage(img)
            self.thumb_images.append(tkimg)
            cell = tk.Frame(self.thumb_frame, bg=t["sidebar"])
            cell.pack(pady=6, padx=10, fill="x")
            bd = t["accent"] if i == self.page_index else t["sidebar"]
            lbl = tk.Label(cell, image=tkimg, bg=t["sidebar"], bd=2, relief="solid",
                            highlightbackground=bd)
            lbl.pack()
            tk.Label(cell, text=f"{i + 1}", bg=t["sidebar"], fg=t["subtext"],
                      font=(FONT_UI[0], 9)).pack()
            lbl.bind("<Button-1>", lambda e, idx=i: self.go_to_page(idx))
            lbl.bind("<Button-3>", lambda e, idx=i: self._thumb_context_menu(e, idx))
            if progress_dialog:
                progress_dialog.set_progress(i + 1, n, f"Rendering thumbnail {i + 1}/{n}")

    def _thumb_context_menu(self, event, idx):
        self.go_to_page(idx)
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label=f"Page {idx + 1}", state="disabled")
        menu.add_separator()
        menu.add_command(label="Rotate 90°", command=lambda: self.page_rotate(idx, 90))
        menu.add_command(label="Duplicate", command=lambda: self.page_duplicate(idx))
        menu.add_command(label="Insert Blank After", command=lambda: self.page_insert_blank(idx))
        menu.add_command(label="Delete", command=lambda: self.page_delete(idx))
        menu.add_separator()
        menu.add_command(label="Move Up", command=lambda: self.page_move(idx, -1))
        menu.add_command(label="Move Down", command=lambda: self.page_move(idx, 1))
        menu.tk_popup(event.x_root, event.y_root)

    # ── structural page ops: keep self.annotations dict in sync with index shifts
    def _remap_annotations(self, mapping):
        """mapping: old_index -> new_index or None (dropped)."""
        new_ann = {}
        for old_idx, items in self.annotations.items():
            new_idx = mapping.get(old_idx, old_idx)
            if new_idx is None:
                continue
            new_ann.setdefault(new_idx, []).extend(items)
        self.annotations = new_ann

    def page_rotate(self, idx, angle):
        if not self.doc or not (0 <= idx < len(self.doc)):
            return
        p = self.doc[idx]
        p.set_rotation((p.rotation + angle) % 360)
        self._render_current_page()
        self._render_thumbnails()
        self._set_status(f"Rotated page {idx + 1}")

    def page_duplicate(self, idx):
        if not self.doc or not (0 <= idx < len(self.doc)):
            return
        self.doc.copy_page(idx, idx + 1)
        mapping = {i: (i if i <= idx else i + 1) for i in self.annotations}
        self._remap_annotations(mapping)
        self.go_to_page(idx + 1)
        self._set_status(f"Duplicated page {idx + 1}")

    def page_insert_blank(self, idx):
        if not self.doc:
            return
        rect = self.doc[idx].rect if 0 <= idx < len(self.doc) else fitz.paper_rect("a4")
        self.doc.new_page(pno=idx + 1, width=rect.width, height=rect.height)
        mapping = {i: (i if i <= idx else i + 1) for i in self.annotations}
        self._remap_annotations(mapping)
        self.go_to_page(idx + 1)
        self._set_status(f"Inserted blank page after {idx + 1}")

    def page_delete(self, idx):
        if not self.doc or len(self.doc) <= 1 or not (0 <= idx < len(self.doc)):
            messagebox.showinfo("Can't delete", "Document needs at least one page.")
            return
        if not messagebox.askyesno("Delete page", f"Delete page {idx + 1}? This can't be undone."):
            return
        self.doc.delete_page(idx)
        mapping = {}
        for i in self.annotations:
            if i == idx:
                mapping[i] = None
            elif i > idx:
                mapping[i] = i - 1
            else:
                mapping[i] = i
        self._remap_annotations(mapping)
        self.page_index = min(idx, len(self.doc) - 1)
        self._render_current_page()
        self._render_thumbnails()
        self._set_status(f"Deleted page {idx + 1}")

    def page_move(self, idx, direction):
        if not self.doc:
            return
        new_idx = idx + direction
        if not (0 <= new_idx < len(self.doc)):
            return
        self.doc.move_page(idx, new_idx)
        mapping = {}
        for i in self.annotations:
            if i == idx:
                mapping[i] = new_idx
            elif idx < i <= new_idx:
                mapping[i] = i - 1
            elif new_idx <= i < idx:
                mapping[i] = i + 1
            else:
                mapping[i] = i
        self._remap_annotations(mapping)
        self.go_to_page(new_idx)
        self._set_status(f"Moved page to {new_idx + 1}")

    def go_to_page(self, idx, scroll_to=None):
        """scroll_to: None keeps default (top), 'top' or 'bottom' places the
        view at that edge — used so wheel-scrolling off one page continues
        smoothly onto the next/previous page instead of jumping."""
        if not self.doc or not (0 <= idx < len(self.doc)):
            return
        self.selected_ann = None
        self.page_index = idx
        self._render_current_page()
        self._render_thumbnails()
        if scroll_to == "bottom":
            self.page_canvas.yview_moveto(1.0)
        elif scroll_to == "top":
            self.page_canvas.yview_moveto(0.0)

    def next_page(self):
        if self.doc and self.page_index < len(self.doc) - 1:
            self.go_to_page(self.page_index + 1)

    def prev_page(self):
        if self.doc and self.page_index > 0:
            self.go_to_page(self.page_index - 1)

    def zoom_in(self):
        self.zoom = min(6.0, self.zoom * 1.2)
        self._render_current_page()

    def zoom_out(self):
        self.zoom = max(0.3, self.zoom / 1.2)
        self._render_current_page()

    def zoom_actual(self):
        self.zoom = 1.0
        self._render_current_page()

    def zoom_fit_width(self):
        if not self.doc:
            return
        page = self.doc[self.page_index]
        canvas_w = self.page_canvas.winfo_width() or 900
        self.zoom = max(0.2, min(6.0, (canvas_w - 20) / page.rect.width))
        self._render_current_page()

    def zoom_fit_page(self):
        """Fit the whole page (width AND height) inside the visible canvas —
        the classic PDF-viewer 'Fit Page' option, as opposed to Fit Width."""
        if not self.doc:
            return
        page = self.doc[self.page_index]
        canvas_w = self.page_canvas.winfo_width() or 900
        canvas_h = self.page_canvas.winfo_height() or 700
        zw = (canvas_w - 24) / page.rect.width
        zh = (canvas_h - 24) / page.rect.height
        self.zoom = max(0.2, min(6.0, min(zw, zh)))
        self._render_current_page()

    def _zoom_at_point(self, factor, cpt):
        """Zoom in/out while keeping the point under the cursor fixed on
        screen, the way Ctrl+scroll zoom works in real PDF viewers."""
        if not self.doc:
            return
        old_zoom = self.zoom
        new_zoom = max(0.2, min(6.0, old_zoom * factor))
        if new_zoom == old_zoom:
            return
        c = self.page_canvas
        # PDF-space point currently under the cursor, so we can re-center on it
        pdf_pt = self._to_pdf(cpt)
        self.zoom = new_zoom
        self._render_current_page()
        new_cx, new_cy = self._to_canvas(pdf_pt)
        cw = c.winfo_width() or 1
        ch = c.winfo_height() or 1
        x0, y0, x1, y1 = c.bbox("page") or (0, 0, cw, ch)
        total_w = max(x1 - x0, 1)
        total_h = max(y1 - y0, 1)
        c.xview_moveto(max(0.0, min(1.0, (new_cx - cpt[0]) / total_w)))
        c.yview_moveto(max(0.0, min(1.0, (new_cy - cpt[1]) / total_h)))

    # ─────────────────────────────────────────── mouse-wheel navigation
    @staticmethod
    def _wheel_delta(event):
        """Normalize wheel direction across Windows/macOS (event.delta) and
        Linux (Button-4/5), returning +1 for 'scroll up/away' and -1 for
        'scroll down/towards' the user."""
        if getattr(event, "num", None) == 4:
            return -1
        if getattr(event, "num", None) == 5:
            return 1
        d = getattr(event, "delta", 0)
        if d == 0:
            return 0
        # Windows fires in multiples of 120; macOS sends small values directly.
        return -1 if d > 0 else 1

    def _on_mousewheel(self, event):
        if not self.doc:
            return
        direction = self._wheel_delta(event)
        if direction == 0:
            return
        c = self.page_canvas
        top, bottom = c.yview()
        at_top = top <= 0.0001
        at_bottom = bottom >= 0.9999
        if direction < 0 and at_top and self.page_index > 0:
            self.go_to_page(self.page_index - 1, scroll_to="bottom")
            return "break"
        if direction > 0 and at_bottom and self.page_index < (len(self.doc) - 1):
            self.go_to_page(self.page_index + 1, scroll_to="top")
            return "break"
        c.yview_scroll(direction * 3, "units")
        return "break"

    def _on_mousewheel_shift(self, event):
        if not self.doc:
            return
        direction = self._wheel_delta(event)
        if direction == 0:
            return
        self.page_canvas.xview_scroll(direction * 3, "units")
        return "break"

    def _on_mousewheel_zoom(self, event):
        if not self.doc:
            return
        direction = self._wheel_delta(event)
        if direction == 0:
            return
        cpt = self._canvas_pt(event)
        self._zoom_at_point(1.1 if direction < 0 else (1 / 1.1), cpt)
        return "break"

    def _on_thumb_mousewheel(self, event):
        direction = self._wheel_delta(event)
        if direction == 0:
            return
        self.thumb_canvas.yview_scroll(direction * 2, "units")
        return "break"

    def _render_current_page(self):
        if not self.doc:
            return
        img = PDFEngine.render_page(self.doc, self.page_index, self.zoom)
        self.tk_page_image = ImageTk.PhotoImage(img)
        self.page_canvas.delete("all")
        self.page_canvas.create_image(0, 0, anchor="nw", image=self.tk_page_image, tags="page")
        self.page_canvas.configure(scrollregion=(0, 0, img.width, img.height))
        self._redraw_overlay()
        self.page_info_label.configure(text=f"Page {self.page_index + 1} / {len(self.doc)}")
        self.zoom_label.configure(text=f"Zoom {int(self.zoom * 100)}%")

    def _redraw_overlay(self):
        """Cheap redraw: annotations + selection handles only (no PDF re-render)."""
        self.page_canvas.delete("ann")
        self.page_canvas.delete("sel")
        self.page_canvas.delete("hit")
        self._draw_annotations_for_current_page()
        if self.current_tool == "select" and self.selected_ann:
            self._draw_selection_handles()
        self._draw_search_hits()

    # ─────────────────────────────────────────── coordinate helpers
    def _canvas_pt(self, event) -> Tuple[float, float]:
        return (self.page_canvas.canvasx(event.x), self.page_canvas.canvasy(event.y))

    def _to_pdf(self, pt):
        return (pt[0] / self.zoom, pt[1] / self.zoom)

    def _to_canvas(self, pt):
        return (pt[0] * self.zoom, pt[1] * self.zoom)

    def _on_motion(self, event):
        if not self.doc:
            return
        pdf = self._to_pdf(self._canvas_pt(event))
        self.coord_label.configure(text=f"x {pdf[0]:.0f}, y {pdf[1]:.0f} pt")

    # ─────────────────────────────────────────── tools
    def set_tool(self, tool_id):
        if tool_id != "select":
            self.selected_ann = None
        self.current_tool = tool_id
        self.page_canvas.configure(cursor=CURSORS.get(tool_id, "crosshair"))
        if tool_id == "highlighter":
            self.opacity_var.set(0.35); self.opacity = 0.35
        self._refresh_tool_highlight()
        self.tool_info_label.configure(text=dict((a, c) for a, b, c in self.TOOLS)[tool_id])
        self._update_selection_panel()
        self._redraw_overlay()

    def _refresh_tool_highlight(self):
        for tid, btn in getattr(self, "tool_buttons", {}).items():
            btn.set_active(tid == self.current_tool)

    def _pick_color(self, c):
        self.draw_color = c
        if self.selected_ann:
            self.selected_ann.color = c
        self._build_right_panel()
        self._redraw_overlay()

    def _pick_custom_color(self):
        c = colorchooser.askcolor(color=self.draw_color)
        if c and c[1]:
            self.draw_color = c[1]
            if self.selected_ann:
                self.selected_ann.color = c[1]
            self._build_right_panel()
            self._redraw_overlay()

    def _set_width(self, v):
        self.stroke_width = v
        if self.selected_ann:
            self.selected_ann.width = v
            self._redraw_overlay()

    def _set_fontsize(self, v):
        """Live-edit the font size of the selected text/balloon annotation.
        Also updates the default used for the next new text/balloon added."""
        self.text_fontsize = v
        if self.selected_ann and self.selected_ann.kind in ("text", "balloon"):
            self.selected_ann.fontsize = v
            self._redraw_overlay()

    def _sync_style_vars_from_selection(self):
        """Pull the selected annotation's own color/width/opacity/fontsize into
        the editing controls, so the sliders show its real current size instead
        of stale values from whatever was drawn previously."""
        ann = self.selected_ann
        if not ann:
            return
        self.draw_color = ann.color
        self.stroke_width = ann.width
        self.opacity = ann.opacity
        self.text_fontsize = getattr(ann, "fontsize", self.text_fontsize)
        for name, val in (("width_var", ann.width), ("opacity_var", ann.opacity),
                           ("fontsize_var", getattr(ann, "fontsize", None))):
            var = getattr(self, name, None)
            if var is not None and val is not None:
                try:
                    var.set(val)
                except Exception:
                    pass

    def _set_opacity(self, v):
        self.opacity = v
        if self.selected_ann:
            self.selected_ann.opacity = v
            self._redraw_overlay()

    def _toggle_fill(self):
        self.fill_shapes = self.fill_var.get()
        if self.selected_ann and self.selected_ann.kind in ("rect", "ellipse"):
            self.selected_ann.fill = self.draw_color if self.fill_shapes else None
            self._redraw_overlay()

    def _toggle_dash(self):
        self.dashed = self.dash_var.get()
        if self.selected_ann:
            self.selected_ann.dashed = self.dashed
            self._redraw_overlay()

    # ─────────────────────────────────────────── selection geometry
    def _bbox_canvas(self, ann):
        pts = [self._to_canvas(p) for p in ann.points]
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        pad = max(8, ann.width + 4)
        return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)

    def _hit_test(self, cpt):
        items = self.annotations.get(self.page_index, [])
        for ann in reversed(items):
            x0, y0, x1, y1 = self._bbox_canvas(ann)
            if x0 <= cpt[0] <= x1 and y0 <= cpt[1] <= y1:
                return ann
        return None

    def _handle_at(self, ann, cpt):
        if len(ann.points) != 2:
            return None
        for i, p in enumerate(ann.points):
            cp = self._to_canvas(p)
            if abs(cp[0] - cpt[0]) <= self.HANDLE_R + 3 and abs(cp[1] - cpt[1]) <= self.HANDLE_R + 3:
                return i
        return None

    def _draw_selection_handles(self):
        ann = self.selected_ann
        if not ann:
            return
        c = self.page_canvas
        t = self.theme
        x0, y0, x1, y1 = self._bbox_canvas(ann)
        c.create_rectangle(x0, y0, x1, y1, outline=t["accent"], dash=(5, 3), width=1.5, tags="sel")
        if len(ann.points) == 2:
            for p in ann.points:
                cx, cy = self._to_canvas(p)
                r = self.HANDLE_R
                c.create_rectangle(cx - r, cy - r, cx + r, cy + r, fill="white",
                                     outline=t["accent"], width=1.5, tags="sel")

    def _deselect(self):
        self.selected_ann = None
        self._update_selection_panel()
        self._redraw_overlay()

    def _update_selection_panel(self):
        if not hasattr(self, "selection_frame"):
            return
        for w in self.selection_frame.winfo_children():
            w.destroy()
        t = self.theme
        if self.selected_ann:
            ann = self.selected_ann
            tk.Label(self.selection_frame, text="SELECTED: " + ann.kind.upper(),
                      bg=t["panel"], fg=t["accent"], font=(FONT_UI[0], 10, "bold")).pack(anchor="w")
            row = tk.Frame(self.selection_frame, bg=t["panel"])
            row.pack(fill="x", pady=(8, 0))
            RoundButton(row, t, icon="🗑", text="Delete", command=self._delete_selected,
                        width=96, height=28).pack(side="left", padx=(0, 6))
            RoundButton(row, t, icon="⧉", text="Duplicate", command=self._duplicate_selected,
                        width=110, height=28).pack(side="left")

            # Size control for whatever is currently selected — font size for
            # text/balloon, stroke width for every drawable shape (pen,
            # highlighter, line, arrow, rect, ellipse). Always editable right
            # here, including right after the item was just added.
            size_row = tk.Frame(self.selection_frame, bg=t["panel"])
            size_row.pack(fill="x", pady=(14, 0))
            if ann.kind in ("text", "balloon"):
                size_label_var = tk.StringVar(value=f"SIZE (FONT · {int(ann.fontsize)}pt)")
                tk.Label(size_row, textvariable=size_label_var,
                          bg=t["panel"], fg=t["subtext"], font=(FONT_UI[0], 9, "bold")).pack(anchor="w")
                sz_var = tk.DoubleVar(value=ann.fontsize)

                def _on_size(v, _var=size_label_var):
                    v = float(v)
                    self._set_fontsize(v)
                    _var.set(f"SIZE (FONT · {int(v)}pt)")
                ttk.Scale(size_row, from_=8, to=96, variable=sz_var, orient="horizontal",
                          command=_on_size).pack(fill="x", pady=(4, 0))
            else:
                size_label_var = tk.StringVar(value=f"SIZE (WIDTH · {ann.width:g}px)")
                tk.Label(size_row, textvariable=size_label_var,
                          bg=t["panel"], fg=t["subtext"], font=(FONT_UI[0], 9, "bold")).pack(anchor="w")
                sz_var = tk.DoubleVar(value=ann.width)

                def _on_size(v, _var=size_label_var):
                    v = float(v)
                    self._set_width(v)
                    _var.set(f"SIZE (WIDTH · {v:.1f}px)")
                ttk.Scale(size_row, from_=1, to=60, variable=sz_var, orient="horizontal",
                          command=_on_size).pack(fill="x", pady=(4, 0))
        else:
            tk.Label(self.selection_frame,
                      text="No selection.\nPick the Select tool (V)\nand click any shape to\nmove, resize or edit it.",
                      bg=t["panel"], fg=t["subtext"], font=(FONT_UI[0], 9), justify="left").pack(anchor="w")

    # ─────────────────────────────────────────── drawing interaction
    def _on_down(self, event):
        if not self.doc:
            return
        self.page_canvas.focus_set()
        cpt = self._canvas_pt(event)
        tool = self.current_tool
        self._temp_canvas_ids = []

        if tool == "select":
            if self.selected_ann is not None:
                hi = self._handle_at(self.selected_ann, cpt)
                if hi is not None:
                    self._drag_mode = "resize"
                    self._resize_index = hi
                    self._orig_points = list(self.selected_ann.points)
                    self._drag_last_pt = cpt
                    return
            hit = self._hit_test(cpt)
            self.selected_ann = hit
            if hit:
                self._drag_mode = "move"
                self._orig_points = list(hit.points)
                self._drag_start = cpt
                self._drag_last_pt = cpt
                self._sync_style_vars_from_selection()
            else:
                self._drag_mode = None
            self._update_selection_panel()
            self._redraw_overlay()
        elif tool in ("pen", "highlighter"):
            self._live_stroke_points = [cpt]
        elif tool in ("line", "arrow", "rect", "ellipse"):
            self._drag_start = cpt
        elif tool == "balloon":
            if self._balloon_anchor is None:
                self._balloon_anchor = cpt
                self._set_status("Balloon: click again to place the bubble")
                return
        elif tool == "text":
            self._prompt_text_annotation(cpt)
        elif tool == "edittext":
            self._prompt_edit_existing_text(cpt)
        elif tool == "eraser":
            self._erase_at(cpt)

    def _on_drag(self, event):
        if not self.doc:
            return
        cpt = self._canvas_pt(event)
        tool = self.current_tool
        c = self.page_canvas

        if tool == "select" and self.selected_ann and self._drag_mode == "move":
            ann = self.selected_ann
            dx = (cpt[0] - self._drag_start[0]) / self.zoom
            dy = (cpt[1] - self._drag_start[1]) / self.zoom
            ann.points = [(x + dx, y + dy) for (x, y) in self._orig_points]
            # incremental pixel move of just this shape + its handles — no delete/recreate,
            # so nothing else on the page is touched (this is what killed the ghosting)
            ddx = cpt[0] - self._drag_last_pt[0]
            ddy = cpt[1] - self._drag_last_pt[1]
            c.move(f"a{id(ann)}", ddx, ddy)
            c.move("sel", ddx, ddy)
            self._drag_last_pt = cpt
            return
        elif tool == "select" and self.selected_ann and self._drag_mode == "resize":
            ann = self.selected_ann
            pdf_pt = self._to_pdf(cpt)
            pts = list(ann.points)
            pts[self._resize_index] = pdf_pt
            ann.points = pts
            citem = getattr(ann, "_citem", None)
            if citem is not None and ann.kind in ("line", "arrow", "rect", "ellipse"):
                p0, p1 = self._to_canvas(pts[0]), self._to_canvas(pts[1])
                c.coords(citem, p0[0], p0[1], p1[0], p1[1])
                c.delete("sel")
                self._draw_selection_handles()
            else:
                # multi-item shapes (balloon) or missing cache: safe fallback, full resync
                self._redraw_overlay()
            self._drag_last_pt = cpt
            return

        for i in self._temp_canvas_ids:
            c.delete(i)
        self._temp_canvas_ids = []

        dash_tuple = (6, 4) if self.dashed else None
        if tool in ("pen", "highlighter"):
            self._live_stroke_points.append(cpt)
            pts = self._live_stroke_points
            if len(pts) >= 2:
                col = self.draw_color
                width = self.stroke_width * (3 if tool == "highlighter" else 1)
                c.create_line(pts[-2][0], pts[-2][1], pts[-1][0], pts[-1][1],
                               fill=col, width=width, capstyle="round", smooth=True, tags="live")
        elif tool in ("line", "arrow") and self._drag_start:
            x0, y0 = self._drag_start
            kw = dict(fill=self.draw_color, width=self.stroke_width,
                      arrow=("last" if tool == "arrow" else None))
            if dash_tuple:
                kw["dash"] = dash_tuple
            self._temp_canvas_ids.append(c.create_line(x0, y0, cpt[0], cpt[1], **kw))
        elif tool == "rect" and self._drag_start:
            x0, y0 = self._drag_start
            fillc = self.draw_color if self.fill_shapes else ""
            kw = dict(outline=self.draw_color, width=self.stroke_width, fill=fillc)
            if dash_tuple:
                kw["dash"] = dash_tuple
            self._temp_canvas_ids.append(c.create_rectangle(x0, y0, cpt[0], cpt[1], **kw))
        elif tool == "ellipse" and self._drag_start:
            x0, y0 = self._drag_start
            fillc = self.draw_color if self.fill_shapes else ""
            kw = dict(outline=self.draw_color, width=self.stroke_width, fill=fillc)
            if dash_tuple:
                kw["dash"] = dash_tuple
            self._temp_canvas_ids.append(c.create_oval(x0, y0, cpt[0], cpt[1], **kw))

    def _on_up(self, event):
        if not self.doc:
            return
        cpt = self._canvas_pt(event)
        tool = self.current_tool

        # BUGFIX: the live preview shape drawn during _on_drag (rect/ellipse/line/arrow)
        # is never tagged, so it used to survive after mouse-up as a stray "ghost" copy
        # sitting on top of the real, saved annotation until the next full re-render
        # (e.g. pressing Fit) wiped the canvas and made it vanish. Always clear it here.
        for _i in self._temp_canvas_ids:
            self.page_canvas.delete(_i)
        self._temp_canvas_ids = []

        if tool == "select" and self.selected_ann and self._drag_mode in ("move", "resize"):
            after = list(self.selected_ann.points)
            if after != self._orig_points:
                self.undo_stack.append({"action": "move", "page": self.page_index,
                                          "ann": self.selected_ann, "before": self._orig_points, "after": after})
                self.redo_stack.clear()
            self._drag_mode = None
            self._redraw_overlay()
            return

        if tool in ("pen", "highlighter"):
            pts = self._live_stroke_points
            if len(pts) >= 2:
                ann = Annotation(kind=tool, points=[self._to_pdf(p) for p in pts],
                                  color=self.draw_color,
                                  width=self.stroke_width * (3 if tool == "highlighter" else 1),
                                  opacity=self.opacity, dashed=self.dashed)
                self._add_annotation(ann)
            self._live_stroke_points = []
            self.page_canvas.delete("live")
            self._redraw_overlay()
        elif tool in ("line", "arrow", "rect", "ellipse") and self._drag_start:
            p0, p1 = self._drag_start, cpt
            if math.hypot(p1[0] - p0[0], p1[1] - p0[1]) > 3:
                ann = Annotation(kind=tool, points=[self._to_pdf(p0), self._to_pdf(p1)],
                                  color=self.draw_color, width=self.stroke_width, opacity=self.opacity,
                                  dashed=self.dashed,
                                  fill=(self.draw_color if self.fill_shapes and tool in ("rect", "ellipse") else None))
                self._add_annotation(ann)
            self._drag_start = None
            self._redraw_overlay()
        elif tool == "balloon" and self._balloon_anchor is not None:
            text = simpledialog.askstring("Balloon text", "Callout message:", parent=self)
            ann = Annotation(kind="balloon", points=[self._to_pdf(self._balloon_anchor), self._to_pdf(cpt)],
                              color=self.draw_color, width=max(1.5, self.stroke_width / 2),
                              text=text or "", fontsize=self.text_fontsize, opacity=self.opacity)
            self._add_annotation(ann)
            self._balloon_anchor = None
            self._redraw_overlay()

    def _on_double_click(self, event):
        if self.current_tool != "select" or not self.doc:
            return
        cpt = self._canvas_pt(event)
        hit = self._hit_test(cpt)
        if hit and hit.kind in ("text", "balloon", "edit_text"):
            label = "Replace with:" if hit.kind == "edit_text" else "Text:"
            new_text = simpledialog.askstring("Edit text", label, initialvalue=hit.text, parent=self)
            if new_text is not None:
                hit.text = new_text
                self._redraw_overlay()

    def _prompt_text_annotation(self, cpt):
        text = simpledialog.askstring("Add text", "Text:", parent=self)
        if not text:
            return
        ann = Annotation(kind="text", points=[self._to_pdf(cpt)], color=self.draw_color,
                          text=text, fontsize=self.text_fontsize, opacity=self.opacity)
        self._add_annotation(ann)
        self._redraw_overlay()

    def _prompt_edit_existing_text(self, cpt):
        """Edit real text that is already IN the PDF page (not an annotation).

        Finds the line of native PDF text under the click, lets the user type
        a replacement, and stores it as an 'edit_text' annotation. On export
        this is applied as a real redaction: the original text is erased and
        the new text is baked into the page in its place — so it's a true
        edit, not a note sitting on top.
        """
        if not self.doc:
            return
        page = self.doc[self.page_index]
        px, py = self._to_pdf(cpt)

        target = None
        try:
            data = page.get_text("dict")
        except Exception:
            data = None
        if data:
            for block in data.get("blocks", []):
                for line in block.get("lines", []):
                    lx0, ly0, lx1, ly1 = line.get("bbox", (0, 0, 0, 0))
                    if lx0 - 2 <= px <= lx1 + 2 and ly0 - 2 <= py <= ly1 + 2:
                        spans = line.get("spans", [])
                        if not spans:
                            continue
                        text = "".join(s.get("text", "") for s in spans)
                        fontsize = spans[0].get("size", self.text_fontsize)
                        color = spancolor_to_hex(spans[0].get("color", 0))
                        target = {"bbox": (lx0, ly0, lx1, ly1), "text": text,
                                  "fontsize": fontsize, "color": color}
                        break
                if target:
                    break

        if not target:
            messagebox.showinfo("No text here",
                                 "Couldn't find any PDF text at that spot.\n"
                                 "Click directly on a line of text to edit it.")
            return

        new_text = simpledialog.askstring("Edit PDF text", "Replace with:",
                                            initialvalue=target["text"], parent=self)
        if new_text is None or new_text == target["text"]:
            return

        x0, y0, x1, y1 = target["bbox"]
        # a little breathing room so the redaction fully covers the old glyphs
        pad = 1.0
        ann = Annotation(kind="edit_text",
                          points=[(x0 - pad, y0 - pad), (x1 + pad, y1 + pad)],
                          color=target["color"], text=new_text,
                          fontsize=target["fontsize"], opacity=1.0)
        self._add_annotation(ann)
        self._redraw_overlay()

    def _add_annotation(self, ann: Annotation):
        self.annotations.setdefault(self.page_index, []).append(ann)
        self.undo_stack.append({"action": "add", "page": self.page_index, "ann": ann})
        self.redo_stack.clear()
        # Auto-select whatever was just added (shape, stroke, balloon, or text)
        # so its size (stroke width or font size) is immediately editable in
        # the right-hand panel without having to switch to the Select tool
        # and click it first.
        self.selected_ann = ann
        self._sync_style_vars_from_selection()
        self._update_selection_panel()

    def _erase_at(self, cpt):
        hit = self._hit_test(cpt)
        if hit:
            lst = self.annotations.get(self.page_index, [])
            if hit in lst:
                lst.remove(hit)
                self.undo_stack.append({"action": "remove", "page": self.page_index, "ann": hit})
                self.redo_stack.clear()
            self._redraw_overlay()

    def clear_page_annotations(self):
        self.annotations[self.page_index] = []
        self.selected_ann = None
        self._update_selection_panel()
        self._redraw_overlay()

    def _delete_selected(self, event=None):
        if self.current_tool != "select" or not self.selected_ann:
            return
        idx = self.page_index
        lst = self.annotations.get(idx, [])
        if self.selected_ann in lst:
            lst.remove(self.selected_ann)
            self.undo_stack.append({"action": "remove", "page": idx, "ann": self.selected_ann})
            self.redo_stack.clear()
        self.selected_ann = None
        self._update_selection_panel()
        self._redraw_overlay()

    def _duplicate_selected(self, event=None):
        if self.current_tool != "select" or not self.selected_ann:
            return
        new_ann = copy.deepcopy(self.selected_ann)
        off = 12 / self.zoom
        new_ann.points = [(x + off, y + off) for (x, y) in new_ann.points]
        self.annotations.setdefault(self.page_index, []).append(new_ann)
        self.undo_stack.append({"action": "add", "page": self.page_index, "ann": new_ann})
        self.redo_stack.clear()
        self.selected_ann = new_ann
        self._update_selection_panel()
        self._redraw_overlay()

    # ─────────────────────────────────────────── undo / redo
    def undo(self):
        if not self.undo_stack:
            return
        e = self.undo_stack.pop()
        idx, ann, act = e["page"], e["ann"], e["action"]
        if act == "add":
            lst = self.annotations.get(idx, [])
            if ann in lst:
                lst.remove(ann)
        elif act == "remove":
            self.annotations.setdefault(idx, []).append(ann)
        elif act == "move":
            ann.points = e["before"]
        self.redo_stack.append(e)
        if self.selected_ann is ann and act == "add":
            self.selected_ann = None
        if idx == self.page_index:
            self._update_selection_panel()
            self._redraw_overlay()

    def redo(self):
        if not self.redo_stack:
            return
        e = self.redo_stack.pop()
        idx, ann, act = e["page"], e["ann"], e["action"]
        if act == "add":
            self.annotations.setdefault(idx, []).append(ann)
        elif act == "remove":
            lst = self.annotations.get(idx, [])
            if ann in lst:
                lst.remove(ann)
        elif act == "move":
            ann.points = e["after"]
        self.undo_stack.append(e)
        if idx == self.page_index:
            self._redraw_overlay()

    # ─────────────────────────────────────────── overlay rendering
    def _draw_annotations_for_current_page(self):
        c = self.page_canvas
        bgc = self.theme["canvas_bg"]
        for a in self.annotations.get(self.page_index, []):
            a._citem = None  # reset per-shape canvas id cache; set below for single-item kinds
            item_tag = f"a{id(a)}"
            tags = ("ann", item_tag)
            pts = [self._to_canvas(p) for p in a.points]
            col = blend_hex(a.color, getattr(a, "opacity", 1.0), bgc)
            fillc = blend_hex(a.fill, getattr(a, "opacity", 1.0), bgc) if a.fill else ""
            dash_tuple = (6, 4) if getattr(a, "dashed", False) else None
            if a.kind in ("pen", "highlighter") and len(pts) >= 2:
                flat = [v for p in pts for v in p]
                kw = dict(fill=col, width=a.width, capstyle="round", smooth=True, tags=tags)
                if dash_tuple and a.kind != "highlighter":
                    kw["dash"] = dash_tuple
                a._citem = c.create_line(*flat, **kw)
            elif a.kind in ("line", "arrow") and len(pts) == 2:
                kw = dict(fill=col, width=a.width, arrow=("last" if a.kind == "arrow" else None), tags=tags)
                if dash_tuple:
                    kw["dash"] = dash_tuple
                a._citem = c.create_line(pts[0][0], pts[0][1], pts[1][0], pts[1][1], **kw)
            elif a.kind == "rect" and len(pts) == 2:
                kw = dict(outline=col, width=a.width, fill=fillc, tags=tags)
                if dash_tuple:
                    kw["dash"] = dash_tuple
                a._citem = c.create_rectangle(pts[0][0], pts[0][1], pts[1][0], pts[1][1], **kw)
            elif a.kind == "ellipse" and len(pts) == 2:
                kw = dict(outline=col, width=a.width, fill=fillc, tags=tags)
                if dash_tuple:
                    kw["dash"] = dash_tuple
                a._citem = c.create_oval(pts[0][0], pts[0][1], pts[1][0], pts[1][1], **kw)
            elif a.kind == "balloon" and len(pts) == 2:
                anchor, body = pts
                bw, bh = 150 * self.zoom / 1.6, 60 * self.zoom / 1.6
                x0, y0 = body[0] - bw / 2, body[1] - bh / 2
                x1, y1 = x0 + bw, y0 + bh
                rpts = round_rect_pts(x0, y0, x1, y1, 10)
                c.create_polygon(rpts, smooth=True, fill="white", outline=col, width=a.width, tags=tags)
                c.create_line(body[0], body[1], anchor[0], anchor[1], fill=col, width=a.width, tags=tags)
                c.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=a.text, fill="#111",
                               width=bw - 12, font=(FONT_UI[0], max(8, int(a.fontsize * self.zoom / 1.6))),
                               tags=tags)
            elif a.kind == "text" and pts:
                a._citem = c.create_text(pts[0][0], pts[0][1], text=a.text, fill=col, anchor="nw",
                               font=(FONT_UI[0], max(8, int(a.fontsize * self.zoom / 1.6)), "bold"), tags=tags)
            elif a.kind == "edit_text" and len(pts) == 2:
                x0, y0 = pts[0]; x1, y1 = pts[1]
                # cover the original PDF text with a white patch, then draw the
                # replacement on top — mirrors the redaction that happens on export
                c.create_rectangle(x0, y0, x1, y1, fill="white", outline="", tags=tags)
                a._citem = c.create_text(x0 + 2, (y0 + y1) / 2, text=a.text, fill=col, anchor="w",
                               font=(FONT_UI[0], max(8, int(a.fontsize * self.zoom / 1.6))), tags=tags)

    # ─────────────────────────────────────────── search
    def open_find(self):
        if not self.doc:
            messagebox.showinfo("No document", "Open a PDF first.")
            return
        d = StudioDialog(self, "Find in Document", height=200)
        q_v = d.labeled_entry("Search text", "")

        def go():
            query = q_v.get().strip()
            d.destroy()
            if not query:
                return
            self._run_search(query)
        d.add_buttons("Search", go)

    def _run_search(self, query):
        self._search_hits = []
        for i in range(len(self.doc)):
            rects = self.doc[i].search_for(query, quads=False)
            for r in rects:
                self._search_hits.append((i, r))
        if not self._search_hits:
            messagebox.showinfo("Find", f"No matches for “{query}”.")
            return
        self._search_hit_index = 0
        self._jump_to_hit()
        self._set_status(f"{len(self._search_hits)} match(es) for “{query}” — press Ctrl+F again to search anew")

    def _jump_to_hit(self):
        if not self._search_hits or self._search_hit_index < 0:
            return
        idx, rect = self._search_hits[self._search_hit_index]
        self.go_to_page(idx)

    def _draw_search_hits(self):
        if not self._search_hits:
            return
        c = self.page_canvas
        for i, (pidx, rect) in enumerate(self._search_hits):
            if pidx != self.page_index:
                continue
            x0, y0 = self._to_canvas((rect.x0, rect.y0))
            x1, y1 = self._to_canvas((rect.x1, rect.y1))
            active = (i == self._search_hit_index)
            c.create_rectangle(x0 - 2, y0 - 2, x1 + 2, y1 + 2,
                                 outline=("#FF9500" if active else "#FFD60A"),
                                 width=2 if active else 1, tags="hit")

    # ─────────────────────────────────────────── command palette
    def open_command_palette(self):
        commands = [
            ("Open PDF…", self.open_pdf), ("Save Annotated PDF As…", self.save_pdf),
            ("Document Properties…", self.dlg_doc_properties),
            ("Open in System Viewer / Print…", self.open_in_system_viewer),
            ("Find in Document…", self.open_find),
            ("Undo", self.undo), ("Redo", self.redo),
            ("Duplicate Selection", self._duplicate_selected), ("Delete Selection", self._delete_selected),
            ("Clear Page Annotations", self.clear_page_annotations),
            ("Toggle Light / Dark Theme", self.toggle_theme),
            ("Zoom In", self.zoom_in), ("Zoom Out", self.zoom_out),
            ("Fit Width", self.zoom_fit_width), ("Fit Page", self.zoom_fit_page),
            ("Actual Size (100%)", self.zoom_actual),
            ("Previous Page", self.prev_page), ("Next Page", self.next_page),
            ("First Page", lambda: self.go_to_page(0)),
            ("Last Page", lambda: self.go_to_page(len(self.doc) - 1) if self.doc else None),
            ("Rotate Current Page 90°", lambda: self.page_rotate(self.page_index, 90)),
            ("Duplicate Current Page", lambda: self.page_duplicate(self.page_index)),
            ("Insert Blank Page After Current", lambda: self.page_insert_blank(self.page_index)),
            ("Delete Current Page", lambda: self.page_delete(self.page_index)),
            ("Move Page Up", lambda: self.page_move(self.page_index, -1)),
            ("Move Page Down", lambda: self.page_move(self.page_index, 1)),
            ("Merge PDFs…", self.dlg_merge), ("Split PDF…", self.dlg_split),
            ("Extract Page Range…", self.dlg_extract), ("Rotate Pages…", self.dlg_rotate),
            ("Add Watermark…", self.dlg_watermark), ("Add Password…", self.dlg_add_password),
            ("Remove Password…", self.dlg_remove_password),
            ("Images → PDF…", self.dlg_images_to_pdf), ("Convert Image Format…", self.dlg_convert_image),
            ("Export Current Page as Image…", self.export_current_page_image),
            ("Export All Pages as Images…", self.export_all_pages_images),
            ("Export as Text…", self.export_text),
            ("Keyboard Shortcuts", self._show_shortcuts),
        ]
        CommandPalette(self, commands)

    # ─────────────────────────────────────────── status
    def _set_status(self, text):
        self.status_label.configure(text=text)

    # ═══════════════════════════════════ EXPORT / CONVERT dialogs ═══════
    def _run_async(self, fn, on_done=None, title="Working…"):
        dlg = ProgressDialog(self, title=title, determinate=False)
        self._set_status(title)

        def worker():
            try:
                result = fn(); err = None
            except Exception as e:
                traceback.print_exc(); result, err = None, e
            self.after(0, lambda: self._finish_async(result, err, on_done, dlg))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_async(self, result, err, on_done, dlg):
        dlg.close()
        if err:
            messagebox.showerror("Operation failed", str(err))
            self._set_status("Error")
        else:
            self._set_status("Done")
            if on_done:
                on_done(result)

    def export_current_page_image(self):
        if not self.doc:
            return
        out = filedialog.asksaveasfilename(defaultextension=".png",
                                            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("BMP", "*.bmp")])
        if not out:
            return
        fmt = os.path.splitext(out)[1].lstrip(".").upper()
        img = PDFEngine.render_page(self.doc, self.page_index, 2.5)
        if fmt in ("JPG", "JPEG"):
            img.convert("RGB").save(out, "JPEG", quality=95)
        else:
            img.save(out, fmt)
        messagebox.showinfo("Exported", f"Page image saved:\n{out}")

    def export_all_pages_images(self):
        if not self.doc:
            return
        out_dir = filedialog.askdirectory(title="Choose output folder")
        if not out_dir:
            return
        self._run_async(lambda: PDFEngine.pdf_to_images(self.doc_path, out_dir, "PNG", 2.5),
                          lambda files: messagebox.showinfo("Exported", f"{len(files)} images saved to:\n{out_dir}"),
                          title="Exporting pages…")

    def export_text(self):
        if not self.doc:
            return
        out = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if not out:
            return
        PDFEngine.pdf_to_text(self.doc_path, out)
        messagebox.showinfo("Exported", f"Text saved:\n{out}")

    def open_tools_menu(self):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Merge PDFs…", command=self.dlg_merge)
        menu.add_command(label="Split PDF…", command=self.dlg_split)
        menu.add_command(label="Extract Page Range…", command=self.dlg_extract)
        menu.add_command(label="Rotate Pages…", command=self.dlg_rotate)
        menu.add_command(label="Add Watermark…", command=self.dlg_watermark)
        menu.add_command(label="Add Password…", command=self.dlg_add_password)
        menu.add_command(label="Remove Password…", command=self.dlg_remove_password)
        menu.add_separator()
        menu.add_command(label="Images → PDF…", command=self.dlg_images_to_pdf)
        menu.add_command(label="Convert Image Format…", command=self.dlg_convert_image)
        menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())

    def dlg_merge(self):
        paths = filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")])
        if not paths:
            return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile="merged.pdf")
        if not out:
            return
        self._run_async(lambda: PDFEngine.merge_pdfs(list(paths), out),
                          lambda _r: messagebox.showinfo("Merged", f"Saved:\n{out}"), title="Merging PDFs…")

    def dlg_split(self):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not path:
            return
        out_dir = filedialog.askdirectory(title="Choose output folder")
        if not out_dir:
            return
        self._run_async(lambda: PDFEngine.split_pdf(path, out_dir),
                          lambda files: messagebox.showinfo("Split", f"{len(files)} files saved to:\n{out_dir}"),
                          title="Splitting PDF…")

    def dlg_extract(self):
        path = self.doc_path or filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not path:
            return
        d = StudioDialog(self, "Extract Page Range", height=260)
        s = d.labeled_entry("Start page (1-based)", "1")
        e = d.labeled_entry("End page (1-based)", "1")

        def go():
            out = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile="extracted.pdf")
            if out:
                try:
                    PDFEngine.extract_pages(path, int(s.get()) - 1, int(e.get()) - 1, out)
                    messagebox.showinfo("Extracted", f"Saved:\n{out}")
                except Exception as ex:
                    messagebox.showerror("Failed", str(ex))
            d.destroy()
        d.add_buttons("Extract", go)

    def dlg_rotate(self):
        path = self.doc_path or filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not path:
            return
        d = StudioDialog(self, "Rotate Pages", height=230)
        a = d.labeled_entry("Angle (90 / 180 / 270)", "90")

        def go():
            out = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile="rotated.pdf")
            if out:
                try:
                    PDFEngine.rotate_pages(path, int(a.get()), out)
                    messagebox.showinfo("Rotated", f"Saved:\n{out}")
                except Exception as ex:
                    messagebox.showerror("Failed", str(ex))
            d.destroy()
        d.add_buttons("Rotate", go)

    def dlg_watermark(self):
        path = self.doc_path or filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not path:
            return
        d = StudioDialog(self, "Add Watermark", height=250)
        txt = d.labeled_entry("Watermark text", "CONFIDENTIAL")

        def go():
            out = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile="watermarked.pdf")
            if out:
                try:
                    PDFEngine.add_watermark(path, txt.get(), out)
                    messagebox.showinfo("Watermarked", f"Saved:\n{out}")
                except Exception as ex:
                    messagebox.showerror("Failed", str(ex))
            d.destroy()
        d.add_buttons("Apply", go)

    def dlg_add_password(self):
        path = self.doc_path or filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not path:
            return
        d = StudioDialog(self, "Add Password", height=280)
        u = d.labeled_entry("User password (to open)", "")
        o = d.labeled_entry("Owner password (optional)", "")

        def go():
            out = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile="protected.pdf")
            if out:
                try:
                    PDFEngine.set_password(path, u.get(), o.get(), out)
                    messagebox.showinfo("Protected", f"Saved:\n{out}")
                except Exception as ex:
                    messagebox.showerror("Failed", str(ex))
            d.destroy()
        d.add_buttons("Encrypt", go)

    def dlg_remove_password(self):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not path:
            return
        d = StudioDialog(self, "Remove Password", height=230)
        pw = d.labeled_entry("Current password", "")

        def go():
            out = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile="unlocked.pdf")
            if out:
                try:
                    PDFEngine.remove_password(path, pw.get(), out)
                    messagebox.showinfo("Unlocked", f"Saved:\n{out}")
                except Exception as ex:
                    messagebox.showerror("Failed", str(ex))
            d.destroy()
        d.add_buttons("Remove", go)

    def dlg_images_to_pdf(self):
        paths = filedialog.askopenfilenames(
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.tiff *.webp")])
        if not paths:
            return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile="images.pdf")
        if not out:
            return
        self._run_async(lambda: PDFEngine.images_to_pdf(list(paths), out),
                          lambda _r: messagebox.showinfo("Created", f"Saved:\n{out}"), title="Building PDF…")

    def dlg_convert_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.tiff *.webp")])
        if not path:
            return
        d = StudioDialog(self, "Convert Image Format", height=250)
        t = self.theme
        tk.Label(d.body, text="Target format", bg=t["panel"], fg=t["subtext"],
                  font=(FONT_UI[0], 11)).pack(anchor="w", pady=(6, 2))
        fmt_var = tk.StringVar(value="PNG")
        ttk.Combobox(d.body, textvariable=fmt_var, state="readonly",
                     values=["PNG", "JPG", "BMP", "TIFF", "WEBP"]).pack(fill="x")

        def go():
            fmt = fmt_var.get()
            out = filedialog.asksaveasfilename(defaultextension="." + fmt.lower(),
                                                initialfile="converted." + fmt.lower())
            if out:
                try:
                    PDFEngine.convert_image(path, out, fmt)
                    messagebox.showinfo("Converted", f"Saved:\n{out}")
                except Exception as ex:
                    messagebox.showerror("Failed", str(ex))
            d.destroy()
        d.add_buttons("Convert", go)


# ════════════════════════════════════════════════════════════════════════
#  Command Palette — Spotlight-style fuzzy launcher (Ctrl+K)
# ════════════════════════════════════════════════════════════════════════
class CommandPalette(tk.Toplevel):
    def __init__(self, app, commands):
        super().__init__(app)
        self.app = app
        self.commands = commands  # list[(label, callback)]
        t = app.theme
        w, h = 520, 380
        x = app.winfo_rootx() + (app.winfo_width() - w) // 2
        y = app.winfo_rooty() + 90
        self.overrideredirect(True)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.configure(bg=t["border"])
        self.attributes("-topmost", True)

        outer = tk.Frame(self, bg=t["panel"], highlightthickness=0)
        outer.pack(fill="both", expand=True, padx=1, pady=1)

        self.query_var = tk.StringVar()
        entry = tk.Entry(outer, textvariable=self.query_var, font=(FONT_UI[0], 15),
                          bg=t["panel"], fg=t["text"], relief="flat", insertbackground=t["text"])
        entry.pack(fill="x", padx=16, pady=(16, 10), ipady=6)
        entry.focus_set()

        self.listbox = tk.Listbox(outer, font=(FONT_UI[0], 12), bg=t["panel"], fg=t["text"],
                                    selectbackground=t["accent"], selectforeground="white",
                                    activestyle="none", relief="flat", highlightthickness=0, bd=0)
        self.listbox.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self.query_var.trace_add("write", lambda *_: self._filter())
        entry.bind("<Down>", self._focus_list)
        entry.bind("<Return>", self._run_selected)
        self.listbox.bind("<Return>", self._run_selected)
        self.listbox.bind("<Double-Button-1>", self._run_selected)
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<FocusOut>", lambda e: None)

        self._filtered = list(commands)
        self._refresh_list()
        self.update_idletasks()
        try:
            self.grab_set()
        except tk.TclError:
            self.after(50, self._safe_grab)

    def _safe_grab(self):
        if self.winfo_exists():
            try:
                self.grab_set()
            except tk.TclError:
                pass

    def _focus_list(self, _e=None):
        self.listbox.focus_set()
        if self._filtered:
            self.listbox.selection_set(0)
        return "break"

    def _filter(self):
        q = self.query_var.get().strip().lower()
        if not q:
            self._filtered = list(self.commands)
        else:
            self._filtered = [c for c in self.commands if q in c[0].lower()]
        self._refresh_list()

    def _refresh_list(self):
        self.listbox.delete(0, "end")
        for label, _cb in self._filtered:
            self.listbox.insert("end", "  " + label)
        if self._filtered:
            self.listbox.selection_set(0)

    def _run_selected(self, _e=None):
        sel = self.listbox.curselection()
        idx = sel[0] if sel else 0
        if 0 <= idx < len(self._filtered):
            _label, cb = self._filtered[idx]
            self.destroy()
            self.app.after(10, cb)
        else:
            self.destroy()


# ════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    # Path to open passed by Windows/macOS/Linux when the file is double-clicked
    # or "Open with → ApEx PdF" is used from Explorer/Finder.
    _open_path_arg = None
    for _a in sys.argv[1:]:
        if _a.lower().endswith(".pdf") and os.path.isfile(_a):
            _open_path_arg = os.path.abspath(_a)
            break

    splash = Splash()
    splash.mainloop()
    app = AppleStudio()
    if _open_path_arg:
        app.after(150, lambda: app._open_path(_open_path_arg))
    app.mainloop()

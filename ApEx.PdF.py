#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════╗
║                              A p E x   P d F   v5                         ║
║        Advanced PDF Editor · Converter · Annotator — single file app      ║
║                        by StRaNgErDrEaMeR                                 ║
╚══════════════════════════════════════════════════════════════════════════╝
WHAT'S NEW IN v5  (advanced GUI + feature pass)
  • NEW: floating toast notifications — quick, non-blocking confirmations
    that slide in, glow with a status color, and fade themselves out.
  • NEW: a third "Sepia / Reading" theme — cycle Light → Dark → Sepia from
    one toolbar button (🌙/📖/☀) instead of a plain on/off toggle.
  • NEW: Focus Mode (⛶ button or Ctrl+Shift+F) — hides the sidebar and the
    style panel for a distraction-free full-width reading/annotation view.
  • NEW: sidebar now has Pages / Outline tabs — the Outline tab lists the
    PDF's real table-of-contents/bookmarks (when present) and jumps to the
    right page on click.
  • NEW: Document Statistics dialog (Tools ▸ Statistics… / ⌘K) — live page,
    word, character, image, bookmark, annotation counts + file size.
  • Everything from v4 kept: crash-proofed callbacks, custom vector logo,
    HD gradient backdrops, real select/move/resize tool, Command Palette,
    Find in Document, page context menu, dashed strokes, document
    properties, progress dialogs, opacity/font-size sliders, recent files,
    fit/actual zoom, full mouse-wheel navigation.
WHAT WAS NEW IN v4  (bug-fix + hardening + visual overhaul pass)
  • Crash-proofed: every Tk callback (button, menu, shortcut, dialog) now
    routes through a central error handler — a mistake anywhere shows a
    friendly dialog instead of freezing or killing the app.
  • Fixed text/balloon selection: clicking near a text or callout annotation
    used to miss it unless you clicked its exact anchor pixel. Selection now
    uses the same box the text is actually rendered/exported into.
  • Fixed thumbnail & canvas visual quality: thumbnails render at higher
    internal resolution (crisper on HD/Retina screens), Windows DPI
    awareness is requested at startup so nothing looks blurry/scaled.
  • New brand identity: a custom vector-drawn "ApEx PdF" logo (no external
    image files needed — generated in-process) used as the window/taskbar
    icon, the launch-screen mark, the sidebar header, and the About dialog.
  • New soft gradient "HD" backgrounds behind the launch screen and behind
    the page canvas (per light/dark theme), redrawn cleanly on resize
    without ever corrupting the page/annotation layers.
  • Clearer, calmer GUI: branded toolbar header, tidier spacing, a live
    zoom/page readout, and an About box — nothing about the working tools
    changed, so muscle memory from v3 still applies.
  • flatten()/export is now defensive per-annotation: one broken annotation
    can no longer abort an entire export; it's skipped and reported.
  • Divide-by-zero / empty-document / zero-size-page guards added across
    zoom-fit, thumbnailing, and page navigation.
  • Everything from v3 kept: real select/move/resize tool, Command Palette,
    Find in Document, page context menu (rotate/duplicate/delete/insert/
    move), dashed strokes, document properties, progress dialogs, opacity +
    font-size sliders, recent files, fit/actual zoom, full mouse-wheel nav.
DEPENDENCIES  (install once)
    pip install PyMuPDF Pillow --break-system-packages
    (drop --break-system-packages on Windows / regular venvs)
RUN
    python3 apex_pdf.py
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

APP_NAME = "ApEx PdF"
APP_VERSION = "5.0"
APP_AUTHOR = "StRaNgErDrEaMeR"

# ────────────────────────────────────────────────────────────────────────
#  Windows HiDPI awareness — must happen before any window is created,
#  otherwise the whole UI renders blurry/upscaled on HD/4K displays.
#  Harmless no-op everywhere else.
# ────────────────────────────────────────────────────────────────────────
if sys.platform.startswith("win"):
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

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
    from PIL import Image, ImageTk, ImageDraw
except Exception:
    _MISSING.append("Pillow")
    Image = ImageTk = ImageDraw = None
if _MISSING:
    msg = (
        "Missing required package(s): " + ", ".join(_MISSING) + "\n\n"
        "Install them with:\n\n"
        "    pip install PyMuPDF Pillow --break-system-packages\n\n"
        "(remove --break-system-packages if you're on Windows or a venv)"
    )
    try:
        _r = tk.Tk(); _r.withdraw()
        messagebox.showerror(f"{APP_NAME} — missing dependencies", msg)
    except Exception:
        pass
    print(msg)
    sys.exit(1)

_APEXPDF_LOGO_PNG_B64 = (
    "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"
    "iHP9E1D0C5X8OdIs+Xjg6GYGpuRAQCGsWE7vqPkQbOIwp8mlthK7kAgt+E12Oh8BUmZqqhVETXXUfcxh0H46otYw2pJVar2mEI1Y"
    "8lZSLkF3UoB7L3RRMqG1wB/itnXFcsTWR51osfFFeWxMmMzN0wqI5RgB4sZMKy59pcopbWvZAlWavLjAeZlmkzSgtuTcdEppsbPJ"
    "Fbm+vn7ta3/xTW/+vZ/4iZ969OjZ29u74X0YtWGXy2Vsp/1ymZiqsl/mkl2r2fpEp6vT5XzZL5fz5bydTre3d6v9gjkv+37atvUw"
    "79jP5zMg2zbO58u+X97/vvf8P77u61760hfu7u7UbN93U1uZjsQlAATbts19+Y294Xu5nMe27eddzIcHc2LfL2a2bdt+2ZcKYe67"
    "60TN9rmL6NOnTz/8933Yf/X1//C/+Pt//+Ezj3ZAxJ77Q3/26iM+FYLtwdX26Lmbl75Mb262m4fjdFIbagOn69P1jWwnGacxNrUB"
    "MxsnNVEb21gR36pDh+o0MZURR0gzP1pvJpsJRMaQzZYOTCzq0WuTGGnLSQUqc3rtaiYnFVOZIicVgexZ/4lcqZxUTqe5v+v3Lq//"
    "lV/53n/+I9/zPe9929tO1zeYMhMFlqE1FqMCrUpFujrYVgJi8SGUcy2D6Zi6ZPNTLxhuClq6SSDZhFGI9jWIXFTSFJ7fEicG5Hmr"
    "11NU59zTDguaFnLOGRlmjBrdQhwg0i9SO59mn82NwbIkNxKoYl0/Ek3G9dZJ+4Lvo7lC1KcobOyLxHxIBhZ0o+j9qJgCW6R5un1n"
    "Aicpoc9IyOqd4o7RzaeiVcAEbwhL94Qe/rWK8MnDDW1mxd/X4rK1eLxWcDddqmlQFdWz3acSBRlNgaDFwqndOuW+rNqvB272Cj3u"
    "wwwMWHXeE1xx4I61XIka03O0kUCmBXxiFSs5xWUnsLNzfairJecVmROFLfYNYicmQQ2Ftu10+/Tx3/07f/drvvZr/6uv/8fPPnok"
    "KpfzeYyBHauFeDqdzpfz+XzZtg3A5XJ58PDB5e6yz7lt2/nurCqXy1nULudzfLZ1rfR8Ps+5y8TY7O7ufNkvS5G1zzmGvfWtv/el"
    "X/Kn//yX/7nFiPb5rgfmyTbG5bLAbTInzHO+cL5cVBdlWi6XOYat8UAu9HOfl8u+bTb3qWaius9l61KPnh/j8Qfe/4V/9I++533v"
    "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"
    "HqXcwWTGmNJXFWZH1hfkp4Btcje5EApgG0fq69atZ1KUsaaaU7Ek65al/hTAJM7blBS0euUYCw4wORHMc6CAzSxmNeUULszrqGfh"
    "BjrT7pHhTChj9ZhjMnM87AAsgVhnhSIqe7a0KsLjsIlgJvybkOxhWX+GALfvPzIUGymlo/+Q51N/C+l59lIJXUIVrvup9owmEoqQ"
    "gBUBEWdQFx6gkovyLXSNZrCdgLkORlCp5TJlc8+oomTOvoVsnVRy4FXlnPf+QQ988B//ycve/va3XXnllfe//yl//Ccvve3WLV//"
    "+ldH9VhCK9TBJpsOO/R+979/sisR1nQzOuKII5/05Cd/+ctnfuGLX5gbzU2n0w0bNvzGbzxveWmxHtWtbwuDsnvf9z5Ly9PTP/GJ"
    "VavmH3DqqW9+01tf8pIXXXHFFalG7u7O4044YTQa5cUuSbfMXX7iyfcUdkLiXBW8dN7ozKPx6LQHnvaRj338uuuuG49Go/HoR1dd"
    "1XU2zBLEuer8889/4e+9+FnP+vX3v/99EsKJJ5z4G899/ste9qfp0Q8giKZs0qXFkiMhud8pp3z3O9/50ZVXrl696iEPeei/vv0d"
    "L3/ZSy+99JIqrafEXDluW/+kJz3lj//k//7nf37ogvPPP+xud3v+81/wkAc95EUv/oPlpaU8bnWVI6H5+VV/87d/d8gh69/73vdt"
    "ue22Rz7ikX/39//4ute99jOf/mRV1d63+cm85z3vuWv3rghe+eDn5+Ye9vCfWrP2XdpUETlX+eAPu9vdH/24xz3pvPPe/773cjXy"
    "3i8sLDz9mc885uij16xZS7TZcSUUklsR3fOe96rr8Yc/+B/j+fnQhmkzmUwnGmLPRMTj8fj4E+7xqlf+2Q+v/MGWLVuI6NCNGx9w"
    "2mnEgSInMuWXfu9737vpppvmxnMv/J0XfvgjH77+hhvH43ppedG5Kp7Jil3bts/7jef/4i/84t/9w9/dvn374x//pNe+5nXPfd5v"
    "bNt6W9SroHGaCKEtaNEcag6H+mh1Fbazzn+SBp3w3OV0xmANrFGQxNnKnHJ8NIjn8+8XQybukX1Siph0pM5StJg94kRNO9XeJDvK"
    "ctZhU7Z8DcmMCdZo0ZETBwqqaWdwCEaOQzIXZMcF10b1fZmYnb5UPWvJ7v/nAQYDFHQd2QuANBNEEuA49+R05e8yl2NmUKYg8oio"
    "vSQmoNgBnbGwV90AKnY72J0NfUJHwHm225l7xRw3yYYpEIbLbKj1rEnP3cE++CEPvfz7P/jMpz9FRFf+8Aff/e65u3YuOVeHDk9P"
    "ZXAIy5NJRvMDaV7qZHn5ggsueupTn/aVr34lYsxPferTlpYmt9x6qxtKh2ua9gdX/uCcs75JzF8580vHHH30L/ziL19++eVVVYXg"
    "89VYXlpqmmn8nIiTMJjQxd/as2fPZHlClBMPhKjDl3ftWTrrrG9cf911AM6MuidJAjPv3rP7jW/8q796w9988UtfvPWWzX/80ld8"
    "4pOfPP+8741Go7Zt063A6sQAkGqG0yaT6be/ffbll11GRJ///Od+/3f/4CV/+Ee//3svDCHk0sD7cMghG3//D170pn980xe+8Pl4"
    "MN/4+tc++rFPPOvZv/7ud71zVNdN28ZbwXv/zGc+64R73OMZz3zG0uIeIrr04ouuuvpHmzff4qoq+h7kO3YymURcKNaQbdtu3ba1"
    "aZp4lirHIuQqppaY6bvnfvdhD/upT33yjF07d4YQHv+/nri8uHzNVVePRqN4n7rgsp8dO3f1j6/+xte/upcSbDQaXXPN1WtWrfmz"
    "P/vzF7/4Rcw8mU4X9yxGirpIEAnxUK+4/NIrLr+0qqrfeO5vnHfed6688sp4p1euCpCi9chHP+Y9//H+c845h4i+f8UVH//4R3ft"
    "3BGN6ZlNFIqgwgzCTqKqO6MxnQEciBc7YSOBlz0jeOS4MzMOyK7F6V3F4HBeurp3K6NL1C6XzSAgeD6ZTts6WmnaqZLLFWIgCLGU"
    "bP+FSXGsfE49H0nUgj2NJshZ81dIlmPIlYxNDKejZUFHPrEZB5kG7Pay7u99Vxhk+PDQy7gXKCZ7/RQZLu57P+HhbLHkmax/gv4T"
    "JMB/DfxW+Z9BQpAgEoIELz7/u/4TgkjwIfgQvG9DnGCm/yfBx3/3ofUh/W06gNAdjOSMsqRrSeNDCpobS3ThhRc+8IGnPf83f+se"
    "J5w4Pz9/w/XX79ixjYkpCLM45jjOZeeimU/6KiEvQ/OrVp111rfWbTjkUY9+zHTarFlY+6QnP/Wzn/+cq0eGT5rYBfWoHtU1EY1H"
    "NRE1bct1hSQG0DpYY2qUrne7UggUiCj4IBKyw5Fzrq7rQw87dM3aNZs2bVq/YUMsyUW6oOMQQl3Xl15y0Xe/993//Tu/98QnPuXu"
    "Rxzx3ne/K8Is+b4O0W2epIiQ5y5HiufmRgtr1jjnxnPzzrnTzzh9wyGHHHvc8SGEyjkRiSj2wx/xCB/C177+tdFoNDc/v3phwXv/"
    "yU+d8YAHnGaYRERE9NCHPPQzn/3s0uKeNWvXjsbj0Xj8lS+feflllzguTaRGo/F4NIqQXCy3p9NJCB525+5kLaxZuPTSS3bs2PH4"
    "JzxRgtR1/bM/93Pf/NY3q1Gd4jM7RbVzjoiquj5kw/rDDjvs2GOPPfroo9dv2GAvQVeWHnbooX//pr879dQHPOtZzxaR8XicC0fv"
    "PY6gR6PR2rXr5lbNH3LIRufceDzHaWYeQnesZ5991h/+4R894xnPOv74e1RVdfNNN/kumBpuN5YsnU01dqrDhULwwfv0rPj4/HT/"
    "2z01PvjgvffdT7qfp1e1+SfSvRX849sQvPdt8F58CMFL8AFXgu4B9PGpzE+whFbE4y+IhORMC7VgXEED9iIBqE0mdFbFWkjX0RTY"
    "xLNIBb1AllHWo4gxOpB8fQUY27ZgZUlNgkkxghA6khkdwApnuTyjV1jhziH7GirvC/AZONr4kk2bDl2zdk3wwVWO1S/SahJzll0k"
    "crDLlsICRumD0rbuPg5Zrqmv7Y+jQ3JQ0GQfobjXMPPmWzYvLS5FeTxrpAQXdKQQQuWq8877zute/RfPee7zn/LUn92za9dXvvLl"
    "j33sw8G3EeNAr5a29Xn5N2PPqt6+4/YzzzzzWc9+zte/9tVHPeYxu/fs/va3z/npxz7Ot77QyEVc4Oijj7nf/U8Zj0Yn3fNe9zvl"
    "Aa961SuYmSRwrJ+6M+JwjAaiSd2j29a33ucuoeIqRuOw47riV77iz3bs2FU53rO052Uv/dM9u3c7F9lK3QjUOff2t/3T3/79mx71"
    "yEf/3d/81Z7du+q69sFr/8YWcGSw9yZxdeWYKUgIwbeNiOzes2cymR5++OHXXH0VLpd3v/sRe/bsmSwvz83N+bYN3jPz5ptuXv2Y"
    "Nc65fEhxw1izdu3Nmzczc9u2PoTQ+rqu4yIVd1Eidq7y3teVi1tpSIDLZDKNI/3Ea+9OYdsGH9pPnfGJ3/zt3zn9vz72sIc+Yn71"
    "6m9+8+u/9Cu/3LYtZnXHnm1xcfejHvlTx771n1vfbli/4fTT/+s973lPXdfe+1gw+hDY0cKa1bdsvvn1r//LN7zhjZ/73Of27Nnj"
    "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"
    "u9859/LLLjviiCP/+E9fdu21P7npxhvqqvYSuqrABSIaVbX4QESfOuP0Zz7zY1/4wudu27Ll0MMOy66nzK6bkXRdWrtmzfojjzp6"
    "YfXq1nsiuenGG+NunQAOcZWrRlVsILbffvs/v/Utf/3Xf3PJJRcxG/I+mgXVdVcdBnDTj430/Nz4n9/6L5dcfum73vWO6WT6sIc9"
    "/O5HHnnZZZdGaCv1P92Kk7QT3cFk3oT3jfeNerExyl8IGY0oKgcpQRcwaflOxrUjS7lBjzBUaDIGTeTSK60DIcd0o7YOYhqy2EKM"
    "zFmprwyVHyuglgmGVtaAtH4QlGZ2VJ6u52FCNAHOVnaQvSM6S2bdCxR1o1r2uk7zCqD8A1jZB8S7d2wjKXXuIr3YV7ROhjleB5GL"
    "jZQRTF3ABrjIcWUU2jEKf4prqhxeGHQLs7NpzZyS49lGR4t4Yeb3vvtdf/Dil7zu9W9o23Zubv673z33wx/+z8gT7+SlEUT2fnHP"
    "YhFzmyqvZmlxSUR+/OOr//Ef/+6cc86mDspYdszOVVGxlQ9+x84di3v2iMi0aVrfwllOCtJARHTrrbc+4uEPe/WrXyvsxqPR9877"
    "3j+95U1VhDuci8374p7FyWSSzpbkpie7jyfJAAB6JklEQVQE2bZt62QyyRsPMyH3AQ3odu/ZvX3b7UoXKCLalWAh6CwhQlVV3b7t"
    "9l99+jN+8Zd/mZ27ZfPm1//VX15w3nkRvs/0lNZ759y/vf2fd+7c+Tu/+weT5WURf+uWW17x8lfcfvvtVVXlsizyU7ds2fKSP/yD"
    "F/7eH7zyz/7cN62r6ve89z3/9dGPxj6p6428H41GX/nKmRs3bXzh779ocffSaFTfdPNN//ov/8TOkWPykNlANJk2TTslol07d/7t"
    "G9/w4x9fzURt0+5ZXPT5dgXR1pZbb33ik3/2dX/1xnFVEYW29a96xcs237K5A/dTuMTt23dEIfFoNPrOuWd/6lNnHH3ssW3rIyyG"
    "2b+RF7T19tubaWO43J1nkZtMp6//q7/8/Re9+O/f9E+h9fOr59/+tred/93vpD0PjUZy8lYCXzp9ddJIiy5Z6smNAlYx7R2IFuMT"
    "FdTrFj304wskYCJAT+DDFHsTERseyOpJG5T1DR66+GgbBKH7DmAADRaLkljiGgqiQCUk9OF2lR+AeK4gTU+MAVrSWCTJmEgfnhHI"
    "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"
)

_apexpdf_logo_source_cache = None


def _load_apexpdf_logo_source():
    """Decode the embedded ApEx PdF brand-mark (PNG, base64) once and cache
    it. Keeping the real logo asset embedded in this single file preserves
    the "single-file app, no external images required" design."""
    global _apexpdf_logo_source_cache
    if _apexpdf_logo_source_cache is None:
        import base64, io
        data = base64.b64decode(_APEXPDF_LOGO_PNG_B64)
        _apexpdf_logo_source_cache = Image.open(io.BytesIO(data)).convert("RGBA")
    return _apexpdf_logo_source_cache


# ════════════════════════════════════════════════════════════════════════
#  THEME
# ════════════════════════════════════════════════════════════════════════
LIGHT = dict(
    bg="#F5F5F7", sidebar="#FBFBFD", panel="#FFFFFF", toolbar="#FBFBFD",
    text="#1D1D1F", subtext="#6E6E73", accent="#007AFF", accent_hover="#0066D6",
    border="#D6D6DA", canvas_bg="#E5E5EA", button="#FFFFFF", button_hover="#EFEFF3",
    button_active="#E2E2E8", danger="#FF3B30", success="#34C759", warn="#FF9500",
    grad_top="#EFEFF4", grad_bottom="#DEDEE4",
)
DARK = dict(
    bg="#1E1E1E", sidebar="#252526", panel="#2C2C2E", toolbar="#252526",
    text="#F5F5F7", subtext="#98989D", accent="#0A84FF", accent_hover="#409CFF",
    border="#3A3A3C", canvas_bg="#0B0B0C", button="#3A3A3C", button_hover="#48484A",
    button_active="#55555A", danger="#FF453A", success="#30D158", warn="#FF9F0A",
    grad_top="#151517", grad_bottom="#0A0A0B",
)
SEPIA = dict(
    bg="#F2E8D5", sidebar="#EFE3CC", panel="#F7EFDD", toolbar="#EFE3CC",
    text="#3B2F1E", subtext="#8A7A5C", accent="#B5651D", accent_hover="#9C5518",
    border="#DCC9A0", canvas_bg="#E5D6B3", button="#F7EFDD", button_hover="#EAD9B4",
    button_active="#DFC79A", danger="#B23A2E", success="#4E7A3D", warn="#B5751D",
    grad_top="#F3E7CC", grad_bottom="#E4D0A2",
)
THEMES = {"light": LIGHT, "dark": DARK, "sepia": SEPIA}
THEME_ORDER = ["light", "dark", "sepia"]
THEME_ICON = {"light": "🌙", "dark": "📖", "sepia": "☀"}
THEME_TOOLTIP = {"light": "Switch to Dark", "dark": "Switch to Sepia (reading)", "sepia": "Switch to Light"}
FONT_UI = ("SF Pro Display", "Helvetica Neue", "Segoe UI", "Arial")
CURSORS = {
    "select": "arrow", "pen": "pencil", "highlighter": "pencil",
    "line": "crosshair", "arrow": "crosshair", "rect": "crosshair",
    "ellipse": "crosshair", "balloon": "crosshair", "text": "xterm",
    "eraser": "circle", "edittext": "xterm",
}


def hexrgb(h):
    try:
        h = h.lstrip("#")
        return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    except Exception:
        return (0, 0, 0)


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
    try:
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
    except Exception:
        return hexcolor if isinstance(hexcolor, str) else "#000000"


def round_rect_pts(x1, y1, x2, y2, r):
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    return [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]


def lerp_hex(a, b, t):
    try:
        a = a.lstrip("#"); b = b.lstrip("#")
        ar, ag, ab = (int(a[i:i + 2], 16) for i in (0, 2, 4))
        br, bg, bb = (int(b[i:i + 2], 16) for i in (0, 2, 4))
        r = int(ar + (br - ar) * t); g = int(ag + (bg - ag) * t); bl = int(ab + (bb - ab) * t)
        return f"#{r:02x}{g:02x}{bl:02x}"
    except Exception:
        return a if isinstance(a, str) else "#000000"


def make_canvas_gradient(w, h, top_hex, bottom_hex, watermark=False, watermark_strength=0.16):
    """A cheap, fast vertical gradient (row-based fill) used as the subtle
    'HD' backdrop behind the page canvas and the splash screen. When
    `watermark=True`, the real ApEx PdF brand mark is also blended in,
    centered, at very low opacity — a subtle branded background. The
    watermark's own black backing is dropped (alpha comes from the
    artwork's brightness, not a solid square) so no seam/rectangle shows."""
    w = max(1, int(w)); h = max(1, int(h))
    img = Image.new("RGB", (w, h), top_hex)
    draw = ImageDraw.Draw(img)
    steps = max(1, min(h, 240))          # cap rows drawn for speed on huge windows
    for i in range(steps):
        y0 = int(i * h / steps)
        y1 = int((i + 1) * h / steps)
        t = i / max(1, steps - 1)
        col = lerp_hex(top_hex, bottom_hex, t)
        draw.rectangle([0, y0, w, y1], fill=col)
    if watermark:
        try:
            wm_size = int(min(w, h) * 0.62)
            if wm_size > 24:
                src_logo = _load_apexpdf_logo_source()
                wm = src_logo.resize((wm_size, wm_size), Image.LANCZOS).convert("RGBA")
                # Use the artwork's own brightness as the alpha mask, so the
                # logo's black background drops out instead of showing as a
                # faint rectangle — only the bright strokes/text bleed through.
                luminance = wm.convert("L")
                alpha = luminance.point(lambda px: int(min(255, px) * watermark_strength))
                r, g, b, _unused_a = wm.split()
                wm = Image.merge("RGBA", (r, g, b, alpha))
                img = img.convert("RGBA")
                img.alpha_composite(wm, ((w - wm_size) // 2, (h - wm_size) // 2))
                img = img.convert("RGB")
        except Exception:
            pass
    return img


def _make_vector_logo_image(size=256):
    """Builds the custom 'ApEx PdF' logo entirely in-process (no external
    image assets required): a rounded gradient badge, a stylised document
    with a folded corner, and a small 'PDF' ribbon tag."""
    size = max(16, int(size))
    scale = size / 256.0
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    # gradient fill, then clip to a rounded-rect mask
    grad = make_canvas_gradient(size, size, "#0A84FF", "#5E5CE6").convert("RGBA")
    mask = Image.new("L", (size, size), 0)
    mdraw = ImageDraw.Draw(mask)
    r = int(56 * scale)
    try:
        mdraw.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=255)
    except Exception:
        mdraw.rectangle([0, 0, size - 1, size - 1], fill=255)
    img = Image.composite(grad, img, mask)
    draw = ImageDraw.Draw(img)
    # subtle top sheen
    try:
        sheen = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        sdraw = ImageDraw.Draw(sheen)
        sdraw.ellipse([-size * 0.2, -size * 0.5, size * 1.2, size * 0.55],
                      fill=(255, 255, 255, 40))
        sheen.putalpha(Image.composite(sheen.split()[-1], Image.new("L", (size, size), 0), mask))
        img = Image.alpha_composite(img, sheen)
        draw = ImageDraw.Draw(img)
    except Exception:
        pass
    # document silhouette with a folded top-right corner
    dw, dh = size * 0.46, size * 0.60
    dx0, dy0 = size * 0.24, size * 0.19
    dx1, dy1 = dx0 + dw, dy0 + dh
    fold = dw * 0.30
    doc_pts = [
        (dx0, dy0), (dx1 - fold, dy0), (dx1, dy0 + fold),
        (dx1, dy1), (dx0, dy1),
    ]
    draw.polygon(doc_pts, fill=(255, 255, 255, 235))
    draw.polygon([(dx1 - fold, dy0), (dx1, dy0 + fold), (dx1 - fold, dy0 + fold)],
                 fill=(210, 226, 255, 255))
    # text lines on the document
    ly = dy0 + dh * 0.40
    for i in range(3):
        yy = ly + i * dh * 0.16
        draw.rectangle([dx0 + dw * 0.14, yy, dx1 - fold * 0.55, yy + max(1, size * 0.022)],
                       fill=(120, 140, 190, 210))
    # "PDF" ribbon tag bottom-right
    rb_w, rb_h = size * 0.50, size * 0.24
    rb_x0, rb_y0 = size * 0.40, size * 0.62
    rb_x1, rb_y1 = rb_x0 + rb_w, rb_y0 + rb_h
    try:
        draw.rounded_rectangle([rb_x0, rb_y0, rb_x1, rb_y1], radius=size * 0.05,
                                fill=(255, 69, 58, 255))
    except Exception:
        draw.rectangle([rb_x0, rb_y0, rb_x1, rb_y1], fill=(255, 69, 58, 255))
    try:
        from PIL import ImageFont
        fs = max(8, int(size * 0.13))
        font = None
        for fname in ("DejaVuSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf"):
            try:
                font = ImageFont.truetype(fname, fs)
                break
            except Exception:
                continue
        if font is None:
            font = ImageFont.load_default()
        txt = "PDF"
        try:
            bbox = draw.textbbox((0, 0), txt, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        except Exception:
            tw, th = fs * 1.6, fs
        draw.text((rb_x0 + (rb_w - tw) / 2, rb_y0 + (rb_h - th) / 2 - th * 0.15),
                  txt, fill="white", font=font)
    except Exception:
        pass
    return img




def make_logo_image(size=256):
    """Return the real ApEx PdF brand mark (the embedded logo artwork),
    resized to `size` x `size`. Falls back to the in-process vector logo
    if the embedded asset can't be decoded for any reason."""
    size = max(16, int(size))
    try:
        src_img = _load_apexpdf_logo_source()
        return src_img.resize((size, size), Image.LANCZOS)
    except Exception:
        return _make_vector_logo_image(size)


# ════════════════════════════════════════════════════════════════════════
#  Splash screen — Apple-style animated launcher with custom logo + gradient
# ════════════════════════════════════════════════════════════════════════
class Splash(tk.Tk):
    def __init__(self):
        super().__init__()
        self.overrideredirect(True)
        w, h = 540, 340
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        self.configure(bg="#0A0A0C")
        self.w, self.h = w, h
        self.attributes("-alpha", 0.0)
        c = tk.Canvas(self, width=w, height=h, bg="#0A0A0C", highlightthickness=0)
        c.pack(fill="both", expand=True)
        self.canvas = c
        # HD gradient backdrop
        try:
            grad = make_canvas_gradient(w, h, "#111114", "#08080A", watermark=True)
            self._bg_photo = ImageTk.PhotoImage(grad)
            c.create_image(0, 0, anchor="nw", image=self._bg_photo)
        except Exception:
            pass
        cx, cy = w / 2, h / 2 - 44
        # soft glow rings behind the logo
        for i, rad in enumerate(range(150, 30, -14)):
            t = i / 10
            col = lerp_hex("#0A0A0C", "#0A84FF", 0.04 + t * 0.09)
            c.create_oval(cx - rad, cy - rad, cx + rad, cy + rad, outline="", fill=col)
        # macOS traffic-light chrome, purely decorative
        for i, col in enumerate(("#FF5F57", "#FEBC2E", "#28C840")):
            c.create_oval(18 + i * 20, 16, 30 + i * 20, 28, fill=col, outline="")
        # custom ApEx PdF logo
        try:
            self._logo_img = make_logo_image(112)
            self._logo_photo = ImageTk.PhotoImage(self._logo_img)
            c.create_image(cx, cy, image=self._logo_photo)
        except Exception:
            c.create_text(cx, cy, text="PDF", font=(FONT_UI[0], 16, "bold"), fill="white")
        self.ring_r1, self.ring_r2 = 78, 64
        self.ring_cx, self.ring_cy = cx, cy
        self.arc1 = c.create_arc(cx - self.ring_r1, cy - self.ring_r1, cx + self.ring_r1, cy + self.ring_r1,
                                  start=0, extent=100, style="arc", outline="#0A84FF", width=3)
        self.arc2 = c.create_arc(cx - self.ring_r2, cy - self.ring_r2, cx + self.ring_r2, cy + self.ring_r2,
                                  start=180, extent=65, style="arc", outline="#409CFF", width=2)
        c.create_text(w / 2, h / 2 + 78, text=f"{APP_NAME}",
                       font=(FONT_UI[0], 21, "bold"), fill="white")
        c.create_text(w / 2, h / 2 + 102, text=f"v{APP_VERSION} · by {APP_AUTHOR}",
                       font=(FONT_UI[0], 10), fill="#8E8E93")
        c.create_rectangle(w / 2 - 130, h / 2 + 132, w / 2 + 130, h / 2 + 138,
                            fill="#2C2C2E", outline="")
        self.bar_bg_x0 = w / 2 - 130
        self.bar_full_w = 260
        self.bar = c.create_rectangle(self.bar_bg_x0, h / 2 + 132, self.bar_bg_x0, h / 2 + 138,
                                       fill="#0A84FF", outline="")
        self.status = c.create_text(w / 2, h / 2 + 156, text="Starting…",
                                     font=(FONT_UI[0], 9), fill="#8E8E93")
        self.progress = 0
        self.spin_angle = 0
        self._steps = ["Loading engine…", "Preparing canvas…", "Warming up tools…", "Ready."]
        self._fade_in()

    def _fade_in(self, a=0.0):
        a = min(1.0, a + 0.08)
        try:
            self.attributes("-alpha", a)
        except Exception:
            pass
        if a < 1.0:
            self.after(12, lambda: self._fade_in(a))
        else:
            self.after(30, self._animate)

    def _animate(self):
        self.spin_angle = (self.spin_angle + 9) % 360
        try:
            self.canvas.itemconfigure(self.arc1, start=self.spin_angle)
            self.canvas.itemconfigure(self.arc2, start=(self.spin_angle * -1.4) % 360)
        except Exception:
            pass
        self.progress = min(100, self.progress + 3)
        x1 = self.bar_bg_x0 + self.bar_full_w * (self.progress / 100)
        y0, y1 = self.h / 2 + 132, self.h / 2 + 138
        try:
            self.canvas.coords(self.bar, self.bar_bg_x0, y0, x1, y1)
            step = self._steps[min(len(self._steps) - 1, self.progress // 26)]
            self.canvas.itemconfigure(self.status, text=step)
        except Exception:
            pass
        if self.progress < 100:
            self.after(16, self._animate)
        else:
            self._fade_out()

    def _fade_out(self, a=1.0):
        a = max(0.0, a - 0.08)
        try:
            self.attributes("-alpha", a)
        except Exception:
            pass
        if a > 0:
            self.after(10, lambda: self._fade_out(a))
        else:
            try:
                self.destroy()
            except Exception:
                pass


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
#  Toast — floating, self-dismissing notification (non-blocking feedback)
# ════════════════════════════════════════════════════════════════════════
class Toast(tk.Toplevel):
    _active = []   # class-level stack, so multiple toasts don't overlap

    def __init__(self, app, message, kind="info", duration=2600):
        super().__init__(app)
        self.app = app
        t = app.theme
        colors = {"info": t["accent"], "success": t["success"],
                  "warn": t["warn"], "error": t["danger"]}
        icons = {"info": "ℹ", "success": "✓", "warn": "⚠", "error": "✕"}
        edge = colors.get(kind, t["accent"])
        self.overrideredirect(True)
        try:
            self.attributes("-topmost", True)
            self.attributes("-alpha", 0.0)
        except Exception:
            pass
        self.configure(bg=edge)
        frame = tk.Frame(self, bg=t["panel"])
        frame.pack(fill="both", expand=True, padx=1, pady=1)
        row = tk.Frame(frame, bg=t["panel"])
        row.pack(fill="both", expand=True, padx=14, pady=10)
        tk.Label(row, text=icons.get(kind, "ℹ"), bg=t["panel"], fg=edge,
                 font=(FONT_UI[0], 13, "bold")).pack(side="left", padx=(0, 8))
        tk.Label(row, text=message, bg=t["panel"], fg=t["text"],
                 font=(FONT_UI[0], 10), wraplength=260, justify="left").pack(side="left")
        self.update_idletasks()
        w, h = max(160, self.winfo_reqwidth()), self.winfo_reqheight()
        Toast._active = [tt for tt in Toast._active if tt.winfo_exists()]
        stack_offset = sum(tt.winfo_height() + 10 for tt in Toast._active) if Toast._active else 0
        try:
            x = app.winfo_rootx() + app.winfo_width() - w - 26
            y = app.winfo_rooty() + app.winfo_height() - h - 48 - stack_offset
        except Exception:
            x, y = 100, 100
        self.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")
        Toast._active.append(self)
        self.duration = duration
        self.bind("<Button-1>", lambda e: self._fade_out(0.94))
        self._fade_in()

    def _fade_in(self, a=0.0):
        if not self.winfo_exists():
            return
        a = min(0.96, a + 0.14)
        try:
            self.attributes("-alpha", a)
        except Exception:
            pass
        if a < 0.96:
            self.after(10, lambda: self._fade_in(a))
        else:
            self.after(self.duration, self._fade_out)

    def _fade_out(self, a=0.96):
        if not self.winfo_exists():
            return
        a = max(0.0, a - 0.12)
        try:
            self.attributes("-alpha", a)
        except Exception:
            pass
        if a > 0:
            self.after(12, lambda: self._fade_out(a))
        else:
            try:
                Toast._active.remove(self)
            except ValueError:
                pass
            try:
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
        try:
            x = self.widget.winfo_rootx() + 10
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
            self.tip = tk.Toplevel(self.widget)
            self.tip.wm_overrideredirect(True)
            self.tip.wm_geometry(f"+{x}+{y}")
            tk.Label(self.tip, text=self.text, bg="#111116", fg="white",
                     font=(FONT_UI[0], 9), padx=8, pady=4, bd=0).pack()
        except Exception:
            self.tip = None

    def _hide(self, _e=None):
        if self.tip:
            try:
                self.tip.destroy()
            except Exception:
                pass
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
            try:
                self.command()
            except Exception:
                traceback.print_exc()
                try:
                    messagebox.showerror(
                        f"{APP_NAME} — action failed",
                        "Something went wrong running that action, but the "
                        "app is still running.\n\nDetails:\n" + traceback.format_exc(limit=2))
                except Exception:
                    pass
        # FIX (v3/v4): the command above may rebuild the UI and destroy this
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
    _citem: object = field(default=None, repr=False, compare=False)


# ════════════════════════════════════════════════════════════════════════
#  PDF ENGINE — pure logic, no Tk. Independently testable / reusable.
# ════════════════════════════════════════════════════════════════════════
class PDFEngine:
    @staticmethod
    def render_page(doc, index, zoom) -> "Image.Image":
        page = doc[index]
        zoom = max(0.05, float(zoom))
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

    @staticmethod
    def flatten(doc, annotations: dict, out_path: str):
        out = fitz.open()
        out.insert_pdf(doc)
        skipped = []
        for idx, items in annotations.items():
            if idx >= len(out) or not items:
                continue
            page = out[idx]
            # ── "Edit existing text" annotations are applied FIRST, as real
            # redactions: the original PDF text is erased (white box) and the
            # replacement is baked into the page content stream in its place.
            edits = [a for a in items if a.kind == "edit_text" and len(a.points) == 2]
            for a in edits:
                try:
                    r = fitz.Rect(*a.points[0], *a.points[1])
                    col = hexrgb(a.color)
                    page.add_redact_annot(
                        r, text=a.text or "", fontsize=a.fontsize, fontname="helv",
                        text_color=col, fill=(1, 1, 1), align=0,
                    )
                except Exception:
                    skipped.append(a)
            if edits:
                try:
                    page.apply_redactions()
                except Exception:
                    pass
            shape = page.new_shape()
            for a in items:
                if a.kind == "edit_text":
                    continue  # already applied above via redaction
                try:
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
                except Exception:
                    # A single malformed annotation should never abort the whole
                    # export — skip it and keep going.
                    skipped.append(a)
            try:
                shape.commit(overlay=True)
            except Exception:
                pass
        out.save(out_path, garbage=4, deflate=True)
        out.close()
        return skipped

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
        if n == 0:
            doc.close()
            raise ValueError("Source PDF has no pages.")
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
        self.bind("<Escape>", lambda e: self.destroy())
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
        # Route every uncaught exception from any Tk callback (button click,
        # menu command, keyboard shortcut, timer, ...) through one friendly
        # handler instead of letting it crash / freeze the whole app.
        self.report_callback_exception = self._on_tk_exception
        self.title(f"{APP_NAME}")
        self.geometry("1380x870")
        self.minsize(1040, 640)
        self.dark = False
        self.theme_name = "light"
        self.theme = LIGHT
        self.focus_mode = False
        self.sidebar_tab = "pages"
        self._outline_entries = []
        self.configure(bg=self.theme["bg"])
        self._logo_photo_refs = []   # keep PhotoImage refs alive
        self._ico_path = None
        self._apply_app_icon()
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
        self._drag_last_pt = None
        # search state
        self._search_hits = []
        self._search_hit_index = -1
        # canvas background gradient state
        self._canvas_bg_photo = None
        self._bg_resize_job = None
        self._build_menu()
        self._build_layout()
        self._bind_shortcuts()
        self._refresh_tool_highlight()

    # ─────────────────────────────────────────── toast notifications
    def _toast(self, message, kind="info"):
        try:
            Toast(self, message, kind=kind)
        except Exception:
            pass

    # ─────────────────────────────────────────── error handling
    def _on_tk_exception(self, exc, val, tb):
        """Central safety net: any exception raised inside a Tk-driven
        callback lands here instead of propagating up and killing / hanging
        the app. We log it to the console and tell the user, then keep going."""
        try:
            traceback.print_exception(exc, val, tb)
        except Exception:
            pass
        try:
            self._set_status("An error occurred — see details for what happened.")
        except Exception:
            pass
        try:
            detail = "".join(traceback.format_exception(exc, val, tb))[-1200:]
            messagebox.showerror(
                f"{APP_NAME} — something went wrong",
                "An unexpected error happened, but " + APP_NAME + " is still "
                "running and your document/annotations are safe.\n\n"
                "Technical details:\n" + detail)
        except Exception:
            pass

    # ─────────────────────────────────────────── branding / icon
    def _apply_app_icon(self):
        try:
            img = make_logo_image(256)
            photo = ImageTk.PhotoImage(img)
            self._logo_photo_refs.append(photo)
            self.iconphoto(True, photo)
            if sys.platform.startswith("win"):
                try:
                    ico_dir = os.path.join(os.path.expanduser("~"), ".apexpdf")
                    os.makedirs(ico_dir, exist_ok=True)
                    ico_path = os.path.join(ico_dir, "apexpdf.ico")
                    img.save(ico_path, format="ICO",
                             sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
                    self.iconbitmap(default=ico_path)
                    self._ico_path = ico_path
                except Exception:
                    pass
        except Exception:
            pass

    def _make_small_logo_photo(self, size=28):
        try:
            photo = ImageTk.PhotoImage(make_logo_image(size))
            self._logo_photo_refs.append(photo)
            return photo
        except Exception:
            return None

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
        self.sidebar = tk.Frame(mid, bg=t["sidebar"], width=180)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        header = tk.Frame(self.sidebar, bg=t["sidebar"])
        header.pack(fill="x", padx=14, pady=(14, 6))
        logo_photo = self._make_small_logo_photo(26)
        if logo_photo:
            tk.Label(header, image=logo_photo, bg=t["sidebar"]).pack(side="left", padx=(0, 6))
        tk.Label(header, text=APP_NAME, bg=t["sidebar"], fg=t["text"],
                  font=(FONT_UI[0], 12, "bold")).pack(side="left")
        # ── Segmented "Pages / Outline" tab control ─────────────────────
        tabbar = tk.Frame(self.sidebar, bg=t["sidebar"])
        tabbar.pack(fill="x", padx=14, pady=(2, 6))
        self.sidebar_tabbar = tabbar
        self._pages_tab_btn = RoundButton(tabbar, t, text="Pages",
                                           command=lambda: self._show_sidebar_tab("pages"),
                                           width=74, height=25, radius=7, fontsize=10)
        self._pages_tab_btn.pack(side="left", padx=(0, 4))
        self._outline_tab_btn = RoundButton(tabbar, t, text="Outline",
                                             command=lambda: self._show_sidebar_tab("outline"),
                                             width=74, height=25, radius=7, fontsize=10)
        self._outline_tab_btn.pack(side="left")
        # ── Pages tab: page thumbnails (existing behaviour) ─────────────
        self.pages_container = tk.Frame(self.sidebar, bg=t["sidebar"])
        tk.Label(self.pages_container, text="PAGES", bg=t["sidebar"], fg=t["subtext"],
                  font=(FONT_UI[0], 10, "bold")).pack(anchor="w", pady=(0, 4))
        self.thumb_canvas = tk.Canvas(self.pages_container, bg=t["sidebar"], highlightthickness=0)
        self.thumb_scroll = ttk.Scrollbar(self.pages_container, orient="vertical", command=self.thumb_canvas.yview)
        self.thumb_frame = tk.Frame(self.thumb_canvas, bg=t["sidebar"])
        self.thumb_frame.bind("<Configure>", lambda e: self.thumb_canvas.configure(
            scrollregion=self.thumb_canvas.bbox("all")))
        self.thumb_canvas.create_window((0, 0), window=self.thumb_frame, anchor="nw")
        self.thumb_canvas.configure(yscrollcommand=self.thumb_scroll.set)
        self.thumb_canvas.pack(side="left", fill="both", expand=True)
        self.thumb_scroll.pack(side="right", fill="y")
        self.thumb_canvas.bind("<MouseWheel>", self._on_thumb_mousewheel)
        self.thumb_canvas.bind("<Button-4>", self._on_thumb_mousewheel)
        self.thumb_canvas.bind("<Button-5>", self._on_thumb_mousewheel)
        # ── Outline tab: real PDF table-of-contents / bookmarks ─────────
        self.outline_container = tk.Frame(self.sidebar, bg=t["sidebar"])
        tk.Label(self.outline_container, text="BOOKMARKS", bg=t["sidebar"], fg=t["subtext"],
                  font=(FONT_UI[0], 10, "bold")).pack(anchor="w", pady=(0, 4))
        self.outline_listbox = tk.Listbox(self.outline_container, font=(FONT_UI[0], 10), bg=t["sidebar"],
                                           fg=t["text"], selectbackground=t["accent"], selectforeground="white",
                                           activestyle="none", relief="flat", highlightthickness=0, bd=0)
        self.outline_listbox.pack(fill="both", expand=True)
        self.outline_listbox.bind("<<ListboxSelect>>", self._on_outline_select)
        self.outline_empty_label = tk.Label(self.outline_container, text="Open a PDF to see its bookmarks.",
                                             bg=t["sidebar"], fg=t["subtext"], font=(FONT_UI[0], 9),
                                             wraplength=150, justify="left")
        self._show_sidebar_tab(self.sidebar_tab)
        self._populate_outline()
        center = tk.Frame(mid, bg=t["canvas_bg"])
        center.pack(side="left", fill="both", expand=True)
        self.center_frame = center
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
        self.page_canvas.bind("<Configure>", self._on_canvas_configure)
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
        # Paint the branded empty-state (logo + Open button) once the canvas
        # has an actual size — <Configure> will keep it correct on resize too.
        self.after(60, lambda: self._regen_canvas_bg(force=True))

    def _build_toolbar(self):
        for w in self.toolbar.winfo_children():
            w.destroy()
        t = self.theme
        brand = tk.Frame(self.toolbar, bg=t["toolbar"])
        brand.pack(side="left", padx=(14, 6), pady=10)
        logo_photo = self._make_small_logo_photo(30)
        if logo_photo:
            tk.Label(brand, image=logo_photo, bg=t["toolbar"]).pack(side="left", padx=(0, 6))
        tk.Label(brand, text=APP_NAME, bg=t["toolbar"], fg=t["text"],
                  font=(FONT_UI[0], 13, "bold")).pack(side="left")
        sep = tk.Frame(self.toolbar, bg=t["border"], width=1)
        sep.pack(side="left", fill="y", pady=10, padx=6)
        left = tk.Frame(self.toolbar, bg=t["toolbar"])
        left.pack(side="left", padx=6, pady=10)
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
        RoundButton(right, t, icon=THEME_ICON.get(self.theme_name, "🌙"), text="",
                    command=self.toggle_theme, width=42,
                    tooltip=THEME_TOOLTIP.get(self.theme_name, "Cycle theme")
                    ).pack(side="left", padx=3)
        RoundButton(right, t, icon="⛶", text="", command=self.toggle_focus_mode, width=42,
                    kind="accent" if self.focus_mode else "normal",
                    tooltip="Focus mode (Ctrl+Shift+F)").pack(side="left", padx=3)
        RoundButton(right, t, icon="📊", text="", command=self.show_document_stats, width=42,
                    tooltip="Document statistics").pack(side="left", padx=3)
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
        filem.add_command(label="Quit                    Ctrl+Q", command=self.quit)
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
        toolm.add_separator()
        toolm.add_command(label="Document Statistics…", command=self.show_document_stats)
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
        viewm.add_command(label="Cycle Theme (Light/Dark/Sepia)  Ctrl+Shift+T", command=self.toggle_theme)
        viewm.add_command(label="Toggle Focus Mode        Ctrl+Shift+F", command=self.toggle_focus_mode)
        m.add_cascade(label="View", menu=viewm)
        helpm = tk.Menu(m, tearoff=0)
        helpm.add_command(label="Document Statistics…", command=self.show_document_stats)
        helpm.add_command(label="Keyboard Shortcuts", command=self._show_shortcuts)
        helpm.add_command(label=f"About {APP_NAME}", command=self._show_about)
        m.add_cascade(label="Help", menu=helpm)

    def _bind_shortcuts(self):
        self.bind("<Control-o>", lambda e: self.open_pdf())
        self.bind("<Control-s>", lambda e: self.save_pdf())
        self.bind("<Control-z>", lambda e: self.undo())
        self.bind("<Control-y>", lambda e: self.redo())
        self.bind("<Control-d>", lambda e: self._duplicate_selected())
        self.bind("<Control-plus>", lambda e: self.zoom_in())
        self.bind("<Control-equal>", lambda e: self.zoom_in())
        self.bind("<Control-minus>", lambda e: self.zoom_out())
        self.bind("<Control-0>", lambda e: self.zoom_actual())
        self.bind("<Control-k>", lambda e: self.open_command_palette())
        self.bind("<Control-f>", lambda e: self.open_find())
        self.bind("<Control-q>", lambda e: self.quit())
        self.bind("<Control-Shift-F>", lambda e: self.toggle_focus_mode())
        self.bind("<Control-Shift-T>", lambda e: self.toggle_theme())
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
            "Ctrl+K  Command palette\nCtrl+F  Find in document\nCtrl+Q  Quit\n"
            "Ctrl+Shift+T  Cycle Light / Dark / Sepia theme\n"
            "Ctrl+Shift+F  Toggle Focus Mode\n"
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

    def _show_about(self):
        try:
            win = tk.Toplevel(self)
            t = self.theme
            win.title(f"About {APP_NAME}")
            win.configure(bg=t["panel"])
            win.resizable(False, False)
            win.transient(self)
            w, h = 360, 300
            x = self.winfo_rootx() + (self.winfo_width() - w) // 2
            y = self.winfo_rooty() + (self.winfo_height() - h) // 2
            win.geometry(f"{w}x{h}+{x}+{y}")
            photo = ImageTk.PhotoImage(make_logo_image(96))
            self._logo_photo_refs.append(photo)
            tk.Label(win, image=photo, bg=t["panel"]).pack(pady=(24, 10))
            tk.Label(win, text=APP_NAME, bg=t["panel"], fg=t["text"],
                      font=(FONT_UI[0], 18, "bold")).pack()
            tk.Label(win, text=f"Version {APP_VERSION}", bg=t["panel"], fg=t["subtext"],
                      font=(FONT_UI[0], 11)).pack(pady=(2, 10))
            tk.Label(win, text=f"by {APP_AUTHOR}", bg=t["panel"], fg=t["subtext"],
                      font=(FONT_UI[0], 10)).pack()
            tk.Label(win, text="Advanced PDF editor, converter & annotator.",
                      bg=t["panel"], fg=t["subtext"], font=(FONT_UI[0], 9),
                      wraplength=300, justify="center").pack(pady=(14, 0))
            RoundButton(win, t, text="Close", kind="accent", command=win.destroy,
                        width=120).pack(pady=18)
            try:
                win.grab_set()
            except tk.TclError:
                pass
        except Exception:
            traceback.print_exc()

    # ─────────────────────────────────────────── document statistics
    def show_document_stats(self):
        if not self.doc:
            messagebox.showinfo("No document", "Open a PDF first.")
            return
        try:
            n_pages = len(self.doc)
            total_words = total_chars = total_images = 0
            for page in self.doc:
                txt = page.get_text() or ""
                total_chars += len(txt)
                total_words += len(txt.split())
                try:
                    total_images += len(page.get_images())
                except Exception:
                    pass
            n_anns = sum(len(v) for v in self.annotations.values())
            size_bytes = os.path.getsize(self.doc_path) if self.doc_path and os.path.exists(self.doc_path) else 0
            size_str = (f"{size_bytes / 1024:.1f} KB" if size_bytes < 1024 * 1024
                        else f"{size_bytes / 1024 / 1024:.2f} MB")
            encrypted = "Yes" if (self.doc.needs_pass or getattr(self.doc, "is_encrypted", False)) else "No"
            try:
                toc_count = len(self.doc.get_toc(simple=True))
            except Exception:
                toc_count = 0
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Couldn't compute statistics", str(e))
            return
        try:
            t = self.theme
            win = tk.Toplevel(self)
            win.title("Document Statistics")
            win.configure(bg=t["panel"])
            win.resizable(False, False)
            win.transient(self)
            w, h = 430, 470
            x = self.winfo_rootx() + (self.winfo_width() - w) // 2
            y = self.winfo_rooty() + (self.winfo_height() - h) // 2
            win.geometry(f"{w}x{h}+{x}+{y}")
            tk.Label(win, text="📊  Document Statistics", bg=t["panel"], fg=t["text"],
                      font=(FONT_UI[0], 15, "bold")).pack(pady=(22, 4))
            tk.Label(win, text=os.path.basename(self.doc_path or "Untitled"), bg=t["panel"],
                      fg=t["subtext"], font=(FONT_UI[0], 10)).pack(pady=(0, 14))
            grid = tk.Frame(win, bg=t["panel"])
            grid.pack(padx=24, fill="x")
            stats = [
                ("Pages", str(n_pages)), ("Words", f"{total_words:,}"),
                ("Characters", f"{total_chars:,}"), ("Images embedded", str(total_images)),
                ("Annotations added", str(n_anns)), ("Bookmarks", str(toc_count)),
                ("File size", size_str), ("Encrypted", encrypted),
            ]
            for i, (label, value) in enumerate(stats):
                cell = tk.Frame(grid, bg=t["bg"], highlightbackground=t["border"], highlightthickness=1)
                cell.grid(row=i // 2, column=i % 2, sticky="nsew", padx=6, pady=6, ipady=8)
                grid.grid_columnconfigure(i % 2, weight=1)
                tk.Label(cell, text=value, bg=t["bg"], fg=t["accent"],
                          font=(FONT_UI[0], 16, "bold")).pack(pady=(6, 0))
                tk.Label(cell, text=label.upper(), bg=t["bg"], fg=t["subtext"],
                          font=(FONT_UI[0], 8, "bold")).pack(pady=(0, 6))
            RoundButton(win, t, text="Close", kind="accent", command=win.destroy,
                        width=120).pack(pady=18)
            try:
                win.grab_set()
            except tk.TclError:
                pass
        except Exception:
            traceback.print_exc()

    # ─────────────────────────────────────────── theme
    def toggle_theme(self):
        """Cycle Light → Dark → Sepia (reading mode) → Light. Kept under its
        original name since menus / shortcuts / the command palette call it."""
        idx = THEME_ORDER.index(self.theme_name) if self.theme_name in THEME_ORDER else 0
        self.theme_name = THEME_ORDER[(idx + 1) % len(THEME_ORDER)]
        self.dark = (self.theme_name == "dark")
        self.theme = THEMES[self.theme_name]
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
        if hasattr(self, "pages_container"):
            self.sidebar_tabbar.configure(bg=t["sidebar"])
            self.pages_container.configure(bg=t["sidebar"])
            self.outline_container.configure(bg=t["sidebar"])
            self.outline_listbox.configure(bg=t["sidebar"], fg=t["text"], selectbackground=t["accent"])
            self.outline_empty_label.configure(bg=t["sidebar"], fg=t["subtext"])
            for btn in (self._pages_tab_btn, self._outline_tab_btn):
                btn.theme = t
                btn.configure(bg=t["sidebar"])
                btn.redraw()
        self._build_toolbar()
        self._build_right_panel()
        self._refresh_tool_highlight()
        self._regen_canvas_bg(force=True)
        if self.doc:
            self._render_thumbnails()
            self._render_current_page()
        self._toast(f"{self.theme_name.capitalize()} theme", kind="info")

    # ─────────────────────────────────────────── focus mode
    def toggle_focus_mode(self):
        """Hide the pages sidebar + style panel for a distraction-free view."""
        self.focus_mode = not self.focus_mode
        if self.focus_mode:
            self.sidebar.pack_forget()
            self.right_panel.pack_forget()
            self._toast("Focus mode on — Ctrl+Shift+F to exit", kind="info")
        else:
            self.sidebar.pack(side="left", fill="y", before=self.center_frame)
            self.right_panel.pack(side="right", fill="y")
            self._toast("Focus mode off", kind="info")

    # ─────────────────────────────────────────── document
    def open_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if path:
            self._open_path(path)

    def _open_path(self, path):
        try:
            newdoc = fitz.open(path)
        except Exception as e:
            messagebox.showerror("Open failed", str(e))
            return
        try:
            if self.doc is not None:
                try:
                    self.doc.close()
                except Exception:
                    pass
            self.doc = newdoc
            self.doc_path = path
            self.page_index = 0
            self.annotations = {}
            self.undo_stack.clear()
            self.redo_stack.clear()
            self.selected_ann = None
            self._search_hits = []
            self._search_hit_index = -1
            self.zoom = 1.6
            n = len(self.doc)
            if n == 0:
                messagebox.showwarning("Empty document", "This PDF has no pages.")
            dlg = ProgressDialog(self, title="Opening PDF…", determinate=True) if n > 3 else None
            self._render_current_page()
            self._render_thumbnails(progress_dialog=dlg)
            self._populate_outline()
            if dlg:
                dlg.close()
            if path in self.recent_files:
                self.recent_files.remove(path)
            self.recent_files.insert(0, path)
            self.recent_files = self.recent_files[:6]
            self._set_status(f"Opened {os.path.basename(path)} · {n} page(s)")
        except Exception as e:
            traceback.print_exc()
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
            skipped = PDFEngine.flatten(self.doc, self.annotations, out)
            self._set_status(f"Saved → {out}")
            if skipped:
                messagebox.showwarning(
                    "Saved with warnings",
                    f"Annotated PDF saved:\n{out}\n\n"
                    f"{len(skipped)} annotation(s) couldn't be applied and were skipped.")
                self._toast(f"Saved with {len(skipped)} warning(s)", kind="warn")
            else:
                messagebox.showinfo("Saved", f"Annotated PDF saved:\n{out}")
                self._toast("Saved successfully", kind="success")
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Save failed", str(e))
            self._toast("Save failed", kind="error")

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
            icon_value = self._ico_path or py
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
            key = winreg.CreateKey(
                winreg.HKEY_CURRENT_USER, r"Software\Classes\Applications\ApExPdF.exe\DefaultIcon")
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, icon_value)
            winreg.CloseKey(key)
            # ProgID Windows can associate with .pdf
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{app_id}")
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "ApEx PdF Document")
            winreg.CloseKey(key)
            key = winreg.CreateKey(
                winreg.HKEY_CURRENT_USER, rf"Software\Classes\{app_id}\DefaultIcon")
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, icon_value)
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
            try:
                img = PDFEngine.render_page(self.doc, i, 0.34)   # higher-res thumbs for HD screens
            except Exception:
                continue
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
        self._toast(f"Page {idx + 1} rotated", kind="success")

    def page_duplicate(self, idx):
        if not self.doc or not (0 <= idx < len(self.doc)):
            return
        self.doc.copy_page(idx, idx + 1)
        mapping = {i: (i if i <= idx else i + 1) for i in self.annotations}
        self._remap_annotations(mapping)
        self.go_to_page(idx + 1)
        self._populate_outline()
        self._set_status(f"Duplicated page {idx + 1}")
        self._toast(f"Page {idx + 1} duplicated", kind="success")

    def page_insert_blank(self, idx):
        if not self.doc:
            return
        rect = self.doc[idx].rect if 0 <= idx < len(self.doc) else fitz.paper_rect("a4")
        self.doc.new_page(pno=idx + 1, width=rect.width, height=rect.height)
        mapping = {i: (i if i <= idx else i + 1) for i in self.annotations}
        self._remap_annotations(mapping)
        self.go_to_page(idx + 1)
        self._populate_outline()
        self._set_status(f"Inserted blank page after {idx + 1}")
        self._toast(f"Blank page inserted after {idx + 1}", kind="success")

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
        self._populate_outline()
        self._set_status(f"Deleted page {idx + 1}")
        self._toast(f"Page {idx + 1} deleted", kind="warn")

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
        self._populate_outline()
        self._set_status(f"Moved page to {new_idx + 1}")
        self._toast(f"Page moved to position {new_idx + 1}", kind="success")

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
        if not self.doc or len(self.doc) == 0:
            return
        page = self.doc[self.page_index]
        canvas_w = self.page_canvas.winfo_width() or 900
        pw = max(1.0, page.rect.width)
        self.zoom = max(0.2, min(6.0, (canvas_w - 20) / pw))
        self._render_current_page()

    def zoom_fit_page(self):
        """Fit the whole page (width AND height) inside the visible canvas —
        the classic PDF-viewer 'Fit Page' option, as opposed to Fit Width."""
        if not self.doc or len(self.doc) == 0:
            return
        page = self.doc[self.page_index]
        canvas_w = self.page_canvas.winfo_width() or 900
        canvas_h = self.page_canvas.winfo_height() or 700
        pw = max(1.0, page.rect.width)
        ph = max(1.0, page.rect.height)
        zw = (canvas_w - 24) / pw
        zh = (canvas_h - 24) / ph
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
        bbox = c.bbox("page")
        x0, y0, x1, y1 = bbox if bbox else (0, 0, cw, ch)
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

    # ─────────────────────────────────────────── sidebar tabs (Pages / Outline)
    def _show_sidebar_tab(self, name):
        self.sidebar_tab = name
        for frame in (getattr(self, "pages_container", None), getattr(self, "outline_container", None)):
            if frame is not None:
                frame.pack_forget()
        if name == "outline":
            self.outline_container.pack(fill="both", expand=True, padx=(14, 8), pady=(0, 10))
            self._pages_tab_btn.set_active(False)
            self._outline_tab_btn.set_active(True)
        else:
            self.pages_container.pack(fill="both", expand=True, padx=(8, 4), pady=(0, 10))
            self._pages_tab_btn.set_active(True)
            self._outline_tab_btn.set_active(False)

    def _populate_outline(self):
        """Load the PDF's real table-of-contents/bookmarks into the Outline tab."""
        if not hasattr(self, "outline_listbox"):
            return
        self.outline_listbox.delete(0, "end")
        self._outline_entries = []
        if not self.doc:
            self.outline_empty_label.configure(text="Open a PDF to see its bookmarks.")
            self.outline_empty_label.pack(pady=10)
            return
        try:
            toc = self.doc.get_toc(simple=True)
        except Exception:
            toc = []
        if not toc:
            self.outline_empty_label.configure(text="This PDF has no bookmarks.")
            self.outline_empty_label.pack(pady=10)
            return
        self.outline_empty_label.pack_forget()
        for level, title, page in toc:
            indent = "    " * max(0, (level or 1) - 1)
            self.outline_listbox.insert("end", f"{indent}{(title or '').strip()}")
            self._outline_entries.append(max(0, (page or 1) - 1))

    def _on_outline_select(self, _e=None):
        sel = self.outline_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if 0 <= idx < len(self._outline_entries):
            self.go_to_page(self._outline_entries[idx])

    # ─────────────────────────────────────────── canvas background (HD gradient)
    def _on_canvas_configure(self, event):
        if self._bg_resize_job:
            try:
                self.after_cancel(self._bg_resize_job)
            except Exception:
                pass
        w, h = event.width, event.height
        self._bg_resize_job = self.after(120, lambda: self._regen_canvas_bg(w, h))

    def _regen_canvas_bg(self, w=None, h=None, force=False):
        self._bg_resize_job = None
        c = getattr(self, "page_canvas", None)
        if c is None or not c.winfo_exists():
            return
        if w is None or h is None:
            w = c.winfo_width(); h = c.winfo_height()
        if w <= 1 or h <= 1:
            return
        try:
            t = self.theme
            img = make_canvas_gradient(w, h, t.get("grad_top", t["canvas_bg"]),
                                        t.get("grad_bottom", t["canvas_bg"]), watermark=True)
            self._canvas_bg_photo = ImageTk.PhotoImage(img)
            c.delete("canvasbg")
            c.create_image(0, 0, anchor="nw", image=self._canvas_bg_photo, tags="canvasbg")
            c.tag_lower("canvasbg")
            if self.doc:
                for tag in ("page", "ann", "sel", "hit", "live"):
                    try:
                        c.tag_raise(tag)
                    except Exception:
                        pass
            else:
                self._render_empty_state(w, h)
        except Exception:
            pass

    def _render_empty_state(self, w=None, h=None):
        """Branded 'no document open' screen: the ApEx PdF logo centered over
        the HD gradient backdrop, with a big Open-PDF button and a quick list
        of recent files — shown instead of a blank canvas."""
        c = getattr(self, "page_canvas", None)
        if c is None or not c.winfo_exists() or self.doc:
            return
        c.delete("emptystate")
        if w is None or h is None:
            w = c.winfo_width(); h = c.winfo_height()
        if w <= 1 or h <= 1:
            return
        t = self.theme
        try:
            cx, cy = w / 2, max(120, h / 2 - 90)
            # logo (cached — regenerated only once, just repositioned on resize)
            if getattr(self, "_empty_logo_photo", None) is None:
                self._empty_logo_photo = ImageTk.PhotoImage(make_logo_image(132))
            c.create_image(cx, cy, image=self._empty_logo_photo, tags="emptystate")
            c.create_text(cx, cy + 92, text=APP_NAME, font=(FONT_UI[0], 24, "bold"),
                           fill=t["text"], tags="emptystate")
            c.create_text(cx, cy + 120, text="Advanced PDF editor · converter · annotator",
                           font=(FONT_UI[0], 11), fill=t["subtext"], tags="emptystate")
            # Open PDF button (canvas-drawn, clickable)
            bw, bh = 210, 46
            bx0, by0 = cx - bw / 2, cy + 150
            pts = round_rect_pts(bx0, by0, bx0 + bw, by0 + bh, 13)
            c.create_polygon(pts, smooth=True, fill=t["accent"], outline="",
                              tags=("emptystate", "emptyopenbtn"))
            c.create_text(cx, by0 + bh / 2, text="📂  Open a PDF", fill="#FFFFFF",
                           font=(FONT_UI[0], 12, "bold"), tags=("emptystate", "emptyopenbtn"))
            c.tag_bind("emptyopenbtn", "<Button-1>", lambda e: self.open_pdf())
            c.tag_bind("emptyopenbtn", "<Enter>", lambda e: c.configure(cursor="hand2"))
            c.tag_bind("emptyopenbtn", "<Leave>", lambda e: c.configure(cursor="arrow"))
            # Ctrl+K hint
            c.create_text(cx, by0 + bh + 24, text="or press Ctrl+K for the Command Palette",
                           font=(FONT_UI[0], 9), fill=t["subtext"], tags="emptystate")
            # Recent files quick-open list
            if self.recent_files:
                ry = by0 + bh + 54
                c.create_text(cx, ry, text="RECENT FILES", font=(FONT_UI[0], 9, "bold"),
                               fill=t["subtext"], tags="emptystate")
                ry += 22
                for p in self.recent_files[:5]:
                    name = os.path.basename(p)
                    item = c.create_text(cx, ry, text=name, font=(FONT_UI[0], 10, "underline"),
                                          fill=t["accent"], tags=("emptystate", f"recent_{ry}"))
                    tag = f"recent_{ry}"
                    c.tag_bind(tag, "<Button-1>", lambda e, pp=p: self._open_path(pp))
                    c.tag_bind(tag, "<Enter>", lambda e: c.configure(cursor="hand2"))
                    c.tag_bind(tag, "<Leave>", lambda e: c.configure(cursor="arrow"))
                    ry += 20
        except Exception:
            pass

    def _render_current_page(self):
        if not self.doc:
            self._render_empty_state()
            return
        self.page_canvas.delete("emptystate")
        if len(self.doc) == 0 or not (0 <= self.page_index < len(self.doc)):
            self.page_index = 0
        try:
            img = PDFEngine.render_page(self.doc, self.page_index, self.zoom)
        except Exception as e:
            messagebox.showerror("Render failed", str(e))
            return
        self.tk_page_image = ImageTk.PhotoImage(img)
        # Only clear the page image itself — the gradient backdrop (drawn on
        # canvas resize) must survive so it never flickers/vanishes.
        self.page_canvas.delete("page")
        self.page_canvas.create_image(0, 0, anchor="nw", image=self.tk_page_image, tags="page")
        self.page_canvas.configure(scrollregion=(0, 0, img.width, img.height))
        if not self._canvas_bg_photo:
            self._regen_canvas_bg(force=True)
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
        z = self.zoom or 1.0
        return (pt[0] / z, pt[1] / z)

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
    def _text_box_canvas_size(self, ann):
        """Canvas-space (w, h) of a text/edit_text annotation's rendered box —
        must mirror both the on-canvas draw AND the exported PDF box so
        selection/hit-testing lines up with what the user actually sees."""
        fs_pdf = getattr(ann, "fontsize", 13) or 13
        lines = (ann.text or "").split("\n") or [""]
        max_len = max((len(ln) for ln in lines), default=0)
        box_w_pdf = max(60.0, max_len * fs_pdf * 0.62 + 10)
        box_h_pdf = fs_pdf * 1.35 * max(1, len(lines)) + 6
        return box_w_pdf * self.zoom, box_h_pdf * self.zoom

    def _bbox_canvas(self, ann):
        pts = [self._to_canvas(p) for p in ann.points]
        if ann.kind == "text" and pts:
            w, h = self._text_box_canvas_size(ann)
            x0, y0 = pts[0]
            pad = 4
            return (x0 - pad, y0 - pad, x0 + w + pad, y0 + h + pad)
        if ann.kind == "balloon" and len(pts) == 2:
            anchor, body = pts
            bw, bh = 150 * self.zoom / 1.6, 60 * self.zoom / 1.6
            x0, y0 = body[0] - bw / 2, body[1] - bh / 2
            x1, y1 = x0 + bw, y0 + bh
            xs = [x0, x1, anchor[0]]; ys = [y0, y1, anchor[1]]
            pad = max(8, ann.width + 4)
            return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)
        if not pts:
            return (0, 0, 0, 0)
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
                try:
                    c.coords(citem, p0[0], p0[1], p1[0], p1[1])
                    c.delete("sel")
                    self._draw_selection_handles()
                except Exception:
                    self._redraw_overlay()
            else:
                # multi-item shapes (balloon, text) or missing cache: safe fallback, full resync
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
        if not self.doc:
            return
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
            try:
                rects = self.doc[i].search_for(query, quads=False)
            except Exception:
                rects = []
            for r in rects:
                self._search_hits.append((i, r))
        if not self._search_hits:
            messagebox.showinfo("Find", f"No matches for \u201c{query}\u201d.")
            return
        self._search_hit_index = 0
        self._jump_to_hit()
        self._set_status(f"{len(self._search_hits)} match(es) for \u201c{query}\u201d — press Ctrl+F again to search anew")

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
            ("Cycle Light / Dark / Sepia Theme", self.toggle_theme),
            ("Toggle Focus Mode", self.toggle_focus_mode),
            ("Document Statistics…", self.show_document_stats),
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
            (f"About {APP_NAME}", self._show_about),
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
            messagebox.showinfo("No document", "Open a PDF first.")
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
            messagebox.showinfo("No document", "Open a PDF first.")
            return
        out_dir = filedialog.askdirectory(title="Choose output folder")
        if not out_dir:
            return
        self._run_async(lambda: PDFEngine.pdf_to_images(self.doc_path, out_dir, "PNG", 2.5),
                          lambda files: messagebox.showinfo("Exported", f"{len(files)} images saved to:\n{out_dir}"),
                          title="Exporting pages…")

    def export_text(self):
        if not self.doc:
            messagebox.showinfo("No document", "Open a PDF first.")
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
                    ang = int(a.get())
                    if ang % 90 != 0:
                        raise ValueError("Angle must be a multiple of 90.")
                    PDFEngine.rotate_pages(path, ang, out)
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
                    if not txt.get().strip():
                        raise ValueError("Watermark text can't be empty.")
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
                    if not u.get():
                        raise ValueError("A user password is required.")
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
    try:
        splash = Splash()
        splash.mainloop()
    except Exception:
        traceback.print_exc()
    try:
        app = AppleStudio()
        if _open_path_arg:
            app.after(150, lambda: app._open_path(_open_path_arg))
        app.mainloop()
    except Exception:
        traceback.print_exc()
        try:
            _r = tk.Tk(); _r.withdraw()
            messagebox.showerror(
                f"{APP_NAME} — startup failed",
                "The app couldn't start. Details:\n\n" + traceback.format_exc(limit=6))
        except Exception:
            pass
        sys.exit(1)

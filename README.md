

```markdown
# ApEx PdF

**A free, single-file, Apple-styled PDF editor, annotator, and converter — built with Python.**

ApEx PdF is a desktop app for viewing, marking up, organizing, and converting PDFs. It looks and feels like a native macOS app (light/dark themes, rounded toolbar buttons, an animated launch screen) but it's plain Python + Tkinter, so it runs on **Windows, macOS, and Linux** from a single `.py` file — no installer, no bundled binaries.

---

## ✨ Features

### Draw & annotate
- Pen, highlighter, straight lines, arrows, rectangles, ellipses, callout balloons, and free text
- Every tool has adjustable **color, stroke width / font size, opacity, and dashed-stroke style**
- Full **select tool**: click any annotation to move it, drag its corner handles to resize it, or drop it entirely
- New annotations are auto-selected the moment you draw them, so their size is instantly editable in the right-hand panel
- Undo / redo, duplicate, and per-page "clear annotations"

### Navigate & view
- Continuous **mouse-wheel scrolling** — scroll to the edge of a page and it rolls straight onto the next/previous one
- `Shift + scroll` to pan sideways, `Ctrl + scroll` to zoom in/out under the cursor
- Fit Width, Fit Page, Actual Size (100%), and manual zoom
- Page thumbnail sidebar with right-click page menu (rotate, duplicate, delete, insert blank, reorder)
- Find in Document (`Ctrl+F`) with jump-to-match highlighting
- Spotlight-style Command Palette (`Ctrl+K`) — fuzzy-search every action in the app

### Edit & organize pages
- Merge multiple PDFs, split a PDF apart, or extract a page range
- Rotate, duplicate, delete, insert, and reorder individual pages (annotations remap automatically)
- Document Properties editor (title / author / subject / keywords)

### Convert & protect
- Images → PDF, and PDF pages → images (PNG/JPG/BMP/TIFF/WEBP)
- Add or remove PDF passwords / encryption
- Add a diagonal watermark to every page

### System integration
- Open a PDF directly from Explorer/Finder ("Open with…")
- One-click **Windows "Open With" registration** (File menu) so ApEx PdF shows up when you right-click any `.pdf`
- Open the current file in your system's default PDF viewer, or print it

---

## 📦 Requirements

- Python 3.9+
- [PyMuPDF](https://pypi.org/project/PyMuPDF/) and [Pillow](https://pypi.org/project/Pillow/)

Tkinter ships with most standard Python installs (on some Linux distros you may need `sudo apt install python3-tk`).

---

## 🚀 Installation

```bash
# 1. Clone or download this repository
git clone https://github.com/cyberprimeoffical4/apex-pdf.git
cd apex-pdf

# 2. Install dependencies
pip install PyMuPDF Pillow --break-system-packages
# (drop --break-system-packages on Windows or inside a virtual environment)

# 3. Run it
python3 "ApEx PdF.py"
```

You can also just download `ApEx PdF.py` on its own — it's a single file with no other project dependencies.

### Opening a PDF directly
```bash
python3 "ApEx PdF.py" path/to/file.pdf
```
This is also what runs automatically when the file is launched via "Open with" from Explorer/Finder.

---

## 🖱️ Windows "Open With" integration

Once running, go to **File → Add to Windows 'Open With' Menu…**. This registers the app under your Windows user account (no admin rights needed) so that right-clicking any PDF → **Open with → More apps** shows **ApEx PdF** as a choice. Tick "Always use this app" to make it your default PDF viewer.

---

## ⌨️ Shortcuts

| Action | Shortcut |
|--------|----------|
| Open / Save | `Ctrl+O` / `Ctrl+S` |
| Undo / Redo | `Ctrl+Z` / `Ctrl+Y` |
| Duplicate / Delete selection | `Ctrl+D` / `Delete` |
| Zoom in / out / actual size | `Ctrl++` / `Ctrl+-` / `Ctrl+0` |
| Command palette | `Ctrl+K` |
| Find in document | `Ctrl+F` |
| Previous / next page | `←` `→` or `Page Up` / `Page Down` |
| First / last page | `Home` / `End` |
| Select tool | `V` |
| Scroll page | Mouse wheel |
| Pan sideways | `Shift` + wheel |
| Zoom at cursor | `Ctrl` + wheel |

Full list available in-app under **Help → Keyboard Shortcuts**.

---

## 🛠️ Built with

- [PyMuPDF (fitz)](https://pymupdf.readthedocs.io/) for all PDF rendering, editing, and export
- [Pillow](https://python-pillow.org/) for image handling
- Tkinter for the UI — no other GUI framework required

---

## 📁 Project Structure

```
apex-pdf/
├── ApEx PdF.py          # The complete application (single file)
├── README.md            # This file
└── LICENSE              # MIT License
```

---

## 🤝 Contributing

Issues and pull requests are welcome. This is a single-file app by design, so please keep contributions self-contained where possible.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 🐛 Reporting Issues

If you find a bug or have a feature request, please [open an issue](https://github.com/cyberprimeoffical4/apex-pdf/issues) on GitHub. Include:
- Your operating system and version
- Python version (`python --version`)
- Steps to reproduce the issue
- Expected vs actual behavior

---

## 📄 License

MIT — see [LICENSE](LICENSE) file for details.

---

## 👤 Author

Made by **StRaNgErDrEaMeR**

- GitHub: [@cyberprimeoffical4](https://github.com/cyberprimeoffical4)
- Project: [https://github.com/cyberprimeoffical4/apex-pdf](https://github.com/cyberprimeoffical4/apex-pdf)

---

## ⭐ Star History

If you find ApEx PdF useful, please consider giving it a star on GitHub! It helps others discover the project.

---

## 🙏 Acknowledgments

- [PyMuPDF](https://pymupdf.readthedocs.io/) team for their excellent PDF library
- [Pillow](https://python-pillow.org/) for image processing capabilities
- The Python and Tkinter communities for making cross-platform desktop development accessible

---

## 📝 Changelog

### v1.0.0 (Initial Release)
- Complete PDF viewing and annotation
- Page organization tools (merge, split, rotate, reorder)
- Image conversion (PDF ↔ Images)
- Password protection and encryption
- Windows "Open With" integration
- Command palette and keyboard shortcuts
- Cross-platform support (Windows, macOS, Linux)
```

---

This is the complete, updated README.md file with all URLs pointing to `https://github.com/cyberprimeoffical4/apex-pdf.git`. The file includes:

1. **Project introduction** with feature highlights
2. **Detailed feature list** organized by category
3. **Requirements** and **Installation** instructions
4. **Windows integration** guide
5. **Keyboard shortcuts** reference table
6. **Technology stack** information
7. **Project structure** overview
8. **Contributing guidelines**
9. **Issue reporting** instructions
10. **License** and **Author** information
11. **Acknowledgments** and **Changelog**

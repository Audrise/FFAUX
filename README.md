<h1 align="center">
  <strong>FFAUX</strong>
</h1>

<h3 align="center">Flexible Format Audio Utility eXchange</h3>

<div align="center">

  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/Python%203.10+-FFD43B?style=for-the-badge&logo=python&logoColor=3776AB"/>
  </a>
  <!-- <br> -->
  <a href="https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/index.html">
    <img src="https://img.shields.io/badge/PySide6-41CD52?style=for-the-badge&logo=qt&logoColor=white"/>
  </a>
  <a href="https://docs.pytest.org/en/stable/">
    <img src="https://img.shields.io/badge/PyTest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white"/>
  </a>
  <!-- <br> -->
  <img src="https://img.shields.io/badge/Windows%20GUI-0078D4?style=for-the-badge&logo=windows11&logoColor=white"/>
  <img src="https://img.shields.io/badge/Windows%20Terminal-0C0C0C?style=for-the-badge&logo=windows-terminal&logoColor=white"/>
  <br>
  <a href="https://github.com/Audrise/FFAUX">
    <img src="https://img.shields.io/badge/FFAUX-1.0.0-0078D4?style=for-the-badge"/>
  </a>
  <a href="https://github.com/Audrise/FFAUX?tab=GPL-3.0-1-ov-file">
    <img src="https://img.shields.io/badge/LICENSE-GPL%203.0-6B7280?style=for-the-badge"/>
  </a>
  <br>
  <img src="https://img.shields.io/github/stars/Audrise/FFAUX?style=social"/>
  <img src="https://img.shields.io/github/forks/Audrise/FFAUX?style=social"/>

</div>

## 📖 Description

<p align="center"><b>Python 3 based FFmpeg wrapper with a PySide6 GUI</b></p>

FFAUX is a desktop application I developed around my own workflow for managing digital audio.
It uses FFmpeg and FFprobe to handle audio conversion and metadata, while PySide6 provides a graphical, playlist-style interface. You can queue multiple audio files, configure conversion settings, and edit metadata without having to work from the command line.

FFAUX runs FFmpeg and FFprobe as external processes instead of reimplementing their functionality. Because of this, a working FFmpeg installation is required for audio conversion and media probing.

## 📑 Table of Contents

* **[📖 Description](#description)**
* **[📌 Features](#features)**
* **[📋 Requirements](#requirements)**
* **[📦 Installation](#installation)**
* **[🗂️ Structure](#structure)**
* **[🛠️ Troubleshooting](#troubleshooting)**
* **[📝 Changelog](#changelog)**

## 📌 Features

* Batch audio conversion with FFmpeg, with options for:

  * Output format
  * Sample rate
  * Bit depth
  * Bitrate
  * Resampling engine (SOXR)
  * Compression level
  * Custom output folder

* Playlist-style with drag-and-drop, multi-select, and resizable columns. Column widths are remembered between sessions and can be restored to their defaults from View -> Reset Column Widths.

* Aggregate progress panel for batch conversion jobs, which can be toggled from the View menu.

* Real-time FFmpeg log viewer, which can also be toggled from the View menu.

* Metadata editor for both single-file and multi-file (batch) editing:

  * Fields are generated from the tags actually present in the selected file(s), including non-standard tags such as ISRC and publisher. The editor is not limited to a fixed list of common fields.
  * Metadata templates can be saved, applied, and previewed in a separate window before being applied.

* Cover art viewer for previewing, replacing, and removing embedded cover art.

* Configurable FFmpeg and FFprobe executable paths through the settings dialog.

* Window size, position, and maximized state are remembered between sessions.

* Discord Rich Presence integration that shows the app's current status (idle / converting) on Discord. It can be left disabled, and the application continues normally if Discord is not installed or running.

## 📋 Requirements

* Python 3.10 or newer
* pip
* PySide6
* FFmpeg and FFprobe executables
* pypresence

## 📦Installation

### 🖥️ Desktop Application

The desktop application is distributed as a Windows installer with FFmpeg and FFprobe bundled with the application.

1. Download the latest release from the [FFAUX Releases](https://github.com/Audrise/FFAUX/releases) page.

2. Run the FFAUX installer and follow the setup instructions until the installation is complete.

3. Launch FFAUX from the Start Menu or the desktop shortcut if one was created during installation.

4. Configure the application according to your preferences. You can customize the available application settings, conversion options, metadata settings, and other preferences from within FFAUX.

5. Add your audio files by dragging and dropping them into the main window, or use the corresponding menu action.

6. Select one or more tracks and configure the desired conversion settings.

7. Start the conversion. Progress is shown in the aggregate progress panel, while detailed FFmpeg output is available in the log viewer.

> **Note:** The desktop release includes FFmpeg and FFprobe. No separate FFmpeg installation is required.

### ⌨️ CLI / From Source

For developers or users who want to run FFAUX directly from the source code:

1. Clone the repository:
   ```bash
   git clone https://github.com/Audrise/FFAUX.git
   cd FFAUX
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```

3. Activate the virtual environment:
   ```bash
   # Windows
   .venv\Scripts\activate
   ```

4. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Install FFmpeg:
   * [Download an FFmpeg build](https://ffmpeg.org/download.html), such as the builds provided by **gyan.dev** or **BtbN** for Windows.
   * Place `ffmpeg.exe` / `ffprobe.exe` in the `bin/` directory, or make sure they are available through the system PATH.
   * You can also configure their paths later from within the application.

6. Launch the FFAUX:
   ```bash
   python main.py
   ```
   - The main window will open with an empty track list and the main toolbar and menu.

   - Add audio files to the track list by dragging and dropping them into the main window, or use the corresponding menu action.

   - Select one or more tracks in the track table.

   - Open the conversion settings dialog and configure the output format, sample rate, bit depth, bitrate, and other available options.

   - Start the conversion. Progress is shown in the aggregate progress panel, while detailed FFmpeg output is available in the log viewer.

   - To edit metadata, select one or more tracks and open the metadata editor. The available fields are generated from the tags found in the selected file(s). You can apply a saved template, edit fields directly, or preview a template before applying it.

## 🗂️ Structure

```
FFAUX/
├── main.py                   # Application entry point
│
├── requirements.txt          # Python dependencies
│
├── bin/                      # Default location for ffmpeg.exe/ffprobe.exe
│
├── assets/
│   ├── icons/                # Application icons
│   │
│   ├── splash/               # Application splash screen
│   │
│   ├── styles/               # Qt stylesheets (QSS)
│   │
│   └── templates/            # Saved metadata templates
│
├── config/                   # Application configuration
│
├── core/                     # Backend logic (no GUI dependencies)
│
├── ffmpeg/                   # FFmpeg/FFprobe process wrappers
│
├── gui/                      # PySide6 presentation layer
│   ├── widgets/
│   │
│   └── dialogs/
│
├── utils/                    # Shared utility helpers
│
└── tests/                    # Automated tests (backend, no GUI required)
```

## 🛠️ Troubleshooting

### 1. The application cannot find FFmpeg or FFprobe.
- Make sure `ffmpeg` and `ffprobe` are either available through the system PATH, placed inside the `bin/` directory, or configured with the correct paths in the application's settings dialog.

### 2. Conversion fails immediately after starting.
- Check the log viewer for the FFmpeg error message. Common causes include an invalid output path, an unsupported input format, or an FFmpeg build that is not suitable for the target platform.

### 3. Metadata fields do not appear as expected.
- The metadata editor generates fields dynamically from the tags found in the selected file(s). If a field is missing, the source file may not contain that tag. When multiple files are selected, a combined, read-only value means that the selected files have different values for that field.

### 4. A tag name that used to be mixed/upper-case (e.g. `ISRC`, `REPLAYGAIN_TRACK_GAIN`) shows up in lowercase after editing metadata.
- This was a known issue where non-standard tag names were converted to lowercase when read from the file. The issue has since been fixed.
- Files that were already re-saved while the issue was present will keep their lowercased tag names. Re-tag them manually if you need to restore the original casing.

### 5. The application crashed with a `UnicodeDecodeError` (e.g. `'charmap' codec can't decode byte...`) while adding files or converting.
- This was caused by FFmpeg/FFprobe output being decoded using Windows' default codepage instead of UTF-8. The issue has since been fixed. If you still encounter it, include the affected file and the exact error message when reporting the problem.

### 6. Window size, position, or track table column widths don't persist between sessions.
- These settings are saved to `config/ffaux.json` when the application closes normally. Make sure the `config/` folder is writable, especially when using a packaged `.exe` installed in a restricted or read-only location.
- Column widths can be restored to their defaults from View -> Reset Column Widths.

### 7. Discord Rich Presence doesn't show up.
- Discord Rich Presence is optional and requires the `pypresence` package, a valid Discord `client_id`, and the Discord desktop application to be running locally. The browser version of Discord is not supported.
- If any of these requirements are missing, the application will continue running normally without showing a presence status.

### 8. The application window does not start or crashes on launch.
- Make sure the virtual environment is activated and that all dependencies from `requirements.txt` have been installed successfully.

<br>

<h1 align="center">DISCLAIMER!</h1>

**FFAUX** is developed strictly for **personal use**, **audio organization**, and **educational purposes**. 
This tool is designed to help you **view, edit, and manage audio metadata and cover art** in a safe, local environment. 
**it doesn't download, stream, or acquire audio content from any source.**

## 📝 Changelog

### v1.0.0 - **Initial Release FFAUX**

<h1></h1>
<h4 align="center">
   © 2026 Audrise. All rights reserved.
</h4>

<div align="center">
   <a href="#description">Back to top</a>
</div>
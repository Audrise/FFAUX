<h1 align="center">
  <strong>FFAUX</strong>
</h1>

<h3 align="center">Flexible Format Audio Utility eXchange</h3>

<div align=center>
    <a href="https://www.python.org/downloads/">
        <img src="https://img.shields.io/badge/Python 3.10+-FFD43B?style=for-the-badge&logo=python&logoColor=blue"/>
    </a>
    <a href="https://github.com/Audrise/FFAUX">
      <img src="https://img.shields.io/badge/Release v1.0.0-FFD43B?style=for-the-badge&logo=python&logoColor=blue"/>
    </a>
    <!-- <br> -->
    <a href="https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/index.html">
      <img src="https://img.shields.io/badge/PySide 6-neon?style=for-the-badge&logo=qt&logoColor=white"/>
    </a>
    <a href="https://docs.pytest.org/en/stable/">
    <img src="https://img.shields.io/badge/PyTest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white"/>
    </a>
    <a href="https://github.com/Audrise/FFAUX?tab=GPL-3.0-1-ov-file">
    <img src="https://img.shields.io/badge/GPL--3.0-blue?style=for-the-badge"/>
    </a>
    <!-- <br> -->
    <img src="https://img.shields.io/badge/windows%20GUI-blue?style=for-the-badge&logo=windows11&%20terminal&logoColor=white"/>
    <img src="https://img.shields.io/badge/windows%20terminal-blue?style=for-the-badge&logo=windows11&%20terminal&logoColor=white"/>
    <!-- <br> -->
    <img src="https://img.shields.io/github/stars/Audrise/FFAUX?style=social"/>
    <img src="https://img.shields.io/github/forks/Audrise/FFAUX?style=social"/>
</div>

## Description

<p align="center"><b>Python 3 based FFmpeg wrapper with a PySide6 GUI</b></p>

FFAUX is a desktop application I developed around my own workflow for managing digital audio.
It uses FFmpeg and FFprobe to handle audio conversion and metadata, while PySide6 provides a graphical, playlist-style interface. You can queue multiple audio files, configure conversion settings, and edit metadata without having to work from the command line.

FFAUX runs FFmpeg and FFprobe as external processes instead of reimplementing their functionality. Because of this, a working FFmpeg installation is required for audio conversion and media probing.

## Table of Contents

* **[Description](#description)**
* **[Features](#features)**
* **[Requirements](#requirements)**
* **[Installation](#installation)**
* **[Quick Start](#quick-start)**
* **[Structure](#structure)**
* **[Troubleshooting](#troubleshooting)**
* **[Changelog](#changelog)**

## Features

* Batch audio conversion with FFmpeg, with options for:

  * Output format
  * Sample rate
  * Bit depth
  * Bitrate
  * Resampling engine (SOXR)
  * Compression level
  * Custom output folder

* Playlist-style track table with drag-and-drop, multi-select, and resizable columns. Column widths are remembered between sessions and can be restored to their defaults from View -> Reset Column Widths.

* Aggregate progress panel for batch conversion jobs, which can be toggled from the View menu.

* Real-time FFmpeg log viewer, which can also be toggled from the View menu.

* Metadata editor for both single-file and multi-file (batch) editing:

  * Fields are generated from the tags actually present in the selected file(s), including non-standard tags such as ISRC and publisher. The editor is not limited to a fixed list of common fields.
  * When multiple selected tracks have different values for the same field, the editor shows a combined, read-only value. Saving without changing that field will not overwrite the original value in each track.
  * Metadata templates can be saved, applied, and previewed in a separate window before being applied.

* Cover art viewer for previewing, replacing, and removing embedded cover art.

* Configurable FFmpeg and FFprobe executable paths through the settings dialog.

* The "Convert Selected Audio" action is automatically disabled when the track list is empty.

* Window size, position, and maximized state are remembered between sessions.

* Discord Rich Presence integration that shows the app's current status (idle / converting) on Discord. It can be left disabled, and the application continues normally if Discord is not installed or running.

## Requirements

* Python 3.10 or newer
* pip
* PySide6
* FFmpeg and FFprobe executables
* pypresence (optional, only required for Discord Rich Presence. *The application runs normally without it*)

## Installation

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
   * Place `ffmpeg` and `ffprobe` (or `ffmpeg.exe` / `ffprobe.exe` on Windows) in the `bin/` directory, or make sure they are available through the system PATH.
   * You can also configure their paths later from within the application.

## Quick Start

1. Launch the application:

   ```bash
   python main.py
   ```

   The main window will open with an empty track list and the main toolbar and menu.

2. Add audio files to the track list by dragging and dropping them into the main window, or use the corresponding menu action.

3. Select one or more tracks in the track table.

4. Open the conversion settings dialog and configure the output format, sample rate, bit depth, bitrate, and other available options.

5. Start the conversion. Progress is shown in the aggregate progress panel, while detailed FFmpeg output is available in the log viewer.

6. To edit metadata, select one or more tracks and open the metadata editor. The available fields are generated from the tags found in the selected file(s). You can apply a saved template, edit fields directly, or preview a template before applying it.

## Structure

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

## Troubleshooting

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

## Changelog

### v1.0.0 - **Initial Release FFAUX**

<h1></h1>
<h4 align="center">
   © 2026 Audrise. All rights reserved.
</h4>

<div align="center">
   <a href="#description">Back to top</a>
</div>
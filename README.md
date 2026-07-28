<h1 align="center">
    <strong>AudriseFFTool</strong>
</h1>

<div align=center>
    <strong>Python 3-based FFmpeg wrapper that uses PySide6 for the GUI</strong>
</div>
<br>

<div align=center>
    <a href="https://www.python.org/">
        <img src="https://img.shields.io/badge/Python 3.10+-FFD43B?style=for-the-badge&logo=python&logoColor=blue"/>
    </a>
    <a href="https://github.com/Audrise/FFTool">
      <img src="https://img.shields.io/badge/FFTool 1.o-FFD43B?style=for-the-badge&logo=python&logoColor=blue"/>
    </a>
    <br>
    <a href="https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/index.html">
      <img src="https://img.shields.io/badge/PySide 6-neon?style=for-the-badge&logo=qt&logoColor=white"/>
    </a>
    <a href="https://docs.pytest.org/en/stable/">
    <img src="https://img.shields.io/badge/PyTest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white"/>
    </a>
    <img src="https://img.shields.io/badge/GPL--3.0-blue?style=for-the-badge"/>
    <br>
    <img src="https://img.shields.io/badge/windows%20GUI-blue?style=for-the-badge&logo=windows11&%20terminal&logoColor=white"/>
    <img src="https://img.shields.io/badge/windows%20terminal-blue?style=for-the-badge&logo=windows11&%20terminal&logoColor=white"/>
    <br>
    <img src="https://img.shields.io/github/stars/Audrise/FFTool?style=social"/>
    <img src="https://img.shields.io/github/forks/Audrise/FFTool?style=social"/>
    <br>
</div>
<br>

<h1 align="center">DISCLAIMER!</h1>
 
**AudriseFFTool** is developed strictly for **personal use**, **audio organization**, and **educational purposes**. This tool is designed to help you **view, edit, and manage audio metadata and cover art** in a **safe, local environment**. it doesn't download, stream, or acquire audio content from any source.
 
Any **unauthorized distribution, redistribution, or commercial use** of audio files you do not own or do not have explicit rights to modify may be considered **illegal** under applicable copyright law. The author(s) of this project are **not responsible** for any misuse of this software or for any copyright infringement resulting from files processed with it.
 
By using AudriseFFTool, you agree that you are solely responsible for ensuring you have the necessary rights or permissions for any audio file you edit, convert, or tag. Use this software responsibly.
 
## Description
AudriseFFTool is a desktop application for converting and tagging audio
files using FFmpeg and FFprobe. It provides a graphical, playlist-style
interface built with PySide6, allowing users to queue multiple audio
files, configure conversion settings, and edit metadata without using
the command line directly.
 
FFmpeg and FFprobe are invoked as external processes rather than being
reimplemented, so the application relies on a working FFmpeg
installation to perform any conversion or probing task.

## Table of Contents
* **[Description](#description)**
* **[Features](#features)**
* **[Requirements](#requirements)**
* **[installation](#installation)**
* **[Quick Start](#quick-start)**
* **[Structure](#structure)**
* **[Troubleshooting](#troubleshooting)**
* **[Changelog](#changelog)**

## Features
- Batch audio conversion via FFmpeg, with configurable:
  - Output format
  - Sample rate
  - Bit depth
  - Bitrate
  - Resampling engine (SOXR)
  - Compression level
  - Custom output folder
- Playlist-style track table supporting drag-and-drop and multi-select,
  with resizable columns. Column widths are remembered across sessions,
  and can be reset back to their defaults from View -> Reset Column
  Widths.
- Aggregate progress panel for batch conversion jobs, toggleable from
  the View menu.
- Real-time FFmpeg log viewer, toggleable from the View menu.
- Metadata editor supporting both single-file and multi-file (batch)
  editing:
  - Dynamic fields based on the tags actually present in the selected
    file(s), including non-standard tags (e.g. ISRC, publisher) --
    not just a fixed list of common fields.
  - Combined, read-only display for fields that differ across multiple
    selected tracks, so saving without editing them never overwrites
    each track's original value.
  - Metadata templates that can be saved, applied, and previewed in a
    separate window before applying.
- Cover art viewer for previewing, replacing, and removing embedded
  cover art.
- Configurable FFmpeg/FFprobe executable paths via a settings dialog.
- The "Convert Selected Audio" action is automatically disabled
  whenever the track list is empty.
- Window size, position, and maximized state are remembered across
  sessions.
- Optional Discord Rich Presence integration, showing the app's
  current status (idle / converting) on Discord. Safe to leave
  disabled, and fails silently if Discord isn't installed or running.

## Requirements
- Python 3.10 or newer
- pip
- PySide6
- FFmpeg and FFprobe executables
- pypresence (optional -- only required for Discord Rich Presence; the
  application runs normally without it)

FFmpeg is not bundled with the application and must be installed
separately. It must either be available on the system PATH, or placed
in the `bin/` directory of the project, or configured manually from
within the application's settings dialog.

## Installation
1. Clone the repository:

   ```bash
   git clone https://github.com/Audrise/FFTool.git
   cd FFTool
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

   - Download a FFmpeg build (e.g. from gyan.dev or BtbN for Windows).
   - Place `ffmpeg` and `ffprobe` (or `ffmpeg.exe` / `ffprobe.exe` on
     Windows) in the `bin/` directory, or ensure they are accessible
     via the system PATH.
   - Alternatively, configure their paths later from within the
     application.

## Quick Start
1. Launch the application:

   ```bash
   python main.py
   ```
    The main window will open, showing an empty track list and the maintoolbar/menu.

2. Add audio files to the track list by dragging and dropping them
   into the main window, or by using the corresponding menu action.
3. Select one or more tracks in the track table.
4. Open the conversion settings dialog to configure output format,
   sample rate, bit depth, bitrate, and other conversion options.
5. Start the conversion. Progress is displayed in the aggregate
   progress panel, and detailed output is available in the log
   viewer.
6. To edit metadata, select one or more tracks and open the metadata
   editor. Fields are generated dynamically based on the tags present
   in the selected file(s). Apply a saved template, edit fields
   directly, or preview a template's contents before applying it.

## Structure
```
AudriseFFTool/
├── main.py                  # Application entry point
├── requirements.txt         # Python dependencies
├── bin/                     # Optional location for ffmpeg/ffprobe executables
├── assets/
│   ├── icons/                # Application icons
│   ├── styles/                # Qt stylesheets (e.g. dark theme)
│   └── templates/             # Saved metadata templates
├── config/                  # Application configuration
├── core/                     # Backend logic (no GUI dependencies)
│   ├── config_service.py
│   ├── discord_presence_service.py
│   ├── ffmpeg_worker.py
│   ├── filename_parser.py
│   ├── job_manager.py
│   ├── metadata_field_merger.py
│   ├── metadata_service.py
│   ├── template_service.py
│   └── models/
├── ffmpeg/                   # FFmpeg/FFprobe process wrappers
│   ├── command_builder.py
│   ├── ffmpeg_runner.py
│   ├── ffprobe_runner.py
│   └── progress_parser.py
├── gui/                       # PySide6 presentation layer
│   ├── main_window.py
│   ├── widgets/
│   │   ├── track_table.py
│   │   ├── progress_panel.py
│   │   ├── log_viewer.py
│   │   ├── metadata_editor.py
│   │   └── cover_art_viewer.py
│   └── dialogs/
│       ├── conversion_settings_dialog.py
│       ├── metadata_editor_dialog.py
│       └── settings_dialog.py
├── utils/                    # Shared utility helpers
│   ├── file_utils.py
│   └── logger.py
└── tests/                    # Automated tests (backend, no GUI required)
```

## Troubleshooting
**The application cannot find FFmpeg or FFprobe.**
Verify that `ffmpeg` and `ffprobe` are either on the system PATH,
placed inside the `bin/` directory, or configured with the correct
path in the application's settings dialog.

**Conversion fails immediately after starting.**
Check the log viewer for the underlying FFmpeg error message. Common
causes include an invalid output path, unsupported input format, or
an incorrect FFmpeg build for the target platform.

**Metadata fields do not appear as expected.**
The metadata editor generates fields dynamically based on the tags
present in the selected file(s). If a field is missing, the source
file may not contain that tag. If multiple files are selected and a
field shows a combined, read-only value, this means the selected
files have differing values for that field.

**A tag name that used to be mixed/upper-case (e.g. `ISRC`,
`REPLAYGAIN_TRACK_GAIN`) shows up in lowercase after editing
metadata.**
This was a known issue where non-standard tag names were
force-lowercased when read from the file, and has since been fixed.
Files that were already re-saved while the issue was present will keep
their lowercased tag names; re-tag them manually if you need the
original casing back.

**The application crashed with a `UnicodeDecodeError` (e.g. `'charmap'
codec can't decode byte...`) while adding files or converting.**
This was caused by FFmpeg/FFprobe output being decoded using Windows'
default codepage instead of UTF-8, and has since been fixed. If you
still run into it, please note the exact file and error message when
reporting it.

**Window size, position, or track table column widths don't persist
between sessions.**
These are saved to `config/app_config.json` when the application
window is closed normally. Make sure the `config/` folder is writable
(this can be an issue for a packaged `.exe` installed to a
restricted/read-only location). Column widths can be reset to their
defaults anytime from View -> Reset Column Widths.

**Discord Rich Presence doesn't show up.**
This feature is optional and requires all of the following: the
`pypresence` package installed, a valid Discord `client_id`
configured, and the Discord desktop app (not the browser version)
running locally. If any of these are missing, the application
continues normally without showing a presence status.

**The application window does not start / crashes on launch.**
Confirm that the virtual environment is activated and that all
dependencies from `requirements.txt` were installed successfully.

## Changelog

### v1.0 - **Initial Release**

<h1></h1>
<h4 align="center">©AUDRISE</h4>
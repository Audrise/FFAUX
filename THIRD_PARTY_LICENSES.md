<h1 align="center">FFTool - Third-Party Licenses</H1>

<p align="center">
    This document contains licensing information for third-party software
    distributed with FFTool.
    The copyright and licenses for the following software remain the property
    of their respective copyright holders.
</p>

## 1. FFmpeg
FFTool bundles selected **FFmpeg** binaries for media processing.

The bundled FFmpeg executables and shared libraries are redistributed
without modification from the official **BtbN FFmpeg-Builds** release.

### Bundled Components
- `ffmpeg.exe`
- `ffprobe.exe`
- `avcodec-62.dll`
- `avdevice-62.dll`
- `avfilter-11.dll`
- `avformat-62.dll`
- `avutil-60.dll`
- `swresample-6.dll`
- `swscale-9.dll`

The following executable from the original distribution is **not included**:

- `ffplay.exe`

### Build Information
| Property | Value |
|---|---|
| **Provider** | BtbN FFmpeg-Builds |
| **Build** | <a href="https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-08-06-13-39/ffmpeg-n8.1.2-34-g9b6c8969e0-win64-gpl-shared-8.1.zip">`ffmpeg-n8.1.2-34-g9b6c8969e0-win64-gpl-shared-8.1`</a>
| **Architecture** | Windows x64 |
| **Configuration** | GPL shared build |
| **License** | GNU General Public License Version 3 (GPLv3) |

### Project Links
- **Project website:** https://ffmpeg.org/
- **Build provider:** https://github.com/BtbN/FFmpeg-Builds
- **Source code:** https://ffmpeg.org/download.html

### Copyright
Copyright (c) the FFmpeg developers.

### Why This Matters (GPLv3 & Dynamic Linking)
FFTool bundles FFmpeg's official **GPLv3-licensed** shared libraries
(the `.dll` files listed above) and dynamically links against them at
runtime. Because of this, FFTool as a whole is distributed under the
terms of the **GPLv3** as well (see the `LICENSE` file). In practice,
this means:

- FFTool's own source code is available under GPL-compatible terms.
- You are free to swap the bundled FFmpeg binaries for your own
  ABI-compatible build/version if you prefer.
- The corresponding source code for this exact FFmpeg build is
  available from the links above, matching the build info in the
  table above.

---

## 2. Qt for Python (PySide6)
**Project:** Qt for Python (PySide6)

**Purpose:** Graphical user interface framework.

### License
Qt for Python is licensed under:

- **GNU Lesser General Public License Version 3 (LGPLv3)**, or
- **GNU General Public License Version 3 (GPLv3)**,

depending on the applicable distribution terms.

### Project Links
- **Project website:** https://www.qt.io/qt-for-python
- **Source code:** https://code.qt.io/

### Copyright
Copyright (C) The Qt Company Ltd.

---
<br>

# License Texts
The full text of the **GNU General Public License Version 3 (GPLv3)**
is included in the <a href="https://github.com/Audrise/FFTool/blob/main/LICENSE">`LICENSE`</a> file distributed with FFTool.
Where required by the applicable license terms, the corresponding source
code for bundled third-party software is available from the respective
project websites listed above.

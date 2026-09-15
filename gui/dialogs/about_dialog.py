"""
# About FFAUX dialog (see main_window.py)

Built from real widgets instead of a rich-text QMessageBox, so everything
is styled from assets/styles/main.qss via setObjectName() like the rest
of the app.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

_VERSION = "FFAUX v1.0.0 [x64]"
_SUBTITLE = "Flexible Format Audio Utility eXchange"

_DESCRIPTION = (
    "FFAUX is a personal project created and maintained by Audrise. "
    "It started from a simple idea of making everyday audio processing "
    "tasks less complicated and easier to work with. Instead of relying "
    "on command-line tools alone, FFAUX brings those capabilities into a "
    "simple graphical interface while still keeping the flexibility that "
    "makes FFmpeg so useful. The project is built with Python and PySide6, "
    "with FFmpeg and FFprobe doing the work behind the scenes."
)

class AboutFFAUXDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setWindowTitle("About")
        self.setObjectName("aboutDialog")
        self.resize(520, 320)

        content = QWidget()
        content.setObjectName("aboutContent")

        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(6)

        title = QLabel(_VERSION)
        title.setObjectName("aboutTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel(_SUBTITLE)
        subtitle.setObjectName("aboutSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        description = QLabel(_DESCRIPTION)
        description.setObjectName("aboutDescription")
        description.setWordWrap(True)

        license_label = QLabel(
            """
            <a href="LICENSE">License</a> - 
            <a href="THIRD_PARTY_LICENSES.html">Third-Party Licenses</a> - 
            <a href="https://github.com/Audrise">GitHub</a>
            """
        )
        license_label.setObjectName("aboutSection")
        license_label.setOpenExternalLinks(True)
        license_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        copyright_label = QLabel("© 2026 Audrise. All rights reserved.")
        copyright_label.setObjectName("aboutCopyright")
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        content_layout.addWidget(title)
        content_layout.addWidget(subtitle)
        content_layout.addSpacing(12)
        content_layout.addWidget(description)

        content_layout.addSpacing(12)
        content_layout.addWidget(license_label)
        content_layout.addWidget(copyright_label)
        content_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setObjectName("aboutScroll")
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close
        )
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(scroll)
        layout.addWidget(buttons)

        self.show()
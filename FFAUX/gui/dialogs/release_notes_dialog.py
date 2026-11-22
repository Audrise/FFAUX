
"""
Release notes window, shown once on first launch (see main_window.py).

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

_VERSION = "Update FFAUX v1.0.3 [x64]"
_SUBTITLE = "Flexible Format Audio Utility eXchange"
_RELEASED = "Released: November 2026"

_SECTIONS: list[tuple[str, list[str]]] = [
    ("What's New", [
        "Improved metadata editing and management.",
        "Enhanced cover art extraction and embedding.",
        "Improved batch processing workflow.",
    ]),
    ("Improvements", [
        "Improved audio conversion command generation.",
        "Improved metadata preservation during audio conversion.",
        "Improved FFmpeg and FFprobe integration.",
        "Improved error handling and process reliability.",
        "Refined application resource management.",
    ]),
    ("Bug Fixes", [
        "Fixed issues affecting audio conversion settings.",
        "Fixed metadata handling inconsistencies.",
        "Fixed cover art handling in supported audio formats.",
        "Fixed minor application stability issues.",
    ]),
    ("Notes", [
        "FFmpeg and FFprobe are required to use FFAUX.",
        "Metadata and cover art support may vary by output format.",
        "OGG and OPUS metadata and cover art handling is currently limited.",
    ]),
]


class ReleaseNotesDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Release Notes")
        self.setObjectName("releaseNotesDialog")
        self.resize(800, 600)

        content = QWidget()
        content.setObjectName("releaseNotesContent")

        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(6)

        title = QLabel(_VERSION)
        title.setObjectName("releaseNotesTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel(_SUBTITLE)
        subtitle.setObjectName("releaseNotesSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        released = QLabel(_RELEASED)
        released.setObjectName("releaseNotesReleased")

        content_layout.addWidget(title)
        content_layout.addWidget(subtitle)
        content_layout.addSpacing(8)
        content_layout.addWidget(released)

        for heading, items in _SECTIONS:
            section_label = QLabel(heading)
            section_label.setObjectName("releaseNotesSection")

            content_layout.addSpacing(10)
            content_layout.addWidget(section_label)

            for item in items:
                # Bullet is part of the text, not a rich-text list element.
                item_label = QLabel(f"•  {item}")
                item_label.setObjectName("releaseNotesItem")
                item_label.setWordWrap(True)

                content_layout.addWidget(item_label)

        content_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setObjectName("releaseNotesScroll")
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

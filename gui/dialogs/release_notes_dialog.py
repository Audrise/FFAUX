"""
# About FFAUX Release (see main_window.py)
"""

from PySide6.QtWidgets import QMessageBox, QDialog
from PySide6.QtCore import Qt

class ReleaseNotesDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        box = QMessageBox(self)
        box.setWindowTitle("Release Notes")
        box.setIcon(QMessageBox.Icon.NoIcon)
        box.setTextFormat(Qt.TextFormat.RichText)
        box.setText("""
            <div style="font-size: 10pt;">

                <h2 align="center">
                    FFAUX v1.0.0 [x64]
                </h2>

                <h4 align="center">
                    Flexible Format Audio Utility eXchange
                </h4>

                <p><b>Released:</b> September 2026</p>

                <h3>What's New</h3>
                <ul>
                    <li>Audio format conversion with FFmpeg.</li>
                    <li>Metadata editing and management.</li>
                    <li>Cover art management.</li>
                    <li>Batch audio processing.</li>
                    <li>Support for MP3, AAC/M4A, FLAC, WAV, OGG, OPUS, and ALAC/M4A.</li>
                    <li>Dark mode support.</li>
                </ul>

                <h3>Improvements</h3>
                <ul>
                    <li>Improved conversion progress reporting.</li>
                    <li>Improved metadata and cover art handling.</li>
                    <li>Improved conversion reliability.</li>
                    <li>Improved application startup and resource handling.</li>
                </ul>

                <h3>Bug Fixes</h3>
                <ul>
                    <li>Fixed corrupted output in certain WAV conversions.</li>
                    <li>Fixed conversion progress issues involving M4A cover art streams.</li>
                    <li>Fixed unwanted video streams being included in audio-only conversions.</li>
                </ul>

                <h3>Notes</h3>
                <ul>
                    <li>FFmpeg and FFprobe are required to use FFAUX.</li>
                    <li>Metadata and cover art support may vary by output format.</li>
                    <li>OGG and OPUS metadata and cover art handling is currently limited.</li>
                </ul>

            </div>
        """)
        box.exec()
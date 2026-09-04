"""
# About FFAUX dialog (see main_window.py)
"""

from PySide6.QtWidgets import QMessageBox, QDialog
from PySide6.QtCore import Qt

class AboutFFAUXDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        box = QMessageBox(self)
        box.setWindowTitle("About")
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

                <p>
                    FFAUX is a personal project created and maintained by <b>Audrise</b>.
                    It started from a simple idea of making everyday audio processing
                    tasks less complicated and easier to work with. Instead of relying
                    on command-line tools alone, FFAUX brings those capabilities into a
                    simple graphical interface while still keeping the flexibility that
                    makes FFmpeg so useful. The project is built with <b>Python</b> and
                    <b>PySide6</b>, with <b>FFmpeg</b> and <b>FFprobe</b> doing the work
                    behind the scenes.
                </p>

                <p>
                    Licensed under:
                    <a href="LICENSE">GNU General Public License v3.0</a><br>

                    Third-party licenses:
                    <a href="THIRD_PARTY_LICENSES.html">View licenses</a><br>

                    GitHub:
                    <a href="https://github.com/Audrise">Audrise</a>
                </p>

                <p>
                    <b>© 2026 Audrise. All rights reserved.
                </p>

            </div>
        """)
        box.exec()

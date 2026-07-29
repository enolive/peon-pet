"""System tray icon with the pet's control menu.

Separate entity from PetWindow: the tray is the control surface (icon in the
panel + context menu), the window is the view (the sprite on screen). They
share no state; `__main__` wires them together.
"""

from __future__ import annotations

from typing import final

from PyQt6 import QtGui, QtWidgets, QtCore

from .config import ASSETS


@final
class TrayIcon(QtWidgets.QSystemTrayIcon):
    """Peon Pet's tray icon.
    """

    on_toggle_visibility = QtCore.pyqtSignal()
    on_reset_to_idle = QtCore.pyqtSignal()

    def __init__(self, app: QtWidgets.QApplication) -> None:
        super().__init__(QtGui.QIcon(str(ASSETS / "orc-dock-icon.png")), app)
        self.setToolTip("Peon Pet")
        menu = QtWidgets.QMenu()
        menu.addAction("Show/Hide", self.on_toggle_visibility)
        menu.addAction("Reset to idle", self.on_reset_to_idle)
        menu.addSeparator()
        menu.addAction("Quit", app.quit)
        self.setContextMenu(menu)

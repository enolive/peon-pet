"""System tray icon with the pet's control menu.

Separate from PetWindow: the tray is the control surface (panel icon + menu),
the window is the view (the sprite). They share no state; `__main__` wires
them together.
"""

from typing import final

from PyQt6 import QtCore, QtGui, QtWidgets

from .config import ICONS


@final
class TrayIcon(QtWidgets.QSystemTrayIcon):
    on_toggle_visibility = QtCore.pyqtSignal()
    on_reset_to_idle = QtCore.pyqtSignal()

    def __init__(self, app: QtWidgets.QApplication) -> None:
        super().__init__(QtGui.QIcon(str(ICONS / "peon-pet-tray.png")), app)
        self.setToolTip("Peon Pet")
        menu = QtWidgets.QMenu()
        _ = menu.addAction("Show/Hide", self.on_toggle_visibility)
        _ = menu.addAction("Clear all sessions", self.on_reset_to_idle)
        _ = menu.addSeparator()
        _ = menu.addAction("Quit", app.quit)
        self.setContextMenu(menu)

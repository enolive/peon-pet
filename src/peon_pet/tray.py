"""System tray icon with the pet's control menu.

Separate from PetWindow: the tray is the control surface (panel icon + menu),
the window is the view (the sprite). They share no state; `__main__` wires
them together.
"""

from importlib.resources import as_file
from typing import final

from PySide6 import QtCore, QtGui, QtWidgets

from . import __version__
from .config import ICONS


@final
class TrayIcon(QtWidgets.QSystemTrayIcon):
    on_toggle_visibility = QtCore.Signal()
    on_reset_to_idle = QtCore.Signal()
    on_set_opacity = QtCore.Signal(float)

    def __init__(self, app: QtWidgets.QApplication) -> None:
        super().__init__(QtGui.QIcon(str(ICONS / "peon-pet-tray.png")), app)
        self.setToolTip("Peon Pet")
        menu = QtWidgets.QMenu()
        opacity_menu = QtWidgets.QMenu("Opacity")
        opacities = {"20%": 0.2, "40%": 0.4, "60%": 0.6, "80%": 0.8, "100%": 1.0}
        for name, value in opacities.items():
            _ = opacity_menu.addAction(
                name, lambda o=value: self.on_set_opacity.emit(o)
            )
        _ = menu.addAction("Show/Hide", self.on_toggle_visibility.emit)
        _ = menu.addMenu(opacity_menu)
        _ = menu.addAction("Clear all sessions", self.on_reset_to_idle.emit)
        _ = menu.addSeparator()
        _ = menu.addAction("About", show_about)
        _ = menu.addAction("Quit", app.quit)
        self.setContextMenu(menu)


# noinspection HtmlUnknownTarget
def show_about() -> None:
    path = ICONS / "peon-pet.png"
    with as_file(path) as p:
        icon = p.as_uri()
        # language=html
        text = f"""<body style="text-align: center">
<h1>Peon Pet</h1>
<p>{__version__}</p>
<p><img src="{icon}" width="100" height="100" alt=""></p>
<p>Friendly pet companion that reacts to <a href="https://www.peonping.com">PeonPing</a> events.</p>
<p>
    <a href="https://github.com/enolive/peon-pet">https://github.com/enolive/peon-pet</a>
</p>
<br>
</body>"""
        box = QtWidgets.QMessageBox()
        box.setWindowTitle("About Peon Pet")
        box.setIcon(QtWidgets.QMessageBox.Icon.NoIcon)
        box.setTextFormat(QtCore.Qt.TextFormat.RichText)
        box.setText(text)
        _ = box.exec()

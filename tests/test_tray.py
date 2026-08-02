"""Tests for the system tray control menu."""

from PySide6 import QtCore, QtWidgets

from peon_pet.tray import TrayIcon


def test_menu_has_about_before_quit(
    single_instance_app: QtWidgets.QApplication,
) -> None:
    sut = TrayIcon(single_instance_app)

    labels = [a.text() for a in sut.contextMenu().actions() if not a.isSeparator()]
    assert labels.index("About") < labels.index("Quit")


def test_about_opens_message_box_with_name_description_and_repo(
    single_instance_app: QtWidgets.QApplication,
) -> None:
    sut = TrayIcon(single_instance_app)
    about = next(a for a in sut.contextMenu().actions() if a.text() == "About")
    seen: dict[str, str] = {}

    def _inspect_and_close() -> None:
        box = single_instance_app.activeModalWidget()
        assert isinstance(box, QtWidgets.QMessageBox)
        seen["title"] = box.windowTitle()
        seen["text"] = box.text()
        box.accept()

    QtCore.QTimer.singleShot(0, _inspect_and_close)

    about.trigger()

    assert seen["title"] == "About Peon Pet"
    assert "Peon Pet" in seen["text"]
    assert "https://github.com/enolive/peon-pet" in seen["text"]

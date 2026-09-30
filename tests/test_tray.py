"""Tests for the system tray control menu."""

from PySide6 import QtCore, QtWidgets
from PySide6.QtGui import QAction
from PySide6.QtTest import QSignalSpy

from peon_pet import __version__
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
    about = _find_context_menu_action_by_text(sut, "About")
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
    assert __version__ in seen["text"]
    assert "https://github.com/enolive/peon-pet" in seen["text"]


def test_show_hide_emits_signal(
    single_instance_app: QtWidgets.QApplication,
) -> None:
    sut = TrayIcon(single_instance_app)
    show_hide = _find_context_menu_action_by_text(sut, "Show/Hide")
    spy = QSignalSpy(sut.on_toggle_visibility)

    show_hide.trigger()

    assert spy.count() == 1


def test_clear_sessions_emits_signal(
    single_instance_app: QtWidgets.QApplication,
) -> None:
    sut = TrayIcon(single_instance_app)
    clear = _find_context_menu_action_by_text(sut, "Clear all sessions")
    spy = QSignalSpy(sut.on_reset_to_idle)

    clear.trigger()

    assert spy.count() == 1


def test_opacity_menu_emits_each_preset(
    single_instance_app: QtWidgets.QApplication,
) -> None:
    sut = TrayIcon(single_instance_app)
    opacity_action = _find_context_menu_action_by_text(sut, "Opacity")
    opacity_menu = opacity_action.menu()
    assert isinstance(opacity_menu, QtWidgets.QMenu)
    emitted: list[float] = []
    _ = sut.on_set_opacity.connect(emitted.append)

    for action in opacity_menu.actions():
        action.trigger()

    assert sorted(emitted) == [0.2, 0.4, 0.6, 0.8, 1.0]


def _find_context_menu_action_by_text(sut: TrayIcon, label_text: str) -> QAction:
    return next(a for a in sut.contextMenu().actions() if a.text() == label_text)

"""Error dialog utilities."""

from PySide6.QtWidgets import QMessageBox


def show_error(parent, title: str, message: str) -> None:
    QMessageBox.critical(parent, title, message, QMessageBox.Ok)


def show_warning(parent, title: str, message: str) -> None:
    QMessageBox.warning(parent, title, message, QMessageBox.Ok)


def show_info(parent, title: str, message: str) -> None:
    QMessageBox.information(parent, title, message, QMessageBox.Ok)

#!/usr/bin/env python3
"""
STM32 CAN Flasher
=================
GUI application for flashing STM32L4 boards via CAN bootloader.

Usage:
    python main.py

Requirements:
    pip install -r requirements.txt
"""

import sys
from PySide6.QtWidgets import QApplication
from src.ui.main_window import MainWindow
from src.ui.theme import DARK_STYLESHEET


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("STM32 CAN Flasher")
    app.setOrganizationName("Terps Racing EV")
    app.setStyleSheet(DARK_STYLESHEET)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()

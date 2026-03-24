"""
Control Panel
=============
Reset to bootloader, stay in bootloader, jump to app, get status.
"""

from PySide6.QtWidgets import (
    QGroupBox, QVBoxLayout, QPushButton, QSpinBox, QHBoxLayout, QLabel,
    QGridLayout,
)
from PySide6.QtCore import Signal


class ControlPanel(QGroupBox):
    """Manual bootloader control buttons."""

    reset_requested = Signal(int)          # module
    stay_in_bl_requested = Signal()
    jump_requested = Signal()
    get_status_requested = Signal()

    def __init__(self, parent=None):
        super().__init__("Bootloader Control", parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # Module selector for reset
        mod_row = QHBoxLayout()
        mod_row.addWidget(QLabel("Module:"))
        self.module_spin = QSpinBox()
        self.module_spin.setRange(0, 15)
        self.module_spin.setFixedWidth(60)
        mod_row.addWidget(self.module_spin)
        mod_row.addStretch()
        layout.addLayout(mod_row)

        # 2x2 button grid
        grid = QGridLayout()
        grid.setSpacing(6)

        self.reset_btn = QPushButton("Reset to BL")
        self.reset_btn.setToolTip("Send CAN reset command to reboot the selected module into bootloader")
        self.reset_btn.clicked.connect(lambda: self.reset_requested.emit(self.module_spin.value()))
        grid.addWidget(self.reset_btn, 0, 0)

        self.stay_btn = QPushButton("Stay in BL")
        self.stay_btn.setToolTip("Send GET_STATUS to prevent auto-jump timeout")
        self.stay_btn.clicked.connect(self.stay_in_bl_requested.emit)
        grid.addWidget(self.stay_btn, 0, 1)

        self.jump_btn = QPushButton("Jump to App")
        self.jump_btn.setToolTip("Command bootloader to jump to the active application bank")
        self.jump_btn.clicked.connect(self.jump_requested.emit)
        grid.addWidget(self.jump_btn, 1, 0)

        self.status_btn = QPushButton("Get Status")
        self.status_btn.setToolTip("Query bootloader state, error, and bytes written")
        self.status_btn.clicked.connect(self.get_status_requested.emit)
        grid.addWidget(self.status_btn, 1, 1)

        layout.addLayout(grid)

    def set_enabled_all(self, enabled: bool):
        self.reset_btn.setEnabled(enabled)
        self.stay_btn.setEnabled(enabled)
        self.jump_btn.setEnabled(enabled)
        self.status_btn.setEnabled(enabled)
        self.module_spin.setEnabled(enabled)

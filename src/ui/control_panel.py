"""
Control Panel
=============
Reset to bootloader, stay in bootloader, jump to app, get status.
"""

from typing import List

from PySide6.QtWidgets import (
    QGroupBox, QVBoxLayout, QPushButton, QSpinBox, QHBoxLayout, QLabel,
    QGridLayout, QComboBox,
)
from PySide6.QtCore import Signal

from src.backend.board_config import BoardConfig


class ControlPanel(QGroupBox):
    """Manual bootloader control buttons."""

    reset_requested = Signal(int, int)       # module, reset_can_id
    stay_in_bl_requested = Signal()
    jump_requested = Signal()
    get_status_requested = Signal()

    def __init__(self, boards: List[BoardConfig], parent=None):
        super().__init__("Bootloader Control", parent)
        self._boards = boards
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # Board selector for reset
        board_row = QHBoxLayout()
        board_row.addWidget(QLabel("Board:"))
        self.board_combo = QComboBox()
        for b in self._boards:
            self.board_combo.addItem(b.name)
        self.board_combo.currentIndexChanged.connect(self._on_board_changed)
        board_row.addWidget(self.board_combo)
        board_row.addStretch()
        layout.addLayout(board_row)

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
        self.reset_btn.clicked.connect(self._on_reset)
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

        # Apply initial board selection
        self._on_board_changed(self.board_combo.currentIndex())

    def _on_board_changed(self, index: int):
        if 0 <= index < len(self._boards):
            board = self._boards[index]
            self.module_spin.setRange(0, board.modules - 1)
            self.module_spin.setEnabled(board.modules > 1)
            if board.modules == 1:
                self.module_spin.setValue(0)

    def _get_reset_can_id(self) -> int:
        idx = self.board_combo.currentIndex()
        board = self._boards[idx]
        module = self.module_spin.value()
        return board.reset_can_ids[module]

    def _on_reset(self):
        self.reset_requested.emit(self.module_spin.value(), self._get_reset_can_id())

    def set_enabled_all(self, enabled: bool):
        self.reset_btn.setEnabled(enabled)
        self.stay_btn.setEnabled(enabled)
        self.jump_btn.setEnabled(enabled)
        self.status_btn.setEnabled(enabled)
        self.board_combo.setEnabled(enabled)
        self.module_spin.setEnabled(enabled)
        if enabled:
            self._on_board_changed(self.board_combo.currentIndex())

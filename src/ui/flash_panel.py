"""
Flash Panel
===========
Firmware directory selection, module ID, progress bar, and flash trigger.
"""

from pathlib import Path
from typing import List

from PySide6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QSpinBox, QLineEdit, QFileDialog, QCheckBox,
    QComboBox, QFrame,
)
from PySide6.QtCore import Signal, QSettings

from src.backend.board_config import BoardConfig
from src.backend.firmware_utils import discover_firmware_files


class FlashPanel(QGroupBox):
    """Firmware directory picker, module ID, flash button, progress."""

    flash_requested = Signal(str, int, int, bool, bool)  # (dir, module, reset_can_id, verify, jump)
    sequential_flash_requested = Signal(str, list, bool, bool)  # (dir, [(module, reset_can_id), ...], verify, jump)
    cancel_requested = Signal()

    def __init__(self, boards: List[BoardConfig], parent=None):
        super().__init__("Flash Firmware", parent)
        self._settings = QSettings("TerpsRacingEV", "STM32-CAN-Flasher")
        self._boards = boards
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Directory picker
        dir_row = QHBoxLayout()
        self.dir_edit = QLineEdit()
        self.dir_edit.setPlaceholderText("Build directory containing _a.bin / _b.bin ...")
        self.dir_edit.textChanged.connect(self._on_dir_changed)
        dir_row.addWidget(self.dir_edit)
        self.browse_btn = QPushButton("Browse")
        dir_row.addWidget(self.browse_btn)
        self.browse_btn.clicked.connect(self._browse)
        layout.addLayout(dir_row)

        # Discovered files
        self.file_label = QLabel("No firmware files found")
        self.file_label.setObjectName("file_missing")
        layout.addWidget(self.file_label)

        # Board + Module row
        board_row = QHBoxLayout()
        board_row.addWidget(QLabel("Board:"))
        self.board_combo = QComboBox()
        self.board_combo.setMinimumWidth(120)
        for b in self._boards:
            self.board_combo.addItem(b.name)
        self.board_combo.currentIndexChanged.connect(self._on_board_changed)
        board_row.addWidget(self.board_combo)
        board_row.addSpacing(16)
        board_row.addWidget(QLabel("Module ID:"))
        self.module_spin = QSpinBox()
        self.module_spin.setRange(0, 15)
        self.module_spin.setFixedWidth(60)
        board_row.addWidget(self.module_spin)
        board_row.addStretch()
        layout.addLayout(board_row)

        # Sequential flash module selection (multi-module boards)
        self._seq_frame = QFrame()
        self._seq_frame.setObjectName("seq_frame")
        seq_layout = QHBoxLayout(self._seq_frame)
        seq_layout.setContentsMargins(4, 2, 4, 2)
        seq_layout.setSpacing(6)

        self._seq_check = QCheckBox("Sequential Flash:")
        self._seq_check.toggled.connect(self._on_seq_toggled)
        seq_layout.addWidget(self._seq_check)

        self._module_checks_layout = QHBoxLayout()
        self._module_checks_layout.setSpacing(8)
        seq_layout.addLayout(self._module_checks_layout)
        self._module_checkboxes: list[QCheckBox] = []

        seq_layout.addSpacing(8)
        self._select_all_btn = QPushButton("All")
        self._select_all_btn.setFixedWidth(40)
        self._select_all_btn.clicked.connect(self._select_all_modules)
        seq_layout.addWidget(self._select_all_btn)
        self._deselect_all_btn = QPushButton("None")
        self._deselect_all_btn.setFixedWidth(46)
        self._deselect_all_btn.clicked.connect(self._deselect_all_modules)
        seq_layout.addWidget(self._deselect_all_btn)
        seq_layout.addStretch()

        layout.addWidget(self._seq_frame)
        self._seq_frame.setVisible(False)

        # Options row
        opts_row = QHBoxLayout()
        self.verify_check = QCheckBox("Read-back Verify")
        self.verify_check.setChecked(True)
        opts_row.addWidget(self.verify_check)
        opts_row.addSpacing(16)
        self.jump_check = QCheckBox("Jump to App")
        self.jump_check.setChecked(True)
        opts_row.addWidget(self.jump_check)
        opts_row.addStretch()
        layout.addLayout(opts_row)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("status_msg")
        layout.addWidget(self.status_label)

        # Buttons
        btn_row = QHBoxLayout()
        self.flash_btn = QPushButton("Flash")
        self.flash_btn.setObjectName("primary_btn")
        self.flash_btn.clicked.connect(self._on_flash)
        btn_row.addWidget(self.flash_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("danger_btn")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_requested.emit)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Restore last used directory
        last_dir = self._settings.value("last_firmware_dir", "")
        if last_dir:
            self.dir_edit.setText(last_dir)

        # Apply initial board selection
        self._on_board_changed(self.board_combo.currentIndex())

    def _browse(self):
        start = self.dir_edit.text() or ""
        d = QFileDialog.getExistingDirectory(self, "Select Firmware Directory", start)
        if d:
            self.dir_edit.setText(d)

    def _on_dir_changed(self, text: str):
        p = Path(text)
        if p.is_dir():
            self._settings.setValue("last_firmware_dir", text)
        a, b = discover_firmware_files(p)
        parts = []
        if a:
            parts.append(f"Bank A: {a.name}")
        if b:
            parts.append(f"Bank B: {b.name}")
        if parts:
            self.file_label.setText("  |  ".join(parts))
            self.file_label.setObjectName("file_found")
        else:
            self.file_label.setText("No firmware files found")
            self.file_label.setObjectName("file_missing")
        self.file_label.style().unpolish(self.file_label)
        self.file_label.style().polish(self.file_label)

    def _on_board_changed(self, index: int):
        if 0 <= index < len(self._boards):
            board = self._boards[index]
            self.module_spin.setRange(0, board.modules - 1)
            self.module_spin.setEnabled(board.modules > 1)
            if board.modules == 1:
                self.module_spin.setValue(0)
            self._rebuild_module_checkboxes(board)

    def _rebuild_module_checkboxes(self, board: BoardConfig):
        # Clear existing checkboxes
        for cb in self._module_checkboxes:
            self._module_checks_layout.removeWidget(cb)
            cb.deleteLater()
        self._module_checkboxes.clear()

        if board.modules > 1:
            for i in range(board.modules):
                cb = QCheckBox(str(i))
                cb.setChecked(True)
                self._module_checkboxes.append(cb)
                self._module_checks_layout.addWidget(cb)
            self._seq_frame.setVisible(True)
            self._on_seq_toggled(self._seq_check.isChecked())
        else:
            self._seq_frame.setVisible(False)
            self._seq_check.setChecked(False)

    def _on_seq_toggled(self, checked: bool):
        for cb in self._module_checkboxes:
            cb.setEnabled(checked)
        self._select_all_btn.setEnabled(checked)
        self._deselect_all_btn.setEnabled(checked)
        # When sequential is active, hide single module spinner
        self.module_spin.setEnabled(not checked and self._boards[self.board_combo.currentIndex()].modules > 1)

    def _select_all_modules(self):
        for cb in self._module_checkboxes:
            cb.setChecked(True)

    def _deselect_all_modules(self):
        for cb in self._module_checkboxes:
            cb.setChecked(False)

    def _get_reset_can_id(self) -> int:
        idx = self.board_combo.currentIndex()
        board = self._boards[idx]
        module = self.module_spin.value()
        return board.reset_can_ids[module]

    def _on_flash(self):
        idx = self.board_combo.currentIndex()
        board = self._boards[idx]
        if self._seq_check.isChecked() and board.modules > 1:
            targets = []
            for i, cb in enumerate(self._module_checkboxes):
                if cb.isChecked():
                    targets.append((i, board.reset_can_ids[i]))
            if not targets:
                return
            self.sequential_flash_requested.emit(
                self.dir_edit.text(),
                targets,
                self.verify_check.isChecked(),
                self.jump_check.isChecked(),
            )
        else:
            self.flash_requested.emit(
                self.dir_edit.text(),
                self.module_spin.value(),
                self._get_reset_can_id(),
                self.verify_check.isChecked(),
                self.jump_check.isChecked(),
            )

    def set_flashing(self, flashing: bool):
        self.flash_btn.setEnabled(not flashing)
        self.cancel_btn.setEnabled(flashing)
        self.browse_btn.setEnabled(not flashing)
        self.dir_edit.setEnabled(not flashing)
        self.module_spin.setEnabled(not flashing)
        self.board_combo.setEnabled(not flashing)
        self.verify_check.setEnabled(not flashing)
        self.jump_check.setEnabled(not flashing)
        self._seq_check.setEnabled(not flashing)
        self._select_all_btn.setEnabled(not flashing)
        self._deselect_all_btn.setEnabled(not flashing)
        for cb in self._module_checkboxes:
            cb.setEnabled(not flashing)
        if flashing:
            self.progress_bar.setValue(0)
            self.status_label.setText("Starting...")

    def set_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        if msg:
            self.status_label.setText(msg)

    def set_status(self, msg: str):
        self.status_label.setText(msg)

"""
Flash Panel
===========
Firmware directory selection, module ID, progress bar, and flash trigger.
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QSpinBox, QLineEdit, QFileDialog, QCheckBox,
)
from PySide6.QtCore import Signal, QSettings

from src.backend.firmware_utils import discover_firmware_files


class FlashPanel(QGroupBox):
    """Firmware directory picker, module ID, flash button, progress."""

    flash_requested = Signal(str, int, bool, bool)  # (dir, module, verify, jump)
    cancel_requested = Signal()

    def __init__(self, parent=None):
        super().__init__("Flash Firmware", parent)
        self._settings = QSettings("TerpsRacingEV", "STM32-CAN-Flasher")
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

        # Module + options row
        opts_row = QHBoxLayout()
        opts_row.addWidget(QLabel("Module ID:"))
        self.module_spin = QSpinBox()
        self.module_spin.setRange(0, 15)
        self.module_spin.setFixedWidth(60)
        opts_row.addWidget(self.module_spin)
        opts_row.addSpacing(16)
        self.verify_check = QCheckBox("Read-back Verify")
        self.verify_check.setChecked(True)
        opts_row.addWidget(self.verify_check)
        opts_row.addSpacing(8)
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

    def _on_flash(self):
        self.flash_requested.emit(
            self.dir_edit.text(),
            self.module_spin.value(),
            self.verify_check.isChecked(),
            self.jump_check.isChecked(),
        )

    def set_flashing(self, flashing: bool):
        self.flash_btn.setEnabled(not flashing)
        self.cancel_btn.setEnabled(flashing)
        self.browse_btn.setEnabled(not flashing)
        self.dir_edit.setEnabled(not flashing)
        self.module_spin.setEnabled(not flashing)
        self.verify_check.setEnabled(not flashing)
        self.jump_check.setEnabled(not flashing)
        if flashing:
            self.progress_bar.setValue(0)
            self.status_label.setText("Starting...")

    def set_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        if msg:
            self.status_label.setText(msg)

    def set_status(self, msg: str):
        self.status_label.setText(msg)

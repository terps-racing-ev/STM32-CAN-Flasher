"""
Status Panel
============
Displays bank validity, active bank, bootloader state, version, last error.
"""

from PySide6.QtWidgets import (
    QGroupBox, QGridLayout, QLabel, QHBoxLayout, QVBoxLayout,
)
from PySide6.QtCore import Qt

from src.backend.bootloader_protocol import STATE_NAMES, ERROR_DESCRIPTIONS, bank_name


class _BankIndicator(QLabel):
    """Small coloured pill for bank A or B."""

    _STYLES = {
        'active_valid': "background: #a6e3a1; color: #1e1e2e; padding: 3px 10px; border-radius: 10px; font-weight: 700; font-size: 11px;",
        'inactive_valid': "background: #89b4fa; color: #1e1e2e; padding: 3px 10px; border-radius: 10px; font-weight: 600; font-size: 11px;",
        'invalid': "background: #f38ba8; color: #1e1e2e; padding: 3px 10px; border-radius: 10px; font-weight: 600; font-size: 11px;",
        'unknown': "background: #585b70; color: #bac2de; padding: 3px 10px; border-radius: 10px; font-size: 11px;",
    }

    def __init__(self, label: str, parent=None):
        super().__init__(label, parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumWidth(90)
        self.set_state('unknown')

    def set_state(self, state: str):
        self.setStyleSheet(self._STYLES.get(state, self._STYLES['unknown']))


class StatusPanel(QGroupBox):
    """Bank status, bootloader state, version, error display."""

    def __init__(self, parent=None):
        super().__init__("Bootloader Status", parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # Bank indicators row
        banks = QHBoxLayout()
        banks.addWidget(QLabel("Bank A:"))
        self.bank_a = _BankIndicator("Unknown")
        banks.addWidget(self.bank_a)
        banks.addSpacing(16)
        banks.addWidget(QLabel("Bank B:"))
        self.bank_b = _BankIndicator("Unknown")
        banks.addWidget(self.bank_b)
        banks.addStretch()
        layout.addLayout(banks)

        # Info grid
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(3)

        lbl = lambda t: self._make_label(t, "section_label")
        val = lambda t: self._make_label(t, "value_label")

        grid.addWidget(lbl("Active Bank"), 0, 0)
        self.active_label = val("\u2014")
        grid.addWidget(self.active_label, 0, 1)

        grid.addWidget(lbl("State"), 0, 2)
        self.state_label = val("\u2014")
        grid.addWidget(self.state_label, 0, 3)

        grid.addWidget(lbl("FW Version"), 1, 0)
        self.version_label = val("\u2014")
        grid.addWidget(self.version_label, 1, 1)

        grid.addWidget(lbl("Last Error"), 1, 2)
        self.error_label = val("\u2014")
        grid.addWidget(self.error_label, 1, 3)

        grid.addWidget(lbl("Bytes Written"), 2, 0)
        self.bytes_label = val("\u2014")
        grid.addWidget(self.bytes_label, 2, 1)

        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        layout.addLayout(grid)

    @staticmethod
    def _make_label(text: str, obj_name: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName(obj_name)
        return lbl

    def update_from_heartbeat(self, hb):
        """Update from a HeartbeatInfo dataclass."""
        active = hb.active_bank
        self.active_label.setText(f"Bank {bank_name(active)}")
        self.version_label.setText(f"{hb.version_major}.{hb.version_minor}")
        self.state_label.setText(STATE_NAMES.get(hb.state, "UNKNOWN"))
        self.error_label.setText(ERROR_DESCRIPTIONS.get(hb.last_error, f"0x{hb.last_error:02X}"))
        self.bytes_label.setText(str(hb.bytes_written))

        # Bank A indicator
        if hb.bank_a_valid:
            self.bank_a.setText("Valid" + (" (Active)" if active == 0 else ""))
            self.bank_a.set_state('active_valid' if active == 0 else 'inactive_valid')
        else:
            self.bank_a.setText("Invalid")
            self.bank_a.set_state('invalid')

        # Bank B indicator
        if hb.bank_b_valid:
            self.bank_b.setText("Valid" + (" (Active)" if active == 1 else ""))
            self.bank_b.set_state('active_valid' if active == 1 else 'inactive_valid')
        else:
            self.bank_b.setText("Invalid")
            self.bank_b.set_state('invalid')

    def update_from_bank_status(self, bs):
        """Update from a BankStatus dataclass."""
        active = bs.active_bank
        self.active_label.setText(f"Bank {bank_name(active)}")

        if bs.bank_a_valid:
            self.bank_a.setText("Valid" + (" (Active)" if active == 0 else ""))
            self.bank_a.set_state('active_valid' if active == 0 else 'inactive_valid')
        else:
            self.bank_a.setText("Invalid")
            self.bank_a.set_state('invalid')

        if bs.bank_b_valid:
            self.bank_b.setText("Valid" + (" (Active)" if active == 1 else ""))
            self.bank_b.set_state('active_valid' if active == 1 else 'inactive_valid')
        else:
            self.bank_b.setText("Invalid")
            self.bank_b.set_state('invalid')

    def clear(self):
        self.bank_a.setText("Unknown")
        self.bank_a.set_state('unknown')
        self.bank_b.setText("Unknown")
        self.bank_b.set_state('unknown')
        self.active_label.setText("—")
        self.state_label.setText("—")
        self.version_label.setText("—")
        self.error_label.setText("—")
        self.bytes_label.setText("—")

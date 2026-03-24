"""Status Panel — shows all heartbeat fields from the BL_Response DBC message."""

from PySide6.QtWidgets import (
    QGroupBox, QGridLayout, QLabel, QVBoxLayout, QFrame,
)
from PySide6.QtCore import Qt

from src.backend.bootloader_protocol import STATE_NAMES, ERROR_DESCRIPTIONS, bank_name


_GREEN  = "#a6e3a1"
_RED    = "#f38ba8"
_BLUE   = "#89b4fa"
_DIM    = "#585b70"


def _flag_html(on: bool, on_text: str, off_text: str) -> str:
    """Return coloured HTML for a boolean flag value."""
    if on:
        return f'<span style="color:{_GREEN};font-weight:600">{on_text}</span>'
    return f'<span style="color:{_RED};font-weight:600">{off_text}</span>'


class StatusPanel(QGroupBox):
    """Displays every signal from the BL_Response READY heartbeat."""

    def __init__(self, parent=None):
        super().__init__("Bootloader Status", parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(10, 14, 10, 8)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(2)

        # Tracks the next free row in each half (left=cols 0-1, right=cols 3-4)
        self._left_row = 0
        self._right_row = 0

        def _add(name: str, side: str) -> QLabel:
            if side == "L":
                r = self._left_row
                c0, c1 = 0, 1
                self._left_row += 1
            else:
                r = self._right_row
                c0, c1 = 3, 4
                self._right_row += 1
            name_lbl = QLabel(name)
            name_lbl.setStyleSheet(f"color: {_DIM}; font-size: 11px;")
            val_lbl = QLabel("\u2014")
            val_lbl.setTextFormat(Qt.RichText)
            val_lbl.setStyleSheet("font-size: 11px;")
            grid.addWidget(name_lbl, r, c0)
            grid.addWidget(val_lbl, r, c1)
            return val_lbl

        # Column separator
        sep_col = QFrame()
        sep_col.setFrameShape(QFrame.VLine)
        sep_col.setStyleSheet("color: #3b3b54;")
        sep_col.setFixedWidth(1)
        grid.addWidget(sep_col, 0, 2, 14, 1)

        # Left column — core status + bank info
        self.v_state = _add("State", "L")
        self.v_last_error = _add("Last Error", "L")
        self.v_ready_code = _add("Ready Code", "L")
        self.v_bytes_written = _add("Bytes Written", "L")
        self.v_active_bank = _add("Active Bank", "L")
        self.v_bank_a_valid = _add("Bank A Valid", "L")
        self.v_bank_b_valid = _add("Bank B Valid", "L")

        # Right column — CRC + diagnostic flags
        self.v_bank_a_crc = _add("Bank A CRC", "R")
        self.v_bank_b_crc = _add("Bank B CRC", "R")
        self.v_metadata_ready = _add("Metadata Ready", "R")
        self.v_can_cmd_seen = _add("CAN Command Seen", "R")
        self.v_image_info = _add("Image Info Valid", "R")
        self.v_verified_bank = _add("Verified Bank Valid", "R")
        self.v_jump_pending = _add("Jump Pending", "R")

        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(4, 1)
        layout.addLayout(grid)

    def update_from_heartbeat(self, hb):
        """Update every field from a HeartbeatInfo dataclass."""
        state_name = STATE_NAMES.get(hb.state, f"UNKNOWN ({hb.state})")
        self.v_state.setText(f'<span style="color:{_BLUE}">{state_name}</span>')

        err_name = ERROR_DESCRIPTIONS.get(hb.last_error, f"0x{hb.last_error:02X}")
        err_color = _GREEN if hb.last_error == 0 else _RED
        self.v_last_error.setText(f'<span style="color:{err_color}">{err_name}</span>')

        self.v_ready_code.setText(f"0x{hb.ready_code:02X}")
        self.v_bytes_written.setText(str(hb.bytes_written))

        active = hb.active_bank
        self.v_active_bank.setText(
            f'<span style="color:{_BLUE};">Bank {bank_name(active)}</span>'
        )

        self.v_bank_a_valid.setText(_flag_html(hb.bank_a_valid, "VALID", "INVALID"))
        self.v_bank_b_valid.setText(_flag_html(hb.bank_b_valid, "VALID", "INVALID"))
        self.v_bank_a_crc.setText(_flag_html(hb.bank_a_crc_ok, "CRC OK", "CRC FAIL"))
        self.v_bank_b_crc.setText(_flag_html(hb.bank_b_crc_ok, "CRC OK", "CRC FAIL"))

        self.v_metadata_ready.setText(_flag_html(hb.metadata_ready, "READY", "NOT READY"))
        self.v_can_cmd_seen.setText(_flag_html(hb.can_cmd_received, "YES", "NO"))
        self.v_image_info.setText(_flag_html(hb.image_info_valid, "VALID", "INVALID"))
        self.v_verified_bank.setText(_flag_html(hb.verified_bank_valid, "VALID", "INVALID"))
        self.v_jump_pending.setText(_flag_html(hb.jump_pending, "PENDING", "NO"))

    def update_from_bank_status(self, bs):
        """Update bank fields from a BankStatus dataclass."""
        self.v_active_bank.setText(
            f'<span style="color:{_BLUE}">Bank {bank_name(bs.active_bank)}</span>'
        )
        self.v_bank_a_valid.setText(_flag_html(bool(bs.bank_a_valid), "VALID", "INVALID"))
        self.v_bank_b_valid.setText(_flag_html(bool(bs.bank_b_valid), "VALID", "INVALID"))

    def clear(self):
        for lbl in (
            self.v_state, self.v_last_error, self.v_ready_code,
            self.v_bytes_written, self.v_active_bank,
            self.v_bank_a_valid, self.v_bank_b_valid,
            self.v_bank_a_crc, self.v_bank_b_crc,
            self.v_metadata_ready, self.v_can_cmd_seen,
            self.v_image_info, self.v_verified_bank,
            self.v_jump_pending,
        ):
            lbl.setText("\u2014")

"""
CAN Log Panel
=============
Collapsible panel showing all CAN TX/RX traffic in a table.
"""

import time

from PySide6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QAbstractItemView,
)
from PySide6.QtCore import Qt

from src.backend.bootloader_protocol import (
    CAN_HOST_ID, CAN_BOOTLOADER_ID, BMS_RESET_CMD_BASE,
    decode_command, decode_response, RESP_READY,
)

MAX_LOG_ROWS = 1000


class CANLogPanel(QGroupBox):
    """Collapsible CAN message log with TX/RX decode."""

    def __init__(self, parent=None):
        super().__init__("CAN Message Log", parent)
        self.setCheckable(True)
        self.setChecked(False)
        self.toggled.connect(self._on_toggle)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(6, 8, 6, 6)
        self._layout.setSpacing(4)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._clear)
        toolbar.addWidget(self.clear_btn)
        self.auto_scroll_btn = QPushButton("Auto-scroll: ON")
        self.auto_scroll_btn.setCheckable(True)
        self.auto_scroll_btn.setChecked(True)
        self.auto_scroll_btn.toggled.connect(self._on_auto_scroll)
        toolbar.addWidget(self.auto_scroll_btn)
        toolbar.addStretch()
        self._layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Time", "Dir", "CAN ID", "DLC", "Data", "Decoded"])
        self.table.setAlternatingRowColors(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(150)
        self._layout.addWidget(self.table)

        self._auto_scroll = True
        self._start_time = time.time()

        # Start collapsed
        self.table.setVisible(False)
        self.clear_btn.setVisible(False)
        self.auto_scroll_btn.setVisible(False)

    def _on_toggle(self, checked: bool):
        self.table.setVisible(checked)
        self.clear_btn.setVisible(checked)
        self.auto_scroll_btn.setVisible(checked)

    def _on_auto_scroll(self, checked: bool):
        self._auto_scroll = checked
        self.auto_scroll_btn.setText(f"Auto-scroll: {'ON' if checked else 'OFF'}")

    def _clear(self):
        self.table.setRowCount(0)

    def add_message(self, direction: str, can_id: int, data: bytes, timestamp: float = 0.0):
        """Add a CAN message row. Called from the main thread."""
        if self.table.rowCount() >= MAX_LOG_ROWS:
            self.table.removeRow(0)

        row = self.table.rowCount()
        self.table.insertRow(row)

        t = timestamp if timestamp else (time.time() - self._start_time)
        self.table.setItem(row, 0, QTableWidgetItem(f"{t:.3f}"))
        self.table.setItem(row, 1, QTableWidgetItem(direction))
        self.table.setItem(row, 2, QTableWidgetItem(f"0x{can_id:08X}"))
        self.table.setItem(row, 3, QTableWidgetItem(str(len(data))))
        self.table.setItem(row, 4, QTableWidgetItem(' '.join(f'{b:02X}' for b in data)))
        self.table.setItem(row, 5, QTableWidgetItem(self._decode(direction, can_id, data)))

        if self._auto_scroll:
            self.table.scrollToBottom()

    @staticmethod
    def _decode(direction: str, can_id: int, data: bytes) -> str:
        if not data:
            return ""
        if can_id == CAN_HOST_ID:
            return decode_command(data[0])
        if can_id == CAN_BOOTLOADER_ID:
            return decode_response(data[0])
        base = can_id & 0xFFFF0FFF
        if base == (BMS_RESET_CMD_BASE & 0xFFFF0FFF):
            module = (can_id >> 12) & 0xF
            return f"RESET Module {module}"
        return ""

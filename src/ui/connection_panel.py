"""
Connection Panel
================
Adapter type selection, channel configuration, and connect/disconnect.
"""

import sys

from PySide6.QtWidgets import (
    QGroupBox, QHBoxLayout, QLabel, QComboBox, QPushButton,
)
from PySide6.QtCore import Signal

_IS_LINUX = sys.platform.startswith('linux')


class ConnectionPanel(QGroupBox):
    """Top bar: adapter type, channel, connect/disconnect."""

    connect_requested = Signal(str, str)   # (adapter_type, channel)
    disconnect_requested = Signal()

    def __init__(self, parent=None):
        super().__init__("Connection", parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)

        layout.addWidget(QLabel("Adapter:"))
        self.adapter_combo = QComboBox()
        self.adapter_combo.addItems(["CANable", "PCAN"])
        self.adapter_combo.setMinimumWidth(100)
        layout.addWidget(self.adapter_combo)

        layout.addSpacing(8)
        layout.addWidget(QLabel("Channel:"))
        self.channel_combo = QComboBox()
        self.channel_combo.setEditable(True)
        if _IS_LINUX:
            self.channel_combo.addItems(["can0", "can1"])
        else:
            self.channel_combo.addItems(["0", "1", "2"])
        self.channel_combo.setMinimumWidth(70)
        layout.addWidget(self.channel_combo)

        self.adapter_combo.currentTextChanged.connect(self._on_adapter_changed)

        layout.addStretch()

        self.status_dot = QLabel("\u2b24")
        self.status_dot.setStyleSheet("color: #f38ba8; font-size: 10px;")
        layout.addWidget(self.status_dot)
        self.status_text = QLabel("Disconnected")
        self.status_text.setStyleSheet("color: #6c7086; font-weight: 500;")
        layout.addWidget(self.status_text)

        layout.addSpacing(8)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setObjectName("connect_btn")
        self.connect_btn.setMinimumWidth(100)
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        layout.addWidget(self.connect_btn)

        self._connected = False

    def _on_adapter_changed(self, text: str):
        self.channel_combo.clear()
        if text == "PCAN":
            self.channel_combo.addItems([f"USB{i}" for i in range(1, 17)])
        elif _IS_LINUX:
            self.channel_combo.addItems(["can0", "can1"])
        else:
            self.channel_combo.addItems(["0", "1", "2"])

    def _on_connect_clicked(self):
        if self._connected:
            self.disconnect_requested.emit()
        else:
            adapter = self.adapter_combo.currentText()
            channel = self.channel_combo.currentText()
            self.connect_requested.emit(adapter, channel)

    def set_connected(self, connected: bool):
        self._connected = connected
        if connected:
            self.status_dot.setStyleSheet("color: #a6e3a1; font-size: 10px;")
            self.status_text.setText("Connected")
            self.status_text.setStyleSheet("color: #a6e3a1; font-weight: 600;")
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setObjectName("disconnect_btn")
            self.connect_btn.style().unpolish(self.connect_btn)
            self.connect_btn.style().polish(self.connect_btn)
            self.adapter_combo.setEnabled(False)
            self.channel_combo.setEnabled(False)
        else:
            self.status_dot.setStyleSheet("color: #f38ba8; font-size: 10px;")
            self.status_text.setText("Disconnected")
            self.status_text.setStyleSheet("color: #6c7086; font-weight: 500;")
            self.connect_btn.setText("Connect")
            self.connect_btn.setObjectName("connect_btn")
            self.connect_btn.style().unpolish(self.connect_btn)
            self.connect_btn.style().polish(self.connect_btn)
            self.adapter_combo.setEnabled(True)
            self.channel_combo.setEnabled(True)

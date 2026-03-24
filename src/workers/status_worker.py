"""
Status Worker
=============
QThread that listens for RESP_READY heartbeats from the bootloader.
"""

import time
from PySide6.QtCore import QThread, Signal

from src.backend.can_adapter import CANAdapter
from src.backend.bootloader_protocol import CAN_BOOTLOADER_ID, RESP_READY
from src.backend.flasher import HeartbeatInfo


class StatusWorker(QThread):
    """Continuously polls for bootloader heartbeats."""

    heartbeat_received = Signal(object)   # HeartbeatInfo
    can_rx = Signal(object)              # CANMessage (all received)

    def __init__(self, adapter: CANAdapter, parent=None):
        super().__init__(parent)
        self.adapter = adapter
        self._running = True
        self._paused = False

    def run(self):
        while self._running:
            if self._paused:
                time.sleep(0.1)
                continue
            try:
                msg = self.adapter.read_message(timeout=0.2)
                if msg is None:
                    continue
                self.can_rx.emit(msg)
                if msg.id == CAN_BOOTLOADER_ID and len(msg.data) > 0 and msg.data[0] == RESP_READY:
                    hb = HeartbeatInfo()
                    if len(msg.data) > 1:
                        hb.version_major = msg.data[1]
                    if len(msg.data) > 2:
                        hb.version_minor = msg.data[2]
                    if len(msg.data) > 3:
                        hb.state = msg.data[3]
                    if len(msg.data) > 4:
                        hb.last_error = msg.data[4]
                    if len(msg.data) > 5:
                        hb.flags = msg.data[5]
                    if len(msg.data) > 7:
                        hb.bytes_written = (msg.data[6] << 8) | msg.data[7]
                    self.heartbeat_received.emit(hb)
            except Exception:
                time.sleep(0.1)

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def stop(self):
        self._running = False
        self.wait(2000)

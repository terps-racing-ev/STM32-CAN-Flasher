"""
Main Window
===========
Top-level window that orchestrates all panels and workers.
"""

import sys

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QStatusBar,
)
from PySide6.QtCore import Slot

from src.backend.can_adapter import CANAdapter
from src.backend.board_config import load_boards
from src.backend.bootloader_protocol import BOOTLOADER_RESPONSE_FILTERS
from src.backend.canable_driver import CANableAdapter, CANableBaudRate
from src.backend.pcan_driver import PCANAdapter, PCANBaudRate, PCANChannel, PCAN_AVAILABLE
from src.backend.flasher import CANBootloaderFlash, HeartbeatInfo
from src.ui.connection_panel import ConnectionPanel
from src.ui.flash_panel import FlashPanel
from src.ui.control_panel import ControlPanel
from src.ui.status_panel import StatusPanel
from src.ui.can_log_panel import CANLogPanel
from src.workers.flash_worker import FlashWorker
from src.workers.status_worker import StatusWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("STM32 CAN Flasher")
        self.setMinimumSize(780, 600)
        self.resize(860, 700)

        self.adapter: CANAdapter | None = None
        self.flasher: CANBootloaderFlash | None = None
        self.status_worker: StatusWorker | None = None
        self.flash_worker: FlashWorker | None = None
        self._boards = load_boards()

        self._build_ui()
        self._connect_signals()
        self._set_controls_enabled(False)

    # -- layout -----------------------------------------------------------

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 10, 12, 6)
        root.setSpacing(8)

        # Connection panel (top)
        self.conn_panel = ConnectionPanel()
        root.addWidget(self.conn_panel)

        # Middle row: Flash panel + control panel side by side
        mid = QHBoxLayout()
        mid.setSpacing(8)

        self.flash_panel = FlashPanel(self._boards)
        mid.addWidget(self.flash_panel, stretch=3)

        self.control_panel = ControlPanel(self._boards)
        mid.addWidget(self.control_panel, stretch=2)

        root.addLayout(mid)

        # Status panel (full width, shows all heartbeat signals)
        self.status_panel = StatusPanel()
        root.addWidget(self.status_panel)

        # CAN log (collapsible)
        self.can_log = CANLogPanel()
        root.addWidget(self.can_log)

        # Status bar
        self.statusBar().showMessage("Disconnected")

    # -- signal wiring ----------------------------------------------------

    def _connect_signals(self):
        self.conn_panel.connect_requested.connect(self._on_connect)
        self.conn_panel.disconnect_requested.connect(self._on_disconnect)

        self.flash_panel.flash_requested.connect(self._on_flash)
        self.flash_panel.cancel_requested.connect(self._on_cancel_flash)

        self.control_panel.reset_requested.connect(self._on_reset)
        self.control_panel.stay_in_bl_requested.connect(self._on_stay_in_bl)
        self.control_panel.jump_requested.connect(self._on_jump)
        self.control_panel.get_status_requested.connect(self._on_get_status)

    def _set_controls_enabled(self, enabled: bool):
        self.flash_panel.flash_btn.setEnabled(enabled)
        self.control_panel.set_enabled_all(enabled)

    # -- connection -------------------------------------------------------

    @Slot(str, str)
    def _on_connect(self, adapter_type: str, channel: str):
        try:
            if adapter_type == "CANable":
                ch = channel if sys.platform.startswith('linux') else int(channel)
                self.adapter = CANableAdapter(channel=ch)
            elif adapter_type == "PCAN":
                if not PCAN_AVAILABLE:
                    QMessageBox.critical(self, "Error", "PCAN drivers not available")
                    return
                self.adapter = PCANAdapter(channel=PCANChannel[channel])
            else:
                QMessageBox.critical(self, "Error", f"Unknown adapter: {adapter_type}")
                return
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", str(e))
            return

        self.adapter.set_receive_filters(BOOTLOADER_RESPONSE_FILTERS)

        if not self.adapter.connect():
            QMessageBox.critical(self, "Connection Error",
                                 f"Failed to connect to {adapter_type} on {channel}")
            self.adapter = None
            return

        if not self.adapter.set_receive_filters(BOOTLOADER_RESPONSE_FILTERS):
            QMessageBox.warning(
                self,
                "Filter Warning",
                "Connected, but failed to apply bootloader receive filters. Performance may degrade on a busy CAN bus.",
            )

        self.flasher = CANBootloaderFlash(self.adapter)
        self.conn_panel.set_connected(True)
        self._set_controls_enabled(True)
        self.statusBar().showMessage(f"Connected: {adapter_type} ch {channel}")

        # Start status worker
        self._start_status_worker()

    @Slot()
    def _on_disconnect(self):
        self._stop_workers()
        if self.adapter:
            self.adapter.disconnect()
            self.adapter = None
        self.flasher = None
        self.conn_panel.set_connected(False)
        self._set_controls_enabled(False)
        self.status_panel.clear()
        self.statusBar().showMessage("Disconnected")

    def _start_status_worker(self):
        if not self.adapter or not self.adapter.is_connected():
            return
        if self.status_worker and self.status_worker.isRunning():
            return
        self.status_worker = StatusWorker(self.adapter)
        self.status_worker.heartbeat_received.connect(self._on_heartbeat)
        self.status_worker.can_rx.connect(self._on_worker_rx)
        self.status_worker.start()

    def _stop_status_worker(self):
        if self.status_worker:
            self.status_worker.stop()
            self.status_worker = None

    def _stop_workers(self):
        self._stop_status_worker()
        if self.flash_worker and self.flash_worker.isRunning():
            self.flash_worker.request_cancel()
            self.flash_worker.wait(3000)
            self.flash_worker = None

    # -- heartbeat --------------------------------------------------------

    @Slot(object)
    def _on_heartbeat(self, hb: HeartbeatInfo):
        self.status_panel.update_from_heartbeat(hb)

    @Slot(object)
    def _on_worker_rx(self, msg):
        self.can_log.add_message("RX", msg.id, msg.data, msg.timestamp)

    # -- flash ------------------------------------------------------------

    @Slot(str, int, int, bool, bool)
    def _on_flash(self, firmware_dir: str, module: int, reset_can_id: int, verify: bool, jump: bool):
        if not firmware_dir:
            QMessageBox.warning(self, "Flash", "Select a firmware directory first")
            return
        if not self.flasher:
            return

        # Stop status worker during flash so only the flash worker reads the adapter.
        self._stop_status_worker()

        self.flash_panel.set_flashing(True)
        self._set_controls_enabled(False)

        self.flash_worker = FlashWorker(
            self.flasher, firmware_dir, module, reset_can_id, verify, jump,
        )
        self.flash_worker.progress.connect(self.flash_panel.set_progress)
        self.flash_worker.status_update.connect(self.flash_panel.set_status)
        self.flash_worker.error_occurred.connect(
            lambda msg: self.statusBar().showMessage(f"Error: {msg}")
        )
        self.flash_worker.can_tx.connect(
            lambda cid, data: self.can_log.add_message("TX", cid, data)
        )
        self.flash_worker.can_rx.connect(
            lambda msg: self.can_log.add_message("RX", msg.id, msg.data, msg.timestamp)
        )
        self.flash_worker.finished_flash.connect(self._on_flash_done)
        self.flash_worker.start()

    @Slot()
    def _on_cancel_flash(self):
        if self.flash_worker:
            self.flash_worker.request_cancel()

    @Slot(bool, str)
    def _on_flash_done(self, success: bool, summary: str):
        self.flash_panel.set_flashing(False)
        self._set_controls_enabled(True)
        self.flash_worker = None
        self._start_status_worker()
        if success:
            self.flash_panel.set_status("Flash complete!")
            self.statusBar().showMessage(summary)
        else:
            self.flash_panel.set_status(f"Failed: {summary}")
            QMessageBox.warning(self, "Flash Failed", summary)

    # -- manual controls --------------------------------------------------

    @Slot(int, int)
    def _on_reset(self, module: int, reset_can_id: int):
        if not self.flasher:
            return
        self.flasher.on_can_tx = lambda cid, data: self.can_log.add_message("TX", cid, data)
        self.flasher.send_reset_message(module, reset_can_id_override=reset_can_id)
        self.statusBar().showMessage(f"Reset sent to module {module}")

    @Slot()
    def _on_stay_in_bl(self):
        if not self.flasher:
            return
        self.flasher.on_can_tx = lambda cid, data: self.can_log.add_message("TX", cid, data)
        if self.flasher.stay_in_bootloader():
            self.statusBar().showMessage("Stay-in-bootloader command sent")
        else:
            self.statusBar().showMessage("Failed to send stay-in-bootloader")

    @Slot()
    def _on_jump(self):
        if not self.flasher:
            return
        self.flasher.on_can_tx = lambda cid, data: self.can_log.add_message("TX", cid, data)
        self.flasher.on_can_rx = lambda msg: self.can_log.add_message("RX", msg.id, msg.data, msg.timestamp)
        self.flasher.jump_to_application()

    @Slot()
    def _on_get_status(self):
        if not self.flasher:
            return
        self.flasher.on_can_tx = lambda cid, data: self.can_log.add_message("TX", cid, data)
        self.flasher.on_can_rx = lambda msg: self.can_log.add_message("RX", msg.id, msg.data, msg.timestamp)
        status = self.flasher.get_status()
        if status:
            self.statusBar().showMessage(str(status))
        else:
            self.statusBar().showMessage("No status response")
        # Also refresh bank status
        bs = self.flasher.get_active_bank()
        if bs:
            self.status_panel.update_from_bank_status(bs)

    # -- cleanup ----------------------------------------------------------

    def closeEvent(self, event):
        self._stop_workers()
        if self.adapter:
            self.adapter.disconnect()
        event.accept()

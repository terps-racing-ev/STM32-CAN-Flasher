"""
Flash Worker
============
QThread that runs the full flash sequence in the background.
"""

from pathlib import Path
from PySide6.QtCore import QThread, Signal

from src.backend.flasher import CANBootloaderFlash, CANMessage


class FlashWorker(QThread):
    """Background thread for the complete flash sequence."""

    progress = Signal(int, str)           # (percent, message)
    status_update = Signal(str)           # status text
    error_occurred = Signal(str)          # error text
    finished_flash = Signal(bool, str)    # (success, summary)
    can_tx = Signal(int, bytes)           # (can_id, data)
    can_rx = Signal(object)              # CANMessage

    def __init__(self, flasher: CANBootloaderFlash, firmware_dir: str,
                 module: int, reset_can_id: int, verify: bool = True,
                 jump: bool = True, parent=None):
        super().__init__(parent)
        self.flasher = flasher
        self.firmware_dir = firmware_dir
        self.module = module
        self.reset_can_id = reset_can_id
        self.verify = verify
        self.jump = jump

    def run(self):
        # Wire callbacks to emit Qt signals
        self.flasher.on_progress = lambda pct, msg: self.progress.emit(pct, msg)
        self.flasher.on_status = lambda msg: self.status_update.emit(msg)
        self.flasher.on_error = lambda msg: self.error_occurred.emit(msg)
        self.flasher.on_can_tx = lambda cid, data: self.can_tx.emit(cid, data)
        self.flasher.on_can_rx = lambda msg: self.can_rx.emit(msg)
        self.flasher._cancel_requested = False

        try:
            self.flasher.adapter.clear_receive_queue()

            # Reset module into bootloader
            self.status_update.emit(f"Resetting module {self.module}...")
            if not self.flasher.send_reset_message(self.module, reset_can_id_override=self.reset_can_id):
                self.finished_flash.emit(False, "Failed to send reset message")
                return

            # Wait for the first READY quickly, before the module can auto-jump.
            if not self.flasher.wait_for_bootloader_ready(timeout=2.0):
                self.error_occurred.emit("Bootloader did not respond with READY")
                self.finished_flash.emit(False, "Bootloader not ready")
                return

            # Immediately send a bootloader command so the reset window does not expire.
            if not self.flasher.get_status():
                self.error_occurred.emit("Bootloader did not respond to initial status request")
                self.finished_flash.emit(False, "Bootloader handshake failed")
                return

            # Run flash sequence
            fw_path = Path(self.firmware_dir)
            ok = self.flasher.flash_firmware(
                fw_path, verify=self.verify, jump=self.jump,
            )

            if ok:
                self.finished_flash.emit(True, "Flash completed successfully")
            else:
                self.finished_flash.emit(False, "Flash failed")

        except Exception as e:
            self.error_occurred.emit(str(e))
            self.finished_flash.emit(False, f"Exception: {e}")

    def request_cancel(self):
        self.flasher.request_cancel()

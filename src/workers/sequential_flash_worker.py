"""
Sequential Flash Worker
=======================
QThread that flashes multiple modules one after another.
"""

from pathlib import Path
from typing import List, Tuple

from PySide6.QtCore import QThread, Signal

from src.backend.flasher import CANBootloaderFlash


class SequentialFlashWorker(QThread):
    """Background thread that flashes a list of modules sequentially."""

    progress = Signal(int, str)           # (overall percent, message)
    status_update = Signal(str)           # status text
    error_occurred = Signal(str)          # error text
    finished_flash = Signal(bool, str)    # (all_success, summary)
    can_tx = Signal(int, bytes)           # (can_id, data)
    can_rx = Signal(object)              # CANMessage

    def __init__(self, flasher: CANBootloaderFlash, firmware_dir: str,
                 targets: List[Tuple[int, int]], verify: bool = True,
                 jump: bool = True, parent=None):
        super().__init__(parent)
        self.flasher = flasher
        self.firmware_dir = firmware_dir
        self.targets = targets          # [(module_id, reset_can_id), ...]
        self.verify = verify
        self.jump = jump
        self._cancel = False

    def run(self):
        total = len(self.targets)
        passed = 0

        self.flasher.on_can_tx = lambda cid, data: self.can_tx.emit(cid, data)
        self.flasher.on_can_rx = lambda msg: self.can_rx.emit(msg)
        self.flasher.on_error = lambda msg: self.error_occurred.emit(msg)

        for i, (module, reset_can_id) in enumerate(self.targets):
            if self._cancel:
                self.finished_flash.emit(False, f"Cancelled after {passed}/{total} modules")
                return

            # Delay between modules (not before the first one)
            if i > 0:
                self.status_update.emit(f"Waiting 5s before module {module}...")
                for _ in range(50):
                    if self._cancel:
                        self.finished_flash.emit(False, f"Cancelled after {passed}/{total} modules")
                        return
                    self.msleep(100)

            base_pct = int(i / total * 100)
            label = f"[{i + 1}/{total}] Module {module}"

            def _progress(pct, msg, _base=base_pct, _span=int(100 / total), _label=label):
                overall = _base + int(pct * _span / 100)
                self.progress.emit(overall, f"{_label}: {msg}")

            self.flasher.on_progress = _progress
            self.flasher.on_status = lambda msg, _l=label: self.status_update.emit(f"{_l}: {msg}")
            self.flasher._cancel_requested = False

            self.status_update.emit(f"{label} — resetting...")
            _progress(0, "Resetting...")

            try:
                self.flasher.adapter.clear_receive_queue()

                if not self.flasher.send_reset_message(module, reset_can_id_override=reset_can_id):
                    self.error_occurred.emit(f"{label}: failed to send reset")
                    self.finished_flash.emit(False, f"Failed at module {module}: could not send reset ({passed}/{total} completed)")
                    return

                if not self.flasher.wait_for_bootloader_ready(timeout=2.0):
                    self.error_occurred.emit(f"{label}: bootloader not ready")
                    self.finished_flash.emit(False, f"Failed at module {module}: bootloader not ready ({passed}/{total} completed)")
                    return

                if not self.flasher.get_status():
                    self.error_occurred.emit(f"{label}: handshake failed")
                    self.finished_flash.emit(False, f"Failed at module {module}: handshake failed ({passed}/{total} completed)")
                    return

                fw_path = Path(self.firmware_dir)
                ok = self.flasher.flash_firmware(
                    fw_path, verify=self.verify, jump=self.jump,
                )

                if ok:
                    passed += 1
                    _progress(100, "Done")
                else:
                    self.finished_flash.emit(False, f"Failed at module {module}: flash failed ({passed}/{total} completed)")
                    return

            except Exception as e:
                self.error_occurred.emit(f"{label}: {e}")
                self.finished_flash.emit(False, f"Failed at module {module}: {e} ({passed}/{total} completed)")
                return

        self.progress.emit(100, "Sequential flash complete")
        self.finished_flash.emit(True, f"All {total} modules flashed successfully")

    def request_cancel(self):
        self._cancel = True
        self.flasher.request_cancel()

"""
CAN Bootloader Flasher
=======================
Core flash logic ported from STM32-CAN-Bootloader/Scripts/Flash_Application.py.
Uses plain-Python callbacks for progress reporting so it stays testable without Qt.
"""

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Callable

from src.backend.can_adapter import CANAdapter, CANMessage
from src.backend.bootloader_protocol import (
    CAN_HOST_ID, CAN_BOOTLOADER_ID, BMS_RESET_CMD_BASE,
    CMD_ERASE_FLASH, CMD_READ_FLASH, CMD_JUMP_TO_APP,
    CMD_GET_STATUS, CMD_SET_ADDRESS, CMD_WRITE_DATA,
    CMD_GET_ACTIVE_BANK, CMD_SET_IMAGE_INFO, CMD_VERIFY_BANK,
    RESP_ACK, RESP_NACK, RESP_READY, RESP_DATA,
    BANK_A_ADDRESS, BANK_B_ADDRESS, BANK_SIZE,
    RESPONSE_TIMEOUT, ERASE_TIMEOUT, WRITE_TIMEOUT, READ_TIMEOUT,
    BOOTLOADER_READY_TIMEOUT, MAX_RETRIES,
    STATE_NAMES, ERROR_DESCRIPTIONS,
    bank_name, reset_can_id, decode_error,
)
from src.backend.firmware_utils import (
    select_firmware_for_bank, compute_crc32, pad_to_8byte_boundary,
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class BootloaderStatus:
    state: int
    error: int
    bytes_written: int

    def __str__(self):
        sn = STATE_NAMES.get(self.state, 'UNKNOWN')
        ed = ERROR_DESCRIPTIONS.get(self.error, f'Error {self.error}')
        return f"State: {sn}, Error: {ed}, Bytes Written: {self.bytes_written}"


@dataclass
class BankStatus:
    active_bank: int
    bank_a_valid: int
    bank_b_valid: int

    @property
    def inactive_bank(self) -> int:
        return 1 if self.active_bank == 0 else 0

    @property
    def inactive_start_address(self) -> int:
        return BANK_B_ADDRESS if self.active_bank == 0 else BANK_A_ADDRESS

    @staticmethod
    def bank_start_address(bank: int) -> int:
        return BANK_A_ADDRESS if bank == 0 else BANK_B_ADDRESS

    def __str__(self):
        an = bank_name(self.active_bank)
        va = 'valid' if self.bank_a_valid else 'invalid'
        vb = 'valid' if self.bank_b_valid else 'invalid'
        return f"Active bank: {an} | Bank A: {va} | Bank B: {vb}"


@dataclass
class HeartbeatInfo:
    """Parsed RESP_READY heartbeat."""
    ready_code: int = 0
    crc_health: int = 0
    state: int = 0
    last_error: int = 0
    flags: int = 0
    bytes_written: int = 0

    @property
    def active_bank(self) -> int:
        return 1 if (self.flags & 0x01) else 0

    @property
    def bank_a_valid(self) -> bool:
        return bool(self.flags & 0x02)

    @property
    def bank_b_valid(self) -> bool:
        return bool(self.flags & 0x04)

    @property
    def metadata_ready(self) -> bool:
        return bool(self.flags & 0x08)

    @property
    def can_cmd_received(self) -> bool:
        return bool(self.flags & 0x10)

    @property
    def image_info_valid(self) -> bool:
        return bool(self.flags & 0x20)

    @property
    def verified_bank_valid(self) -> bool:
        return bool(self.flags & 0x40)

    @property
    def jump_pending(self) -> bool:
        return bool(self.flags & 0x80)

    @property
    def bank_a_crc_ok(self) -> bool:
        return bool(self.crc_health & 0x01)

    @property
    def bank_b_crc_ok(self) -> bool:
        return bool(self.crc_health & 0x02)


# ---------------------------------------------------------------------------
# Flasher
# ---------------------------------------------------------------------------

class CANBootloaderFlash:
    """
    Main class for flashing firmware via the CAN bootloader.

    Progress is reported through optional callbacks so the GUI worker layer
    can bridge them into Qt signals without coupling this module to PySide6.
    """

    def __init__(self, adapter: CANAdapter):
        self.adapter = adapter
        self.connected = False

        # Last parsed heartbeat state
        self.last_heartbeat: Optional[HeartbeatInfo] = None

        # Callbacks — set by the worker before starting operations
        self.on_progress: Optional[Callable[[int, str], None]] = None   # (percent, message)
        self.on_status: Optional[Callable[[str], None]] = None          # status text
        self.on_error: Optional[Callable[[str], None]] = None           # error text
        self.on_can_tx: Optional[Callable[[int, bytes], None]] = None   # (can_id, data)
        self.on_can_rx: Optional[Callable[[CANMessage], None]] = None   # received msg

        # Cancellation flag (set by worker thread via requestInterruption)
        self._cancel_requested = False

    # -- helpers ----------------------------------------------------------

    def _emit_status(self, msg: str):
        if self.on_status:
            self.on_status(msg)

    def _emit_error(self, msg: str):
        if self.on_error:
            self.on_error(msg)

    def _emit_progress(self, pct: int, msg: str = ""):
        if self.on_progress:
            self.on_progress(pct, msg)

    def _check_cancel(self) -> bool:
        return self._cancel_requested

    def request_cancel(self):
        self._cancel_requested = True

    # -- connection -------------------------------------------------------

    def connect(self) -> bool:
        self._emit_status("Connecting to CAN adapter...")
        if not self.adapter.connect():
            self._emit_error("Failed to connect to CAN adapter")
            return False
        self.connected = True
        self.adapter.clear_receive_queue()
        self._emit_status("Connected")
        return True

    def disconnect(self):
        if self.connected:
            self.adapter.disconnect()
            self.connected = False

    # -- low-level protocol -----------------------------------------------

    def send_command(self, command: int, data: list) -> bool:
        msg_data = [command] + data
        while len(msg_data) < 8:
            msg_data.append(0x00)
        raw = bytes(msg_data[:8])
        if self.on_can_tx:
            self.on_can_tx(CAN_HOST_ID, raw)
        return self.adapter.send_message(CAN_HOST_ID, raw, is_extended=True)

    def wait_response(self, timeout: float = RESPONSE_TIMEOUT) -> Optional[CANMessage]:
        start = time.time()
        while (time.time() - start) < timeout:
            remaining = timeout - (time.time() - start)
            if remaining <= 0:
                break
            msg = self.adapter.read_message(timeout=min(0.05, remaining))
            if msg and msg.id == CAN_BOOTLOADER_ID:
                if self.on_can_rx:
                    self.on_can_rx(msg)
                return msg
            # Forward non-bootloader messages to monitor
            if msg and self.on_can_rx:
                self.on_can_rx(msg)
        return None

    # -- bootloader commands ----------------------------------------------

    def wait_for_bootloader_ready(self, timeout: float = BOOTLOADER_READY_TIMEOUT) -> bool:
        self._emit_status("Waiting for bootloader READY...")
        start = time.time()
        while (time.time() - start) < timeout:
            msg = self.adapter.read_message(timeout=0.1)
            if msg and self.on_can_rx:
                self.on_can_rx(msg)
            if msg and msg.id == CAN_BOOTLOADER_ID and len(msg.data) > 0 and msg.data[0] == RESP_READY:
                hb = HeartbeatInfo()
                if len(msg.data) > 1:
                    hb.ready_code = msg.data[1]
                if len(msg.data) > 2:
                    hb.crc_health = msg.data[2]
                if len(msg.data) > 3:
                    hb.state = msg.data[3]
                if len(msg.data) > 4:
                    hb.last_error = msg.data[4]
                if len(msg.data) > 5:
                    hb.flags = msg.data[5]
                if len(msg.data) > 7:
                    hb.bytes_written = (msg.data[6] << 8) | msg.data[7]
                self.last_heartbeat = hb
                self._emit_status(
                    f"Bootloader READY "
                    f"(active bank {bank_name(hb.active_bank)})"
                )
                return True
        self._emit_status("No READY message received")
        return False

    def get_status(self) -> Optional[BootloaderStatus]:
        self._emit_status("Getting status...")
        for attempt in range(MAX_RETRIES):
            if attempt > 0:
                self.adapter.clear_receive_queue()
                time.sleep(0.05)
            if not self.send_command(CMD_GET_STATUS, []):
                continue
            resp = self.wait_response()
            if not resp or len(resp.data) < 7:
                continue
            if resp.data[0] == RESP_DATA:
                return BootloaderStatus(
                    state=resp.data[1],
                    error=resp.data[2],
                    bytes_written=(resp.data[3] << 24) | (resp.data[4] << 16) |
                                  (resp.data[5] << 8) | resp.data[6],
                )
        return None

    def get_active_bank(self) -> Optional[BankStatus]:
        self._emit_status("Querying active bank...")
        for attempt in range(MAX_RETRIES):
            if attempt > 0:
                self.adapter.clear_receive_queue()
                time.sleep(0.05)
            if not self.send_command(CMD_GET_ACTIVE_BANK, []):
                continue
            resp = self.wait_response()
            if not resp or len(resp.data) < 4:
                continue
            if resp.data[0] == RESP_DATA:
                return BankStatus(
                    active_bank=resp.data[1],
                    bank_a_valid=resp.data[2],
                    bank_b_valid=resp.data[3],
                )
        return None

    def erase_flash(self) -> bool:
        self._emit_status("Erasing flash...")
        self._emit_progress(0, "Erasing...")
        for attempt in range(MAX_RETRIES):
            if attempt > 0:
                self.adapter.clear_receive_queue()
                time.sleep(0.1)
            if not self.send_command(CMD_ERASE_FLASH, []):
                continue
            resp = self.wait_response(timeout=ERASE_TIMEOUT)
            if not resp:
                continue
            if resp.data[0] == RESP_ACK:
                self._emit_status("Flash erased")
                return True
            if resp.data[0] == RESP_NACK:
                ec = resp.data[1] if len(resp.data) > 1 else 0
                self._emit_error(f"Erase NACK: {decode_error(ec)}")
                return False
        self._emit_error("Erase failed after retries")
        return False

    def set_address(self, address: int) -> bool:
        addr_bytes = [
            (address >> 24) & 0xFF,
            (address >> 16) & 0xFF,
            (address >> 8) & 0xFF,
            address & 0xFF,
        ]
        if not self.send_command(CMD_SET_ADDRESS, addr_bytes):
            return False
        resp = self.wait_response()
        if not resp:
            return False
        if resp.data[0] == RESP_ACK:
            return True
        if resp.data[0] == RESP_NACK:
            ec = resp.data[1] if len(resp.data) > 1 else 0
            self._emit_error(f"Set address NACK: {decode_error(ec)}")
        return False

    def write_4bytes(self, data: bytes) -> bool:
        if len(data) != 4:
            return False
        cmd_data = [0x04] + list(data)
        if not self.send_command(CMD_WRITE_DATA, cmd_data):
            return False
        resp = self.wait_response(timeout=WRITE_TIMEOUT)
        if not resp:
            return False
        if resp.data[0] == RESP_ACK:
            return True
        if resp.data[0] == RESP_NACK:
            ec = resp.data[1] if len(resp.data) > 1 else 0
            self._emit_error(f"Write NACK: {decode_error(ec)}")
        return False

    def write_firmware(self, firmware_data: bytes, start_address: int) -> bool:
        firmware_data = pad_to_8byte_boundary(firmware_data)
        total = len(firmware_data)
        self._emit_status(f"Writing {total} bytes...")
        self._emit_progress(0, "Writing...")

        # Set initial address
        for attempt in range(MAX_RETRIES):
            if self.set_address(start_address):
                break
            self.adapter.clear_receive_queue()
            time.sleep(0.05)
        else:
            self._emit_error("Failed to set initial address")
            return False

        self.adapter.clear_receive_queue()
        written = 0
        start_time = time.time()
        last_pct = -1

        # Suppress per-message CAN callbacks during the hot write loop
        saved_tx = self.on_can_tx
        saved_rx = self.on_can_rx
        self.on_can_tx = None
        self.on_can_rx = None

        try:
            while written < total:
                if self._check_cancel():
                    self._emit_error("Cancelled by user")
                    return False

                word = firmware_data[written:written + 8]
                chunk_a, chunk_b = word[:4], word[4:]

                success = False
                for attempt in range(MAX_RETRIES):
                    if attempt > 0:
                        self.adapter.clear_receive_queue()
                        time.sleep(0.01)
                        if not self.set_address(start_address + written):
                            continue
                    if not self.write_4bytes(chunk_a):
                        continue
                    if not self.write_4bytes(chunk_b):
                        continue
                    success = True
                    break

                if not success:
                    self._emit_error(f"Write failed at offset 0x{written:08X}")
                    return False

                written += 8
                pct = int(written * 100 / total)
                if pct != last_pct:
                    elapsed = time.time() - start_time
                    speed = written / elapsed / 1024 if elapsed > 0 else 0
                    self._emit_progress(pct, f"{pct}% \u2014 {speed:.1f} KB/s")
                    last_pct = pct

        finally:
            self.on_can_tx = saved_tx
            self.on_can_rx = saved_rx

        elapsed = time.time() - start_time
        self._emit_status(f"Write complete ({elapsed:.1f}s)")
        return True

    def read_data(self, address: int, length: int) -> Optional[bytes]:
        if length == 0 or length > 7:
            return None
        addr_bytes = [
            (address >> 24) & 0xFF,
            (address >> 16) & 0xFF,
            (address >> 8) & 0xFF,
            address & 0xFF,
            length,
        ]
        if not self.send_command(CMD_READ_FLASH, addr_bytes):
            return None
        msg = self.wait_response(timeout=READ_TIMEOUT)
        if msg and len(msg.data) > 0 and msg.data[0] == RESP_DATA:
            return bytes(msg.data[1:1 + length])
        return None

    def set_image_info(self, crc32: int, image_size: int) -> bool:
        if image_size <= 0 or image_size > BANK_SIZE:
            self._emit_error(f"Invalid image size: {image_size}")
            return False
        payload = [
            (crc32 >> 24) & 0xFF, (crc32 >> 16) & 0xFF,
            (crc32 >> 8) & 0xFF, crc32 & 0xFF,
            (image_size >> 16) & 0xFF, (image_size >> 8) & 0xFF, image_size & 0xFF,
        ]
        if not self.send_command(CMD_SET_IMAGE_INFO, payload):
            return False
        resp = self.wait_response()
        return bool(resp and resp.data[0] == RESP_ACK)

    def verify_inactive_bank_crc(self) -> bool:
        self._emit_status("Verifying CRC...")
        if not self.send_command(CMD_VERIFY_BANK, []):
            return False
        resp = self.wait_response(timeout=ERASE_TIMEOUT)
        if not resp:
            self._emit_error("Verify CRC timeout")
            return False
        if resp.data[0] == RESP_ACK:
            self._emit_status("CRC verified")
            return True
        if resp.data[0] == RESP_NACK:
            ec = resp.data[1] if len(resp.data) > 1 else 0
            self._emit_error(f"CRC verify NACK: {decode_error(ec)}")
        return False

    def verify_flash(self, expected_data: bytes, start_address: int) -> bool:
        self._emit_status("Read-back verification...")
        self._emit_progress(0, "Verifying...")
        total = len(expected_data)
        verified = 0
        chunk_size = 4
        last_pct = -1
        self.adapter.clear_receive_queue()

        # Suppress per-message CAN callbacks during verify loop
        saved_tx = self.on_can_tx
        saved_rx = self.on_can_rx
        self.on_can_tx = None
        self.on_can_rx = None

        try:
            while verified < total:
                if self._check_cancel():
                    self._emit_error("Cancelled by user")
                    return False

                remaining = total - verified
                read_size = min(chunk_size, remaining)
                read_bytes = None
                for attempt in range(MAX_RETRIES):
                    if attempt > 0:
                        self.adapter.clear_receive_queue()
                        time.sleep(0.01)
                    read_bytes = self.read_data(start_address + verified, read_size)
                    if read_bytes is not None:
                        break

                if read_bytes is None:
                    self._emit_error(f"Read failed at 0x{start_address + verified:08X}")
                    return False

                expected_chunk = expected_data[verified:verified + read_size]
                if read_bytes != expected_chunk:
                    self._emit_error(
                        f"Verify mismatch at 0x{start_address + verified:08X}: "
                        f"expected {expected_chunk.hex()} got {read_bytes.hex()}"
                    )
                    return False

                verified += read_size
                pct = int(verified * 100 / total)
                if pct != last_pct:
                    self._emit_progress(pct, f"Verifying {pct}%")
                    last_pct = pct

        finally:
            self.on_can_tx = saved_tx
            self.on_can_rx = saved_rx

        self._emit_status("Verification passed")
        return True

    def jump_to_application(self) -> bool:
        self._emit_status("Jumping to application...")
        if not self.send_command(CMD_JUMP_TO_APP, []):
            self._emit_error("Failed to send jump command")
            return False
        resp = self.wait_response(timeout=0.5)
        if resp and resp.data[0] == RESP_ACK:
            self._emit_status("Application started")
            return True
        if resp and resp.data[0] == RESP_NACK:
            ec = resp.data[1] if len(resp.data) > 1 else 0
            self._emit_error(f"Jump NACK: {decode_error(ec)}")
            return False
        # No response may mean bootloader already jumped
        self._emit_status("Jump command sent (bootloader may have jumped)")
        return True

    def send_reset_message(self, module: int, reset_can_id_override: int | None = None) -> bool:
        if reset_can_id_override is not None:
            rid = reset_can_id_override
        else:
            if module < 0 or module > 15:
                self._emit_error(f"Invalid module: {module}")
                return False
            rid = reset_can_id(module)
        self._emit_status(f"Resetting module {module} (CAN ID 0x{rid:08X})...")
        if self.on_can_tx:
            self.on_can_tx(rid, bytes(8))
        if not self.adapter.send_message(rid, bytes(8), is_extended=True):
            self._emit_error("Failed to send reset message")
            return False
        self._emit_status("Reset message sent")
        return True

    def stay_in_bootloader(self) -> bool:
        """Send GET_STATUS to prevent the bootloader auto-jump timeout."""
        return self.send_command(CMD_GET_STATUS, [])

    # -- high-level flash sequence ----------------------------------------

    def flash_firmware(self, firmware_path: Path, verify: bool = True,
                       jump: bool = True, target_bank: Optional[int] = None) -> bool:
        self._cancel_requested = False

        # Determine active / target bank
        bank_status = self.get_active_bank()
        hb_bank = self.last_heartbeat.active_bank if self.last_heartbeat else None

        if target_bank is None:
            active = hb_bank if hb_bank is not None else (bank_status.active_bank if bank_status else None)
            if active is None:
                self._emit_error("Cannot determine active bank")
                return False
            target_bank = 1 if active == 0 else 0
        else:
            active = bank_status.active_bank if bank_status else hb_bank

        if active is not None and target_bank == active:
            self._emit_error(
                f"Cannot flash Bank {bank_name(target_bank)}: it is currently active"
            )
            return False

        target_address = BankStatus.bank_start_address(target_bank)
        selected = select_firmware_for_bank(firmware_path, target_bank)
        if not selected or not selected.exists():
            self._emit_error("Could not resolve firmware file for target bank")
            return False

        self._emit_status(
            f"Flashing {selected.name} → Bank {bank_name(target_bank)} "
            f"@ 0x{target_address:08X}"
        )

        # Read firmware
        try:
            fw_data = selected.read_bytes()
        except Exception as e:
            self._emit_error(f"Failed to read firmware: {e}")
            return False

        if len(fw_data) > BANK_SIZE:
            self._emit_error(f"Firmware too large ({len(fw_data)} > {BANK_SIZE})")
            return False

        fw_data = pad_to_8byte_boundary(fw_data)
        crc = compute_crc32(fw_data)

        # Get initial status
        self.get_status()

        # Erase
        if not self.erase_flash():
            return False

        # Write
        if not self.write_firmware(fw_data, target_address):
            return False

        # CRC metadata
        if not self.set_image_info(crc, len(fw_data)):
            self._emit_error("Failed to send image info")
            return False

        if not self.verify_inactive_bank_crc():
            return False

        # Optional read-back verify
        if verify:
            if not self.verify_flash(fw_data, target_address):
                return False

        # Jump
        if jump:
            self._emit_status(f"Committing bank switch → Bank {bank_name(target_bank)}...")
            if not self.jump_to_application():
                self._emit_error("Jump command may have failed")

        self._emit_status("Flash complete")
        self._emit_progress(100, "Complete")
        return True

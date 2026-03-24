"""
Bootloader Protocol Constants
==============================
CAN IDs, command/response codes, error codes, state definitions,
and timing constants for the STM32L432 CAN bootloader protocol.
"""

# ---------------------------------------------------------------------------
# CAN IDs — 29-bit Extended
# ---------------------------------------------------------------------------
CAN_HOST_ID = 0x18000701        # PC → Bootloader
CAN_BOOTLOADER_ID = 0x18000700  # Bootloader → PC
BMS_RESET_CMD_BASE = 0x08F00F02 # Reset MCU command (module ID in bits 15:12)

# ---------------------------------------------------------------------------
# Commands (first byte of host → bootloader frame)
# ---------------------------------------------------------------------------
CMD_ERASE_FLASH = 0x01
CMD_WRITE_FLASH = 0x02      # Legacy
CMD_READ_FLASH = 0x03
CMD_JUMP_TO_APP = 0x04
CMD_GET_STATUS = 0x05
CMD_SET_ADDRESS = 0x06
CMD_WRITE_DATA = 0x07       # 4-byte buffered write
CMD_GET_ACTIVE_BANK = 0x08
CMD_SET_IMAGE_INFO = 0x09
CMD_VERIFY_BANK = 0x0A

COMMAND_NAMES = {
    CMD_ERASE_FLASH: "ERASE_FLASH",
    CMD_WRITE_FLASH: "WRITE_FLASH",
    CMD_READ_FLASH: "READ_FLASH",
    CMD_JUMP_TO_APP: "JUMP_TO_APP",
    CMD_GET_STATUS: "GET_STATUS",
    CMD_SET_ADDRESS: "SET_ADDRESS",
    CMD_WRITE_DATA: "WRITE_DATA",
    CMD_GET_ACTIVE_BANK: "GET_ACTIVE_BANK",
    CMD_SET_IMAGE_INFO: "SET_IMAGE_INFO",
    CMD_VERIFY_BANK: "VERIFY_BANK",
}

# ---------------------------------------------------------------------------
# Responses (first byte of bootloader → host frame)
# ---------------------------------------------------------------------------
RESP_ACK = 0x10
RESP_NACK = 0x11
RESP_ERROR = 0x12
RESP_BUSY = 0x13
RESP_READY = 0x14
RESP_DATA = 0x15

RESPONSE_NAMES = {
    RESP_ACK: "ACK",
    RESP_NACK: "NACK",
    RESP_ERROR: "ERROR",
    RESP_BUSY: "BUSY",
    RESP_READY: "READY",
    RESP_DATA: "DATA",
}

# ---------------------------------------------------------------------------
# Error Codes
# ---------------------------------------------------------------------------
ERR_NONE = 0x00
ERR_INVALID_COMMAND = 0x01
ERR_INVALID_ADDRESS = 0x02
ERR_FLASH_ERASE_FAILED = 0x03
ERR_FLASH_WRITE_FAILED = 0x04
ERR_INVALID_DATA_LENGTH = 0x05
ERR_NO_VALID_APP = 0x06
ERR_TIMEOUT = 0x07
ERR_CRC_MISMATCH = 0x08

ERROR_DESCRIPTIONS = {
    ERR_NONE: "No error",
    ERR_INVALID_COMMAND: "Invalid command",
    ERR_INVALID_ADDRESS: "Invalid address",
    ERR_FLASH_ERASE_FAILED: "Flash erase failed",
    ERR_FLASH_WRITE_FAILED: "Flash write failed",
    ERR_INVALID_DATA_LENGTH: "Invalid data length",
    ERR_NO_VALID_APP: "No valid application",
    ERR_TIMEOUT: "Operation timeout",
    ERR_CRC_MISMATCH: "CRC mismatch",
}

# ---------------------------------------------------------------------------
# Bootloader States
# ---------------------------------------------------------------------------
STATE_IDLE = 0
STATE_ERASING = 1
STATE_WRITING = 2
STATE_READING = 3
STATE_VERIFYING = 4
STATE_JUMPING = 5

STATE_NAMES = {
    STATE_IDLE: "IDLE",
    STATE_ERASING: "ERASING",
    STATE_WRITING: "WRITING",
    STATE_READING: "READING",
    STATE_VERIFYING: "VERIFYING",
    STATE_JUMPING: "JUMPING",
}

# ---------------------------------------------------------------------------
# Heartbeat Flags (byte 5 of RESP_READY)
# ---------------------------------------------------------------------------
FLAG_ACTIVE_BANK = 0x01       # bit 0: 0=A, 1=B
FLAG_BANK_A_VALID = 0x02      # bit 1
FLAG_BANK_B_VALID = 0x04      # bit 2
FLAG_METADATA_READY = 0x08    # bit 3
FLAG_CAN_CMD_RECEIVED = 0x10  # bit 4
FLAG_IMAGE_INFO_VALID = 0x20  # bit 5
FLAG_VERIFIED_BANK = 0x40     # bit 6
FLAG_JUMP_PENDING = 0x80      # bit 7

# ---------------------------------------------------------------------------
# CRC Health Flags (byte 2 of RESP_READY)
# ---------------------------------------------------------------------------
CRC_BANK_A_OK = 0x01          # bit 0: Bank A stored CRC matches flash
CRC_BANK_B_OK = 0x02          # bit 1: Bank B stored CRC matches flash

# ---------------------------------------------------------------------------
# Memory Layout
# ---------------------------------------------------------------------------
BANK_A_ADDRESS = 0x08008000
BANK_B_ADDRESS = 0x08022000
BANK_SIZE = 104 * 1024  # 104 KB

# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------
RESPONSE_TIMEOUT = 2.0    # Normal response timeout (s)
ERASE_TIMEOUT = 15.0      # Flash erase timeout (s)
WRITE_TIMEOUT = 0.5       # Per-chunk write ACK timeout (s)
READ_TIMEOUT = 0.5        # Per-chunk read response timeout (s)
BOOTLOADER_READY_TIMEOUT = 3.0  # Wait for READY heartbeat (s)
MAX_RETRIES = 3

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def bank_name(bank: int) -> str:
    return 'A' if bank == 0 else 'B'


def reset_can_id(module: int) -> int:
    """Compute CAN ID for resetting a specific module into bootloader."""
    return BMS_RESET_CMD_BASE | (module << 12)


def decode_command(byte0: int) -> str:
    return COMMAND_NAMES.get(byte0, f"UNKNOWN(0x{byte0:02X})")


def decode_response(byte0: int) -> str:
    return RESPONSE_NAMES.get(byte0, f"UNKNOWN(0x{byte0:02X})")


def decode_error(code: int) -> str:
    return ERROR_DESCRIPTIONS.get(code, f"Unknown error 0x{code:02X}")

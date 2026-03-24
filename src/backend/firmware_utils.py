"""
Firmware Utilities
==================
File discovery, bank-specific selection, CRC32 computation, and padding.
"""

import binascii
from pathlib import Path
from typing import Optional, List, Tuple


def discover_firmware_files(directory: Path) -> Tuple[Optional[Path], Optional[Path]]:
    """
    Scan *directory* for ``*_a.bin`` and ``*_b.bin`` firmware files.

    Returns:
        (bank_a_file, bank_b_file) — either may be None if not found.
    """
    if not directory.is_dir():
        return None, None

    bank_a = None
    bank_b = None

    for f in sorted(directory.glob('*.bin')):
        stem = f.stem.lower()
        if stem.endswith('_a'):
            bank_a = bank_a or f
        elif stem.endswith('_b'):
            bank_b = bank_b or f

    return bank_a, bank_b


def select_firmware_for_bank(input_path: Path, target_bank: int) -> Optional[Path]:
    """
    Pick the correct firmware file for *target_bank* (0 = A, 1 = B).

    *input_path* may be a directory containing ``*_a.bin`` / ``*_b.bin`` pairs,
    or a specific ``.bin`` file.
    """
    target_suffix = '_a' if target_bank == 0 else '_b'
    other_suffix = '_b' if target_bank == 0 else '_a'

    if input_path.is_dir():
        candidates = sorted(input_path.glob(f'*{target_suffix}.bin'))
        return candidates[0] if candidates else None

    stem = input_path.stem
    if stem.endswith(target_suffix):
        return input_path

    if stem.endswith(other_suffix):
        candidate = input_path.with_name(stem[:-2] + target_suffix + input_path.suffix)
        return candidate if candidate.exists() else None

    candidate = input_path.with_name(stem + target_suffix + input_path.suffix)
    if candidate.exists():
        return candidate

    return input_path if input_path.exists() else None


def compute_crc32(data: bytes) -> int:
    """Return unsigned CRC-32 of *data*."""
    return binascii.crc32(data) & 0xFFFFFFFF


def pad_to_8byte_boundary(data: bytes) -> bytes:
    """Pad *data* to the next 8-byte boundary with ``0xFF``."""
    remainder = len(data) % 8
    if remainder:
        data += b'\xFF' * (8 - remainder)
    return data

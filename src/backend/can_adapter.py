"""
CAN Adapter Abstraction Layer
==============================
Abstract base class and unified message type for CAN adapters.
Supports both CANable (gs_usb) and PCAN adapters.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List
import time


@dataclass
class CANMessage:
    """Unified CAN message compatible with all adapter backends."""
    id: int
    data: bytes
    timestamp: float = field(default_factory=time.time)
    is_extended: bool = False
    is_remote: bool = False
    is_error: bool = False
    is_fd: bool = False
    dlc: int = 0

    def __post_init__(self):
        if self.dlc == 0:
            self.dlc = len(self.data)

    def __str__(self):
        msg_type = "EXT" if self.is_extended else "STD"
        data_str = ' '.join(f'{b:02X}' for b in self.data)
        return f"ID: 0x{self.id:08X} [{msg_type}] DLC: {self.dlc} Data: [{data_str}]"


@dataclass(frozen=True)
class CANFilter:
    """Receive filter definition compatible with python-can backends."""

    can_id: int
    can_mask: int
    extended: Optional[bool] = None

    def matches(self, can_id: int, is_extended: bool) -> bool:
        if self.extended is not None and self.extended != is_extended:
            return False
        return (can_id & self.can_mask) == (self.can_id & self.can_mask)

    def to_python_can(self) -> dict:
        filter_dict = {
            "can_id": self.can_id,
            "can_mask": self.can_mask,
        }
        if self.extended is not None:
            filter_dict["extended"] = self.extended
        return filter_dict


class CANAdapter(ABC):
    """Abstract base class for CAN adapters."""

    @abstractmethod
    def connect(self) -> bool:
        """Connect to the CAN adapter. Returns True on success."""
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the CAN adapter."""
        ...

    @abstractmethod
    def send_message(self, can_id: int, data: bytes, is_extended: bool = False) -> bool:
        """Send a CAN message. Returns True on success."""
        ...

    @abstractmethod
    def read_message(self, timeout: float = 1.0) -> Optional[CANMessage]:
        """Read a CAN message. Returns None on timeout."""
        ...

    @abstractmethod
    def clear_receive_queue(self) -> bool:
        """Drain all pending received messages. Returns True on success."""
        ...

    @abstractmethod
    def set_receive_filters(self, filters: Optional[List[CANFilter]]) -> bool:
        """Configure adapter receive filters. Pass None to clear them."""
        ...

    @abstractmethod
    def get_available_devices(self) -> List[dict]:
        """Return a list of discovered devices (dicts with adapter-specific keys)."""
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        """Return True if currently connected."""
        ...

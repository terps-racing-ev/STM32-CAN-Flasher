"""
PCAN Driver
===========
Adapter for PEAK PCAN-USB devices.
Requires: python-can, PCAN drivers installed.
"""

import time
from enum import Enum
from typing import Optional, List

try:
    from can import Bus, Message
    from can.interfaces.pcan.basic import (
        PCANBasic, PCAN_USBBUS1, PCAN_USBBUS2, PCAN_USBBUS3, PCAN_USBBUS4,
        PCAN_USBBUS5, PCAN_USBBUS6, PCAN_USBBUS7, PCAN_USBBUS8,
        PCAN_USBBUS9, PCAN_USBBUS10, PCAN_USBBUS11, PCAN_USBBUS12,
        PCAN_USBBUS13, PCAN_USBBUS14, PCAN_USBBUS15, PCAN_USBBUS16,
        PCAN_CHANNEL_CONDITION, PCAN_CHANNEL_AVAILABLE, PCAN_CHANNEL_OCCUPIED,
        PCAN_ERROR_OK, PCAN_DEVICE_NUMBER,
        PCAN_BAUD_1M, PCAN_BAUD_800K, PCAN_BAUD_500K, PCAN_BAUD_250K,
        PCAN_BAUD_125K, PCAN_BAUD_100K, PCAN_BAUD_50K, PCAN_BAUD_20K,
        PCAN_BAUD_10K,
    )
    PCAN_AVAILABLE = True
except ImportError:
    PCAN_AVAILABLE = False

from src.backend.can_adapter import CANAdapter, CANFilter, CANMessage


class PCANBaudRate(Enum):
    BAUD_1M = 1000000
    BAUD_800K = 800000
    BAUD_500K = 500000
    BAUD_250K = 250000
    BAUD_125K = 125000
    BAUD_100K = 100000
    BAUD_50K = 50000
    BAUD_20K = 20000
    BAUD_10K = 10000


class PCANChannel(Enum):
    USB1 = 'PCAN_USBBUS1'
    USB2 = 'PCAN_USBBUS2'
    USB3 = 'PCAN_USBBUS3'
    USB4 = 'PCAN_USBBUS4'
    USB5 = 'PCAN_USBBUS5'
    USB6 = 'PCAN_USBBUS6'
    USB7 = 'PCAN_USBBUS7'
    USB8 = 'PCAN_USBBUS8'
    USB9 = 'PCAN_USBBUS9'
    USB10 = 'PCAN_USBBUS10'
    USB11 = 'PCAN_USBBUS11'
    USB12 = 'PCAN_USBBUS12'
    USB13 = 'PCAN_USBBUS13'
    USB14 = 'PCAN_USBBUS14'
    USB15 = 'PCAN_USBBUS15'
    USB16 = 'PCAN_USBBUS16'


# Map PCANChannel -> PCANBasic handle constants for device enumeration
_CHANNEL_HANDLES = {}
if PCAN_AVAILABLE:
    _CHANNEL_HANDLES = {
        PCANChannel.USB1: PCAN_USBBUS1, PCANChannel.USB2: PCAN_USBBUS2,
        PCANChannel.USB3: PCAN_USBBUS3, PCANChannel.USB4: PCAN_USBBUS4,
        PCANChannel.USB5: PCAN_USBBUS5, PCANChannel.USB6: PCAN_USBBUS6,
        PCANChannel.USB7: PCAN_USBBUS7, PCANChannel.USB8: PCAN_USBBUS8,
        PCANChannel.USB9: PCAN_USBBUS9, PCANChannel.USB10: PCAN_USBBUS10,
        PCANChannel.USB11: PCAN_USBBUS11, PCANChannel.USB12: PCAN_USBBUS12,
        PCANChannel.USB13: PCAN_USBBUS13, PCANChannel.USB14: PCAN_USBBUS14,
        PCANChannel.USB15: PCAN_USBBUS15, PCANChannel.USB16: PCAN_USBBUS16,
    }


class PCANAdapter(CANAdapter):
    """PCAN-USB adapter via python-can pcan interface."""

    def __init__(self, channel: PCANChannel = PCANChannel.USB1,
                 baudrate: PCANBaudRate = PCANBaudRate.BAUD_500K):
        if not PCAN_AVAILABLE:
            raise RuntimeError("PCAN driver not available. Install python-can and PCAN drivers.")
        self._bus: Optional[Bus] = None
        self._channel = channel
        self._baudrate = baudrate
        self._connected = False
        self._pcan_basic = PCANBasic()
        self._receive_filters: Optional[List[CANFilter]] = None
        self._hardware_filtering = False

    def _python_can_filters(self) -> Optional[List[dict]]:
        if not self._receive_filters:
            return None
        return [can_filter.to_python_can() for can_filter in self._receive_filters]

    def _apply_receive_filters(self) -> bool:
        if not self._bus:
            self._hardware_filtering = False
            return True
        try:
            self._bus.set_filters(self._python_can_filters())
            self._hardware_filtering = bool(self._receive_filters)
            return True
        except Exception:
            self._hardware_filtering = False
            return False

    def _message_allowed(self, can_id: int, is_extended: bool) -> bool:
        if not self._receive_filters:
            return True
        return any(can_filter.matches(can_id, is_extended) for can_filter in self._receive_filters)

    @staticmethod
    def _to_can_message(msg) -> CANMessage:
        return CANMessage(
            id=msg.arbitration_id,
            data=bytes(msg.data),
            timestamp=msg.timestamp,
            is_extended=msg.is_extended_id,
            is_remote=msg.is_remote_frame,
            is_error=msg.is_error_frame,
            is_fd=msg.is_fd,
            dlc=msg.dlc,
        )

    def get_available_devices(self) -> List[dict]:
        devices: List[dict] = []
        for ch in PCANChannel:
            try:
                handle = _CHANNEL_HANDLES[ch]
                result = self._pcan_basic.GetValue(handle, PCAN_CHANNEL_CONDITION)
                if result[0] == PCAN_ERROR_OK:
                    condition = result[1]
                    if condition & PCAN_CHANNEL_AVAILABLE:
                        info: dict = {
                            'channel': ch.name,
                            'available': True,
                            'occupied': bool(condition & PCAN_CHANNEL_OCCUPIED),
                        }
                        res2 = self._pcan_basic.GetValue(handle, PCAN_DEVICE_NUMBER)
                        if res2[0] == PCAN_ERROR_OK:
                            info['device_number'] = res2[1]
                        devices.append(info)
            except Exception:
                pass
        return devices

    def connect(self) -> bool:
        if self._connected:
            return False
        try:
            bus_kwargs = {
                'interface': 'pcan',
                'channel': self._channel.value,
                'bitrate': self._baudrate.value,
            }
            python_can_filters = self._python_can_filters()
            if python_can_filters is not None:
                bus_kwargs['can_filters'] = python_can_filters
            try:
                self._bus = Bus(**bus_kwargs)
                self._hardware_filtering = bool(python_can_filters)
            except TypeError:
                bus_kwargs.pop('can_filters', None)
                self._bus = Bus(**bus_kwargs)
                self._hardware_filtering = False
            if self._receive_filters and not self._hardware_filtering:
                self._apply_receive_filters()
            self._connected = True
            return True
        except Exception:
            self._hardware_filtering = False
            return False

    def disconnect(self) -> None:
        if self._bus:
            try:
                self._bus.shutdown()
            except Exception:
                pass
            self._bus = None
        self._connected = False
        self._hardware_filtering = False

    def send_message(self, can_id: int, data: bytes, is_extended: bool = False) -> bool:
        if not self._connected or not self._bus:
            return False
        try:
            self._bus.send(Message(arbitration_id=can_id, data=data, is_extended_id=is_extended))
            return True
        except Exception:
            return False

    def read_message(self, timeout: float = 1.0) -> Optional[CANMessage]:
        if not self._connected or not self._bus:
            return None
        try:
            if not self._receive_filters or self._hardware_filtering:
                msg = self._bus.recv(timeout=timeout)
                if msg is None:
                    return None
                return self._to_can_message(msg)

            deadline = None if timeout is None else time.monotonic() + max(timeout, 0.0)
            while True:
                remaining = None
                if deadline is not None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        return None

                msg = self._bus.recv(timeout=remaining)
                if msg is None:
                    return None
                if self._message_allowed(msg.arbitration_id, msg.is_extended_id):
                    return self._to_can_message(msg)
        except Exception:
            return None

    def clear_receive_queue(self) -> bool:
        if not self._connected:
            return False
        try:
            while self.read_message(timeout=0.01):
                pass
            return True
        except Exception:
            return False

    def set_receive_filters(self, filters: Optional[List[CANFilter]]) -> bool:
        self._receive_filters = list(filters) if filters else None
        if not self._bus:
            self._hardware_filtering = False
            return True
        return self._apply_receive_filters()

    def is_connected(self) -> bool:
        return self._connected

"""
CANable Driver
==============
Adapter for CANable USB-to-CAN devices using candleLight firmware (gs_usb).
Requires: python-can, pyusb, libusb-1.0.dll (Windows)
"""

import os
import sys
import time
from typing import Optional, List
from enum import Enum

try:
    from can import Bus, Message
except ImportError:
    raise ImportError("python-can library required: pip install python-can")

try:
    import usb.core
    import usb.util
except ImportError:
    usb = None

from src.backend.can_adapter import CANAdapter, CANFilter, CANMessage


class CANableBaudRate(Enum):
    BAUD_1M = 1000000
    BAUD_800K = 800000
    BAUD_500K = 500000
    BAUD_250K = 250000
    BAUD_125K = 125000
    BAUD_100K = 100000
    BAUD_50K = 50000
    BAUD_20K = 20000
    BAUD_10K = 10000


# USB Vendor/Product IDs for gs_usb compatible devices
GS_USB_DEVICES = [
    (0x1D50, 0x606F),  # CANable (candleLight)
    (0x1209, 0x0001),  # CANtact/CANable (older)
    (0x16D0, 0x0F67),  # candleLight
]


class CANableAdapter(CANAdapter):
    """CANable adapter using gs_usb/Candle API via libusb."""

    def __init__(self, channel: int = 0, baudrate: CANableBaudRate = CANableBaudRate.BAUD_500K):
        self._bus: Optional[Bus] = None
        self._channel = channel
        self._baudrate = baudrate
        self._connected = False
        self._device_info: Optional[dict] = None
        self._receive_filters: Optional[List[CANFilter]] = None
        self._hardware_filtering = False
        self._setup_libusb_path()

    @staticmethod
    def _setup_libusb_path():
        if sys.platform == 'win32':
            # Ensure pyusb always uses libusb1 backend on Windows
            os.environ.setdefault('PYUSB_BACKEND', 'libusb1')

            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_dir = os.path.dirname(os.path.dirname(script_dir))
            libusb_path = os.path.join(project_dir, 'libusb-1.0.dll')
            if os.path.exists(libusb_path):
                os.environ['PATH'] = project_dir + os.pathsep + os.environ.get('PATH', '')

    def get_available_devices(self) -> List[dict]:
        devices: List[dict] = []
        if usb is None:
            return devices
        try:
            idx = 0
            for vid, pid in GS_USB_DEVICES:
                for dev in usb.core.find(find_all=True, idVendor=vid, idProduct=pid):
                    try:
                        manufacturer = usb.util.get_string(dev, dev.iManufacturer) if dev.iManufacturer else "Unknown"
                        product = usb.util.get_string(dev, dev.iProduct) if dev.iProduct else "Unknown"
                        serial = usb.util.get_string(dev, dev.iSerialNumber) if dev.iSerialNumber else "Unknown"
                    except Exception:
                        manufacturer = product = serial = "Unknown"
                    devices.append({
                        'index': idx,
                        'vid': vid,
                        'pid': pid,
                        'manufacturer': manufacturer,
                        'product': product,
                        'serial_number': serial,
                        'description': f"{manufacturer} {product}",
                    })
                    idx += 1
        except Exception:
            pass
        return devices

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

    def connect(self) -> bool:
        if self._connected:
            return False
        try:
            bus_kwargs = {
                'interface': 'gs_usb',
                'channel': self._channel,
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
            devices = self.get_available_devices()
            if self._channel < len(devices):
                self._device_info = devices[self._channel]
            return True
        except Exception:
            # Clean up partially-created Bus to avoid "not properly shut down"
            if self._bus is not None:
                try:
                    self._bus.shutdown()
                except Exception:
                    pass
                self._bus = None
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

    def __del__(self):
        """Ensure Bus is shut down if adapter is garbage collected."""
        if getattr(self, '_bus', None) is not None:
            try:
                self._bus.shutdown()
            except Exception:
                pass

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

    @property
    def device_info(self) -> Optional[dict]:
        return self._device_info

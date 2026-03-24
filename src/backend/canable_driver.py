"""
CANable Driver
==============
Adapter for CANable USB-to-CAN devices using candleLight firmware (gs_usb).
Requires: python-can, pyusb, libusb-1.0.dll (Windows)
"""

import os
import sys
import threading
from typing import Optional, List, Callable
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

from src.backend.can_adapter import CANAdapter, CANMessage


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
        self._setup_libusb_path()

    @staticmethod
    def _setup_libusb_path():
        if sys.platform == 'win32':
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

    def connect(self) -> bool:
        if self._connected:
            return False
        try:
            self._bus = Bus(
                interface='gs_usb',
                channel=self._channel,
                bitrate=self._baudrate.value,
            )
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
            return False

    def disconnect(self) -> None:
        if self._bus:
            try:
                self._bus.shutdown()
            except Exception:
                pass
            self._bus = None
        self._connected = False

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
            msg = self._bus.recv(timeout=timeout)
            if msg is None:
                return None
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

    def is_connected(self) -> bool:
        return self._connected

    @property
    def device_info(self) -> Optional[dict]:
        return self._device_info

# STM32-CAN-Flasher

PySide6 GUI application for flashing STM32L4 boards over CAN bus using the [STM32-CAN-Bootloader](https://github.com/terps-racing-ev/STM32-CAN-Bootloader).

## Features

- **Dual-bank flashing** — auto-selects `*_a.bin` / `*_b.bin` for the inactive bank
- **CAN adapter support** — CANable (gs_usb / candleLight) and PCAN-USB
- **Reset to bootloader** — sends `CAN_RESET_CMD` to reboot a BMS module into bootloader mode
- **Stay in bootloader** — prevents the 1-second auto-jump timeout
- **Bank status display** — shows Bank A/B validity, active bank, bootloader state, firmware version
- **Collapsible CAN log** — real-time TX/RX traffic with decoded command/response names
- **Progress tracking** — live progress bar with speed and ETA during writes
- **Read-back verify** — optional CRC verification plus byte-by-byte read-back

## Requirements

- Python 3.10+
- CANable (with candleLight firmware) or PCAN-USB adapter
- `libusb-1.0.dll` in the project root (Windows only, for CANable)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

1. Select adapter type (CANable / PCAN) and channel, then click **Connect**
2. Browse to the build directory containing `*_a.bin` and `*_b.bin` firmware files
3. Select the module ID (0–15)
4. Click **Flash** — the tool will automatically:
   - Reset the module into bootloader
   - Wait for the READY heartbeat
   - Query the active bank and flash the inactive one
   - Erase → Write → CRC verify → Read-back verify → Jump to app

### Manual Controls

- **Reset to Bootloader** — reboot a running module into bootloader mode
- **Stay in Bootloader** — send `GET_STATUS` to block the auto-jump timer
- **Jump to App** — command the bootloader to jump to the active application
- **Get Status** — query bootloader state and refresh the status panel

## Project Structure

```
STM32-CAN-Flasher/
├── main.py                         Entry point
├── requirements.txt                PySide6, python-can, pyusb
├── src/
│   ├── backend/
│   │   ├── can_adapter.py          Abstract CAN adapter + CANMessage
│   │   ├── canable_driver.py       CANable (gs_usb) adapter
│   │   ├── pcan_driver.py          PCAN-USB adapter
│   │   ├── bootloader_protocol.py  CAN IDs, commands, responses, error codes
│   │   ├── flasher.py              Core flash logic (erase/write/verify/jump)
│   │   └── firmware_utils.py       File discovery, CRC32, padding
│   ├── ui/
│   │   ├── main_window.py          Top-level window orchestration
│   │   ├── connection_panel.py     Adapter/channel selection
│   │   ├── flash_panel.py          Firmware dir, progress, flash button
│   │   ├── control_panel.py        Manual bootloader control buttons
│   │   ├── status_panel.py         Bank status and bootloader state
│   │   └── can_log_panel.py        Collapsible CAN message log
│   └── workers/
│       ├── flash_worker.py         QThread for background flash operations
│       └── status_worker.py        QThread for heartbeat monitoring
```

## CAN Protocol

| Direction | CAN ID (29-bit) | Purpose |
|-----------|-----------------|---------|
| Host → BL | `0x18000701` | Bootloader commands |
| BL → Host | `0x18000700` | Bootloader responses / heartbeat |
| Host → BMS | `0x08F0xF02` | Module reset (x = module ID in bits 15:12) |

500 kbps, 8-byte CAN 2.0B frames. See [bootloader_protocol.py](src/backend/bootloader_protocol.py) for all command/response/error constants.

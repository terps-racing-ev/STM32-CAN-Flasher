"""
Theme
=====
Centralized dark theme stylesheet for the application.
"""

DARK_STYLESHEET = """
/* ── Global ─────────────────────────────────────────────── */
QMainWindow, QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}

/* ── Group boxes ─────────────────────────────────────────── */
QGroupBox {
    background-color: #252536;
    border: 1px solid #3b3b54;
    border-radius: 8px;
    margin-top: 6px;
    padding: 14px 10px 10px 10px;
    font-weight: 600;
    font-size: 13px;
    color: #a6adc8;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 6px;
    color: #a6adc8;
}
/* Checkable group box indicator (CAN log) */
QGroupBox::indicator {
    width: 14px;
    height: 14px;
    border: 1px solid #585b70;
    border-radius: 3px;
    background: #313244;
}
QGroupBox::indicator:checked {
    background: #89b4fa;
    border-color: #89b4fa;
}

/* ── Buttons ─────────────────────────────────────────────── */
QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 18px;
    font-weight: 500;
    min-height: 24px;
}
QPushButton:hover {
    background-color: #45475a;
    border-color: #585b70;
}
QPushButton:pressed {
    background-color: #585b70;
}
QPushButton:disabled {
    background-color: #252536;
    color: #585b70;
    border-color: #313244;
}

/* Primary action buttons */
QPushButton#primary_btn {
    background-color: #89b4fa;
    color: #1e1e2e;
    border: none;
    font-weight: 700;
    padding: 8px 28px;
}
QPushButton#primary_btn:hover {
    background-color: #a6c8ff;
}
QPushButton#primary_btn:pressed {
    background-color: #74a8f7;
}
QPushButton#primary_btn:disabled {
    background-color: #45475a;
    color: #6c7086;
}

/* Danger button */
QPushButton#danger_btn {
    background-color: #45475a;
    color: #f38ba8;
    border: 1px solid #f38ba8;
}
QPushButton#danger_btn:hover {
    background-color: #f38ba8;
    color: #1e1e2e;
}
QPushButton#danger_btn:disabled {
    background-color: #252536;
    color: #585b70;
    border-color: #313244;
}

/* Connect / Disconnect special */
QPushButton#connect_btn {
    background-color: #a6e3a1;
    color: #1e1e2e;
    border: none;
    font-weight: 700;
    padding: 6px 22px;
}
QPushButton#connect_btn:hover {
    background-color: #b8f0b3;
}
QPushButton#disconnect_btn {
    background-color: #f38ba8;
    color: #1e1e2e;
    border: none;
    font-weight: 700;
    padding: 6px 22px;
}
QPushButton#disconnect_btn:hover {
    background-color: #f5a0b8;
}

/* ── Inputs ──────────────────────────────────────────────── */
QLineEdit, QComboBox, QSpinBox {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 5px 8px;
    min-height: 22px;
    selection-background-color: #89b4fa;
    selection-color: #1e1e2e;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border-color: #89b4fa;
}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {
    background-color: #252536;
    color: #585b70;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #a6adc8;
    margin-right: 6px;
}
QComboBox QAbstractItemView {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    selection-background-color: #45475a;
}
QSpinBox::up-button, QSpinBox::down-button {
    background: #45475a;
    border: none;
    width: 18px;
}
QSpinBox::up-button { border-top-right-radius: 5px; }
QSpinBox::down-button { border-bottom-right-radius: 5px; }
QSpinBox::up-arrow {
    border-left: 3px solid transparent;
    border-right: 3px solid transparent;
    border-bottom: 4px solid #cdd6f4;
}
QSpinBox::down-arrow {
    border-left: 3px solid transparent;
    border-right: 3px solid transparent;
    border-top: 4px solid #cdd6f4;
}

/* ── Checkbox ────────────────────────────────────────────── */
QCheckBox {
    spacing: 6px;
    color: #cdd6f4;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #585b70;
    border-radius: 4px;
    background: #313244;
}
QCheckBox::indicator:checked {
    background: #89b4fa;
    border-color: #89b4fa;
}
QCheckBox:disabled {
    color: #585b70;
}

/* ── Progress bar ────────────────────────────────────────── */
QProgressBar {
    background-color: #313244;
    border: none;
    border-radius: 6px;
    height: 18px;
    text-align: center;
    color: #cdd6f4;
    font-size: 11px;
    font-weight: 600;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #89b4fa, stop:1 #74c7ec);
    border-radius: 6px;
}

/* ── Labels ──────────────────────────────────────────────── */
QLabel {
    color: #cdd6f4;
    background: transparent;
}
QLabel#section_label {
    color: #a6adc8;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
}
QLabel#value_label {
    color: #cdd6f4;
    font-weight: 500;
}
QLabel#status_msg {
    color: #a6adc8;
    font-size: 12px;
}
QLabel#file_found {
    color: #a6e3a1;
    font-size: 12px;
}
QLabel#file_missing {
    color: #6c7086;
    font-size: 12px;
}

/* ── Table (CAN log) ─────────────────────────────────────── */
QTableWidget {
    background-color: #1e1e2e;
    alternate-background-color: #252536;
    border: 1px solid #3b3b54;
    border-radius: 6px;
    gridline-color: #313244;
    color: #cdd6f4;
    font-family: "Cascadia Code", "Consolas", monospace;
    font-size: 12px;
}
QTableWidget::item {
    padding: 2px 6px;
}
QTableWidget::item:selected {
    background-color: #45475a;
}
QHeaderView::section {
    background-color: #313244;
    color: #a6adc8;
    border: none;
    border-bottom: 1px solid #45475a;
    padding: 4px 8px;
    font-weight: 600;
    font-size: 11px;
}

/* ── Scrollbar ───────────────────────────────────────────── */
QScrollBar:vertical {
    background: #1e1e2e;
    width: 8px;
    border: none;
}
QScrollBar::handle:vertical {
    background: #45475a;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #585b70;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

/* ── Status bar ──────────────────────────────────────────── */
QStatusBar {
    background-color: #181825;
    color: #a6adc8;
    border-top: 1px solid #313244;
    font-size: 12px;
    padding: 2px 8px;
}

/* ── Tooltips ────────────────────────────────────────────── */
QToolTip {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}
"""

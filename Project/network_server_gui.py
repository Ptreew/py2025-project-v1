from __future__ import annotations

import json
import os
import sys
import threading
from collections import deque
from datetime import datetime, timedelta
from typing import Deque, Dict, Tuple

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Local modules
from logger import Logger
from server.server import NetworkServer

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

class _DataAggregator:

    def __init__(self) -> None:
        # sensor_id -> deque[(datetime, float)] ordered oldest→newest
        self._buffers: Dict[str, Deque[Tuple[datetime, float]]] = {}

    def add_reading(self, sensor_id: str, ts: datetime, value: float) -> None:
        buf = self._buffers.setdefault(sensor_id, deque())
        buf.append((ts, value))
        # Keep only last 12h of data
        cutoff = ts - timedelta(hours=12)
        while buf and buf[0][0] < cutoff:
            buf.popleft()

    def latest(self, sensor_id: str) -> Tuple[datetime | None, float | None]:
        buf = self._buffers.get(sensor_id)
        if not buf:
            return None, None
        return buf[-1]

    def average(self, sensor_id: str, hours: int) -> float | None:
        buf = self._buffers.get(sensor_id)
        if not buf:
            return None
        cutoff = datetime.now() - timedelta(hours=hours)
        values = [v for ts, v in buf if ts >= cutoff]
        if not values:
            return None
        return sum(values) / len(values)


class SensorTable(QTableWidget):
    HEADERS = [
        "Sensor",
        "Wartość",
        "Jednostka",
        "Timestamp",
        "Śr. 1h",
        "Śr. 12h",
    ]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(0, len(self.HEADERS), parent)
        self.setHorizontalHeaderLabels(self.HEADERS)
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setStretchLastSection(True)
        self._row_for_sensor: Dict[str, int] = {}
        self.setEditTriggers(QTableWidget.NoEditTriggers)

    def upsert(
        self,
        sensor_id: str,
        value: float,
        unit: str,
        ts: datetime,
        avg1h: float | None,
        avg12h: float | None,
    ) -> None:
        if sensor_id in self._row_for_sensor:
            row = self._row_for_sensor[sensor_id]
        else:
            row = self.rowCount()
            self.insertRow(row)
            self._row_for_sensor[sensor_id] = row

        def _set(col: int, text: str) -> None:
            item = QTableWidgetItem(text)
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.setItem(row, col, item)

        _set(0, sensor_id)
        _set(1, f"{value:.2f}")
        _set(2, unit)
        _set(3, ts.strftime("%Y-%m-%d %H:%M:%S"))
        _set(4, f"{avg1h:.2f}" if avg1h is not None else "-")
        _set(5, f"{avg12h:.2f}" if avg12h is not None else "-")


class GUIAwareServer(NetworkServer):
    def __init__(self, port: int, on_data, logger: Logger | None = None):
        super().__init__(port, logger)
        self._on_data = on_data

    def _deserialize(self, raw: bytes):
        data = super()._deserialize(raw)
        try:
            self._on_data(data)
        except Exception:
            pass
        return data

class MainWindow(QMainWindow):
    sensor_data_signal = pyqtSignal(dict)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Network Server GUI")
        self.resize(720, 400)

        # Data & threads
        self._aggregator = _DataAggregator()
        self._server: GUIAwareServer | None = None
        self._server_thread: threading.Thread | None = None
        self._logger: Logger | None = None

        self._build_ui()

        # Connect signal → slot
        self.sensor_data_signal.connect(self._handle_sensor_data)

        # Load initial port from config
        self._load_config_port()

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)

        vbox = QVBoxLayout(central)

        # Top controls
        controls = QHBoxLayout()
        vbox.addLayout(controls)

        controls.addWidget(QLabel("Port:"))
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        controls.addWidget(self.port_spin)

        self.btn_start = QPushButton("Start")
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setEnabled(False)
        controls.addWidget(self.btn_start)
        controls.addWidget(self.btn_stop)
        controls.addStretch(1)

        # Table
        self.table = SensorTable(self)
        vbox.addWidget(self.table)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._set_status("Zatrzymany")

        # Connections
        self.btn_start.clicked.connect(self._start_server)
        self.btn_stop.clicked.connect(self._stop_server)

    def _load_config_port(self) -> None:
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as fp:
                cfg = json.load(fp)
            port = int(cfg.get("network", {}).get("port", 9999))
        except Exception:
            port = 9999
        self.port_spin.setValue(port)

    def _save_port_to_config(self, port: int) -> None:
        try:
            cfg = {}
            if os.path.isfile(CONFIG_PATH):
                with open(CONFIG_PATH, "r", encoding="utf-8") as fp:
                    cfg = json.load(fp)
            cfg.setdefault("network", {})["port"] = port
            with open(CONFIG_PATH, "w", encoding="utf-8") as fp:
                json.dump(cfg, fp, indent=2)
        except Exception:
            pass

    def _start_server(self) -> None:
        if self._server_thread and self._server_thread.is_alive():
            return

        port = int(self.port_spin.value())
        self._save_port_to_config(port)

        # Logger
        self._logger = Logger(CONFIG_PATH)
        self._logger.start()

        # Server
        self._server = GUIAwareServer(port, on_data=self.sensor_data_signal.emit, logger=self._logger)
        self._server_thread = threading.Thread(target=self._server.start, daemon=True)
        self._server_thread.start()

        # UI state
        self.port_spin.setEnabled(False)
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self._set_status(f"Nasłuchiwanie na porcie {port}")

    def _stop_server(self) -> None:
        if not self._server:
            return
        # Stop server and thread
        self._server.stop()
        if self._server_thread:
            self._server_thread.join(timeout=1)
        # Stop logger
        if self._logger:
            self._logger.stop()

        self._server = None
        self._server_thread = None
        self._logger = None

        # UI state
        self.port_spin.setEnabled(True)
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._set_status("Zatrzymany")

    def _handle_sensor_data(self, payload: dict) -> None:
        for sensor_id, info in payload.items():
            try:
                value = float(info.get("value"))
                unit = str(info.get("unit", ""))
                ts_str = str(info.get("timestamp"))
                ts = datetime.fromisoformat(ts_str)
            except Exception:
                continue

            self._aggregator.add_reading(sensor_id, ts, value)
            avg1h = self._aggregator.average(sensor_id, 1)
            avg12h = self._aggregator.average(sensor_id, 12)
            self.table.upsert(sensor_id, value, unit, ts, avg1h, avg12h)

    def _set_status(self, text: str) -> None:
        self.status_bar.showMessage(text)
    def closeEvent(self, event):
        if self._server:
            self._stop_server()
        super().closeEvent(event)


def main() -> None:
    app = QApplication(sys.argv)

    win = MainWindow()
    win.show()

    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

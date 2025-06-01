from __future__ import annotations

import json
import os
import queue
import threading
import time
from collections import deque
from datetime import datetime, timedelta
from typing import Deque, Dict, Tuple

import tkinter as tk
from tkinter import messagebox, ttk

from logger import Logger
from server.server import NetworkServer

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")


class _DataAggregator:
    """Store last 12h of readings and compute averages."""

    def __init__(self) -> None:
        self._buffers: Dict[str, Deque[Tuple[datetime, float]]] = {}

    def add_reading(self, sensor_id: str, ts: datetime, value: float) -> None:
        buf = self._buffers.setdefault(sensor_id, deque())
        buf.append((ts, value))
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
        vals = [v for ts, v in buf if ts >= cutoff]
        if not vals:
            return None
        return sum(vals) / len(vals)


class GUIAwareServer(NetworkServer):
    def __init__(self, port: int, on_payload, logger: Logger | None = None):
        super().__init__(port, logger)
        self._on_payload = on_payload

    def _deserialize(self, raw: bytes):
        data = super()._deserialize(raw)
        try:
            self._on_payload(data)
        except Exception:
            pass
        return data


class NetworkServerGUI(tk.Tk):
    COLS = ("sensor", "value", "unit", "timestamp", "avg1h", "avg12h")

    def __init__(self) -> None:
        super().__init__()
        self.title("Network Server GUI")

        # Data structures
        self._aggregator = _DataAggregator()
        self._queue: "queue.Queue[dict]" = queue.Queue()
        self._server: GUIAwareServer | None = None
        self._server_thread: threading.Thread | None = None
        self._logger: Logger | None = None

        # Build UI
        self._build_widgets()
        self._load_port_from_config()

        # Schedule queue processing
        self.after(200, self._process_queue)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_widgets(self) -> None:
        # Top frame (controls)
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=8, pady=4)

        ttk.Label(top, text="Port:").pack(side=tk.LEFT)
        self.port_var = tk.IntVar(value=9999)
        self.port_entry = ttk.Spinbox(
            top, from_=1, to=65535, textvariable=self.port_var, width=6
        )
        self.port_entry.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_start = ttk.Button(top, text="Start", command=self._start_server)
        self.btn_start.pack(side=tk.LEFT)
        self.btn_stop = ttk.Button(top, text="Stop", command=self._stop_server, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=(5, 0))

        # Table
        self.tree = ttk.Treeview(self, columns=self.COLS, show="headings")
        for col, heading in zip(self.COLS, [
            "Sensor", "Wartość", "Jednostka", "Timestamp", "Śr. 1h", "Śr. 12h"
        ]):
            self.tree.heading(col, text=heading)
            self.tree.column(col, anchor=tk.CENTER, stretch=True)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        # Status bar
        self.status_var = tk.StringVar(value="Zatrzymany")
        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT, padx=4)

    def _start_server(self) -> None:
        if self._server_thread and self._server_thread.is_alive():
            return

        port = int(self.port_var.get())
        self._save_port_to_config(port)

        # Logger
        self._logger = Logger(CONFIG_PATH)
        self._logger.start()

        # Server
        self._server = GUIAwareServer(port, on_payload=self._queue.put, logger=self._logger)
        self._server_thread = threading.Thread(target=self._server.start, daemon=True)
        self._server_thread.start()

        # UI state
        self.btn_start["state"] = tk.DISABLED
        self.btn_stop["state"] = tk.NORMAL
        self.port_entry["state"] = tk.DISABLED
        self._set_status(f"Nasłuchiwanie na porcie {port}")

    def _stop_server(self) -> None:
        if not self._server:
            return
        self._server.stop()
        if self._server_thread:
            self._server_thread.join(timeout=1)
        if self._logger:
            self._logger.stop()

        self._server = None
        self._server_thread = None
        self._logger = None

        # UI state
        self.btn_start["state"] = tk.NORMAL
        self.btn_stop["state"] = tk.DISABLED
        self.port_entry["state"] = tk.NORMAL
        self._set_status("Zatrzymany")

    def _process_queue(self) -> None:
        while not self._queue.empty():
            payload: dict = self._queue.get()
            self._handle_payload(payload)
        self.after(200, self._process_queue)

    def _handle_payload(self, payload: dict) -> None:
        for sensor_id, info in payload.items():
            try:
                value = float(info.get("value"))
                unit = str(info.get("unit", ""))
                ts_str = str(info.get("timestamp"))
                ts = datetime.fromisoformat(ts_str)
            except Exception:
                continue

            # Update aggregator
            self._aggregator.add_reading(sensor_id, ts, value)
            avg1h = self._aggregator.average(sensor_id, 1)
            avg12h = self._aggregator.average(sensor_id, 12)

            # Insert/update row
            if sensor_id in self.tree.get_children():
                iid = sensor_id
            else:
                iid = self.tree.insert("", "end", iid=sensor_id, values=("",) * len(self.COLS))
            self.tree.item(iid, values=(
                sensor_id,
                f"{value:.2f}",
                unit,
                ts.strftime("%Y-%m-%d %H:%M:%S"),
                f"{avg1h:.2f}" if avg1h is not None else "-",
                f"{avg12h:.2f}" if avg12h is not None else "-",
            ))

    def _load_port_from_config(self) -> None:
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as fp:
                cfg = json.load(fp)
            port = int(cfg.get("network", {}).get("port", 9999))
        except Exception:
            port = 9999
        self.port_var.set(port)

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

    def _set_status(self, text: str) -> None:
        self.status_var.set(text)

    def _on_close(self) -> None:
        self._stop_server()
        self.destroy()

def main() -> None:
    gui = NetworkServerGUI()
    gui.geometry("700x400")
    gui.mainloop()


if __name__ == "__main__":
    main()

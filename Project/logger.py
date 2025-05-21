import os
import json
import csv
import zipfile
from datetime import datetime, timedelta
from typing import Optional, Iterator, Dict


class Logger:
    def __init__(self, config_path: str):
        self._load_config(config_path)
        self.buffer = []
        self.csv_writer = None
        self.current_file = None
        self.current_file_path = None
        self.last_rotation_time = datetime.now()
        self.line_count = 0
        self._ensure_directories_exist()

    # Domyśle wartości, jeśli config.json jest pusty / nie istnieje
    def _load_config(self, config_path: str):
        with open(config_path, 'r') as f:
            config = json.load(f)
        self.log_dir = config.get('log_dir', './logs')
        self.filename_pattern = config.get('filename_pattern', 'sensors_%Y%m%d.csv')
        self.buffer_size = config.get('buffer_size', 100)
        self.rotate_every_hours = config.get('rotate_every_hours', 24)
        self.max_size_mb = config.get('max_size_mb', 10)
        self.rotate_after_lines = config.get('rotate_after_lines', 100)
        self.retention_days = config.get('retention_days', 30)

    def _ensure_directories_exist(self):
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(os.path.join(self.log_dir, 'archive'), exist_ok=True)

    def start(self):
        now = datetime.now()
        filename = now.strftime(self.filename_pattern)
        self.current_file_path = os.path.join(self.log_dir, filename)
        file_exists = os.path.isfile(self.current_file_path)

        self.current_file = open(self.current_file_path, 'a', newline='')
        self.csv_writer = csv.writer(self.current_file)

        if not file_exists:
            self.csv_writer.writerow(['timestamp', 'sensor_id', 'value', 'unit'])

        self.last_rotation_time = now
        self.line_count = self._get_line_count()

    def stop(self):
        """
        Zakończenie działania loggera - wymusza zapis wszystkich danych z bufora
        i wykonuje rotację, jeśli jest to konieczne.
        """
        # Wymuszenie zapisu wszystkich danych w buforze przed zakończeniem
        self.flush()

        if self.current_file:
            self.current_file.close()
            self.current_file = None

        # Wykonaj rotację pliku, jeśli to konieczne
        self._rotate_if_needed()

    def log_reading(self, sensor_id: str, timestamp: datetime, value: float, unit: str):
        """
        Dodaje wpis do bufora i zapisuje dane, jeśli bufor osiągnie wymaganą wielkość
        lub jeśli wykonano określoną liczbę zapisów (np. co 10 zapisów).
        """
        # Dodaj dane do bufora
        self.buffer.append([timestamp.isoformat(), sensor_id, f"{value:.2f}", unit])

        # Sprawdź, czy bufor osiągnął wymagany rozmiar
        if len(self.buffer) >= self.buffer_size:
            self.flush()
            self._rotate_if_needed()

        # Wymuszony zapis po 10 zapisach, aby upewnić się, że dane są zapisywane regularnie
        elif len(self.buffer) % 10 == 0:
            self.flush()
            self._rotate_if_needed()

    def flush(self):
        if self.current_file and self.buffer:
            self.csv_writer.writerows(self.buffer)
            self.line_count += len(self.buffer)
            self.buffer.clear()
            self.current_file.flush()

    def _should_rotate(self) -> bool:
        now = datetime.now()
        elapsed_hours = (now - self.last_rotation_time).total_seconds() / 3600
        if elapsed_hours >= self.rotate_every_hours:
            return True

        if os.path.isfile(self.current_file_path):
            size_mb = os.path.getsize(self.current_file_path) / (1024 * 1024)
            if size_mb >= self.max_size_mb:
                return True

        if self.line_count >= self.rotate_after_lines:
            return True

        return False

    def _rotate_if_needed(self):
        if self._should_rotate():
            self._archive()
            self._cleanup_old_archives()
            self.start()

    def _archive(self):
        if self.current_file_path and os.path.isfile(self.current_file_path):
            archive_name = os.path.basename(self.current_file_path)
            archive_path = os.path.join(self.log_dir, 'archive', f'{archive_name}.zip')
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(self.current_file_path, arcname=archive_name)
            os.remove(self.current_file_path)

    def _cleanup_old_archives(self):
        archive_dir = os.path.join(self.log_dir, 'archive')
        now = datetime.now()
        for fname in os.listdir(archive_dir):
            path = os.path.join(archive_dir, fname)
            if os.path.isfile(path):
                file_time = datetime.fromtimestamp(os.path.getmtime(path))
                if (now - file_time).days > self.retention_days:
                    os.remove(path)

    def _get_line_count(self) -> int:
        if not os.path.isfile(self.current_file_path):
            return 0
        with open(self.current_file_path, 'r') as f:
            return sum(1 for _ in f) - 1  # minus header

    def read_logs(self, start: datetime, end: datetime, sensor_id: Optional[str] = None) -> Iterator[Dict]:
        def parse_file(file_path):
            with open(file_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row_ts = datetime.fromisoformat(row['timestamp'])
                    if start <= row_ts <= end and (sensor_id is None or row['sensor_id'] == sensor_id):
                        yield {
                            'timestamp': row_ts,
                            'sensor_id': row['sensor_id'],
                            'value': float(row['value']),
                            'unit': row['unit']
                        }

        def parse_zip(zip_path):
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                for name in zipf.namelist():
                    with zipf.open(name) as f:
                        lines = f.read().decode().splitlines()
                        reader = csv.DictReader(lines)
                        for row in reader:
                            row_ts = datetime.fromisoformat(row['timestamp'])
                            if start <= row_ts <= end and (sensor_id is None or row['sensor_id'] == sensor_id):
                                yield {
                                    'timestamp': row_ts,
                                    'sensor_id': row['sensor_id'],
                                    'value': float(row['value']),
                                    'unit': row['unit']
                                }

        # Parsowanie aktualnych plików CSV
        for fname in os.listdir(self.log_dir):
            if fname.endswith('.csv'):
                yield from parse_file(os.path.join(self.log_dir, fname))

        # Parsowanie zarchiwizowanych plików CSV
        archive_dir = os.path.join(self.log_dir, 'archive')
        for fname in os.listdir(archive_dir):
            if fname.endswith('.zip'):
                yield from parse_zip(os.path.join(archive_dir, fname))

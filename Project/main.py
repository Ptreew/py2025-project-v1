import json
import argparse
import sys
import os
from datetime import datetime
import time
from sensors import TemperatureSensor, HumiditySensor, PressureSensor, LightSensor

# Import modules
from network.client import NetworkClient
from server.server import NetworkServer
from logger import Logger


def load_config(config_path="config.json"):
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Błąd podczas wczytywania konfiguracji: {str(e)}")
        sys.exit(1)


def run_client(config, logger, interval: float = 5.0):
    # Pobranie parametrów sieciowych z konfiguracji
    network_cfg = config.get("network", {})
    host = network_cfg.get("host", "localhost")
    port = network_cfg.get("port", 5000)
    timeout = network_cfg.get("timeout", 5.0)
    retries = network_cfg.get("retries", 3)

    # Inicjalizacja listy czujników
    sensors = [
        TemperatureSensor(),
        HumiditySensor(),
        PressureSensor(),
        LightSensor(),
    ]

    # Każdy odczyt z czujnika jest zapisywany w loggerze
    for sensor in sensors:
        sensor.register_callback(
            lambda sensor_id, ts, val, unit: logger.log_reading(sensor_id, ts, val, unit)
        )

    # Utworzenie klienta sieciowego
    client = NetworkClient(host, port, timeout, retries, logger)

    if not client.connect():
        print(f"[!] Nie udało się połączyć z serwerem {host}:{port}")
        return

    print(
        f"[+] Połączono z {host}:{port}. Rozpoczynam odczyt czujników co {interval}s (Ctrl+C aby przerwać)"
    )

    consecutive_failures = 0
    max_consecutive_failures = retries  # Maksymalna liczba kolejnych nieudanych prób

    try:
        while True:
            payload = {}
            for sensor in sensors:
                value = sensor.read_value()
                payload[sensor.sensor_id] = {
                    "name": sensor.name,
                    "value": value,
                    "unit": sensor.unit,
                    "timestamp": datetime.now().isoformat(),
                }
                print(f"{sensor.name} ({sensor.unit}): {value:.2f}")

            # Wysłanie pakietu z danymi
            if client.send(payload):
                print("[+] Pakiet wysłany oraz potwierdzony (ACK).")
                consecutive_failures = 0  # Resetuj licznik po udanym wysłaniu
            else:
                consecutive_failures += 1
                print(f"[!] Nie udało się wysłać pakietu – brak ACK. ({consecutive_failures}/{max_consecutive_failures})")
                
                if consecutive_failures >= max_consecutive_failures:
                    print("[!] Osiągnięto maksymalną liczbę kolejnych nieudanych prób. Kończenie pracy.")
                    break

            print("-" * 60)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n[*] Zatrzymano pracę klienta (Ctrl+C).")
    finally:
        client.close()


def run_server(config, logger):
    network_config = config.get("network", {})
    port = network_config.get("port", 5000)
    
    print(f"Uruchamianie serwera na porcie {port}")
    
    server = NetworkServer(port, logger)
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nPrzerwanie pracy serwera...")
    finally:
        server.stop()
        print("Serwer zakończył pracę.")


def main():
    parser = argparse.ArgumentParser(description="Moduł komunikacji sieciowej")
    parser.add_argument(
        "mode", 
        choices=["client", "server"], 
        help="Tryb działania aplikacji: client (klient) lub server (serwer)"
    )
    parser.add_argument(
        "-c", "--config", 
        default="config.json", 
        help="Ścieżka do pliku konfiguracyjnego (domyślnie: config.json)"
    )
    parser.add_argument(
        "-i", "--interval",
        type=float,
        default=3.0,
        help="Interwał odczytu sensorów w sekundach (domyślnie 3)",
    )
    
    args = parser.parse_args()
    
    # Wczytywanie konfiguracji
    config_path = args.config
    if not os.path.isfile(config_path):
        print(f"Błąd: Plik konfiguracyjny '{config_path}' nie istnieje.")
        sys.exit(1)
        
    config = load_config(config_path)
    
    # Inicjalizacja loggera
    logger = Logger(config_path)
    logger.start()
    
    try:
        # Uruchomienie w odpowiednim trybie
        if args.mode == "client":
            run_client(config, logger, args.interval)
        else:  # server
            run_server(config, logger)
    finally:
        logger.stop()


if __name__ == "__main__":
    main()

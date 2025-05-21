from sensors import TemperatureSensor, HumiditySensor, PressureSensor, LightSensor
from logger import Logger
from network.client import NetworkClient
import json
import time
from datetime import datetime, timedelta
import argparse
import sys


def load_config(config_path="config.json"):
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Błąd podczas wczytywania konfiguracji: {str(e)}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="System monitorowania sensorów z przesyłaniem danych")
    parser.add_argument(
        "-c", "--config", 
        default="config.json", 
        help="Ścieżka do pliku konfiguracyjnego (domyślnie: config.json)"
    )
    parser.add_argument(
        "-i", "--interval", 
        type=float, 
        default=5.0, 
        help="Interwał odczytu sensorów w sekundach (domyślnie: 5)"
    )
    
    args = parser.parse_args()
    
    # Wczytywanie konfiguracji
    config = load_config(args.config)
    network_config = config.get("network", {})
    
    # Parametry sieciowe z konfiguracji
    host = network_config.get("host", "localhost")
    port = network_config.get("port", 5000)
    timeout = network_config.get("timeout", 5.0)
    retries = network_config.get("retries", 3)
    
    # Inicjalizacja loggera
    logger = Logger(args.config)
    logger.start()
    
    # Inicjalizacja czujników
    sensors = [
        TemperatureSensor(),
        HumiditySensor(),
        PressureSensor(),
        LightSensor()
    ]
    
    # Rejestracja callbacków do loggera
    for s in sensors:
        s.register_callback(lambda sensor_id, ts, val, unit: logger.log_reading(sensor_id, ts, val, unit))
    
    # Inicjalizacja klienta sieciowego
    client = NetworkClient(host, port, timeout, retries, logger)
    
    # Główna pętla programu
    try:
        print(f"\n[+] Rozpoczęto monitorowanie sensorów i wysyłanie danych do {host}:{port}")
        print(f"[+] Dane są odczytywane co {args.interval} sekund")
        print("[+] Naciśnij Ctrl+C, aby zatrzymać\n")
        
        while True:
            # Zbieranie danych ze wszystkich sensorów
            sensor_data = {}
            for s in sensors:
                value = s.read_value()
                print(f"{s.name} ({s.unit}): {value:.2f}")
                
                # Dodanie danych do pakietu, który zostanie wysłany
                sensor_data[s.sensor_id] = {
                    "name": s.name,
                    "value": value,
                    "unit": s.unit,
                    "timestamp": datetime.now().isoformat()
                }
            
            # Próba wysłania danych
            send_result = client.send(sensor_data)
            if send_result:
                print("\n[+] Dane zostały pomyślnie wysłane do serwera")
            else:
                print("\n[!] Błąd podczas wysyłania danych do serwera")
            
            print("-" * 50)
            time.sleep(args.interval)
            
    except KeyboardInterrupt:
        print("\n[*] Zatrzymano monitorowanie (Ctrl+C).")
    except Exception as e:
        print(f"\n[!] Wystąpił błąd: {str(e)}")
    finally:
        # Zamknięcie połączenia i loggera
        client.close()
        logger.stop()
        print("[*] Program zakończył działanie.")


if __name__ == "__main__":
    main()

from sensors import TemperatureSensor, HumiditySensor, PressureSensor, LightSensor
from logger import Logger
from datetime import datetime, timedelta
import time

# Inicjalizacja loggera
logger = Logger('config.json')
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

def run_logging_loop():
    try:
        while True:
            print("[Logowanie odczytów]")
            for s in sensors:
                value = s.read_value()
                print(f"{s.name} ({s.unit}): {value:.2f}")
            print("---")
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nZatrzymano logowanie (Ctrl+C).")

def read_logs():
    print("\n[Odczyt danych z logów (ostatnie 24h)]")
    start_time = datetime.now() - timedelta(hours=24)
    end_time = datetime.now()
    for entry in logger.read_logs(start=start_time, end=end_time):
        print(f"{entry['timestamp']} - {entry['sensor_id']}: {entry['value']} {entry['unit']}")
    print("[Koniec odczytu logów]")

# Menu główne
try:
    while True:
        print("\n=== MENU ===")
        print("1. Rozpocznij logowanie danych (Ctrl+C aby przerwać)")
        print("2. Odczytaj dane z logów (ostatnie 24h)")
        print("0. Wyjście")
        choice = input("Wybierz opcję: ").strip()

        if choice == '1':
            run_logging_loop()
        elif choice == '2':
            read_logs()
        elif choice == '0':
            print("Zamykam program.")
            break
        else:
            print("Nieprawidłowy wybór. Spróbuj ponownie.")
finally:
    logger.stop()

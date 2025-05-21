## 1. Ogólne wymagania modułu czujników

### A. Cel modułu

Moduł „Czujników” ma symulować działanie fizycznych sensorów w systemie monitoringu. Zadaniem modułu jest generowanie losowych lub o określonych właściwościach danych symulujących odczyty czujników, ułatwiając tym samym ich dalszą analizę, logowanie i wizualizację.

### B. Wymagania funkcjonalne

  **Inicjalizacja i konfiguracja czujnika:**
  Każdy czujnik powinien mieć unikalny identyfikator, nazwę, typ oraz parametry konfiguracyjne (np. przedział wartości, częstotliwość odczytu, jednostki miary).

  **Generowanie odczytów:**
  Każdy czujnik musi posiadać metodę symulującą pobranie wartości, która generuje aktualne dane (np. poprzez funkcję losującą wartości w określonym zakresie lub zgodnie z rozkładem statystycznym).

  **Kalibracja:**
  Opcjonalnie – możliwość przeliczania i kalibracji odczytów. Może to być metoda umożliwiająca wprowadzenie korekt w generowanych wartościach.

  **Stan czujnika:**
  Możliwość sprawdzenia, czy czujnik jest aktywny, zatrzymany lub wymaga serwisu. Można to osiągnąć przez dodatkowy atrybut lub metodę.

  **Zachowanie historii:**
  Przynajmniej w pamięci (oraz opcjonalnie poprzez system logowania) czujnik powinien zapisywać ostatnio wygenerowane wartości, co umożliwi późniejszą analizę i debugowanie.

  **Interfejs API:**
  Klasa bazowa ma udostępniać spójny interfejs do generowania odczytów, dzięki czemu kolejne typy sensorów (dziedziczące z klasy bazowej) będą mogły redefiniować tylko specyficzne zachowania.


## 2. Specyfikacja klasy bazowej Sensor

### A. Atrybuty klasy Sensor

  sensor_id (string/int): Unikalny identyfikator czujnika.

  name (string): Nazwa lub opis czujnika.

  unit (string): Jednostka miary (np. °C, %, hPa, lux).

  min_value / max_value: Zakres dopuszczalnych wartości, który określa możliwy do wygenerowania przedział.

  frequency (float/int): Częstotliwość odczytów w sekundach (lub inna jednostka czasu).

  active (bool): Flaga określająca, czy czujnik jest aktywny.

  last_value: Ostatnio wygenerowana wartość.

### B. Metody klasy Sensor

  __init__(...)
  Inicjuje podstawowe atrybuty, ustawia domyślne parametry oraz flagę aktywności.

  read_value()
  Metoda generująca symulację odczytu. W klasie bazowej może udostępniać przykładową implementację (np. zwracając losową wartość z zadanego przedziału). Metoda ta będzie nadpisywana przez konkretne implementacje.

  calibrate(calibration_factor)
  Opcjonalna metoda modyfikująca wynik odczytu, pozwalająca „skalibrować” czujnik – np. poprzez mnożenie wartości przez podany współczynnik.

  get_last_value()
  Zwraca ostatni wygenerowany odczyt (przechowywany w atrybucie last_value).

  start() / stop()
  Proste metody umożliwiające włączanie lub wyłączanie symulacji czujnika (zmiana wartości flagi active).

### C. Przykładowa implementacja klasy bazowej Sensor

```python

import random
import time

class Sensor:
    def __init__(self, sensor_id, name, unit, min_value, max_value, frequency=1):
        """
        Inicjalizacja czujnika.

        :param sensor_id: Unikalny identyfikator czujnika
        :param name: Nazwa lub opis czujnika
        :param unit: Jednostka miary (np. '°C', '%', 'hPa', 'lux')
        :param min_value: Minimalna wartość odczytu
        :param max_value: Maksymalna wartość odczytu
        :param frequency: Częstotliwość odczytów (sekundy)
        """
        self.sensor_id = sensor_id
        self.name = name
        self.unit = unit
        self.min_value = min_value
        self.max_value = max_value
        self.frequency = frequency
        self.active = True
        self.last_value = None

    def read_value(self):
        """
        Symuluje pobranie odczytu z czujnika.
        W klasie bazowej zwraca losową wartość z przedziału [min_value, max_value].
        """
        if not self.active:
            raise Exception(f"Czujnik {self.name} jest wyłączony.")

        value = random.uniform(self.min_value, self.max_value)
        self.last_value = value
        return value

    def calibrate(self, calibration_factor):
        """
        Kalibruje ostatni odczyt przez przemnożenie go przez calibration_factor.
        Jeśli nie wykonano jeszcze odczytu, wykonuje go najpierw.
        """
        if self.last_value is None:
            self.read_value()

        self.last_value *= calibration_factor
        return self.last_value

    def get_last_value(self):
        """
        Zwraca ostatnią wygenerowaną wartość, jeśli była wygenerowana.
        """
        if self.last_value is None:
            return self.read_value()
        return self.last_value

    def start(self):
        """
        Włącza czujnik.
        """
        self.active = True

    def stop(self):
        """
        Wyłącza czujnik.
        """
        self.active = False

    def __str__(self):
        return f"Sensor(id={self.sensor_id}, name={self.name}, unit={self.unit})"
```


3. 4 z 7 typów czujników do zasymulowania

Wybrać co najmniej 4 z poniższej listy do implementacji. Każdy typ powinien dziedziczyć po klasie bazowej Sensor i nadpisywać metodę read_value(), aby dostosować generację danych do specyfiki danego czujnika.

  Czujnik temperatury (TemperatureSensor):

      Parametry: Zakres np. -20°C do 50°C.

      Specyfika: Symulacja wartości temperatury, można dodać uwzględnienie okresowych zmian (np. cykle dzienne).

  Czujnik wilgotności (HumiditySensor):

      Parametry: Zakres 0%–100%.

      Specyfika: Generacja wartości z uwzględnieniem zmienności środowiskowej, możliwość wprowadzenia opóźnienia lub wpływu temperatury.

  Czujnik ciśnienia atmosferycznego (PressureSensor):

      Parametry: Zakres np. 950 hPa do 1050 hPa.

      Specyfika: Wygenerowanie wartości ciśnienia, ewentualnie z niewielkimi fluktuacjami, symulacja zjawisk meteorologicznych.

  Czujnik natężenia oświetlenia (LightSensor):

      Parametry: Zakres w luksach – np. 0 lx (noc) do 10000 lx (słoneczny dzień).

      Specyfika: Symulacja zmian oświetlenia w zależności od pory dnia.

  Czujnik jakości powietrza (AirQualitySensor):

      Parametry: Poziom zanieczyszczeń, np. indeks AQI od 0 do 500.

      Specyfika: Generowanie wartości, które mogą wskazywać zarówno dobre, jak i złe warunki środowiskowe, możliwość symulacji nagłych spadków lub wzrostów jakości powietrza.

  Czujnik akcelerometru (AccelerometerSensor):

      Parametry: Trójwymiarowe przyspieszenie – zakresy dla osi X, Y, Z (np. od -16g do +16g).

      Specyfika: Zwracanie wektora z trzema wartościami; symulacja dynamicznych zmian podczas ruchu lub wstrząsów.

  Czujnik zbliżeniowy (ProximitySensor):

      Parametry: Odległość w centymetrach lub metrach (np. 0 cm do 200 cm).

      Specyfika: Symulacja wykrywania obiektów w pobliżu, możliwość wprowadzenia progów wyzwalających zdarzenie (np. obiekt pojawiający się w określonej odległości).


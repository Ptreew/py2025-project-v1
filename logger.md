## Specyfikacja modułu logowania i operacji na plikach

### 1. Cel modułu
Moduł „Logowania i operacji na plikach” ma zapewnić:
- Zapis odczytów z czujników do plików CSV w sposób uporządkowany i odtwarzalny.
- Rotację i archiwizację plików logów według konfiguracji.
- Odczyt historycznych danych z plików bieżących i archiwalnych.
- Integrację z modułem czujników poprzez wzorzec obserwatora (Observer).

### 2. Wymagania funkcjonalne

1. **Inicjalizacja**
   - Konstruktor klasy `Logger(config_path: str)`:
     - Wczytuje konfigurację z pliku JSON.
     - Ustawia katalog logów (`log_dir`), wzorzec nazwy pliku (`filename_pattern`), rozmiar bufora (`buffer_size`) oraz parametry rotacji i retencji.
   - Tworzy (jeśli nie istnieją) katalogi: `log_dir/` oraz `log_dir/archive/`.

2. **Obsługa cyklu życia**
   - `start()`: otwiera nowy plik CSV (według `filename_pattern`) i, jeśli plik jest nowy, zapisuje nagłówek.
   - `stop()`: wymusza zapis (flush) wszystkich buforowanych wierszy i zamyka aktualny plik.

3. **Logowanie odczytów**
   - `log_reading(sensor_id: str, timestamp: datetime, value: float, unit: str)`:
     - Dodaje nowy wiersz (`timestamp, sensor_id, value, unit`) do wewnętrznego bufora.
     - Po przekroczeniu `buffer_size` wykonuje flush do pliku.
     - Sprawdza potrzebę rotacji pliku (opisane poniżej).

4. **Rotacja i archiwizacja plików**
   Rotacja oznacza zamknięcie bieżącego pliku logu i utworzenie nowego, gdy spełniony jest któryś z warunków:
   - **Interwał czasowy**: co `rotate_every_hours` godzin (np. co 24 h).
   - **Rozmiar pliku**: gdy bieżący plik osiągnie `max_size_mb` megabajtów.
   - (Opcjonalnie) **Liczba wpisów**: gdy liczba wierszy w pliku przekroczy `rotate_after_lines`.

   **Parametry rotacji (konfigurowane w JSON):**
   ```json
   {
     "rotate_every_hours": 24,
     "max_size_mb": 10,
     "rotate_after_lines": 100000,
     "retention_days": 30
   }
   ```
   - `rotate_every_hours` (int): liczba godzin pomiędzy kolejnymi rotacjami.
   - `max_size_mb` (float): maksymalny rozmiar pliku w megabajtach.
   - `rotate_after_lines` (int): (opcjonalnie) liczba wierszy po której następuje rotacja.
   - `retention_days` (int): liczba dni, po których archiwa są usuwane.

   **Proces rotacji:**
   1. Wywołanie `stop()` — zapisu i zamknięcia pliku.
   2. Przeniesienie zamkniętego pliku do podfolderu `archive/`.
   3. (Opcjonalnie) Skompresowanie pliku ZIP-em zachowując oryginalną nazwę z rozszerzeniem `.zip`.
   4. Usunięcie archiwów starszych niż `retention_days` dni.
   5. Wywołanie `start()` — otworzenie nowego pliku wg wzorca `filename_pattern`.

5. **Odczyt logów**
   - `read_logs(start: datetime, end: datetime, sensor_id: Optional[str] = None) -> Iterator[Dict]`:
     - Iteruje przez pliki `.csv` w `log_dir/` i archiwa `.zip` w `log_dir/archive/`.
     - Parsuje każdą linię do postaci słownika:
       ```python
       {
         "timestamp": datetime,
         "sensor_id": str,
         "value": float,
         "unit": str
       }
       ```
     - Zwraca tylko wpisy, których `timestamp` mieści się w przedziale `[start, end]`,
       i (opcjonalnie) `sensor_id` odpowiada podanemu filtr.

### 3. Publiczne API klasy `Logger`
```python
class Logger:
    def __init__(self, config_path: str):
        """
        Inicjalizuje logger na podstawie pliku JSON.
        :param config_path: Ścieżka do pliku konfiguracyjnego (.json)
        """
        ...

    def start(self) -> None:
        """
        Otwiera nowy plik CSV do logowania. Jeśli plik jest nowy, zapisuje nagłówek.
        """
        ...

    def stop(self) -> None:
        """
        Wymusza zapis bufora i zamyka bieżący plik.
        """
        ...

    def log_reading(
        self,
        sensor_id: str,
        timestamp: datetime,
        value: float,
        unit: str
    ) -> None:
        """
        Dodaje wpis do bufora i ewentualnie wykonuje rotację pliku.
        """
        ...

    def read_logs(
        self,
        start: datetime,
        end: datetime,
        sensor_id: Optional[str] = None
    ) -> Iterator[Dict]:
        """
        Pobiera wpisy z logów zadanego zakresu i opcjonalnie konkretnego czujnika.
        """
        ...
```

> **Uwaga**: Będziesz potrzebował prywatnych metod związanych z implementacją rotacji (na przykład: _rotate, _archive, _clean_old_archives). Nie zostały uwzględnione w szablonie klasy, gdyż nie należą do jej publicznego API. Zastanów się jak zrealizować mechanizm zarządzania logami i zaimplementuj odpowiednie funkcje.

---

### 4. Integracja z modułem czujników
- Wzorzec Observer: czujnik po odczycie wywołuje zarejestrowane callbacki.
- Przykład rejestracji:
  ```python
  sensor.register_callback(logger.log_reading)
  ```

Należy zatem zmodyfikować klasę bazową sensora, aby mógł w metodzie przyjmować funkcję loggera, a następnie uruchamiać ją w momencie odczytu wartości z czujnika).

---

### 5. Przykładowy fragment pliku `config.json`
```json
{
  "log_dir": "./logs",
  "filename_pattern": "sensors_%Y%m%d.csv",
  "buffer_size": 200,
  "rotate_every_hours": 24,
  "max_size_mb": 5,
  "rotate_after_lines": 100000,
  "retention_days": 30
}
```

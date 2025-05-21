# Specyfikacja modułu komunikacji sieciowej

## 1. Cel modułu

Moduł ma umożliwić wysyłanie danych zebranych przez moduł sensorów do zdalnego serwera oraz odbiór potwierdzeń, z zachowaniem współpracy z istniejącym modułem loggera.

## 2. Założenia

Komunikacja w oparciu o protokół TCP.

Dane przesyłane w formacie JSON.

Integracja z modułem ```logger``` w celu rejestrowania przebiegu transmisji.

Konfigurowalny adres serwera, port, timeout oraz liczba prób ponowienia komunikacji.

## 3. Wymagania funkcjonalne

1. Konfiguracja połączenia:

    - Wczytywanie ustawień z pliku ```config.yaml``` lub przekazanie parametrów do konstruktora.

2. Nawiązywanie i zamykanie połączenia:

    - Metody connect() i close().

3. Wysyłanie danych:

    - **Metoda send(data: dict) -> bool:**

        - Serializacja do JSON, wysłanie na serwer.

        - Oczekiwanie na potwierdzenie (ack).

        - Zwraca True przy sukcesie, False przy porażce.

4. Obsługa błędów i retry:

    -  W przypadku braku potwierdzenia lub błędu sieciowego: próba ponowienia (konfigurowalna liczba prób).

5. Integracja z loggerem:

    - Rejestrowanie zdarzeń:

        - Połączenie (info).

        - Wysłanie pakietu / potwierdzenie (info).

        - Błąd / timeout (error).

## 4. Wymagania niefunkcjonalne

Prosty interfejs API: klasa NetworkClient z czytelnymi metodami.

Czytelna dokumentacja metod i nazewnictwo składników modułu (zmiennych, metod, klas).

## 5. Projekt API
```python
class NetworkClient:
    def __init__(
        self,
        host: str,
        port: int,
        timeout: float = 5.0,
        retries: int = 3
    ):
        """Inicjalizuje klienta sieciowego."""

    def connect(self) -> None:
        """Nawiazuje połączenie z serwerem."""

    def send(self, data: dict) -> bool:
        """Wysyła dane i czeka na potwierdzenie zwrotne."""

    def close(self) -> None:
        """Zamyka połączenie."""

    # Metody pomocnicze:
    def _serialize(self, data: dict) -> bytes:
        pass

    def _deserialize(self, raw: bytes) -> dict:
        pass
```

## 6.Specyfikacja serwera odbiorczego

### Należy również zaimplementować prosty serwer TCP, który:

- Odczytuje port nasłuchiwania z config.yaml lub przyjmuje go jako parametr przy uruchomieniu.
- Metoda start() otwiera gniazdo TCP i oczekuje na połączenia od klientów.
- Dla każdego przychodzącego połączenia:
  - Odbiera pełną wiadomość JSON (np. zakończoną nową linią).
  - Deserializuje do słownika.
  - Wysyła potwierdzenie ACK (np. "ACK" + newline).

-  Wyświetla zawartość słownika na konsoli (w czytelnej formie: klucze i wartości).

-  Zamyka połączenie.

### Obsługa błędów:

Loguje błędy przy parsowaniu JSON i przy przesyłaniu potwierdzenia (wypisuje na stderr).

## 7. Przykład API Serwera odbiorczego

```python
class NetworkServer:
    def __init__(self, port: int):
        """Inicjalizuje serwer na wskazanym porcie."""

    def start(self) -> None:
        """Uruchamia nasłuchiwanie połączeń i obsługę klientów."""

    def _handle_client(self, client_socket) -> None:
        """Odbiera dane, wysyła ACK i wypisuje je na konsolę."""
```

## 8. Struktura katalogów

```python
project-root/
├── network/
│   ├── __init__.py
│   ├── client.py           # implementacja NetworkClient
│   └── config.py           # wczytywanie konfiguracji dla klienta
├── server/
│   ├── __init__.py
│   └── server.py           # implementacja NetworkServer
├── config.yaml             # konfiguracja host, port (klient i serwer), timeout, retries
└── tests/
    ├── test_network.py     # opcjonalne testy jednostkowe klienta
    └── test_server.py      # opcjonalne testy jednostkowe serwera
```


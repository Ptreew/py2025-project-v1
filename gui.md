# Specyfikacja modułu GUI dla serwera sieciowego

## Cel

Zapewnienie użytkownikowi intuicyjnego interfejsu do zarządzania serwerem TCP oraz wizualizacji stanu i odczytów czujników w czasie rzeczywistym.

## Główne funkcje

### Sterowanie serwerem

- Włączenie i wyłączenie nasłuchiwania na zadanym porcie.
- Wyświetlanie aktualnego statusu: zatrzymany, nasłuchiwanie, błąd.

### Lista czujników

Tabela z kolumnami:
- Sensor: unikalny identyfikator czujnika.
- Ostatnia wartość: najnowszy odczyt liczbowy.
- Jednostka: jednostka pomiaru.
- Timestamp: data i godzina ostatniego odczytu.
- Średnia 1h: średnia z odczytów z ostatniej godziny.
- Średnia 12h: średnia z odczytów z ostatnich 12 godzin.

### Automatyczna aktualizacja co kilka sekund.

### Konfiguracja

- Możliwość ustawienia portu TCP przed startem.

- Zachowanie ustawień między uruchomieniami (np. plik konfiguracyjny).

### Obsługa błędów

- Łapanie wyjątków z wątku serwera i prezentacja komunikatu o błędzie.

### Interfejs użytkownika

Górny panel:

- Pole wpisu portu TCP.
- Przycisk Start (uruchom nasłuchiwanie).
- Przycisk Stop (zatrzymaj serwer).

Środkowa część:

- Tabela czujników (łagodne przewijanie, czytelne kolumny).

Dolny panel:

- Pasek statusu informujący o działaniu serwera.

### Architektura logiczna

Komponent GUI odpowiada za rysowanie interfejsu i reagowanie na akcje użytkownika.

Moduł serwera ukrywa szczegóły komunikacji sieciowej, udostępniając mechanizm rejestracji callbacków na nowe odczyty.

### Mechanizm agregacji

Buforowanie historii odczytów per czujnik (można użyć loggera).
Obliczanie średnich wartości dla zadanych przedziałów czasowych.

## Scenariusz użytkowania

- Użytkownik uruchamia aplikację i ustawia port.
- Po naciśnięciu Start rozpoczyna się nasłuchiwanie.
- W miarę pojawiania się danych lista czujników jest automatycznie aktualizowana.
- Użytkownik widzi w tabeli ostatnie wartości oraz obliczone średnie z interwałów 1h i 12h.
- W razie potrzeby naciska Stop, aby zatrzymać serwer, lub otrzymuje komunikaty o błędach.

## Przykładowy widok GUI:

<img width="672" alt="gui_project-v1" src="https://github.com/user-attachments/assets/7db04305-0dc8-4296-8a3a-0b32373832c1" />

import socket
import json
import sys
import threading
import traceback
from datetime import datetime
from typing import List

class NetworkServer:
    def __init__(self, port: int, logger=None):
        self.port = port
        self.logger = logger
        self.server_socket = None
        self.running = False
        self._client_sockets: List[socket.socket] = []
        self._clients_lock = threading.Lock()
        
    def start(self) -> None:
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', self.port))
            self.server_socket.listen(5)
            self.running = True
            
            print(f"[+] Serwer uruchomiony na porcie {self.port}")
            if self.logger:
                self.logger.log_reading("server", datetime.now(), 1, f"started_on_port_{self.port}")
            
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    print(f"[+] Nowe połączenie od {client_address[0]}:{client_address[1]}")
                    if self.logger:
                        self.logger.log_reading("server", datetime.now(), 1, f"connection_from_{client_address[0]}:{client_address[1]}")
                    
                    # Obsługa klienta w nowym wątku
                    client_thread = threading.Thread(target=self._handle_client, args=(client_socket, client_address))
                    client_thread.daemon = True
                    client_thread.start()
                    
                    # Track client sockets
                    with self._clients_lock:
                        self._client_sockets.append(client_socket)
                    
                except KeyboardInterrupt:
                    print("\n[*] Przerwanie pracy serwera...")
                    self.stop()
                    break
                except Exception as e:
                    print(f"[!] Błąd podczas akceptowania połączenia: {str(e)}")
                    if self.logger:
                        self.logger.log_reading("server", datetime.now(), 0, f"accept_error: {str(e)}")
                    # Jeśli serwer jest w trakcie zamykania, przerwij pętlę
                    if not self.running and isinstance(e, OSError):
                        break
        
        except Exception as e:
            print(f"[!] Błąd podczas uruchamiania serwera: {str(e)}")
            if self.logger:
                self.logger.log_reading("server", datetime.now(), 0, f"start_error: {str(e)}")
    
    def stop(self) -> None:
        self.running = False
        if self.server_socket:
            try:
                try:
                    self.server_socket.shutdown(socket.SHUT_RDWR)
                except OSError:
                    # Socket may already be closed or not connected; ignore.
                    pass
                self.server_socket.close()
                self.server_socket = None
                if self.logger:
                    self.logger.log_reading("server", datetime.now(), 0, "server_stopped")
            except Exception as e:
                print(f"[!] Błąd podczas zatrzymywania serwera: {str(e)}")
                if self.logger:
                    self.logger.log_reading("server", datetime.now(), 0, f"stop_error: {str(e)}")
        
        # Close all connected client sockets
        with self._clients_lock:
            for cs in self._client_sockets:
                try:
                    cs.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                try:
                    cs.close()
                except Exception:
                    pass
            self._client_sockets.clear()
    
    def _handle_client(self, client_socket, client_address) -> None:
        try:
            # Ustawienie timeout na gniazdo klienta (można zostawić, aby nie blokować serwera w nieskończoność)
            client_socket.settimeout(60.0)

            buffer = b""
            while True:
                # Odbiór porcji danych
                chunk = client_socket.recv(1024)
                if not chunk:
                    # Klient zamknął połączenie
                    raise ConnectionResetError("client disconnected")

                buffer += chunk

                # Przetworzenie wszystkich kompletnych wiadomości z bufora
                while b"\n" in buffer:
                    msg, _, buffer = buffer.partition(b"\n")
                    json_bytes = msg + b"\n"

                    try:
                        json_data = self._deserialize(json_bytes)
                        print(f"\n[+] Odebrano dane od {client_address[0]}:{client_address[1]}:")
                        self._print_formatted_json(json_data)

                        # Wysłanie ACK
                        client_socket.sendall(b"ACK\n")
                        if self.logger:
                            self.logger.log_reading(
                                "server",
                                datetime.now(),
                                len(json_bytes),
                                f"data_received_from_{client_address[0]}:{client_address[1]}"
                            )
                            self.logger.log_reading(
                                "server",
                                datetime.now(),
                                1,
                                f"ack_sent_to_{client_address[0]}:{client_address[1]}"
                            )
                    except json.JSONDecodeError as e:
                        print(f"[!] Błąd dekodowania JSON: {str(e)}")
                        if self.logger:
                            self.logger.log_reading("server", datetime.now(), 0, f"json_decode_error: {str(e)}")
        except (ConnectionResetError, socket.timeout, OSError):
            print(f"[*] Zamknięto połączenie z {client_address[0]}:{client_address[1]}")
        except Exception as e:
            print(f"[!] Błąd podczas obsługi klienta {client_address[0]}:{client_address[1]}: {str(e)}")
            traceback.print_exc()
            if self.logger:
                self.logger.log_reading("server", datetime.now(), 0, f"client_handling_error: {str(e)}")
        finally:
            # Remove socket from tracking list
            with self._clients_lock:
                if client_socket in self._client_sockets:
                    self._client_sockets.remove(client_socket)
            try:
                client_socket.close()
            except:
                pass
    
    def _deserialize(self, raw: bytes) -> dict:
        return json.loads(raw.decode('utf-8').strip())
    
    def _print_formatted_json(self, data: dict) -> None:
        if isinstance(data, dict):
            for key, value in data.items():
                print(f"  {key}: {value}")
        else:
            print(f"  {data}")

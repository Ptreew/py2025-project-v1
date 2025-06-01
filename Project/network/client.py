import socket
import json
import time
import sys
from datetime import datetime

class NetworkClient:
    def __init__(
        self,
        host: str,
        port: int,
        timeout: float = 5.0,
        retries: int = 3,
        logger = None
    ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.retries = retries
        self.logger = logger
        self.socket = None
        
    def connect(self) -> bool:
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            
            if self.logger:
                self.logger.log_reading("network", datetime.now(), 1, "connection")
                
            return True
        except Exception as e:
            if self.logger:
                self.logger.log_reading("network", datetime.now(), 0, f"connection_error: {str(e)}")
            return False
    
    def send(self, data: dict) -> bool:
        if not self.socket:
            if not self.connect():
                return False
        
        retry_count = 0
        while retry_count < self.retries:
            try:
                # Serializacja i wysłanie danych
                message = self._serialize(data)
                self.socket.sendall(message)
                
                if self.logger:
                    self.logger.log_reading("network", datetime.now(), len(message), "bytes_sent")
                
                # Oczekiwanie na potwierdzenie
                response = self.socket.recv(1024)
                if response.strip() == b"ACK":
                    if self.logger:
                        self.logger.log_reading("network", datetime.now(), 1, "ack_received")
                    return True
                else:
                    if self.logger:
                        self.logger.log_reading("network", datetime.now(), 0, f"invalid_ack: {response}")
                    
            except socket.timeout:
                if self.logger:
                    self.logger.log_reading("network", datetime.now(), 0, f"timeout (attempt {retry_count+1}/{self.retries+1})")
            except Exception as e:
                if self.logger:
                    self.logger.log_reading("network", datetime.now(), 0, f"error: {str(e)} (attempt {retry_count+1}/{self.retries+1})")
                
                # Próba ponownego nawiązania połączenia
                try:
                    self.close()
                    self.connect()
                except:
                    pass
            
            retry_count += 1
            time.sleep(min(retry_count, 5))
        
        return False
    
    def close(self) -> None:
        if self.socket:
            try:
                self.socket.close()
                if self.logger:
                    self.logger.log_reading("network", datetime.now(), 0, "connection_closed")
            except Exception as e:
                if self.logger:
                    self.logger.log_reading("network", datetime.now(), 0, f"close_error: {str(e)}")
            finally:
                self.socket = None
    
    def _serialize(self, data: dict) -> bytes:
        json_str = json.dumps(data)
        return (json_str + "\n").encode('utf-8')
    
    def _deserialize(self, raw: bytes) -> dict:
        return json.loads(raw.decode('utf-8'))

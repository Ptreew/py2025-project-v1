import threading
import time
import socket

from network.client import NetworkClient
from server.server import NetworkServer


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("localhost", 0))
        return s.getsockname()[1]


def _run_server(port: int):
    srv = NetworkServer(port)
    t = threading.Thread(target=srv.start, daemon=True)
    t.start()
    time.sleep(0.2)
    return srv, t


def test_ack_single_message():
    port = _free_port()
    srv, t = _run_server(port)

    client = NetworkClient("localhost", port, timeout=2, retries=0)
    assert client.connect()
    assert client.send({"msg": "hello"}) is True

    client.close()
    srv.stop()
    t.join(timeout=1)


def test_multiple_messages_same_connection():
    port = _free_port()
    srv, t = _run_server(port)

    client = NetworkClient("localhost", port, timeout=2, retries=0)
    assert client.connect()

    for i in range(5):
        assert client.send({"n": i}) is True

    client.close()
    srv.stop()
    t.join(timeout=1)

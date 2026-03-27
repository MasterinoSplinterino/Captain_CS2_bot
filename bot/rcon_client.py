import socket
import struct

SERVERDATA_AUTH = 3
SERVERDATA_EXECCOMMAND = 2


def _pack(request_id: int, pkt_type: int, body: str) -> bytes:
    body_bytes = body.encode("utf-8") + b"\x00\x00"
    size = 4 + 4 + len(body_bytes)
    return struct.pack("<iii", size, request_id, pkt_type) + body_bytes


def _read(sock: socket.socket):
    raw = b""
    while len(raw) < 4:
        chunk = sock.recv(4 - len(raw))
        if not chunk:
            raise ConnectionError("Connection closed")
        raw += chunk
    size = struct.unpack("<i", raw)[0]
    data = b""
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise ConnectionError("Connection closed")
        data += chunk
    request_id = struct.unpack("<i", data[0:4])[0]
    pkt_type = struct.unpack("<i", data[4:8])[0]
    body = data[8:-2].decode("utf-8", errors="replace")
    return request_id, pkt_type, body


def execute(host: str, port: int, password: str, command: str, timeout: float = 5.0) -> str:
    """Execute a single RCON command on a remote CS2 server."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))

        # Authenticate
        sock.sendall(_pack(1, SERVERDATA_AUTH, password))
        rid, _, _ = _read(sock)
        if rid == -1:
            raise PermissionError("RCON authentication failed — wrong password")
        # Some servers send an extra empty packet after auth
        try:
            sock.settimeout(0.5)
            _read(sock)
        except socket.timeout:
            pass

        # Execute
        sock.settimeout(timeout)
        sock.sendall(_pack(2, SERVERDATA_EXECCOMMAND, command))

        # Read response (may be multi-packet)
        response = ""
        sock.settimeout(2)
        try:
            while True:
                _, _, body = _read(sock)
                response += body
        except socket.timeout:
            pass
        return response.strip()
    finally:
        sock.close()


def test_connection(host: str, port: int, password: str, timeout: float = 5.0) -> tuple[bool, str]:
    """Test RCON connection. Returns (ok, message)."""
    try:
        result = execute(host, port, password, "status", timeout)
        return True, result
    except PermissionError as e:
        return False, str(e)
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"

import socket
import struct
import time
from bot_config import RCON_HOST, RCON_PORT, RCON_PASSWORD

SERVERDATA_AUTH = 3
SERVERDATA_EXECCOMMAND = 2
SERVERDATA_AUTH_RESPONSE = 2
SERVERDATA_RESPONSE_VALUE = 0

class RCONClient:
    def __init__(self):
        self.host = RCON_HOST
        self.port = RCON_PORT
        self.password = RCON_PASSWORD
        self.timeout = 5

    def _create_packet(self, id, type, body):
        body_encoded = body.encode('utf-8')
        size = 4 + 4 + len(body_encoded) + 1 + 1
        return struct.pack(f'<iii{len(body_encoded)}scc', size, id, type, body_encoded, b'\x00', b'\x00')

    def _read_packet(self, sock):
        try:
            size_data = sock.recv(4)
            if not size_data: return None
            size = struct.unpack('<i', size_data)[0]
            
            # Read the rest of the packet
            data = b''
            while len(data) < size:
                chunk = sock.recv(size - len(data))
                if not chunk: break
                data += chunk
            
            if len(data) < size: return None

            id, type = struct.unpack('<ii', data[:8])
            body = data[8:-2].decode('utf-8', errors='replace')
            return id, type, body
        except socket.timeout:
            return None

    def execute(self, command: str) -> str:
        """Executes a single RCON command and returns the response."""
        sock = None
        try:
            sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
            
            # Authenticate
            sock.sendall(self._create_packet(1, SERVERDATA_AUTH, self.password))
            
            # Read Auth Response
            # Note: Sometimes server sends multiple packets. Auth response usually comes first.
            auth_resp = self._read_packet(sock)
            if not auth_resp:
                return "Error: No auth response from server."
            
            id, type, body = auth_resp
            if id == -1:
                return "Error: RCON Authentication Failed (Wrong Password)."
            
            # Send Command
            sock.sendall(self._create_packet(2, SERVERDATA_EXECCOMMAND, command))
            
            # Read Response
            # CS2 might send multiple packets for long responses.
            # A common trick is to send an empty command after to mark end, but for now simple read.
            # We'll read until timeout or empty packet if we want to be robust, 
            # but for simple commands one read might be enough or we loop.
            
            response_text = ""
            while True:
                packet = self._read_packet(sock)
                if not packet: break
                
                pid, ptype, pbody = packet
                # Some servers echo the command back, some just send response.
                if pbody:
                    response_text += pbody
                
                # If we got a response, we might be done. 
                # Real RCON implementation is tricky because there's no "end of response" marker.
                # But usually for 'status' etc it comes in one or two bursts.
                # We can rely on timeout (short) or just return what we got.
                
                # Optimization: if we got data, maybe wait a tiny bit for more, else break
                sock.settimeout(0.5) 
            
            return response_text.strip()

        except Exception as e:
            return f"Error executing RCON command: {type(e).__name__}: {e}"
        finally:
            if sock:
                sock.close()

    def change_map(self, map_name: str) -> str:
        return self.execute(f"changelevel {map_name}")

    def change_mode(self, mode_command: str, map_name: str = None) -> str:
        cmds = [mode_command]
        if map_name:
            if map_name.startswith("workshop/"):
                # Extract ID from workshop/ID/name
                try:
                    workshop_id = map_name.split('/')[1]
                    cmds.append(f"host_workshop_map {workshop_id}")
                except IndexError:
                    # Fallback if format is unexpected
                    cmds.append(f"map {map_name}")
            else:
                cmds.append(f"map {map_name}")
        return self.execute("; ".join(cmds))

    def kick_player(self, player_name: str) -> str:
        return self.execute(f"kick \"{player_name}\"")

    def add_bot(self, team: str) -> str:
        # Execute commands sequentially to ensure they apply
        self.execute("sv_cheats 1")
        self.execute("bot_difficulty 3")
        self.execute("bot_stop 0")
        self.execute("bot_zombie 0")
        self.execute("bot_freeze 0")
        self.execute("ai_disable 0")
        return self.execute(f"bot_add_{team}")

    def remove_bots(self) -> str:
        return self.execute("bot_kick")

    def get_status(self) -> str:
        return self.execute("status")

    def get_full_info(self) -> dict:
        """Fetches detailed server info."""
        status_raw = self.execute("status")
        password_raw = self.execute("sv_password")
        game_type_raw = self.execute("game_type")
        game_mode_raw = self.execute("game_mode")
        map_raw = self.execute("host_map") # host_map usually returns the map name

        return {
            "status": status_raw,
            "password": password_raw,
            "game_type": game_type_raw,
            "game_mode": game_mode_raw,
            "map": map_raw
        }

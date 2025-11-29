import socket
import struct
import sys

HOST = 'cs2'
PORT = 27015
PASSWORD = 'rconcs2captainbot'

SERVERDATA_AUTH = 3
SERVERDATA_AUTH_RESPONSE = 2

def create_packet(id, type, body):
    body_encoded = body.encode('utf-8')
    size = 4 + 4 + len(body_encoded) + 1 + 1
    return struct.pack(f'<iii{len(body_encoded)}scc', size, id, type, body_encoded, b'\x00', b'\x00')

def read_packet(sock):
    size_data = sock.recv(4)
    if not size_data: return None
    size = struct.unpack('<i', size_data)[0]
    data = sock.recv(size)
    id, type = struct.unpack('<ii', data[:8])
    body = data[8:-2].decode('utf-8', errors='replace')
    return id, type, body

try:
    print(f"Connecting to {HOST}:{PORT}...")
    sock = socket.create_connection((HOST, PORT), timeout=5)
    print("Connected.")

    print("Sending Auth...")
    sock.sendall(create_packet(1, SERVERDATA_AUTH, PASSWORD))

    print("Waiting for response...")
    response = read_packet(sock)
    if response:
        id, type, body = response
        print(f"Response: ID={id}, Type={type}, Body='{body}'")
        if id == -1:
            print("AUTH FAILED (Bad Password)")
        else:
            print("AUTH SUCCESS")
    else:
        print("No response received.")

    sock.close()
except Exception as e:
    print(f"Error: {e}")

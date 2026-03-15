import socket
import threading
import sys

HOST = '127.0.0.1'
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
NAME = sys.argv[2] if len(sys.argv) > 2 else 'anonymous'

def receive_messages(sock):
    """Runs in its own thread — listens for incoming messages."""
    while True:
        try:
            data = sock.recv(1024)
            if not data:
                print("[Server closed the connection]")
                break
            print(data.decode().strip())
        except Exception:
            print("[Disconnected from server]")
            break

def send_messages(sock):
    """Runs in main thread — reads your input and sends it."""
    while True:
        try:
            msg = input()
            sock.send(msg.encode() + b"\n")
        except EOFError:
            break
        except Exception:
            print("[Lost connection to server]")
            break

# Connect to server
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((HOST, PORT))

# Send name first
sock.send(NAME.encode() + b"\n")
print(f"Connected as {NAME}")

# Start receive thread
thread = threading.Thread(target=receive_messages, args=(sock,))
thread.daemon = True
thread.start()

# Send loop runs in main thread
send_messages(sock)

sock.close()
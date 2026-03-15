import socket
import threading
import time
import sys

HOST = '127.0.0.1'

def run_client(port, client_id, msg_rate, max_msgs):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((HOST, port))
    except ConnectionRefusedError:
        return

    try:
        name = f"load_client_{client_id}"
        sock.send(name.encode() + b"\n")
        time.sleep(0.1)

        interval = 1.0 / msg_rate if msg_rate > 0 else 999999
        msg_count = 0

        while max_msgs == 0 or msg_count < max_msgs:
            sock.send(f"msg_{msg_count}\n".encode())
            msg_count += 1
            time.sleep(interval)

    except (ConnectionResetError, BrokenPipeError, OSError):
        pass
    finally:
        try:
            sock.close()
        except Exception:
            pass

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: python3 load_test.py <port> <client_id> <msg_rate> [max_msgs]")
        sys.exit(1)

    port     = int(sys.argv[1])
    cid      = sys.argv[2]
    msg_rate = float(sys.argv[3])
    max_msgs = int(sys.argv[4]) if len(sys.argv) > 4 else 0  # 0 = unlimited

    run_client(port, cid, msg_rate, max_msgs)

    
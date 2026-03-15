import socket
import threading
import time
import os
from datetime import datetime

HOST = '127.0.0.1'
PORT = 5000
STATS_INTERVAL = 5
MAX_LOG_LINES = 1000

human_clients = {}
load_clients  = {}
clients_lock  = threading.Lock()

server_log       = None
chat_log         = None
server_log_lines = 0
chat_log_lines   = 0
log_lock         = threading.Lock()

human_stats = {}

metrics = {
    'messages_total': 0,
    'bytes_total':    0,
    'messages_last':  0,
    'bytes_last':     0,
    'clients_ever':   0,
    'start_time':     None,
    'last_report':    None,
}

def ts():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def is_load_client(name):
    return name.startswith("load_client_")

def write_log(f, line, counter_name):
    global server_log_lines, chat_log_lines
    if f is None:
        return
    with log_lock:
        if counter_name == 'server':
            if server_log_lines >= MAX_LOG_LINES:
                f.seek(0)
                f.truncate()
                server_log_lines = 0
            f.write(line + "\n")
            f.flush()
            server_log_lines += 1
        elif counter_name == 'chat':
            if chat_log_lines >= MAX_LOG_LINES:
                f.seek(0)
                f.truncate()
                chat_log_lines = 0
            f.write(line + "\n")
            f.flush()
            chat_log_lines += 1

def log_server(msg):
    """Silent log to server.log only."""
    write_log(server_log, f"[{ts()}] {msg}", 'server')

def log_server_event(msg):
    """Lifecycle events — terminal + server.log."""
    line = f"[{ts()}] {msg}"
    print(line)
    write_log(server_log, line, 'server')

def log_chat(name, text):
    """Human message — terminal + chat.log + server.log."""
    human_stats[name] = human_stats.get(name, 0) + 1
    line = f"[{ts()}] {name}: {text}"
    write_log(chat_log,   line, 'chat')
    write_log(server_log, line, 'server')
    print(f"  {line}  [{name} msgs: {human_stats[name]}]")

def broadcast(targets, message, sender_conn):
    with clients_lock:
        for conn in list(targets):
            if conn != sender_conn:
                try:
                    conn.send(message)
                except Exception:
                    targets.pop(conn, None)

def print_stats():
    while True:
        time.sleep(STATS_INTERVAL)
        now   = time.time()
        up    = now - metrics['start_time']
        since = now - metrics['last_report']

        msg_delta  = metrics['messages_total'] - metrics['messages_last']
        byte_delta = metrics['bytes_total']    - metrics['bytes_last']
        msg_rate   = msg_delta  / since if since > 0 else 0
        byte_rate  = byte_delta / since if since > 0 else 0
        avg_msg    = metrics['messages_total'] / up if up > 0 else 0
        avg_byte   = metrics['bytes_total']    / up if up > 0 else 0

        print(f"\n{'─'*60}")
        print(f"  ⏱  Uptime:      {up:.0f}s")
        print(f"  👥 Clients:     {len(human_clients)} human / {len(load_clients)} load / {metrics['clients_ever']} ever")
        print(f"  📨 Messages:    {metrics['messages_total']} total  |  {msg_rate:.1f} msg/s now  |  {avg_msg:.1f} msg/s avg")
        print(f"  📊 Throughput:  {byte_rate/1024:.2f} KB/s now  |  {avg_byte/1024:.2f} KB/s avg")
        print(f"  📦 Bytes in:    {metrics['bytes_total']:,}")
        print(f"  📝 Log lines:   server.log {server_log_lines}/{MAX_LOG_LINES}  |  chat.log {chat_log_lines}/{MAX_LOG_LINES}")
        print(f"{'─'*60}\n")

        metrics['last_report']   = now
        metrics['messages_last'] = metrics['messages_total']
        metrics['bytes_last']    = metrics['bytes_total']

def handle_client(conn, addr):
    name = None
    load = False
    try:
        name_data = conn.recv(1024)
        if not name_data:
            conn.close()
            return
        name = name_data.decode().strip()
        load = is_load_client(name)
        metrics['clients_ever'] += 1

        with clients_lock:
            if load:
                load_clients[conn] = name
            else:
                human_clients[conn] = name

        log_server_event(f"[+] '{name}' connected from {addr} | "
                         f"humans: {len(human_clients)}  load: {len(load_clients)}")

        if not load:
            broadcast(human_clients, f"[Server] '{name}' joined the chat\n".encode(), conn)

        while True:
            try:
                data = conn.recv(1024)
                if not data:
                    break

                metrics['messages_total'] += 1
                metrics['bytes_total']    += len(data)
                text = data.decode().strip()

                if load:
                    log_server(f"{name}: {text}")
                    broadcast(load_clients, f"{name}: {text}\n".encode(), conn)
                else:
                    log_chat(name, text)
                    broadcast(human_clients, f"{name}: {text}\n".encode(), conn)

            except Exception:
                break

    except Exception:
        pass
    finally:
        with clients_lock:
            human_clients.pop(conn, None)
            load_clients.pop(conn, None)
        conn.close()
        display_name = name or str(addr)
        log_server_event(f"[-] '{display_name}' disconnected | "
                         f"humans: {len(human_clients)}  load: {len(load_clients)}")
        if not is_load_client(display_name) and display_name in human_stats:
            print(f"    {display_name} sent {human_stats[display_name]} message(s) total.")
        if not load:
            broadcast(human_clients, f"[Server] '{display_name}' left the chat\n".encode(), conn)

# Open log files
for fname, counter in [("server.log", "server"), ("chat.log", "chat")]:
    if os.path.exists(fname):
        with open(fname, 'r') as f:
            lines = sum(1 for _ in f)
        if counter == 'server':
            server_log_lines = min(lines, MAX_LOG_LINES)
        else:
            chat_log_lines = min(lines, MAX_LOG_LINES)

server_log = open("server.log", "a")
chat_log   = open("chat.log",   "a")

# Start stats thread
metrics['start_time']  = time.time()
metrics['last_report'] = time.time()
stats_thread = threading.Thread(target=print_stats)
stats_thread.daemon = True
stats_thread.start()

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((HOST, PORT))
server_socket.listen()

log_server_event(f"Server started on {HOST}:{PORT}")
print(f"Human chat → chat.log  (printed here with per-user counts)")
print(f"Load test  → server.log only (silent in terminal)")
print(f"Log limit:   {MAX_LOG_LINES} lines per file (rotates when full)")
print(f"Stats every {STATS_INTERVAL}s\n")

try:
    while True:
        conn, addr = server_socket.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.daemon = True
        thread.start()
except KeyboardInterrupt:
    log_server_event("Server shutting down.")
    if human_stats:
        print("\n=== Session Summary ===")
        for user, count in sorted(human_stats.items()):
            print(f"  {user}: {count} message(s)")
    server_log.close()
    chat_log.close()
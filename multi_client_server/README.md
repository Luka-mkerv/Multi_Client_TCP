# Multi-Client Chat Server Lab

A multi-client chat server built with Python `threading`, demonstrating concurrent
socket programming, broadcast messaging, and load testing.

## Files

| File | Purpose |
|------|---------|
| `server.py` | TCP server — accepts connections, broadcasts messages, writes logs, prints stats |
| `client.py` | Interactive CLI client for human users |
| `load_test.py` | Single automated bot client (used by `stress_test.sh`) |
| `stress_test.sh` | Spawns N load bots for stress testing |
| `start.sh` | Starts the server |
| `server.log` | Auto-generated: all server events + load bot traffic (max 1000 lines, rotates) |
| `chat.log` | Auto-generated: human chat messages only (max 1000 lines, rotates) |

---

## Quick Start

### 1. Start the server
```bash
./start.sh
# or
python3 server.py
```
Server always runs on **port 5000**. You can override:
```bash
python3 server.py 9999
```

### 2. Connect as a human user (separate terminal)
```bash
python3 client.py 5000 alice
python3 client.py 5000 bob
```
Type messages and press Enter to chat. Human messages are saved to `chat.log` and printed in the server terminal with a per-user message count.

### 3. Run a stress test (separate terminal)
```bash
./stress_test.sh 5000 50 2
# 50 bots, 2 messages/sec each → ~100 msg/sec total
```
Load bot traffic goes silently to `server.log` only — it does not appear in your terminal and does **not** interfere with human clients.

---

## How It Works

### Two separate client pools

The server maintains two independent sets of connections:
```
load_clients  ──broadcasts──▶  other load_clients only
human_clients ──broadcasts──▶  other human_clients only
```

Any client whose name starts with `load_client_` is treated as a bot. Everyone else is a human. This means you can run a stress test at full speed without flooding human clients.

### Logging

| What | Where | Terminal |
|------|-------|----------|
| Server start/stop | `server.log` | ✅ printed |
| Client connect/disconnect | `server.log` | ✅ printed |
| Human messages | `server.log` + `chat.log` | ✅ printed with msg count |
| Load bot messages | `server.log` only | ❌ silent |

Both log files rotate automatically when they reach **1000 lines** — the file is truncated and reused from the start, so disk and RAM stay bounded.

### Stats (every 5 seconds in server terminal)
```
────────────────────────────────────────────────────────────
  ⏱  Uptime:      30s
  👥 Clients:     2 human / 50 load / 52 ever
  📨 Messages:    3012 total  |  99.4 msg/s now  |  100.4 msg/s avg
  📊 Throughput:  0.68 KB/s now  |  0.68 KB/s avg
  📦 Bytes in:    20,481
  📝 Log lines:   server.log 312/1000  |  chat.log 4/1000
────────────────────────────────────────────────────────────
```

---

## Stress Testing

### `stress_test.sh` usage
```bash
./stress_test.sh <port> <num_clients> <msg_rate> [max_msgs]
```

| Argument | Description |
|----------|-------------|
| `port` | Server port (5000) |
| `num_clients` | Number of bots to spawn |
| `msg_rate` | Messages per second per bot |
| `max_msgs` | *(optional)* Stop each bot after this many messages. Omit for unlimited. |

### Examples
```bash
./stress_test.sh 5000 50 2          # 50 bots, 2 msg/sec, runs until Ctrl+C
./stress_test.sh 5000 100 1         # 100 bots, 1 msg/sec, runs until Ctrl+C
./stress_test.sh 5000 50 2 100      # 50 bots, 2 msg/sec, stop after 100 msgs each
./stress_test.sh 5000 200 0.5 50    # 200 bots, 0.5 msg/sec, stop after 50 msgs each
```

Press `Ctrl+C` to stop all bots cleanly.

### Running stress test alongside human clients
Since load bots and human clients are in separate broadcast pools, you can run both simultaneously without interference:
```
Terminal 1          Terminal 2                   Terminal 3
──────────          ──────────                   ──────────
./start.sh          ./stress_test.sh 5000 50 2   python3 client.py 5000 alice
```

---

## Architecture
```
┌─────────────────────────────────────┐
│            server.py                │
│         Port: 5000                  │
│                                     │
│  Main thread: accept() loop         │
│    └── spawns Thread per client     │
│                                     │
│  human_clients ◀──▶ human_clients   │  → chat.log + terminal
│  load_clients  ◀──▶ load_clients    │  → server.log only
│                                     │
│  clients_lock: protects shared list │
│  Stats: every 5s to terminal        │
│  Logs:  rotate at 1000 lines        │
└──────────────┬──────────────────────┘
               │ TCP/IP  port 5000
       ┌───────┼──────────────────────┐
       │       │                      │
  ┌─────────┐  │            ┌─────────────────────┐
  │ alice   │  │            │  load_test.py × N   │
  │ bob     │  │            │  (stress_test.sh)   │
  │(client) │  │            └─────────────────────┘
  └─────────┘  │
          ┌─────────┐
          │ irakli  │
          │(client) │
          └─────────┘
```

---

## Key Concepts Demonstrated

- **TCP Sockets** — reliable, ordered, stream-oriented connections
- **threading** — one OS thread per client, handling hundreds of concurrent connections
- **Lock** — protects shared client list from race conditions between threads
- **Broadcast pools** — routing messages only to the relevant set of recipients
- **Log rotation** — bounding file size without external tools
- **Process-per-client load testing** — RAM-efficient stress testing using separate OS processes

---

## Threading vs asyncio

This lab uses **threading** — one OS thread per client. The Week 1 lab used **asyncio** — a single event loop. Both solve the same multi-client problem differently:

| | Threading (this lab) | asyncio (Week 1) |
|---|---|---|
| Concurrency model | OS threads | Event loop |
| Code style | Blocking calls | `async/await` |
| Shared state | `Lock` required | Single thread, no locks needed |
| Best for | Simpler to reason about | Thousands of clients |

---

## Troubleshooting

**"Connection refused"**
Server isn't running. Start it first: `./start.sh`

**"Address already in use"**
Port 5000 is taken. Find and kill the process:
```bash
lsof -i :5000
kill <PID>
```
Or run on a different port: `python3 server.py 9999`

**"I see load bot messages in my client terminal"**
Make sure bot names start with `load_client_`. Any other name is treated as human.

**"No messages received between human clients"**
The server only broadcasts to *other* clients — you won't see your own messages echoed back. Make sure at least two human clients are connected.

---

## Requirements

- Python 3.7+
- Standard library only (`socket`, `threading`, `time`, `datetime`, `os`)
- Bash (for `start.sh` and `stress_test.sh`)
- Linux / macOS
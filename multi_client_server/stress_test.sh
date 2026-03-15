#!/bin/bash
# Stress test launcher.
# Usage: ./stress_test.sh <port> <num_clients> <msg_rate> [max_msgs]

if [ $# -lt 3 ]; then
    echo "Usage: ./stress_test.sh <port> <num_clients> <msg_rate> [max_msgs]"
    echo ""
    echo "Examples:"
    echo "  ./stress_test.sh 5000 50 2        # 50 clients, 2 msg/sec, unlimited"
    echo "  ./stress_test.sh 5000 50 2 100    # 50 clients, 2 msg/sec, stop after 100 msgs each"
    exit 1
fi

PORT=$1
NUM_CLIENTS=$2
MSG_RATE=$3
MAX_MSGS=${4:-0}

CLIENT_PIDS=()
TOTAL_RATE=$(python3 -c "print(int($NUM_CLIENTS * $MSG_RATE))")

if [ "$MAX_MSGS" -gt 0 ]; then
    LIMIT_STR="$MAX_MSGS msgs/client then stop"
else
    LIMIT_STR="unlimited (Ctrl+C to stop)"
fi

echo "🚀 Stress test started"
echo "   Port:       $PORT"
echo "   Clients:    $NUM_CLIENTS"
echo "   Rate:       $MSG_RATE msg/sec per client (~${TOTAL_RATE} msg/sec total)"
echo "   Limit:      $LIMIT_STR"
echo "   Logs:       server.log"
echo ""

for i in $(seq 1 "$NUM_CLIENTS"); do
    python3 load_test.py "$PORT" "$i" "$MSG_RATE" "$MAX_MSGS" < /dev/null > /dev/null 2>&1 &
    CLIENT_PIDS+=($!)
done

echo "✓ All $NUM_CLIENTS clients launched. Waiting..."

cleanup() {
    echo ""
    echo "Stopping all clients..."
    kill "${CLIENT_PIDS[@]}" 2>/dev/null
    wait "${CLIENT_PIDS[@]}" 2>/dev/null
    echo "✓ Done."
    exit 0
}

trap cleanup INT TERM

wait "${CLIENT_PIDS[@]}"
if [ "$MAX_MSGS" -gt 0 ]; then
    echo "✓ All clients finished ($MAX_MSGS messages each)."
fi
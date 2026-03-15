#!/bin/bash
echo "Connect a client:  python3 client.py 5000 <username>"
echo "Run a load test:   ./stress_test.sh 5000 <num_clients> <msg_rate>"
echo "Press Ctrl+C to stop."
echo ""
python3 -u server.py
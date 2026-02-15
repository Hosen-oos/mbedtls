#!/bin/bash
# Quick test script that works without compiling mbedtls
# Uses Python SSL library for demonstration

set -e

OUTPUT_DIR="tls_capture_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTPUT_DIR"

echo "=========================================="
echo "TLS Message Capture Test (Python SSL)"
echo "=========================================="
echo "Output directory: $OUTPUT_DIR"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found"
    exit 1
fi

# Start Python proxy
echo "Starting TLS capture proxy..."
echo "Proxy will listen on port 8443 and forward to port 4433"
echo ""

python3 capture_tls_python.py 8443 4433 > "$OUTPUT_DIR/proxy.log" 2>&1 &
PROXY_PID=$!
sleep 2

# Check if proxy started
if ! kill -0 $PROXY_PID 2>/dev/null; then
    echo "Error: Proxy failed to start"
    exit 1
fi

echo "Proxy started (PID: $PROXY_PID)"
echo ""
echo "Now you can:"
echo "1. Start a TLS server on port 4433 (in another terminal)"
echo "2. Connect a TLS client to localhost:8443"
echo ""
echo "Or use openssl to test:"
echo "  openssl s_client -connect localhost:8443 -showcerts"
echo ""
echo "Press Ctrl+C to stop the proxy and save messages..."
echo ""

# Wait for user interrupt
trap "kill $PROXY_PID 2>/dev/null; exit" INT TERM

wait $PROXY_PID

# Move captured file
if [ -f "tls_all_messages.txt" ]; then
    mv tls_all_messages.txt "$OUTPUT_DIR/"
    echo ""
    echo "Messages saved to: $OUTPUT_DIR/tls_all_messages.txt"
fi

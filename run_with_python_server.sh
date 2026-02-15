#!/bin/bash
# Run TLS capture with Python TLS server
# This doesn't require building mbedtls

set -e

OUTPUT_DIR="tls_capture_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTPUT_DIR"

echo "=========================================="
echo "TLS Message Capture (Python Server)"
echo "=========================================="
echo "Output directory: $OUTPUT_DIR"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found"
    exit 1
fi

# Generate a simple self-signed certificate for testing
if [ ! -f "server.crt" ] || [ ! -f "server.key" ]; then
    echo "Generating self-signed certificate for testing..."
    openssl req -x509 -newkey rsa:2048 -keyout server.key -out server.crt \
        -days 365 -nodes -subj "/CN=localhost" 2>/dev/null || {
        echo "Warning: openssl not found. Server may not work properly."
        echo "You can install openssl or use a pre-built TLS server."
    }
fi

# Start Python proxy in background
echo "Starting TLS capture proxy on port 8443..."
python3 capture_tls_python.py 8443 4433 > "$OUTPUT_DIR/proxy.log" 2>&1 &
PROXY_PID=$!
sleep 2

# Start Python TLS server
echo "Starting Python TLS server on port 4433..."
python3 simple_tls_server.py 4433 > "$OUTPUT_DIR/server.log" 2>&1 &
SERVER_PID=$!
sleep 2

# Try to connect with openssl client (if available)
if command -v openssl &> /dev/null; then
    echo "Running TLS client (openssl)..."
    echo "GET / HTTP/1.0\r\n\r\n" | \
        openssl s_client -connect localhost:8443 -verify_return_error \
        -CAfile server.crt 2>&1 | head -50 > "$OUTPUT_DIR/client.log" || true
else
    echo "openssl not found. You can manually connect to localhost:8443"
    echo "For example, using:"
    echo "  openssl s_client -connect localhost:8443"
    echo ""
    echo "Press Enter when done testing..."
    read
fi

sleep 1

# Cleanup
echo "Stopping servers..."
kill $SERVER_PID 2>/dev/null || true
kill $PROXY_PID 2>/dev/null || true
wait $SERVER_PID 2>/dev/null || true
wait $PROXY_PID 2>/dev/null || true

# Move captured file
if [ -f "tls_all_messages.txt" ]; then
    mv tls_all_messages.txt "$OUTPUT_DIR/"
fi

echo ""
echo "=========================================="
echo "Capture complete!"
echo "=========================================="
echo "Files saved in: $OUTPUT_DIR"
ls -lh "$OUTPUT_DIR" | tail -n +2
echo ""
if [ -f "$OUTPUT_DIR/tls_all_messages.txt" ]; then
    echo "Main capture file: $OUTPUT_DIR/tls_all_messages.txt"
    echo ""
    echo "First few messages:"
    head -100 "$OUTPUT_DIR/tls_all_messages.txt"
fi

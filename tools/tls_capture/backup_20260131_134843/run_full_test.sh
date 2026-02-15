#!/bin/bash
# Complete TLS test with message capture
# Uses openssl and Python proxy - no compilation needed

set -e

OUTPUT_DIR="tls_capture_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTPUT_DIR"
cd "$OUTPUT_DIR"

echo "=========================================="
echo "Complete TLS Message Capture Test"
echo "=========================================="
echo "Output directory: $(pwd)"
echo ""

# Check dependencies
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found"
    exit 1
fi

if ! command -v openssl &> /dev/null; then
    echo "Error: openssl not found"
    exit 1
fi

# Create self-signed certificate
echo "1. Creating self-signed certificate..."
openssl req -x509 -newkey rsa:2048 -keyout server.key -out server.crt \
    -days 365 -nodes -subj "/CN=localhost" \
    -addext "subjectAltName=DNS:localhost" 2>&1 | grep -v "^Generating" || true
echo "   Certificate created: server.crt, server.key"
echo ""

# Clean up any existing processes on these ports
echo "2. Cleaning up any existing processes..."
lsof -ti:8443 | xargs kill -9 2>/dev/null || true
lsof -ti:4433 | xargs kill -9 2>/dev/null || true
sleep 1

# Start Python proxy
echo "3. Starting TLS capture proxy on port 8443..."
cd ..
python3 capture_tls_python.py 8443 4433 > "$OUTPUT_DIR/proxy.log" 2>&1 &
PROXY_PID=$!
sleep 3

if ! kill -0 $PROXY_PID 2>/dev/null; then
    echo "Error: Proxy failed to start"
    echo "Check proxy.log for details:"
    tail -20 "$OUTPUT_DIR/proxy.log" || true
    exit 1
fi
echo "   Proxy started (PID: $PROXY_PID)"
echo ""

# Start openssl server
echo "4. Starting OpenSSL TLS server on port 4433..."
cd "$OUTPUT_DIR"
openssl s_server -accept 4433 -cert server.crt -key server.key \
    -www -quiet > server.log 2>&1 &
SERVER_PID=$!
sleep 2

if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo "Error: Server failed to start"
    kill $PROXY_PID 2>/dev/null
    exit 1
fi
echo "   Server started (PID: $SERVER_PID)"
echo ""

# Run client through proxy
echo "5. Running TLS client through proxy..."
echo "   Client connecting to localhost:8443..."
cd ..
(echo "GET / HTTP/1.0"; echo ""; sleep 1) | \
    openssl s_client -connect localhost:8443 -quiet \
    -showcerts 2>&1 | head -50 > "$OUTPUT_DIR/client.log" || true
echo "   Client connection completed"
echo ""

# Wait a bit for all messages
sleep 2

# Cleanup
echo "6. Stopping services..."
kill $SERVER_PID 2>/dev/null || true
kill $PROXY_PID 2>/dev/null || true
wait $SERVER_PID 2>/dev/null || true
wait $PROXY_PID 2>/dev/null || true
sleep 1

# Move captured file
if [ -f "tls_all_messages.txt" ]; then
    mv tls_all_messages.txt "$OUTPUT_DIR/"
fi

echo ""
echo "=========================================="
echo "Test Complete!"
echo "=========================================="
echo "All files saved in: $OUTPUT_DIR"
echo ""
echo "Files:"
ls -lh "$OUTPUT_DIR" | tail -n +2
echo ""

if [ -f "$OUTPUT_DIR/tls_all_messages.txt" ]; then
    MSG_COUNT=$(grep -c "^Message #" "$OUTPUT_DIR/tls_all_messages.txt" || echo "0")
    echo "Captured $MSG_COUNT TLS messages"
    echo ""
    echo "To view messages:"
    echo "  cat $OUTPUT_DIR/tls_all_messages.txt"
    echo ""
    echo "Message types captured:"
    grep "HandshakeType:" "$OUTPUT_DIR/tls_all_messages.txt" | sort -u || echo "  (check file for details)"
fi

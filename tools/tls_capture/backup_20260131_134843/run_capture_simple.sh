#!/bin/bash
# Simple TLS Capture Script using Python proxy
# This script runs a TLS handshake and captures all messages

set -e

OUTPUT_DIR="tls_capture_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTPUT_DIR"

echo "=========================================="
echo "TLS Message Capture (Python Proxy Method)"
echo "=========================================="
echo "Output directory: $OUTPUT_DIR"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found"
    exit 1
fi

# Check if we need to build programs first
if [ ! -f "programs/ssl/ssl_server" ]; then
    echo "Note: ssl_server not found. You may need to build mbedtls first."
    echo "This script will try to use the Python proxy method."
    echo ""
fi

# Start Python proxy in background
echo "Starting TLS capture proxy on port 8443..."
python3 capture_tls_python.py 8443 4433 > "$OUTPUT_DIR/proxy.log" 2>&1 &
PROXY_PID=$!
sleep 2

# Start server (if available)
if [ -f "programs/ssl/ssl_server" ]; then
    echo "Starting mbedtls TLS server on port 4433..."
    programs/ssl/ssl_server > "$OUTPUT_DIR/server.log" 2>&1 &
    SERVER_PID=$!
    sleep 2
    
    # Run client through proxy
    echo "Running TLS client through proxy (port 8443)..."
    if [ -f "programs/ssl/ssl_client1" ]; then
        # Modify client to connect to proxy port
        SERVER_NAME=localhost SERVER_PORT=8443 programs/ssl/ssl_client1 > "$OUTPUT_DIR/client.log" 2>&1 || true
    else
        echo "Client not found. You can manually connect to localhost:8443"
        echo "Press Enter when done..."
        read
    fi
    
    sleep 1
    kill $SERVER_PID 2>/dev/null || true
else
    # Try to use Python server or openssl s_server
    echo "mbedtls server not found. Trying alternative methods..."
    
    # Method 1: Try Python server
    if [ -f "simple_tls_server.py" ]; then
        # Generate certificate if needed
        if [ ! -f "server.crt" ] || [ ! -f "server.key" ]; then
            echo "Generating self-signed certificate..."
            openssl req -x509 -newkey rsa:2048 -keyout server.key -out server.crt \
                -days 365 -nodes -subj "/CN=localhost" 2>/dev/null || {
                echo "Failed to generate certificate"
            }
        fi
        
        echo "Starting Python TLS server on port 4433..."
        python3 simple_tls_server.py 4433 > "$OUTPUT_DIR/server.log" 2>&1 &
        SERVER_PID=$!
        sleep 2
        
        # Use openssl as client
        if command -v openssl &> /dev/null; then
            echo "Running openssl client through proxy (port 8443)..."
            echo -e "GET / HTTP/1.0\r\n\r\n" | \
                openssl s_client -connect localhost:8443 -quiet \
                -verify_return_error 2>&1 | head -20 > "$OUTPUT_DIR/client.log" || true
        else
            echo "openssl not found. Please connect manually to localhost:8443"
            echo "Press Enter when done..."
            read
        fi
        
        sleep 1
        kill $SERVER_PID 2>/dev/null || true
    # Method 2: Try openssl s_server
    elif command -v openssl &> /dev/null; then
        # Generate certificate if needed
        if [ ! -f "server.crt" ] || [ ! -f "server.key" ]; then
            echo "Generating self-signed certificate..."
            openssl req -x509 -newkey rsa:2048 -keyout server.key -out server.crt \
                -days 365 -nodes -subj "/CN=localhost" 2>/dev/null
        fi
        
        echo "Starting openssl s_server on port 4433..."
        openssl s_server -accept 4433 -cert server.crt -key server.key \
            -www > "$OUTPUT_DIR/server.log" 2>&1 &
        SERVER_PID=$!
        sleep 2
        
        echo "Running openssl client through proxy (port 8443)..."
        echo -e "GET / HTTP/1.0\r\n\r\n" | \
            openssl s_client -connect localhost:8443 -quiet \
            -verify_return_error 2>&1 | head -20 > "$OUTPUT_DIR/client.log" || true
        
        sleep 1
        kill $SERVER_PID 2>/dev/null || true
    else
        echo "No server available. Please start your TLS server on port 4433 manually"
        echo "Then connect your client to localhost:8443"
        echo "Press Ctrl+C when done..."
        wait $PROXY_PID
    fi
fi

# Stop proxy
kill $PROXY_PID 2>/dev/null || true
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
echo "Main capture file: $OUTPUT_DIR/tls_all_messages.txt"

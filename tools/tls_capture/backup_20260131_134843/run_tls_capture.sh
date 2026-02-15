#!/bin/bash
# TLS Message Capture Script
# This script runs a TLS handshake and captures all messages

set -e

PORT=4433
CAPTURE_DIR="tls_capture_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$CAPTURE_DIR"

echo "=========================================="
echo "TLS Message Capture Tool"
echo "=========================================="
echo "Capture directory: $CAPTURE_DIR"
echo ""

# Check if tcpdump is available
if command -v tcpdump &> /dev/null; then
    echo "Starting tcpdump to capture network traffic..."
    sudo tcpdump -i lo -w "$CAPTURE_DIR/tls_traffic.pcap" port $PORT &
    TCPDUMP_PID=$!
    sleep 1
    USE_TCPDUMP=1
else
    echo "tcpdump not found, will use program-level capture only"
    USE_TCPDUMP=0
fi

# Build the capture tool if needed
if [ ! -f "capture_tls_server" ]; then
    echo "Building capture tools..."
    gcc -o capture_tls_server capture_tls_messages.c \
        -I./include -I./library \
        -L./library -lmbedtls -lmbedx509 -lmbedcrypto \
        -lpthread -ldl 2>&1 | tee "$CAPTURE_DIR/build.log" || {
        echo "Build failed, trying with existing programs..."
        USE_EXISTING=1
    }
fi

if [ "$USE_EXISTING" != "1" ]; then
    # Run the capture server in background
    echo "Starting TLS server..."
    ./capture_tls_server > "$CAPTURE_DIR/server.log" 2>&1 &
    SERVER_PID=$!
    sleep 2
    
    # Run client
    echo "Starting TLS client..."
    if [ -f "programs/ssl/ssl_client1" ]; then
        programs/ssl/ssl_client1 > "$CAPTURE_DIR/client.log" 2>&1 || true
    elif [ -f "programs/ssl/ssl_client2" ]; then
        echo "localhost" | programs/ssl/ssl_client2 > "$CAPTURE_DIR/client.log" 2>&1 || true
    else
        echo "Client program not found, please build programs first"
    fi
    
    # Wait a bit
    sleep 2
    
    # Kill server
    kill $SERVER_PID 2>/dev/null || true
    wait $SERVER_PID 2>/dev/null || true
else
    # Use existing programs
    echo "Using existing ssl_server2 and ssl_client1..."
    
    # Start server
    programs/ssl/ssl_server2 > "$CAPTURE_DIR/server.log" 2>&1 &
    SERVER_PID=$!
    sleep 2
    
    # Run client
    programs/ssl/ssl_client1 > "$CAPTURE_DIR/client.log" 2>&1 || true
    
    sleep 1
    kill $SERVER_PID 2>/dev/null || true
    wait $SERVER_PID 2>/dev/null || true
fi

# Stop tcpdump
if [ "$USE_TCPDUMP" = "1" ]; then
    echo "Stopping tcpdump..."
    sudo kill $TCPDUMP_PID 2>/dev/null || true
    wait $TCPDUMP_PID 2>/dev/null || true
    sleep 1
    
    # Convert pcap to text if tshark is available
    if command -v tshark &> /dev/null; then
        echo "Converting pcap to text format..."
        tshark -r "$CAPTURE_DIR/tls_traffic.pcap" -V > "$CAPTURE_DIR/tls_traffic.txt" 2>&1 || true
        tshark -r "$CAPTURE_DIR/tls_traffic.pcap" -x > "$CAPTURE_DIR/tls_traffic_hex.txt" 2>&1 || true
    fi
fi

# Collect any message files
if [ -f "tls_client_messages.txt" ]; then
    mv tls_client_messages.txt "$CAPTURE_DIR/"
fi
if [ -f "tls_server_messages.txt" ]; then
    mv tls_server_messages.txt "$CAPTURE_DIR/"
fi
if [ -f "tls_debug.log" ]; then
    mv tls_debug.log "$CAPTURE_DIR/"
fi

echo ""
echo "=========================================="
echo "Capture complete!"
echo "=========================================="
echo "All files saved in: $CAPTURE_DIR"
echo ""
echo "Files:"
ls -lh "$CAPTURE_DIR" | tail -n +2
echo ""
echo "To view pcap file, use:"
echo "  wireshark $CAPTURE_DIR/tls_traffic.pcap"
echo "  or"
echo "  tshark -r $CAPTURE_DIR/tls_traffic.pcap"

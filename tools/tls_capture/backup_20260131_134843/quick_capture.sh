#!/bin/bash
# Quick TLS Message Capture Script
# This script quickly runs a TLS handshake and captures messages

set -e

echo "=========================================="
echo "Quick TLS Message Capture"
echo "=========================================="
echo ""

# Check if programs are built
if [ ! -f "programs/ssl/ssl_server" ] || [ ! -f "programs/ssl/ssl_client1" ]; then
    echo "Programs not built. Building..."
    if [ -f "Makefile" ]; then
        make -j4 programs
    elif [ -f "CMakeLists.txt" ]; then
        mkdir -p build
        cd build
        cmake ..
        make -j4
        cd ..
    else
        echo "Error: Cannot find build system"
        exit 1
    fi
fi

# Create output directory
OUTPUT_DIR="tls_capture_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTPUT_DIR"

echo "Output directory: $OUTPUT_DIR"
echo ""

# Method 1: Try tcpdump if available and has permission
if command -v tcpdump &> /dev/null && [ "$EUID" -eq 0 ]; then
    echo "Method: Using tcpdump (requires root)"
    echo "Starting tcpdump..."
    tcpdump -i lo -w "$OUTPUT_DIR/tls_traffic.pcap" port 4433 &
    TCPDUMP_PID=$!
    sleep 1
    
    # Start server
    echo "Starting server..."
    programs/ssl/ssl_server > "$OUTPUT_DIR/server.log" 2>&1 &
    SERVER_PID=$!
    sleep 2
    
    # Run client
    echo "Running client..."
    programs/ssl/ssl_client1 > "$OUTPUT_DIR/client.log" 2>&1 || true
    
    sleep 1
    
    # Cleanup
    kill $SERVER_PID 2>/dev/null || true
    kill $TCPDUMP_PID 2>/dev/null || true
    wait $TCPDUMP_PID 2>/dev/null || true
    
    # Convert pcap if tshark available
    if command -v tshark &> /dev/null; then
        echo "Converting pcap to text..."
        tshark -r "$OUTPUT_DIR/tls_traffic.pcap" -V > "$OUTPUT_DIR/tls_messages_detailed.txt" 2>&1 || true
        tshark -r "$OUTPUT_DIR/tls_traffic.pcap" -x > "$OUTPUT_DIR/tls_messages_hex.txt" 2>&1 || true
    fi
    
    echo ""
    echo "Capture complete!"
    echo "Files saved in: $OUTPUT_DIR"
    echo "  - tls_traffic.pcap (use wireshark or tshark to view)"
    if [ -f "$OUTPUT_DIR/tls_messages_detailed.txt" ]; then
        echo "  - tls_messages_detailed.txt"
        echo "  - tls_messages_hex.txt"
    fi
    
# Method 2: Use program-level capture
else
    echo "Method: Using program-level capture"
    echo "Note: This captures at application level, not network level"
    echo ""
    
    # Try to build capture tool
    if [ ! -f "capture_client" ]; then
        echo "Building capture tool..."
        if [ -f "Makefile.capture" ]; then
            make -f Makefile.capture capture_client || {
                echo "Build failed, using alternative method..."
                # Fallback: just run server and client with debug
                echo "Starting server with debug..."
                MBEDTLS_DEBUG_LEVEL=4 programs/ssl/ssl_server > "$OUTPUT_DIR/server_debug.log" 2>&1 &
                SERVER_PID=$!
                sleep 2
                
                echo "Running client with debug..."
                MBEDTLS_DEBUG_LEVEL=4 programs/ssl/ssl_client1 > "$OUTPUT_DIR/client_debug.log" 2>&1 || true
                
                sleep 1
                kill $SERVER_PID 2>/dev/null || true
                
                echo ""
                echo "Capture complete (debug logs only)"
                echo "Files saved in: $OUTPUT_DIR"
                echo "  - server_debug.log"
                echo "  - client_debug.log"
                exit 0
            }
        fi
    fi
    
    # Start server
    echo "Starting server..."
    programs/ssl/ssl_server > "$OUTPUT_DIR/server.log" 2>&1 &
    SERVER_PID=$!
    sleep 2
    
    # Run capture client
    if [ -f "capture_client" ]; then
        echo "Running capture client..."
        ./capture_client "$OUTPUT_DIR/tls_all_messages.txt" 2>&1 | tee "$OUTPUT_DIR/capture.log" || true
    else
        echo "Running regular client..."
        programs/ssl/ssl_client1 > "$OUTPUT_DIR/client.log" 2>&1 || true
    fi
    
    sleep 1
    kill $SERVER_PID 2>/dev/null || true
    wait $SERVER_PID 2>/dev/null || true
    
    echo ""
    echo "Capture complete!"
    echo "Files saved in: $OUTPUT_DIR"
    ls -lh "$OUTPUT_DIR" | tail -n +2
fi

echo ""
echo "To view messages, check files in: $OUTPUT_DIR"

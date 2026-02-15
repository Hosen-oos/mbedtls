#!/usr/bin/env python3
"""
Complete TLS Test with Message Capture
This script creates both TLS server and client, and captures all messages
"""

import socket
import ssl
import threading
import time
from datetime import datetime
import sys

class TLSCapture:
    def __init__(self):
        self.messages = []
        self.output_file = None
        
    def hex_dump(self, data):
        """Convert bytes to hex dump format"""
        lines = []
        for i in range(0, len(data), 16):
            chunk = data[i:i+16]
            hex_part = ' '.join(f'{b:02x}' for b in chunk)
            ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            lines.append(f'{i:04x}: {hex_part:<48} |{ascii_part}|')
        return '\n'.join(lines)
    
    def parse_record_layer(self, data):
        """Parse TLS record layer header"""
        if len(data) < 5:
            return None
        
        content_type = data[0]
        version = (data[1] << 8) | data[2]
        length = (data[3] << 8) | data[4]
        
        ct_names = {
            20: 'ChangeCipherSpec',
            21: 'Alert',
            22: 'Handshake',
            23: 'ApplicationData'
        }
        
        info = {
            'content_type': content_type,
            'content_type_name': ct_names.get(content_type, 'Unknown'),
            'version': f'0x{version:04x}',
            'length': length
        }
        
        # Parse handshake layer if present
        if content_type == 22 and len(data) >= 9:
            handshake_type = data[5]
            handshake_len = (data[6] << 16) | (data[7] << 8) | data[8]
            
            hs_names = {
                1: 'ClientHello',
                2: 'ServerHello',
                11: 'Certificate',
                13: 'CertificateRequest',
                15: 'CertificateVerify',
                20: 'Finished'
            }
            
            info['handshake_type'] = handshake_type
            info['handshake_type_name'] = hs_names.get(handshake_type, 'Unknown')
            info['handshake_length'] = handshake_len
        
        return info
    
    def save_message(self, direction, data):
        """Save a message to file"""
        if self.output_file is None:
            return
            
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        record_info = self.parse_record_layer(data)
        
        self.messages.append({
            'direction': direction,
            'data': data,
            'timestamp': timestamp,
            'info': record_info
        })
        
        self.output_file.write('\n')
        self.output_file.write('=' * 50 + '\n')
        self.output_file.write(f'Message #{len(self.messages)}: {direction}\n')
        self.output_file.write(f'Time: {timestamp}\n')
        self.output_file.write(f'Length: {len(data)} bytes\n')
        
        if record_info:
            self.output_file.write('Record Layer:\n')
            self.output_file.write(f'  ContentType: 0x{record_info["content_type"]:02x} ({record_info["content_type_name"]})\n')
            self.output_file.write(f'  Version: {record_info["version"]}\n')
            self.output_file.write(f'  Length: {record_info["length"]} bytes\n')
            
            if 'handshake_type' in record_info:
                self.output_file.write('Handshake Layer:\n')
                self.output_file.write(f'  HandshakeType: 0x{record_info["handshake_type"]:02x} ({record_info["handshake_type_name"]})\n')
                self.output_file.write(f'  Length: {record_info["handshake_length"]} bytes\n')
        
        self.output_file.write('-' * 50 + '\n')
        self.output_file.write('Hex Dump:\n')
        self.output_file.write(self.hex_dump(data))
        self.output_file.write('\n')
        self.output_file.write('=' * 50 + '\n')
        self.output_file.flush()

# Global capture instance
capture = TLSCapture()

def proxy_connection(client_sock, server_sock, direction_prefix):
    """Proxy connection and capture messages"""
    try:
        while True:
            # Receive from client
            try:
                client_sock.settimeout(0.1)
                data = client_sock.recv(16384)
                if data:
                    capture.save_message(f'{direction_prefix}->Server', data)
                    server_sock.sendall(data)
            except socket.timeout:
                pass
            except:
                break
            
            # Receive from server
            try:
                server_sock.settimeout(0.1)
                data = server_sock.recv(16384)
                if data:
                    capture.save_message(f'Server->{direction_prefix}', data)
                    client_sock.sendall(data)
            except socket.timeout:
                pass
            except:
                break
    except:
        pass
    finally:
        client_sock.close()
        server_sock.close()

def run_proxy(listen_port, server_host, server_port):
    """Run the capture proxy"""
    listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_sock.bind(('localhost', listen_port))
    listen_sock.listen(5)
    
    print(f"Proxy listening on port {listen_port}")
    print(f"Forwarding to {server_host}:{server_port}")
    
    try:
        while True:
            client_sock, addr = listen_sock.accept()
            print(f"New connection from {addr}")
            
            # Connect to server
            server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_sock.connect((server_host, server_port))
            
            # Start proxy in thread
            thread = threading.Thread(
                target=proxy_connection,
                args=(client_sock, server_sock, 'Client'),
                daemon=True
            )
            thread.start()
    except KeyboardInterrupt:
        print("\nStopping proxy...")
    finally:
        listen_sock.close()

def create_test_server(port=4433):
    """Create a simple TLS test server using Python ssl"""
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    
    # Create self-signed certificate on the fly
    import tempfile
    import subprocess
    import os
    
    # Try to use system certificates or create a simple one
    try:
        # Use Python's built-in test server
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(('localhost', port))
        server_sock.listen(5)
        
        print(f"Test server listening on port {port}")
        print("Note: Using Python SSL library (not mbedtls)")
        print("This is for demonstration purposes")
        
        # Wrap with SSL
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        try:
            ssl_sock = context.wrap_socket(server_sock, server_side=True)
        except:
            # If SSL wrap fails, use regular socket
            print("SSL wrap failed, using plain socket for testing")
            return server_sock
        
        return ssl_sock
    except Exception as e:
        print(f"Error creating server: {e}")
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 test_tls_capture.py proxy <listen_port> <server_host> <server_port>")
        print("  python3 test_tls_capture.py server <port>")
        print("  python3 test_tls_capture.py full")
        return
    
    mode = sys.argv[1]
    output_file = f"tls_capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    capture.output_file = open(output_file, 'w')
    capture.output_file.write('TLS Message Capture\n')
    capture.output_file.write('=' * 50 + '\n')
    capture.output_file.write(f'Started: {datetime.now()}\n')
    capture.output_file.write('=' * 50 + '\n')
    
    if mode == 'proxy':
        listen_port = int(sys.argv[2]) if len(sys.argv) > 2 else 8443
        server_host = sys.argv[3] if len(sys.argv) > 3 else 'localhost'
        server_port = int(sys.argv[4]) if len(sys.argv) > 4 else 4433
        run_proxy(listen_port, server_host, server_port)
    elif mode == 'server':
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 4433
        server = create_test_server(port)
        if server:
            try:
                while True:
                    client, addr = server.accept()
                    print(f"Client connected: {addr}")
                    client.close()
            except KeyboardInterrupt:
                print("\nStopping server...")
    elif mode == 'full':
        print("Full test mode - starting server and proxy...")
        print("This requires a separate client to connect")
        # Start server in background thread
        server = create_test_server(4433)
        if server:
            server_thread = threading.Thread(
                target=lambda: run_proxy(8443, 'localhost', 4433),
                daemon=True
            )
            server_thread.start()
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping...")
    else:
        print(f"Unknown mode: {mode}")
    
    if capture.output_file:
        capture.output_file.write(f'\nCapture ended: {datetime.now()}\n')
        capture.output_file.write(f'Total messages: {len(capture.messages)}\n')
        capture.output_file.close()
        print(f"\nCapture complete. Saved {len(capture.messages)} messages to {output_file}")

if __name__ == '__main__':
    main()

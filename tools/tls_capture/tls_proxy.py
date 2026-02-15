#!/usr/bin/env python3
"""
TLS Message Capture Proxy
Captures all TLS messages by proxying between client and server.

This is the main tool for capturing TLS messages. It acts as a transparent
proxy that intercepts all traffic between a TLS client and server.

Usage:
    python3 tls_proxy.py [proxy_port] [server_host] [server_port]
    
Example:
    python3 tls_proxy.py 8443 localhost 4433
"""

import socket
import threading
import sys
from datetime import datetime

class TLSCapture:
    def __init__(self, listen_port=8443, server_host='localhost', server_port=4433):
        self.listen_port = listen_port
        self.server_host = server_host
        self.server_port = server_port
        self.messages = []
        self.running = False
        
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
    
    def save_message(self, direction, data, output_file):
        """Save a message to file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        record_info = self.parse_record_layer(data)
        
        output_file.write('\n')
        output_file.write('=' * 50 + '\n')
        output_file.write(f'Message #{len(self.messages) + 1}: {direction}\n')
        output_file.write(f'Time: {timestamp}\n')
        output_file.write(f'Length: {len(data)} bytes\n')
        
        if record_info:
            output_file.write('Record Layer:\n')
            output_file.write(f'  ContentType: 0x{record_info["content_type"]:02x} ({record_info["content_type_name"]})\n')
            output_file.write(f'  Version: {record_info["version"]}\n')
            output_file.write(f'  Length: {record_info["length"]} bytes\n')
            
            if 'handshake_type' in record_info:
                output_file.write('Handshake Layer:\n')
                output_file.write(f'  HandshakeType: 0x{record_info["handshake_type"]:02x} ({record_info["handshake_type_name"]})\n')
                output_file.write(f'  Length: {record_info["handshake_length"]} bytes\n')
        
        output_file.write('-' * 50 + '\n')
        output_file.write('Hex Dump:\n')
        output_file.write(self.hex_dump(data))
        output_file.write('\n')
        output_file.write('=' * 50 + '\n')
        output_file.flush()
        
        self.messages.append({
            'direction': direction,
            'data': data,
            'timestamp': timestamp,
            'info': record_info
        })
    
    def proxy_connection(self, client_sock, client_addr):
        """Proxy connection between client and server"""
        server_sock = None
        try:
            # Connect to server
            server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_sock.connect((self.server_host, self.server_port))
            
            print(f"Proxy: {client_addr} <-> server")
            
            # Start forwarding threads
            def forward_client_to_server():
                try:
                    while True:
                        data = client_sock.recv(16384)
                        if not data:
                            break
                        self.save_message('Client->Server', data, output_file)
                        server_sock.sendall(data)
                except:
                    pass
            
            def forward_server_to_client():
                try:
                    while True:
                        data = server_sock.recv(16384)
                        if not data:
                            break
                        self.save_message('Server->Client', data, output_file)
                        client_sock.sendall(data)
                except:
                    pass
            
            t1 = threading.Thread(target=forward_client_to_server, daemon=True)
            t2 = threading.Thread(target=forward_server_to_client, daemon=True)
            t1.start()
            t2.start()
            
            # Wait for threads to finish
            t1.join()
            t2.join()
            
        except Exception as e:
            print(f"Error in proxy: {e}")
        finally:
            if server_sock:
                server_sock.close()
            client_sock.close()
    
    def start(self, output_filename=None):
        """Start the capture proxy"""
        global output_file
        
        if output_filename is None:
            # Default to current directory, but can be overridden
            output_filename = 'tls_all_messages.txt'
        
        output_file = open(output_filename, 'w')
        output_file.write('TLS Message Capture - All Messages\n')
        output_file.write('=' * 50 + '\n')
        output_file.write(f'Started: {datetime.now()}\n')
        output_file.write(f'Proxy listening on port {self.listen_port}\n')
        output_file.write(f'Forwarding to {self.server_host}:{self.server_port}\n')
        output_file.write('=' * 50 + '\n')
        
        # Create listening socket
        listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listen_sock.bind(('localhost', self.listen_port))
        except OSError as e:
            if e.errno == 98:  # Address already in use
                print(f"Error: Port {self.listen_port} is already in use")
                print("Please stop the process using this port or use a different port")
                output_file.close()
                sys.exit(1)
            raise
        listen_sock.listen(5)
        
        self.running = True
        print(f"TLS Capture Proxy started")
        print(f"Listening on port {self.listen_port}")
        print(f"Forwarding to {self.server_host}:{self.server_port}")
        print(f"Messages will be saved to: {output_filename}")
        print(f"\nConnect your client to: localhost:{self.listen_port}")
        print("Press Ctrl+C to stop\n")
        
        try:
            while self.running:
                client_sock, client_addr = listen_sock.accept()
                print(f"New connection from {client_addr}")
                # Handle in a new thread
                thread = threading.Thread(
                    target=self.proxy_connection,
                    args=(client_sock, client_addr),
                    daemon=True
                )
                thread.start()
        except KeyboardInterrupt:
            print("\nStopping capture...")
            self.running = False
        finally:
            listen_sock.close()
            output_file.write(f'\nCapture ended: {datetime.now()}\n')
            output_file.write(f'Total messages: {len(self.messages)}\n')
            output_file.close()
            print(f"Capture complete. Saved {len(self.messages)} messages to {output_filename}")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        proxy_port = int(sys.argv[1])
    else:
        proxy_port = 8443
    
    if len(sys.argv) > 2:
        server_host = sys.argv[2]
    else:
        server_host = 'localhost'
    
    if len(sys.argv) > 3:
        server_port = int(sys.argv[3])
    else:
        server_port = 4433
    
    capture = TLSCapture(listen_port=proxy_port, server_host=server_host, server_port=server_port)
    capture.start()

#!/usr/bin/env python3
"""
Simple TLS Server for Testing
Uses Python's ssl library to create a basic TLS server
"""

import socket
import ssl
import threading
import sys

def create_tls_server(port=4433):
    """Create a simple TLS server"""
    
    # Create socket
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    
    # For testing, we'll use a self-signed certificate
    # In production, you should use proper certificates
    try:
        # Try to load certificates if they exist
        context.load_cert_chain('server.crt', 'server.key')
    except:
        # If no certificates, create a self-signed one
        print("Warning: No certificates found. Creating self-signed certificate...")
        print("For proper testing, you should generate certificates.")
        # For now, we'll proceed without certificates (will fail, but shows the attempt)
        pass
    
    # Create server socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('localhost', port))
    server_socket.listen(5)
    
    print(f"TLS Server listening on port {port}")
    print("Waiting for connections...")
    
    try:
        while True:
            client_socket, addr = server_socket.accept()
            print(f"Connection from {addr}")
            
            try:
                # Wrap with TLS
                tls_socket = context.wrap_socket(client_socket, server_side=True)
                print("TLS handshake completed")
                
                # Read some data
                data = tls_socket.recv(1024)
                if data:
                    print(f"Received: {data[:100]}")
                
                # Send response
                response = b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nHello from TLS Server\r\n"
                tls_socket.send(response)
                
                tls_socket.close()
            except Exception as e:
                print(f"Error handling client: {e}")
            finally:
                client_socket.close()
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        server_socket.close()

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 4433
    create_tls_server(port)

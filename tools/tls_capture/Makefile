# Makefile for TLS capture tools (C language)

CC = gcc
CFLAGS = -Wall -Wextra -O2 -g
INCLUDES = -I../../include -I../../library -I../../tests/include
LIBS = -L../../library -lmbedtls -lmbedx509 -lmbedcrypto -lpthread -ldl
SRCDIR = .

# Check if libraries exist
LIBDIR = ../../library
ifeq ($(wildcard $(LIBDIR)/libmbedtls.a),)
    # Try shared libraries
    LIBS = -lmbedtls -lmbedx509 -lmbedcrypto -lpthread -ldl
endif

all: capture_client

capture_client: capture_client.c
	@echo "Building capture_client..."
	@echo "Note: This requires mbedtls to be built first"
	$(CC) $(CFLAGS) $(INCLUDES) -o capture_client capture_client.c $(LIBS)
	@echo "Build complete: ./capture_client"

clean:
	rm -f capture_client
	rm -f *.log *.txt *.pcap

.PHONY: all clean

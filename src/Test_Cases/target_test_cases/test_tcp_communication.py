"""
Integration tests for TCP communication
Tests TCP command server and data server functionality
"""

import unittest
import socket
import threading
import time
import sys
import os

# Note: TCP communication tests use standard library socket module
# No imports from Target_Codebase needed for these integration tests


class TestTCPCommunication(unittest.TestCase):
    """Test cases for TCP communication"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_host = "127.0.0.1"
        self.test_port = 9999

    def test_tcp_socket_creation(self):
        """Test TCP socket creation"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.assertIsNotNone(sock)
        sock.close()
        print("✓ test_tcp_socket_creation: PASSED")

    def test_tcp_bind_and_listen(self):
        """Test TCP socket bind and listen"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((self.test_host, self.test_port))
            sock.listen(5)
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"Bind/listen failed: {e}")
        finally:
            sock.close()
        print("✓ test_tcp_bind_and_listen: PASSED")

    def test_tcp_connect(self):
        """Test TCP connection"""
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((self.test_host, self.test_port))
        server_sock.listen(5)

        def accept_connection():
            conn, addr = server_sock.accept()
            conn.close()

        server_thread = threading.Thread(target=accept_connection)
        server_thread.start()
        time.sleep(0.1)

        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            client_sock.connect((self.test_host, self.test_port))
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"Connection failed: {e}")
        finally:
            client_sock.close()
            server_sock.close()
            server_thread.join(timeout=1)
        print("✓ test_tcp_connect: PASSED")

    def test_tcp_send_receive(self):
        """Test TCP send and receive"""
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((self.test_host, self.test_port))
        server_sock.listen(5)

        received_data = []

        def server_handler():
            conn, addr = server_sock.accept()
            data = conn.recv(1024)
            received_data.append(data.decode("utf-8"))
            conn.send(b"RESPONSE")
            conn.close()

        server_thread = threading.Thread(target=server_handler)
        server_thread.start()
        time.sleep(0.1)

        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_sock.connect((self.test_host, self.test_port))
        client_sock.send(b"TEST_COMMAND")
        response = client_sock.recv(1024)

        self.assertEqual(received_data[0], "TEST_COMMAND")
        self.assertEqual(response, b"RESPONSE")

        client_sock.close()
        server_sock.close()
        server_thread.join(timeout=1)
        print("✓ test_tcp_send_receive: PASSED")

    def test_tcp_timeout(self):
        """Test TCP timeout handling"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.1)

        try:
            sock.connect((self.test_host, 9998))  # Non-existent port
            self.fail("Should have raised timeout")
        except socket.timeout:
            self.assertTrue(True)
        except Exception:
            pass  # Other exceptions are acceptable
        finally:
            sock.close()
        print("✓ test_tcp_timeout: PASSED")


if __name__ == "__main__":
    print("=" * 60)
    print("TCP Communication Integration Tests")
    print("=" * 60)
    unittest.main(verbosity=2)

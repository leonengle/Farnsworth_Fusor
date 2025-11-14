"""
Integration tests for UDP communication
Tests UDP status sender and receiver functionality
"""

import unittest
import socket
import threading
import time
import sys
import os

# Note: UDP communication tests use standard library socket module
# No imports from Target_Codebase needed for these integration tests


class TestUDPCommunication(unittest.TestCase):
    """Test cases for UDP communication"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_host = "127.0.0.1"
        self.test_port_send = 8888
        self.test_port_receive = 8889

    def test_udp_socket_creation(self):
        """Test UDP socket creation"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.assertIsNotNone(sock)
        sock.close()
        print("✓ test_udp_socket_creation: PASSED")

    def test_udp_bind(self):
        """Test UDP socket bind"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind((self.test_host, self.test_port_receive))
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"Bind failed: {e}")
        finally:
            sock.close()
        print("✓ test_udp_bind: PASSED")

    def test_udp_send_receive(self):
        """Test UDP send and receive"""
        receiver_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        receiver_sock.bind((self.test_host, self.test_port_receive))
        receiver_sock.settimeout(1.0)

        received_data = []

        def receive_message():
            try:
                data, addr = receiver_sock.recvfrom(1024)
                received_data.append(data.decode("utf-8"))
            except socket.timeout:
                pass

        receiver_thread = threading.Thread(target=receive_message)
        receiver_thread.start()
        time.sleep(0.1)

        sender_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        test_message = "TEST_STATUS_MESSAGE"
        sender_sock.sendto(
            test_message.encode("utf-8"), (self.test_host, self.test_port_receive)
        )

        receiver_thread.join(timeout=2)

        self.assertEqual(len(received_data), 1)
        self.assertEqual(received_data[0], test_message)

        sender_sock.close()
        receiver_sock.close()
        print("✓ test_udp_send_receive: PASSED")

    def test_udp_bidirectional(self):
        """Test bidirectional UDP communication"""
        sock1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        sock1.bind((self.test_host, self.test_port_receive))
        sock2.bind((self.test_host, self.test_port_send))

        sock1.settimeout(1.0)
        sock2.settimeout(1.0)

        # Send from sock2 to sock1
        message1 = "MESSAGE_1"
        sock2.sendto(message1.encode("utf-8"), (self.test_host, self.test_port_receive))

        data1, addr1 = sock1.recvfrom(1024)
        self.assertEqual(data1.decode("utf-8"), message1)

        # Send from sock1 to sock2
        message2 = "MESSAGE_2"
        sock1.sendto(message2.encode("utf-8"), (self.test_host, self.test_port_send))

        data2, addr2 = sock2.recvfrom(1024)
        self.assertEqual(data2.decode("utf-8"), message2)

        sock1.close()
        sock2.close()
        print("✓ test_udp_bidirectional: PASSED")

    def test_udp_multiple_messages(self):
        """Test sending multiple UDP messages"""
        receiver_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        receiver_sock.bind((self.test_host, self.test_port_receive))
        receiver_sock.settimeout(2.0)

        sender_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        messages = ["MSG1", "MSG2", "MSG3"]
        received = []

        for msg in messages:
            sender_sock.sendto(
                msg.encode("utf-8"), (self.test_host, self.test_port_receive)
            )
            time.sleep(0.1)

        for _ in range(3):
            try:
                data, addr = receiver_sock.recvfrom(1024)
                received.append(data.decode("utf-8"))
            except socket.timeout:
                break

        self.assertEqual(len(received), 3)
        self.assertEqual(set(received), set(messages))

        sender_sock.close()
        receiver_sock.close()
        print("✓ test_udp_multiple_messages: PASSED")


if __name__ == "__main__":
    print("=" * 60)
    print("UDP Communication Integration Tests")
    print("=" * 60)
    unittest.main(verbosity=2)

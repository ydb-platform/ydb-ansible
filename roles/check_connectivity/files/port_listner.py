# Simple script for checking connectivity
# It's starting TCP server to listen several ports
# Usage:
#   python3 port_listner.py <port1> [..<portN>]
#
import socket
import threading
import sys

def listen_port4(port):
    try:
        # Set up IPv4 address
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("0.0.0.0", port))
        s.listen(5)

        print(f"Listen port IPv4 {port}...")

        while True:
            conn, addr = s.accept()
            with conn:
                print(f"New connection from {addr}")
            conn.close()
    except:
        print(f"No IPv4")

def listen_port6(port):
    try:
        # Set up IPv6 address
        s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        s.bind(("::", port))
        s.listen(5)

        print(f"Listen port IPv6 {port}...")

        while True:
            conn, addr = s.accept()
            with conn:
                print(f"New connection from {addr}")
            conn.close()
    except:
        print(f"No IPv6")


def main():
    if len(sys.argv) < 2:
        print("No ports to listen!")
        return

    ports = [int(port) for port in sys.argv[1:]]

    threads = []

    for port in ports:
        thread = threading.Thread(target=listen_port6, args=(port,))
        threads.append(thread)
        thread.start()
        thread = threading.Thread(target=listen_port4, args=(port,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

if __name__ == "__main__":
    main()

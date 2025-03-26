# Simple script for checking connectivity
# It's starting TCP server to listen several ports
#
# Expected result: Listen on IPv4/IPv6 interface for incoming requests
# Version: 1.2
# Author: Eugene Arbatsky
#
# Usage:
#   python3 port_listner.py <FQDN> <port1> [..<portN>]
#
import socket
import threading
import sys
import time

def listen_port4(port):
    tries = 0
    while tries < 10:
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
            break
        except:
            print(f"No IPv4 or port is busy.. try again")
        tries = tries + 1
        time.sleep(1)

def listen_port6(port):
    tries = 0
    while tries < 10:
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
            break
        except:
            print(f"No IPv6 or port is busy .. try again")
        tries = tries + 1
        time.sleep(1)


def main():
    if len(sys.argv) < 3:
        print("No ports to listen!")
        return

    fqdn = sys.argv[1]
    ports = [int(port) for port in sys.argv[2:]]

    threads = []
    # Determine prefered IP protocol
    info = socket.getaddrinfo(fqdn,ports[0])

    for port in ports:
        if 'AddressFamily.AF_INET6' in str(info[0][0]):
            thread = threading.Thread(target=listen_port6, args=(port,))
        else:
            thread = threading.Thread(target=listen_port4, args=(port,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

if __name__ == "__main__":
    main()
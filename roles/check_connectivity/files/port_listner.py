# Simple script for checking connectivity
# It's starting TCP server to listen several ports
# Usage:
#   python3 port_listner.py <port1> [..<portN>]
#
import socket
import threading
import sys

def listen_port(port):
    sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)  
    sock.bind(('::', port)) 
    sock.listen(5)  

    print(f"Listen port {port}...")

    while True:
        conn, addr = sock.accept()
        with conn:
            print(f"New connection fomr {addr}")

def main():
    if len(sys.argv) < 2:
        print("No ports to listen!")
        return

    ports = [int(port) for port in sys.argv[1:]]

    threads = []

    for port in ports:
        thread = threading.Thread(target=listen_port, args=(port,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

if __name__ == "__main__":
    main()
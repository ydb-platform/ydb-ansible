#!/usr/bin/env python3
#
# Simple script for checking connectivity
# It's starting TCP server to listen several ports
#
# Expected result: Listen on IPv4/IPv6 interface for incoming requests
# Version: 2.0
# Author: Eugene Arbatsky
#
# Usage:
#   python3 port_listner2.py <FQDN> <port1> [..<portN>]

import sys
import socket
import threading
import errno

def handle_connection(client_sock, addr, family, port):
    """Обработка входящего соединения (эхо-сервер)"""
    try:
        peer = f"[{addr[0]}]:{addr[1]}" if family == socket.AF_INET6 else f"{addr[0]}:{addr[1]}"
        print(f"Accepted connection on port {port} ({family_name(family)}): {peer}")
        
        while True:
            data = client_sock.recv(1024)
            if not data:
                break
            client_sock.sendall(data)
    except OSError as e:
        if e.errno != errno.ECONNRESET:
            print(f"Connection error on port {port}: {e}")
    finally:
        client_sock.close()

def family_name(family):
    """Возвращает строковое представление семейства адресов"""
    return "IPv6" if family == socket.AF_INET6 else "IPv4"

def create_socket(family, port):
    """Создаёт и настраивает сокет для заданного семейства адресов"""
    try:
        sock = socket.socket(family, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Для IPv6: разрешаем независимую работу с IPv4
        if family == socket.AF_INET6:
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        
        # Привязка к интерфейсу
        host = "::" if family == socket.AF_INET6 else "0.0.0.0"
        sock.bind((host, port))
        sock.listen(5)
        print(f"Listening on port {port} ({family_name(family)})")
        return sock
    except OSError as e:
        if e.errno == errno.EAFNOSUPPORT:
            print(f"IPv6 not supported, skipping port {port} for IPv6")
        elif e.errno == errno.EADDRINUSE:
            print(f"Port {port} already in use ({family_name(family)})")
        else:
            print(f"Error creating {family_name(family)} socket on port {port}: {e}")
        return None

def accept_connections(server_sock, family, port):
    """Принимает входящие соединения для сокета"""
    try:
        while True:
            client, addr = server_sock.accept()
            thread = threading.Thread(
                target=handle_connection,
                args=(client, addr, family, port),
                daemon=True
            )
            thread.start()
    except OSError as e:
        if e.errno != errno.EBADF:
            print(f"Accept error on port {port}: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: ./port_listener.py PORT1 [PORT2] ...")
        sys.exit(1)

    try:
        ports = [int(p) for p in sys.argv[1:]]
    except ValueError:
        print("Error: All ports must be integers")
        sys.exit(1)

    servers = []
    threads = []
    
    # Создаем серверы для каждого порта
    for port in ports:
        # IPv6 сервер
        sock_v6 = create_socket(socket.AF_INET6, port)
        if sock_v6:
            servers.append(sock_v6)
            thread = threading.Thread(
                target=accept_connections,
                args=(sock_v6, socket.AF_INET6, port),
                daemon=True
            )
            thread.start()
            threads.append(thread)
        
        # IPv4 сервер
        sock_v4 = create_socket(socket.AF_INET, port)
        if sock_v4:
            servers.append(sock_v4)
            thread = threading.Thread(
                target=accept_connections,
                args=(sock_v4, socket.AF_INET, port),
                daemon=True
            )
            thread.start()
            threads.append(thread)
    
    if not servers:
        print("No servers started. Exiting.")
        sys.exit(1)
    
    # Ожидание завершения (Ctrl+C)
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("\nShutting down servers...")
        for s in servers:
            s.close()
        sys.exit(0)

if __name__ == "__main__":
    main()

""" SHUTDOWN SERVER """
import socket
from modul import SERVER_HOST, SERVER_PORT


def shutdown_server():
    print("Server is shutting down...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(b'connection closed', (SERVER_HOST, SERVER_PORT))
    sock.sendto(b'shutdown', (SERVER_HOST, SERVER_PORT))
    sock.close()


if __name__ == '__main__':
    shutdown_server()

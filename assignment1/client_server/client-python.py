###############################################################################
# client-python.py
# Name:
# JHED ID:
###############################################################################

import sys
import socket


SEND_BUFFER_SIZE = 2048

def client(server_ip, server_port):
    """TODO: Open socket and send message from sys.stdin"""

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((server_ip, server_port))

    while(1):
        data = sys.stdin.read(SEND_BUFFER_SIZE)

        if(not data):
            break
        l = 0
        while(l != len(data)):
            l += s.send(data[l:])

    s.close()

def main():
    """Parse command-line arguments and call client function """
    if len(sys.argv) != 3:
        sys.exit("Usage: python client-python.py [Server IP] [Server Port] < [message]")
    server_ip = sys.argv[1]
    server_port = int(sys.argv[2])
    client(server_ip, server_port)

if __name__ == "__main__":
    main()

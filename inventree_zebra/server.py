# server.py
# simple listener to an IP port to test the zebra plugin with IP conection

import socket

PORT = 9100  # Port to listen on (non-privileged ports are > 1023)

s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', PORT))
s.listen(1)
while True:
    conn, addr = s.accept()
    print("Connected by {addr}")
    while True:
        data = conn.recv(9100)
        print(data)
        if not data:
            break


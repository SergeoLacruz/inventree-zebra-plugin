# server.py
# simple listener to an IP port to test the zebra plugin with IP conection in case you
# do not have a printer with IP interface.

import socket

PORT = 9100  # Port to listen on

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', PORT))
s.listen(1)
while True:
    conn, addr = s.accept()
    print(addr)
    while True:
        data = conn.recv(9100)
        print('data received')
        print('Sending to printer...')
#        printer=open('/dev/usb/lp0','w')
#        printer.write(data)
#        printer.close()
        if not data:
            break

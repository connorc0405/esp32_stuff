import socket
from pyubx2 import UBXReader, UBXMessage, GET

listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
listen_sock.bind(('127.0.0.1', 8080))
listen_sock.listen(1)
conn_sock, _ = listen_sock.accept()
with conn_sock.makefile('rb') as filey:
	reader = UBXReader(filey)

	for (_, parsed_data) in reader:
		print(parsed_data)
import network
import socket
from machine import UART
import time

# Do I need to handle CFG messages?


def recv_ubx(conn_sock):
    recv_buf = bytearray()
    recv_buf.extend(conn_sock.recv(6))
    payload_len = int.from_bytes(recv_buf[4:], 'little')

    while len(recv_buf) < payload_len + 8:  # 6 bytes + payload + 2 bytes checksum
        print(payload_len)
        data = conn_sock.recv(payload_len+2)
        if len(data) == 0:
            print("Closed socket")
            return None
        recv_buf.extend(data)

    return bytes(recv_buf)


ap = network.WLAN(network.AP_IF)
ap.ifconfig(('10.10.10.1', '255.255.255.0', '10.10.10.1', '8.8.8.8'))
ap.config(essid='ESP32', channel=6)
ap.config(hidden=False)
ap.active(False)
ap.active(True)

uart = UART(2, 115200)
uart.init(115200, bits=8, parity=None, stop=1)


listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
listen_sock.bind(('10.10.10.1', 8080))
listen_sock.listen(1)

while True:
    print("Waiting on connection")
    conn_sock, _ = listen_sock.accept()
    print("New connection")
    print("Starting...")
    num = 1
    while True:

        #print("Receiving a packet...")
        ubx_pkt = recv_ubx(conn_sock)
        if ubx_pkt is None: # Socket was closed
            conn_sock.close()
            break
        print("Packet " + str(num))
        num+=1
        uart.write(ubx_pkt)

import network
import socket
from machine import UART
import time


# Do I need to handle CFG messages?


def recv_ubx(conn_sock):
    recv_buf = bytearray()
    try:
        data = conn_sock.recv(1)  # Check if keepalive
        print("received 1 byte")
    except:
        print("Socket timeout")
        return ("fail", None)

    if len(data) == 0:
        print("Closed socket")
        return ("fail", None)
    elif data == b'A':
        return ("keepalive", None)
    print("Not A")
    print(repr(data))
    recv_buf.extend(data)

    while len(recv_buf) < 6:  # Idx 4-5 contain payload length
        try:
            data = conn_sock.recv(6-len(recv_buf)) # TODO make sure we get 6!!!
        except:
            print("Socket timeout")
            return ("fail", None)

        if len(data) == 0:
            print("Closed socket")
            return ("fail", None)
        
        recv_buf.extend(data)

    payload_len = int.from_bytes(recv_buf[4:], 'little')

    while len(recv_buf) < payload_len + 8:  # 6 bytes + payload + 2 bytes checksum
        try:
            data = conn_sock.recv(payload_len + 8 - len(recv_buf))
        except:
            print("Socket timeout")
            return ("fail", None)
        
        if len(data) == 0:
            print("Closed socket")
            return ("fail", None)
        
        recv_buf.extend(data)

    return ("newpkt", bytes(recv_buf))


ap = network.WLAN(network.AP_IF)
ap.ifconfig(('10.10.10.1', '255.255.255.0', '10.10.10.1', '8.8.8.8'))
ap.config(essid='malware test-net', channel=6)
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
    conn_sock.settimeout(5)
    print("New connection")
    num=1
    cur_pkt = None
    while True:
        print("Here")
        status, new_pkt = recv_ubx(conn_sock)
        if status == "fail": # Socket was closed
            conn_sock.close()
            break
        elif status == "keepalive":
            print("Keepalive")
        elif status == "newpkt":  # Good packet
            print("Packet " + str(num))
            cur_pkt = new_pkt
            print(type(cur_pkt))
            num+=1
        else:
            raise Exception("IDK")
        uart.write(cur_pkt)

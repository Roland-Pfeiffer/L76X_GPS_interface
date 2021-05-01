#!/usr/bin/env python3

import serial
import datetime
import copy
import time
import numpy as np
import matplotlib.pyplot as plt
import cartopy
import cartopy.crs as ccrs


DEFAULT_SERIAL_PORT = '/dev/ttyUSB0'
BAUD_RATE = 9600


def set_port(port):
    if port is not None:
        return port
    else:
        global DEFAULT_SERIAL_PORT
        return DEFAULT_SERIAL_PORT


def get_line_content(data_line):
    line = data_line.decode()
    line = line.partition('*')[0]
    return line.split(',')


def pkg_is_valid(raw_pkg):
    """Returns True when a package is valid, and False when it's invalid."""
    # The third entry in comma-separated GNRMC package says "V" for invalid package, and "A" for a valid one.
    validity_code = raw_pkg[0].decode().split(',')[2]
    if validity_code == 'A':
        return True
    elif validity_code == 'V':
        print('[WARNING] Invalid package. Not yet connected to satellites?')
        return False
    else:
        print('[ERROR] Unknown package validity. Incorrect code. (i.e. not "V" (invalid) or "A" (valid).')
        return False


class Waypoint(object):
    def __init__(self, timestamp_utc: datetime = None, valid_waypoint: bool = None, latitude: float = None,
                 longitude: float = None, altitude_m: float = None, heading_deg: float = None, speed_kmh: float = None,
                 satellite_count: int = None, raw_data=None):
        self.timestamp_utc = timestamp_utc
        self.valid_waypoint = valid_waypoint
        self.latitude = latitude
        self.longitude = longitude
        self.altitude_m = altitude_m
        self.heading_deg = heading_deg
        self.speed_kmh = speed_kmh
        self.satellite_count = satellite_count
        self.raw_data = raw_data


def get_raw_package(port=None, baud_rate=BAUD_RATE, stop_bits=1):
    """Starts reading once the next incoming package starts.
    Reads it, line by line, and returns a list of line strings."""
    serial_port = set_port(port)
    print('Waiting for start of next transmission package...')
    while True:
        with serial.Serial(serial_port, baudrate=baud_rate, timeout=1, stopbits=stop_bits) as ser:
            # Continuously read:
            data = ser.readline()
            out = []
            # Find start of a new package
            if data.decode().startswith('$GNRMC'):
                # Then start recording
                out.append(data)
                while True:
                    out.append(ser.readline())
                    if out[-1].decode().startswith('$GNRMC'):
                        break
                break
    out = out[:-1]  # Cut off the last element (start of the next package)
    return out

def monitor_gps():
    with serial.Serial('/dev/ttyUSB0', baudrate=BAUD_RATE, timeout=1, stopbits=1) as ser:
        counter = 0
        while True:
            data = ser.readline()
            if data.decode().startswith('$GNRMC'):
                print('\n[Start of transmission package]')
                counter = 0
            print('{0}\t{1}'.format(counter, data.decode()), end='')
            counter += 1


def get_waypoint():
    last_waypoint = Waypoint()
    package = get_raw_package()
    last_waypoint.raw_pkg = copy.copy(package)

    for line in package:
        if line.decode().startswith('$GNRMC'):
            line = get_line_content(line)

            time_utc = line[1]  # hhmmss.sss
            date = line[9]  # ddmmyy
            recording_time_utc = date + ',' + time_utc
            timestamp_datetime = time.strptime(recording_time_utc, "%d%m%y,%H%M%S.%f")

            valid = line[2]
            if valid == 'A':
                last_waypoint.valid_waypoint = True
            else:
                last_waypoint.valid_waypoint = False

            lat_deg = int(line[3][0:2])
            lat_min = float(line[3][2:])
            latitude = lat_deg + (lat_min / 60)
            hemisphere = line[4]
            if hemisphere == 'S':
                latitude *= -1

            long_deg = int(line[5][0:3])
            long_min = float(line[5][3:])
            longitude = long_deg + (long_min / 60)
            long_dir = line[6]
            if long_dir == 'W':
                longitude *= -1

            heading_deg = float(line[8])

            last_waypoint.timestamp_utc = timestamp_datetime
            last_waypoint.latitude = latitude
            last_waypoint.longitude = longitude
            last_waypoint.heading_deg = heading_deg

        elif line.decode().startswith('$GNVTG'):
            line = get_line_content(line)
            speed_kmh = float(line[7])
            last_waypoint.speed_kmh = speed_kmh

        elif line.decode().startswith('$GNGGA'):
            line = get_line_content(line)
            satellites = int(line[7])
            altitude_m = line[11]
            last_waypoint.satellite_count = satellites
            last_waypoint.altitude_m = altitude_m

    return last_waypoint


def print_package(msg_id: str = None):
    pkg = get_raw_package()
    if msg_id is None:
        for line in pkg:
            print(line.decode(), end='')
    if msg_id is not None:
        for line in pkg:
            if line.decode().startswith(msg_id):
                data_line = get_line_content(line)
                counter = 0
                for element in data_line:
                    print(f'{counter}\t{element}')
                    counter += 1

def gps_test():
    print('Starting GPS test.')
    point = get_waypoint()
    print(f'Valid GPS point: {point.valid_waypoint}')
    lat = point.latitude
    long = point.longitude
    print(f'Lat.: {lat} | Long.: {long} | Package healthy: {point.valid_waypoint}')


if __name__ == '__main__':
    gps_test()
    monitor_gps()
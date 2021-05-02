#!/usr/bin/env python3

import copy
import logging
import time

import gpxpy
import serial


# ToDo: add a function that loops and waits until the packages are valid.
# ToDo: decode each byte literal only once, and have the helper functions use the decoded strings as input.
# ToDo: add a variable or a parameter to both run via UART and as a Pi HAT


DEFAULT_SERIAL_PORT = '/dev/ttyUSB0'
BAUD_RATE = 9600
logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s]\t%(message)s')
logging.disable()


class Waypoint(object):
    def __init__(self,
                 altitude_m: float = None,
                 heading_deg: float = None,
                 latitude: float = None,
                 longitude: float = None,
                 raw_data=None,
                 satellite_count: int = None,
                 speed_kmh: float = None,
                 timestamp_utc=None,
                 valid_waypoint: bool = None,
                 ):
        self.altitude_m = altitude_m
        self.heading_deg = heading_deg
        self.latitude = latitude
        self.longitude = longitude
        self.raw_pkg = raw_data
        self.satellite_count = satellite_count
        self.speed_kmh = speed_kmh
        self.timestamp_utc = timestamp_utc
        self.valid_waypoint = valid_waypoint

    def show_waypoint(self, buffer=17):
        print('Timestamp (UTC):'.ljust(buffer) + time.strftime('%Y-%m-%d %H:%M:%S', self.timestamp_utc))
        print('Valid point:'.ljust(buffer) + str(self.valid_waypoint))
        print('Latitude:'.ljust(buffer) + str(self.latitude))
        print('Longitude:'.ljust(buffer) + str(self.longitude))
        print('Altitude (m)'.ljust(buffer) + str(self.altitude_m))
        print('Satellite #:'.ljust(buffer) + str(self.satellite_count))


def set_port(port):
    if port is not None:
        return port
    else:
        global DEFAULT_SERIAL_PORT
        return DEFAULT_SERIAL_PORT


def get_raw_package(serial_port=DEFAULT_SERIAL_PORT, baud_rate=BAUD_RATE, stop_bits=1):
    """Starts reading once the next incoming package starts.
    Reads it, line by line, and returns a list of byte strings, one for each line.
    Does not check for waypoint validity.
    Because packages are being transmitted at a one-second interval, no package is lost once recording starts"""

    logging.info('Waiting for start of next transmission package...')
    out = []
    while True:
        with serial.Serial(serial_port, baudrate=baud_rate, timeout=1, stopbits=stop_bits) as ser:
            # Continuously read:
            raw_line = ser.readline()
            decoded_line = decode_line(raw_line)
            # Find start of a new package
            if decoded_line.startswith('$GNRMC'):
                # Then start recording
                out.append(raw_line)
                # Then keep recording until you reach the start of a new package
                while True:
                    current_line_raw = ser.readline()
                    out.append(current_line_raw)
                    current_line_decoded = decode_line(current_line_raw)
                    if current_line_decoded.startswith('$GNGLL'):
                        break
                break
    return out


def decode_line(data_line):
    """Takes a line and splits it by comma. Returns a list of elements."""
    line = data_line.decode()
    # Cut off what comes after * since it marks the end of the data field.
    line = line.partition('*')[0]
    return line


def get_line_elements(decoded_line):
    return decoded_line.split(',')


def pkg_is_valid(raw_pkg):
    """Returns True when a package is valid, and False when it's invalid."""
    # The third entry in comma-separated GNRMC package says "V" for invalid package, and "A" for a valid one.
    line = decode_line(raw_pkg[0])
    elements = get_line_elements(line)
    validity_code = elements[2]
    if validity_code == 'A':
        return True
    elif validity_code == 'V':
        logging.info('[WARNING] Invalid package. Not yet connected to satellites?')
        return False
    else:
        print('[ERROR] Unknown package validity. Incorrect code. (i.e. not "V" (invalid) or "A" (valid).')
        return False


def wait_for_satellites():
    counter = 1
    while True:
        if counter == 10:
            counter = 0

        msg = '\rWaiting for satellites' + '.' * counter
        print(msg.ljust(40), end='')
        pkg = get_raw_package()
        if pkg_is_valid(pkg):
            print('\nSatellites found.')
            break

        counter += 1


def extract_lat_long(decoded_line):
    elements = get_line_elements(decoded_line)
    # Get latitude values
    lat_deg = int(elements[3][0:2])  # two digits, max. 90
    lat_min = float(elements[3][2:])
    # Calculate decimal coordinate
    latitude = lat_deg + (lat_min / 60)
    # Check if it should be positive (northern hemisphere) or negative (southern hemisphere).
    hemisphere = elements[4]
    if hemisphere == 'S':
        latitude *= -1

    # Get longitude values
    long_deg = int(elements[5][0:3])  # Three digits, max. 180
    long_min = float(elements[5][3:])
    # Calculate decimal coordinate
    longitude = long_deg + (long_min / 60)
    # Check if it's positive longitude (eastern hemisphere) or negative longitude (western hemisphere)
    long_dir = elements[6]
    if long_dir == 'W':
        longitude *= -1

    return latitude, longitude


def monitor_gps_raw(serial_port=DEFAULT_SERIAL_PORT):
    print('MONITORING RAW')
    with serial.Serial(serial_port, baudrate=BAUD_RATE, timeout=1, stopbits=1) as ser:
        while True:
            print(ser.readline())


def monitor_gps(serial_port=DEFAULT_SERIAL_PORT, package_limit: int=None):
    with serial.Serial(serial_port, baudrate=BAUD_RATE, timeout=1, stopbits=1) as ser:
        if package_limit:
            counter = 0
        while True:
            current_line = ser.readline()
            current_line_decoded = decode_line(current_line).strip()
            if current_line_decoded.startswith('$GNRMC'):
                logging.info('\n[Start of transmission package]\nLine:\tContents:')
                counter = 0
            print(f'{current_line_decoded}')
            if package_limit:
                counter += 1
                if counter * 10 == package_limit:
                    break


def get_waypoint():
    last_waypoint = Waypoint()

    package = get_raw_package()
    last_waypoint.raw_pkg = copy.copy(package)
    last_waypoint.valid_waypoint = pkg_is_valid(package)

    for line in package:
        decoded_line = decode_line(line)
        # Read contents of GNRMC line.
        if decoded_line.startswith('$GNRMC'):
            elements = get_line_elements(decoded_line)
            time_utc = elements[1]  # hhmmss.sss
            date = elements[9]  # ddmmyy
            recording_time_utc = date + ',' + time_utc
            timestamp_datetime = time.strptime(recording_time_utc, "%d%m%y,%H%M%S.%f")
            last_waypoint.timestamp_utc = timestamp_datetime

            # Read lat/long coords, if the waypoint has them
            if last_waypoint.valid_waypoint:
                latitude, longitude = extract_lat_long(decoded_line)
                last_waypoint.latitude = latitude
                last_waypoint.longitude = longitude
            else:
                last_waypoint.latitude = None
                last_waypoint.longitude = None

            heading_deg = float(get_line_elements(decoded_line)[8])
            last_waypoint.heading_deg = heading_deg

        # Read contents of GNVTG line:
        elif decoded_line.startswith('$GNVTG'):
            elements = get_line_elements(decoded_line)
            speed_kmh = float(elements[7])
            last_waypoint.speed_kmh = speed_kmh

        elif decoded_line.startswith('$GNGGA'):
            elements = get_line_elements(decoded_line)
            satellites = int(elements[7])
            altitude_m = elements[11]
            last_waypoint.satellite_count = satellites
            last_waypoint.altitude_m = altitude_m

    return last_waypoint


def gps_test():
    print('Starting GPS test.')
    point = get_waypoint()
    print(f'Valid GPS point: {point.valid_waypoint}')
    lat = point.latitude
    long = point.longitude
    print(f'Lat.: {lat} | Long.: {long} | Package healthy: {point.valid_waypoint}')


# def create_gpx_file(location, fname=time.strftime(time.now())):
#     if fname is None:
#         pass
#     pass


if __name__ == '__main__':
    wait_for_satellites()
    wp1 = get_waypoint()
    wp1.show_waypoint()

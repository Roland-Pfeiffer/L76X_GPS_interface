#!/usr/bin/env bash

# Assuming you need sudo in the pi to access ttyUSB0
# sudo /home/pi/Code/GPS_interface/venv/bin/python3 /home/pi/Code/GPS_interface/pi_read_to_file.py

# Since pi is already in dialout group, it seems you don't need sudo on the pi
/home/pi/Code/GPS_interface/venv/bin/python3 /home/pi/Code/GPS_interface/pi_read_to_file.py
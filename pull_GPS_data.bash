#!/usr/bin/env bash

# rsync -v -u -h --stats pi@192.168.178.41:/home/pi/gps_sensor_data/* /media/findux/DATA/Code/GPS_interface/Data/
scp pi@192.168.178.41:~/gps_sensor_data/* /media/findux/DATA/Code/GPS_interface/Data/
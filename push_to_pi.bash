#!/usr/bin/env bash

echo "Updating execution permissions..."
chmod +x ./start_reading_gps_rpi.bash
echo "Uploading code to RPI..."
rsync -v -E -u /media/findux/DATA/Code/GPS_interface/* pi@192.168.178.41:/home/pi/Code/GPS_interface/
echo "Done uploading."

# -v : verbose
# -E : Keeps executability of files
# -u : skips files who are newer at destination than at source

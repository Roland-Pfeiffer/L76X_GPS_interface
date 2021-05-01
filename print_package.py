#!/usr/bin/env python3
import gps

pkg = gps.get_raw_package()

for line in pkg:
    print(line.decode(), end='')

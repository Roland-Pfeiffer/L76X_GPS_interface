#!/usr/bin/env python3

import sys
import gps

try:
    fpath = sys.argv[1]
except IndexError:
    print('No path argument provided.')
else:
    gps.add_cet_timestamp_to_csv(fpath)

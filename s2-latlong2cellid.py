#! /usr/bin/env python
"""
Author: Adrian Leong (cheeky4n6monkey@gmail.com)

Python 2.7 script to convert lat, long and cellid level to a 64 bit Google S2 cellid.
(up to 14 decimal places)

Uses https://github.com/sidewalklabs/s2sphere Python library
To install s2sphere use:
pip install s2sphere

s2sphere documentation at:
http://s2sphere.sidewalklabs.com/en/latest/index.html

For testing mapping, see:
http://s2map.com
http://s2map.com/README.html

Usage Example:
python s2-latlong2cellid.py 36.114574 -115.180628 24
Running s2-latlong2cellid.py v2016-08-12

S2 cellid = 9279882692622716928

"""

import s2sphere
import argparse

version_string = "s2-latlong2cellid.py v2016-08-12"

print("Running " + version_string + "\n")

# Handle command line args
parser = argparse.ArgumentParser(description='Converts lat, long and cellid level to a 64 bit Google S2 cellid')
parser.add_argument("llat", type=float,
                  help="Latitude in decimal degrees")
parser.add_argument("llong", type=float,
                  help="Latitude in decimal degrees")
parser.add_argument("level", type=int,
                  help="S2 cell level")
args = parser.parse_args()

#print(repr(args.llat))
#print(repr(args.llong))
#print(str(args.level))

pos = s2sphere.LatLng.from_degrees(args.llat, args.llong)
s2cell = s2sphere.CellId.from_lat_lng(pos).parent(args.level) # this also sets the level of s2cell
print("S2 cellid = " + str(s2cell.id()))



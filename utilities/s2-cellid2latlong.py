#! /usr/bin/env python
"""
Author: Adrian Leong (cheeky4n6monkey@gmail.com)

Python 2.7 script to convert a 64 bit Google S2 cellid to a lat, long and S2 cellid level.
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
python s2-cellid2latlong.py 9279882692622716928
Running s2-cellid2latlong.py v2016-08-12

S2 Level = 24
36.114574473973924 , -115.18062802526205

"""

import s2sphere
import argparse

version_string = "s2-cellid2latlong.py v2016-08-12"

print("Running " + version_string + "\n")

# Handle command line args
parser = argparse.ArgumentParser(description='Convert a 64 bit Google S2 cellid to a lat, long and S2 cellid level')
parser.add_argument("cellid", type=int,
                  help="Google S2 cellid")
args = parser.parse_args()

s2cell = s2sphere.CellId(args.cellid)
print("S2 Level = " + str(s2cell.level()))
print(repr(s2cell.to_lat_lng().lat().degrees) + " , " + repr(s2cell.to_lat_lng().lng().degrees))
#print(s2cell.to_token())



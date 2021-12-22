#! /usr/bin/env python

# google-ei-time.py = Python script takes a Google Search URL or ei parameter and returns a human readable timestamp
#
# Copyright (C) 2014 Adrian Leong (cheeky4n6monkey@gmail.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You can view the GNU General Public License at <http://www.gnu.org/licenses/>
#
# Special Thanks to Phillip Moore for suggesting the idea and for helping to test it.
#
# Reference:
# https://deedpolloffice.com/blog/articles/decoding-ei-parameter
# Example:
# http://www.google.com.au/?gfe_rd=cr&ei=tci4UszSJeLN7Ab9xYD4CQ 
# ei=tci4UszSJeLN7Ab9xYD4CQ => 1387841717 => 23rd December 2013 at 23.35.17
#
# Version History:
# v2014-10-10 Initial Version

import sys
from optparse import OptionParser
import datetime
import base64
import urlparse

version_string = "google-ei-time.py v2014-10-10"
usage = "%prog -e EITERM -q OR %prog -u URL -q"

parser = OptionParser(usage=usage)
parser.add_option("-e", dest="eiterm", 
                  action="store", type="string",
                  help="Google search URLs EI parameter value")
parser.add_option("-u", dest="url",
                  action="store", type="string",
                  help="Complete Google search URL")
parser.add_option("-q", dest="quiet",
                  action="store_true", 
                  help="(Optional) Quiet output (only outputs timestamp string)")
(options, args) = parser.parse_args()

if not (options.quiet):
    print "Running " + version_string + "\n"

# No arguments given by user, print help and exit
if len(sys.argv) == 1:
    parser.print_help()
    exit(-1)

if ((options.eiterm == None) and (options.url == None)):
    print "Error! Neither ei or URL terms were specified. Choose one!\n"
    parser.print_help()
    exit(-1)

if ((options.eiterm != None) and (options.url != None)):
    print "Error! BOTH ei and URL terms were specified. Choose one!\n"
    parser.print_help()
    exit(-1)

ei = ""
if (options.url != None):    
    parsed = urlparse.urlparse(options.url)
    #print parsed
    # returns a 6 tuple list. The element we're interested in is "parsed.query" 
    if ("ei" not in parsed.query):
        if not (options.quiet):
            print "No ei parameter found in URL!"
        exit(-1)

    # search parsed query for "ei" parameter and extract the returned list item
    # parse_qs returns a dictionary item, hence the following ["ei"]. 
    # The dictionary value is a list, hence the following [0]
    ei = urlparse.parse_qs(parsed.query)["ei"][0]
    if not (options.quiet):
        print "URL's ei term = " + ei
else:
    ei = options.eiterm
    if not (options.quiet):
        print "Input ei term = " + ei

# ei parameter may require padding (length must be a multiple of 4 for Python's base64 decode)
num_extra_bytes = (len(ei) % 4) # equals number of extra bytes past last multiple of 4 eg equals 1 for ei length of 21
if (num_extra_bytes != 0):
    padlength = 4 - num_extra_bytes # eg 4 - 1 results in 3 extra "=" pad bytes being added 
    padstring = ei + padlength*'='
else:
    padstring = ei

if not (options.quiet):
    print "Padded base64 string = " + padstring

# Apparently the base64 string are made URL safe by substituting - instead of + and _ instead of /
# Python base64 conveniently has a "urlsafe_b64decode" function to handle the reverse of the above substitution
# Will the wonders never cease?
decoded = base64.urlsafe_b64decode(padstring)

#print decoded
#print "decoded length = " + str(len(decoded))
# decoded should be 16 bytes ...

# grab 1st 4 bytes and treat as LE unsigned int
# byte 0 is least significant ... byte 3 is most significant
# a byte is 8 bits and ranges from 00000000 to 11111111 (dec. 255)
# Each byte range is 256 times the previous bytes range
# ie xFF = 255, xFF00 = 255 * 256 = 65280 dec, xFF0000 = 255 * 256 *256 = 16711680 dec
# Calling "ord" converts the given byte string into a number
timestamp = ord(decoded[0]) + ord(decoded[1])*256 + ord(decoded[2])*(256**2) + ord(decoded[3])*(256**3)

if not (options.quiet):
    print "Extracted timestamp = " + str(timestamp)

try: 
    datetimestr = datetime.datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%dT%H:%M:%S')
except:
    datetimestr = "Unknown"

if not (options.quiet):
    print "Human readable timestamp (UTC) = " + datetimestr
else:
    print datetimestr

exit(0)

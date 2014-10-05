#! /usr/bin/env python

# Python script to parse CallHistory from a Windows 8.0 phone's store.vol file
# Author: cheeky4n6monkey@gmail.com (Adrian Leong)
# 
# Special Thanks to Detective Cindy Murphy (@cindymurph) and the Madison, WI Police Department 
# for the initial test data and encouragement.
# Thanks also to Brian McGarry (Garda) and JoAnn Gibb (Ohio Attorney Generals Office) for providing test data/feedback.
#
# WARNING: This program is provided "as-is" and has been tested on a limited set of data from a Nokia Lumia 520 Windows Phone 8
# See http://cheeky4n6monkey.blogspot.com/ for further details.

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

# store.vol CallHistory record structure
# [?][Flag][0x8 bytes][Start FILETIME][Stop FILETIME][0x7 or 0xF or 0x13 bytes][ID][0x14 bytes][Phone1][1 byte][Name1][1 byte][Name2][1 byte][Phone2][1 byte][GUID]
#
# Flag value: 0x00 = Outgoing, 0x01 = Incoming, 0x02 = Missed
# ID is a null-terminated variable length string of digits (ASCII encoded)
#
# Script searches for fixed GUID and works backwards to read Phone/Name/ID/FILETIME/Flag fields.
# From the sample test data, the script ass-umes there's a constant 0x14 bytes between 
# the last byte of the ID string and the first byte of the Phone1 string. 
# Similarly, the script ass-umes there's either 0x7 or 0xF or 0x13 bytes between
# the last byte of Stop FILETIME and the first byte of the ID string.
# A sanity check is performed on Start/Stop FILETIMEs and is set to "Unknown" on out of range error.
#
# History
# v2014-08-13 Initial version
# v2014-08-16 Adjusted for variable length ID fields and added Flag extraction
# v2014-08-22 Experimental version that searches for stop timestamps for a given range offset
# v2014-10-05 Renamed script from "win8callhistory-ex.py" to "wp8-callhistory.py"

import codecs
import sys
import struct
import datetime
import string
from optparse import OptionParser

version_string = "wp8-callhistory v2014-10-05"

# Read in 8 byte MS FILETIME (number of 100 ns since 1 Jan 1601) and 
# Returns equivalent unix epoch offset or 0 on error
def read_filetime(f):
    begin = f.tell()
    try:
        #print "time at offset: " + str(begin)
        mstime = struct.unpack('<Q', f.read(8))[0]
    except:
        print "Bad FILETIME extraction at " + hex(begin).rstrip("L")
        exctype, value = sys.exc_info()[:2]
        print ("Exception type = ",exctype,", value = ",value) 
        return 0
    #print (mstime)
    #print hex(mstime)

    # Date Range Sanity Check
    # min = 0x01CD000000000000 ns = 03:27 12MAR2012 (Win8 released 29OCT2012)
    # max = 0x01D9000000000000 ns = 12:26 24NOV2022 (give it 10 years?)
    if (mstime < 0x01CD000000000000) or (mstime > 0x01D9000000000000):
        #print "Bad filetime value!"
        return 0
    # From https://libforensics.googlecode.com/hg-history/a41c6dfb1fdbd12886849ea3ac91de6ad931c363/code/lf/utils/time.py
    # Function filetime_to_unix_time(filetime)
    unixtime = (mstime - 116444736000000000) // 10000000
    return unixtime

# Find all indices of a substring in a given string (Python recipe) 
# From http://code.activestate.com/recipes/499314-find-all-indices-of-a-substring-in-a-given-string/
def all_indices(bigstring, substring, listindex=[], offset=0):
    i = bigstring.find(substring, offset)
    while i >= 0:
        listindex.append(i)
        i = bigstring.find(substring, i + 1)

    return listindex

# Extract a Unicode null terminated string given file. 
# Starts at the beginning of last (null) Unicode char and 
# reads Unicode string in reverse. Returns read string or "Error!"
def rev_extract_unistring(f):
    readchar = 0xABCD
    readcharlist = []
    flag = True
    charcount = 0
    begin = f.tell()
    while (flag):
        try:
            readchar = f.read(1)
            charcount += 1
            if ( (readchar == unichr(0)) and (charcount > 1) ): # bailout if null char and not null at end of string
                flag = False
            else:
                if ( (readchar == unichr(0)) and (charcount == 1) ): # skip null at end of string
                    f.seek(f.tell() - 4) # jump back to the previous Unicode char
                    continue
                if (readchar in string.printable): # record each printable char in list
                    #print "readchar = " + readchar
                    readcharlist.insert(0, readchar)
                    f.seek(f.tell() - 4)
                else:
                    #print "Unprintable Unicode char at " + hex(f.tell() - 2).rstrip("L")
                    flag = False # unprintable means we've gone past first char of string / invalid string
        except:
            print "Unicode read error at offset " + hex(begin).rstrip("L")
            exctype, value = sys.exc_info()[:2]
            print ("Exception type = ",exctype,", value = ",value) 
            return "Error!"

    readstring = ''.join(readcharlist) # convert the list into a string
    return readstring

# Reads ASCII encoded string given file.
# Returns read string or "Error!" (reads backwards from last char (null))
def rev_extract_ascii_string(f):
    readchar = 0xAB
    readcharlist = []
    flag = True
    charcount = 0
    begin = f.tell()
    while (flag):
        try:
            readchar = f.read(1)
            charcount += 1
            if ( (readchar == chr(0)) and (charcount > 1) ): # bailout if null char and not null at end of string
                flag = False
            else:
                if ( (readchar == chr(0)) and (charcount == 1) ): # skip null at end of string
                    f.seek(f.tell() - 2) # jump back to the previous ascii char
                    continue
                if (readchar in string.printable): # record each printable char in list
                    #print "readchar = " + readchar
                    readcharlist.insert(0, readchar)
                    f.seek(f.tell() - 2)
                else:
                    #print "Unprintable ASCII char at " + hex(f.tell() - 1).rstrip("L")
                    flag = False # unprintable means we've gone past first char of string / invalid string
        except:
            print "ASCII read error at offset " + hex(begin).rstrip("L")
            exctype, value = sys.exc_info()[:2]
            print ("Exception type = ",exctype,", value = ",value) 
            return "Error!"

    readstring = ''.join(readcharlist) # convert the list into a string
    return readstring

# Searches backwards for a valid timestamp from a given file ptr and range
# Returns 0 if error or not found otherwise returns unix timestamp value
def find_timestamp(f, maxoffset, minoffset):
    begin = f.tell()
    # maxoffset is inclusive => need range from minoffset : maxoffset+1
    for i in range(minoffset, maxoffset+1, 1):
        if ((begin - i) < 0):
            return 0 # FILETIME can't be before start of file
        else:
            f.seek(begin-i)
            value = read_filetime(f)
            if (value != 0):
                return value
            #otherwise keep searching until maxoffset
    # if we get here, we haven't found a valid timestamp, so return 0
    return 0

# Main
print "Running " + version_string + "\n"
usage = " %prog -f inputfile -o outputfile"

# Handle command line args
parser = OptionParser(usage=usage)
parser.add_option("-f", dest="filename", 
                  action="store", type="string",
                  help="Input File To Be Searched")
parser.add_option("-o", dest="tsvfile",
                  action="store", type="string",
                  help="Tab Separated Output Filename")
(options, args) = parser.parse_args()

# Check if no arguments given by user, exit
if len(sys.argv) == 1:
    parser.print_help()
    exit(-1)
if (options.filename == None) :
    parser.print_help()
    print "\nInput filename incorrectly specified!"
    exit(-1)
if (options.tsvfile == None) :
    parser.print_help()
    print "\nOutput filename incorrectly specified!"
    exit(-1)

# Open store.vol for unicode encoded text reads
try:
	funi = codecs.open(options.filename, encoding="utf-16-le", mode="r")
except:
    print ("Input File Not Found (unicode attempt)")
    exit(-1)

# Open store.vol for binary byte ops (eg timestamps)
try:
	fb = open(options.filename, "rb")
except:
    print ("Input File Not Found (binary attempt)")
    exit(-1)

# read file into one big BINARY string
filestring = fb.read()
# search the big file string for the hex equivalent of the GUID which marks CallHistory records
# GUID is "{B1776703-738E-437D-B891-44555CEB6669}" in hex
GUID = "\x7b\x00\x42\x00\x31\x00\x37\x00\x37\x00\x36\x00\x37\x00\x30\x00\x33\x00\x2d\x00\x37\x00\x33\x00\x38\x00\x45\x00\x2d\x00\x34\x00\x33\x00\x37\x00\x44\x00\x2d\x00\x42\x00\x38\x00\x39\x00\x31\x00\x2d\x00\x34\x00\x34\x00\x35\x00\x35\x00\x35\x00\x43\x00\x45\x00\x42\x00\x36\x00\x36\x00\x36\x00\x39\x00\x7d\x00"
#print GUID
hits = all_indices(filestring, GUID, [])
#print "CallHistory hits = " + str(len(hits))

# Dict for storing results (keyed by offset)
call_entries = {}

for hit in hits:
    #print "Hit at " + hex(hit).rstrip("L")
    # Should be Phone2
    funi.seek(hit - 0x3)
    Phone2 = rev_extract_unistring(funi)
    #print "Phone2 = " + Phone2
    # Should be Name2
    funi.seek(funi.tell() - 0x3)
    Name2 = rev_extract_unistring(funi)
    #print "Name2 = " + Name2
    # Should be Name1
    funi.seek(funi.tell() - 0x3)
    Name1 = rev_extract_unistring(funi)
    #print "Name1 = " + Name1
    # Should be Phone1
    funi.seek(funi.tell() - 0x3)
    Phone1 = rev_extract_unistring(funi)
    #print "Phone1 = " + Phone1
    
    # To handle variable sized IDs, we start at end of ASCII ID string and read backwards until null char or unprintable
    idoffset_end = funi.tell() - 0x15 # ass-umes end of ID string is fixed offset away from first byte of Phone1
    #print "idoffset_end = " + hex(idoffset).rstrip("L")
    fb.seek(idoffset_end)
    idstring = rev_extract_ascii_string(fb)
    #print "ID = " + idstring

    stoptimestring = "Unknown" 
    starttimestring = "Unknown"
    flagvalue = -1
    valid_startime = False
    valid_stoptime = False

    # From test data, there's either 0x7, 0xF or 0x13 bytes between start of ASCII ID and end of Stop FILETIME
    # So we search backwards for a valid timestamp from the start of the ASCII ID (current file position)
    # Max bytes to go back is 0x13 + sizeof Stop FILETIME (8 bytes) = 0x1B
    # Min bytes to go back is 0x7 + sizeof Stop FILETIME (8 bytes) = 0xF
    # WARNING: Might need to adjust these values for other data sets 
    stoptimeval = find_timestamp(fb, 0x1B, 0xF)
    afterstop_offset = fb.tell() # cursor should be at byte just after the stop timeoffset

    if (stoptimeval!=0):
        try:
            stoptimestring = datetime.datetime.utcfromtimestamp(stoptimeval).isoformat()
            valid_stoptime = True
        except:
            stoptimestring = "Error"

        # Read start time
        startoffset = afterstop_offset-0x10 # start of Start timestamp is 0x10 bytes before end of Stop timestamp
        #print "startoffset = " + hex(startoffset)
        fb.seek(startoffset) 
        starttimeval = read_filetime(fb)
        if (starttimeval!=0):
            try:
                starttimestring = datetime.datetime.utcfromtimestamp(starttimeval).isoformat()
                valid_startime = True
            except:
                starttimestring = "Error"

            # Only check flag if start time was read OK
            flagoffset = startoffset-0x9
            fb.seek(flagoffset) # 0x8 bytes between Flag and Start timestamp
            try:
                #print "Flag value at offset: " + hex(flagoffset).rstrip("L")
                flagvalue = struct.unpack('B', fb.read(1))[0]
            except:
                print "Bad Flag extraction at " + hex(flagoffset).rstrip("L")
                exctype, value = sys.exc_info()[:2]
                print ("Exception type = ",exctype,", value = ",value) 
            
    #print "Start = " + starttimestring
    #print "Stop = " + stoptimestring
    #print "Flag = " + str(flagvalue)

    # Store parsed data in dictionary keyed by hit offset
    call_entries[hit] = (str(flagvalue), starttimestring, stoptimestring, idstring, Phone1, Name1, Name2, Phone2)

#ends for hits loop

print "Processed " + str(len(hits)) + " Call History entries\n"

# sort by starttimestring
sorted_calls_keys = sorted(call_entries, key = lambda x : (call_entries[x][1], call_entries[x][1])) 

# print to TSV
# open contacts output file if reqd
if (options.tsvfile != None):
    try:
        tsvof = open(options.tsvfile, "w")
    except:
        print ("Trouble Opening TSV Output File")
        exit(-1)
    tsvof.write("GUID_Offset\tFlag\tStart_Time\tStop_Time\tID\tPhone_1\tName_1\tName_2\tPhone_2\n")
    for key in sorted_calls_keys:
        tsvof.write(hex(key).rstrip("L") + "\t" + call_entries[key][0] + "\t" + call_entries[key][1] + "\t" + call_entries[key][2] + \
        "\t" + call_entries[key][3]+ "\t" + call_entries[key][4] + "\t" + call_entries[key][5] + "\t" + call_entries[key][6] + \
        "\t" + call_entries[key][7] + "\n")
    print "Finished writing out TSV"
    tsvof.close()

funi.close()
fb.close()

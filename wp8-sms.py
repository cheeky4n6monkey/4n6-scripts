#! /usr/bin/env python

# Python script to parse SMStext messages from a Windows 8.0 phone's store.vol file
# Author: cheeky4n6monkey@gmail.com (Adrian Leong)
# 
# Special Thanks to Detective Cindy Murphy (@cindymurph) and the Madison, WI Police Department (MPD)
# for the test data and encouragement.
# Thanks also to JoAnn Gibb (Ohio Attorney Generals Office) and Brian McGarry (Garda) for providing testing data/feedback.
#
# WARNING: This program is provided "as-is" and has been tested with 2 types of Windows Phone 8.0 (Nokia Lumia 520, HTC PM23300)
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

"""
Data Notes:
===========
\\Users\WPCOMMSSERVICES\APPDATA\Local\Unistore\store.vol contains SMS text messages, contact and limited MMS information.
\\Users\WPCOMMSSERVICES\APPDATA\Local\UserData\Phone contains call log information.
\SharedData\Comms\Unistore\data contains various .dat files for MMS messages

From analysis of MPD store.vol test data (Nokia 520 Windows 8 phone) there are two areas of focus (tables?) for SMS data

Area 1 = The "SMStext" content area. Each SMS message has its own record within this area.
Each content record seems to follow one of these structures:

[?][FILETIME1][?][FILETIME2][?][PHONE0][[1 byte]["IPM.SMStext" string][1 byte][PHONE1][1 byte][PHONE2][1 byte][PHONE3][1 byte][Received Message][?][FILETIME3][?][FILETIME4] 
or
[?][FILETIME1][?][FILETIME2][?]["IPM.SMStext" string][1 byte][Sent Message][?][FILETIME3][?][FILETIME4] 

? = unknown / varying number of bytes
All strings are Unicode UTF-16-LE and null terminated
FILETIMEs are 8 byte LE and record the number of 100 ns intervals since 1 JAN 1601 (ie MS FILETIME)

For MPD test data, there seems to consistently be:
 0xBF bytes between FILETIME2 and "SMStext" for Sent SMS (0xB7 bytes between start of "IPM.SMStext" and start of FILETIME2)
 0xEA bytes between FILETIME2 and "SMStext" for Recvd SMS (subject to length of PHONE0)

For the supplied OHIO data, There seems to consistently be:
 0xB4 bytes between FILETIME2 and "SMStext" for Sent SMS
 0xDF bytes between FILETIME2 and "SMStext" for Recvd SMS (subject to length of PHONE0)

CHECK YOUR DATA OFFSETS! They will probably vary between phones / data sets.

Unfortunately, sent SMS does not record the destination phone number in Area 1 records.
For these, we need to check an area of store.vol we'll call Area 2. The records in Area 2 look like:

[?][FILETIMEX][0x1B bytes]["SMS" string][1 byte][PHONEX][?]

Note: the Area 2 record formats seemed consistent between the Nokia 520 and HTC phones.
FILETIMEX value seems to correspond exactly to an Area 1 record's FILETIME2 field. 
So we might be able to find out the destination number of a sent SMS by doing a search of Area2 fields for a specific FILETIMEX value.
This seems to work well with our MPD test data.

Program Notes:
==============
Given a specified input store.vol and output TSV filename, this script will
- Search for "SMStext" entries (in Area 1 ie "Message" table) and store the sent/recvd direction, FILETIME2, Text message, Offset of the Text Message and PHONE1.
- For any sent SMS, it will also look up the destination phone number (in Area 2 ie "Recipient" table) using FILETIME2 / FILETIMEX as a key.
- Print out results to a nominated Tab Separated Variable file format (screen output is not typically large enough)

Known Issues:
- Offsets might have to be adjusted between phones/datasets particularly between the start of FILETIME2 and the start of "SMStext".
This script version tries an experimental method of calculating the offset so the user doesn't have to (theoretically).
- There may be unprintable characters in null term string fields AFTER the NULL but before the 0x1 field marker. Added goto_next_field function to handle these.
- If the script does not detect Unicode digits 0x11 bytes before the start of "SMStext", it ass-umes that the message is a Sent SMS (ie no numbers). This also means that SMS with one/two digit phone numbers might not be identified correctly as received.

Change history:
v2014-08-30: 
- Revised for non-printable characters appearing after the null in nullterm unicode strings but before the 0x1.
- Assumes each field is demarcated by 0x01 bytes.
- Also adjusted the max offset range for Sent SMS FILETIME2 based on test data. Increased it to 0xEA (from 0xC4).

v2014-09-01:
- Changed logic so that if we don't see Unicode digits before "SMStext", the script assumes the message is a Sent SMS (no numbers).
- Decreased Sent SMS "find_timestamp" min parameter based on 1SEP data to x7D (from 0xAF)

v2014-09-05:
- Added trace output for when the script skips record extractions (ie when it can't find/read fields)
- Adjusted minimum "find_timestamp" parameters based on MPD log data to 0x9B for received SMS

v2014-09-29:
- Modified read_nullterm_unistring so it returns whatever valid characters it has read on a bad read exception.
Previously, it was returning an empty string. This was done to handle emoticons ... 

v2014-10-05:
- Renamed script from "win8sms-ex2.py" to "wp8-sms.py"

v2015-07-10:
- Changed script to search for hex strings in chunks of CHUNK_SIZE rather than in one big read 
(makes it quicker when running against whole .bin files). Thanks to Boss Rob :)

"""

import codecs
import sys
import struct
import datetime
import string
from optparse import OptionParser
import re
import os

version_string = "wp8-sms.py v2015-07-10"
CHUNK_SIZE = 2000000000 # max value of CHUNK_SIZE + DELTA is 2147483647 (C long limit with Python 2)
DELTA = 1000 # read this extra bit to catch any hits crossing chunk boundaries. Should be AT LEAST max size of record being searched for.

# Read in unicode chars one at a time until a null char ie "0x00 0x00"
# Returns empty string on error otherwise it filters out return/newlines and returns the string read
def read_nullterm_unistring(f):
    readstrg = ""
    readchar = 0xABCD
    flag = True
    unprintablechars = False
    begin = f.tell()
    
    while (flag):
        try:
            #print "char at " + hex(f.tell()).rstrip("L")
            readchar = f.read(1)
            if (readchar == unichr(0)): # bailout if null char
                flag = False
            if (flag):
                if (readchar in string.printable) and (readchar != "\r") and (readchar != "\n"):
                    readstrg += readchar
                else:
                    readstrg += " "
                    unprintablechars = True
                    #print "unprintable at " + hex(f.tell()-1).rstrip("L")
        except:
            print "Warning ... bad unicode string at offset " + hex(begin).rstrip("L")
            exctype, value = sys.exc_info()[:2]
            print ("Exception type = ",exctype,", value = ",value) 
            #readstrg = ""
            return readstrg # returns partial strings
    
    if (unprintablechars):
        print "String substitution(s) due to unrecognized/unprintable characters at " + hex(begin).rstrip("L")
    
    return readstrg

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

# DEPRACATED: Find all indices of a substring in a given string (Python recipe) 
# From http://code.activestate.com/recipes/499314-find-all-indices-of-a-substring-in-a-given-string/
#def all_indices(bigstring, substring, listindex=[], offset=0):
#    i = bigstring.find(substring, offset)
#    while i >= 0:
#        listindex.append(i)
#        i = bigstring.find(substring, i + 1)
#
#    return listindex

# Find all indices of the "pattern" regular expression in a given string (using regex)
# Where pattern is a compiled Python re pattern object (ie the output of "re.compile")
def regsearch(bigstring, pattern, listindex=[]):
    hitsit = pattern.finditer(bigstring)
    for it in hitsit:
        # iterators only last for one shot so we capture the offsets to a list
        listindex.append(it.start())
    return listindex

# Given a file ptr to "SMStext" field, looks for the 3rd last "PHONE0" digit value
# If we see a digit, we know its a received SMS
def find_flag(f):
    begin = f.tell()
    #fb.seek(begin - 0xD) # last digit offset 
    fb.seek(begin - 0x11) # usually the 3rd last digit offset but can be the last digit eg 1SEP DUB data
    val = struct.unpack("B", fb.read(1))[0]
    if (val >= 0x30) and (val <= 0x39):
        val2 = struct.unpack("B", fb.read(1))[0]
        if (val2 == 0x00):
            return val # 0x30 0x00 to 0x39 0x00 (corresponds to Unicode for "0" to "9")    
        else:
            return 0 # assume its a sent sms
    else:
        return val # means no number present (ie sent SMS)

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

# Takes a binary file ptr, a starting offset and reads bytes until it finds 0x1 or the maxbytes limit.
# Returns True if 0x1 found, False otherwise
# Used to get to the next field offset (assuming they are separated by a byte value of 0x1. 
def goto_next_field(f, offset, maxbytes):
    for i in range(maxbytes+1): # 0 ... maxbytes
        f.seek(offset+i)
        val = struct.unpack("B", f.read(1))[0]
        if (val == 0x1):
            #print "Found next field marker at " + hex(f.tell()-1).rstrip("L")
            return True
    return False

# Searches chunks of a file (using RE) and returns file offsets of any hits.
# Intended for searching of large files where we cant read the whole thing into memory
# This function calls the "regsearch" search method
def sliceNsearchRE(fd, chunksize, delta, term):
    final_hitlist = [] # list of file offsets which contain the search term
    pattern = re.compile(term, re.DOTALL) # should only really call this once at start, if same substring.
    stats = os.fstat(fd.fileno())
    #print("sliceNsearchRE Input file " + filename + " is " + str(stats.st_size) + " bytes\n")
    begin_chunk = 0

    # Handle if filesize is less than CHUNK_SIZE (eg store.vol instead of image.bin)
    # Should be able to read whole file in 1 chunk 
    if (chunksize >= stats.st_size):
        fd.seek(begin_chunk)
        raw = fd.read()
        final_hitlist = regsearch(raw, pattern, [])
        #print(str(len(final_hitlist)) + " hits found in 1 chunk for " + str(term))
    else:
        # Filesize is greater than 1 chunk, need to loop thru
        while ((begin_chunk + chunksize) <= stats.st_size) :
            chunk_size_to_read = chunksize + delta
            if ((chunk_size_to_read + begin_chunk) > stats.st_size):
                chunk_size_to_read = stats.st_size - begin_chunk
            #print("seeking " + str(begin_chunk) + " with size = " + str(chunk_size_to_read))
            fd.seek(begin_chunk)
            rawchunk = fd.read(chunk_size_to_read)
            subhits = regsearch(rawchunk, pattern, [])
            #print(str(len(subhits)) + " hits found at " + str(subhits))
            # Items in subhits will be offsets relative to the start of the rawchunk (not relative to the file)
            # Need to adjust offsets ...
            for hit in subhits :
                if (hit < chunksize) :
                    final_hitlist.append(begin_chunk + hit)
                    #print("adding " + str(begin_chunk + hit) + " to list")
                elif (hit >= chunksize) :
                    #print("ignoring " + str(begin_chunk + hit) + " to list")
                    break # don't care if we get here because hit should be processed in next chunk
                    # subhits can start at index 0 so possible hit offsets are 0 to chunksize-1 inclusive
            begin_chunk += chunksize
    #print("final_hitlist = " + str(final_hitlist))
    return(final_hitlist)

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
# search the file chunks for the hex equivalent of "SMStext" which marks SMS Text content (ie Area 1)
substring1 = "\x53\x00\x4d\x00\x53\x00\x74\x00\x65\x00\x78\x00\x74\x00\x00\x00" #ie "SMStext"
hits = sliceNsearchRE(fb, CHUNK_SIZE, DELTA, substring1)
#print "SMStext hits = " + str(len(hits))

# search for "SMS" which marks the SMS log entries (ie Area 2 times and phone number)
# this will include SMStext hits so we need to some de-duping afterwards
substring2 = "\x53\x00\x4d\x00\x53\x00\x00\x00" # ie "SMS"
smshits = sliceNsearchRE(fb, CHUNK_SIZE, DELTA, substring2)
#smshits = all_indices(filestring, substring2, [])
#print "SMS hits = " + str(len(smshits)) + " smshits"

# Filter smshits further (the hits above will include some false positives eg "SMStext")
smslogdict = {}
# for each valid "SMS" log hit, grab the filetime and phone number for later use
for smshit in smshits:
    # go back 2 bytes and check for "@" (0x40) and process as sms log entry if required
    fb.seek(smshit - 2)
    val = struct.unpack("B", fb.read(1))[0]
    if (val == 0x40):
        #print "sms log hit = " + hex(smshit - 2).rstrip("L")
        # Get sms log filetime associated with this SMS (ASS-UME it matches with FILETIME2 retrieved later)
        fb.seek(smshit - 0x23) # seek to 1st byte of FILETIMEX
        smstimeval = read_filetime(fb)
        smstimestring = ""
        if (smstimeval != 0):
            try:
                # returns UTC time
                smstimestring = datetime.datetime.utcfromtimestamp(smstimeval).isoformat()
            except:
                smstimestring = "Error" # if we get here, the hit is a false one. The date at this offset is not valid
                continue
            #print "SMS log Time2 (UTC) = " + smstimestring
        else:
            # must be wrong offset / read error so ignore this hit
            continue

        # Retrieve phone number string (PHONEX) from sms log
        funi.seek(smshit + 0x9) # seek to 1st byte of phone num
        smsnumstring = read_nullterm_unistring(funi)
        #print "SMS log # = " + smsnumstring + "\n"
        if ( (smstimestring not in smslogdict.keys()) and (smsnumstring != "") ):
            # If not already there and not an empty string, store phone number in dictionary keyed by time
            smslogdict[smstimestring] = smsnumstring

#print "smslogdict = " + str(len(smslogdict.keys()))    
    
# storage variable for printing parsed data to TSV later
sms_entries = {}

# for each "SMStext" hit
for hit in hits:
    nums_listed = -1
    string_offset = 0
    unistring = ""
    phonestring = "Not parsed"
    sentflag = "Unknown"
    
    #print "Text Offset = " + hex(hit) # offset to "SMStext"
    fb.seek(hit)
    # Look for "PHONE0"s 3rd last digit value
    flagvalue = find_flag(fb)
    #print "flag = " + hex(flagvalue)
    # Changed logic for 1SEP DUB data. Assume its a Sent message if no number detected at offset
    if ((flagvalue >= 0x30 and flagvalue <=0x39)):
        nums_listed = 1
        sentflag = "Recvd" # digit was detected, must be a received SMS
    else:
        nums_listed = 0
        sentflag = "Sent"

    #print "Direction: " + sentflag

    # Jump forward from start of "SMStext" to get to first unicode text (either number or text message)
    funi.seek(hit)
    IPMSMStext = read_nullterm_unistring(funi)
    offset_after_IPMSMStext = funi.tell()
    # Look for next 0x1 value marking the next field. If we don't find it after 3 bytes, skip this hit
    found_next_field = goto_next_field(fb, offset_after_IPMSMStext, 3)
    if (not found_next_field):
        print "Skipping hit at " + hex(hit) + " - cannot find next field after SMStext"
        continue # can't find next field so skip this hit

    #print "found next string after IPM.SMStext at " + hex(fb.tell()).rstrip("L")
    # we are either at beginning of sms string (sent) or at beginning of list of 3 null terminated phone numbers (each *usually* separated by 1 byte ... for recvd)
    if (nums_listed == 0):
        # Sent sms only has text
        string_offset = fb.tell()
        funi.seek(string_offset)
        unistring = read_nullterm_unistring(funi)
        #print "Text (" + hex(string_offset).rstrip("L")  +"): " + unistring
        
    if (nums_listed == 1):
        # At the beginning of phone numbers
        funi.seek(fb.tell())
        #print "Recvd at " + hex(funi.tell())
        phonestring1 = read_nullterm_unistring(funi)
        if (phonestring1 == ""):
            print "Skipping hit at " + hex(hit) + " - cannot read PHONE1 field"
            continue # skip this hit if empty string
        phonestring = phonestring1 # just collect the first phone string for printing at this time
        #print phonestring1

        offset_after_string = funi.tell()
        found_next_field = goto_next_field(fb, offset_after_string, 3)
        if (not found_next_field):
            print "Skipping hit at " + hex(hit) + " - cannot find PHONE2 field"
            continue # can't find next field so skip this hit
        funi.seek(fb.tell())
        phonestring2 = read_nullterm_unistring(funi)
        if (phonestring2 == ""):
            print "Skipping hit at " + hex(hit) + " - cannot read PHONE2 field"
            continue # skip this hit if empty string
        #print phonestring2

        offset_after_string = funi.tell()
        found_next_field = goto_next_field(fb, offset_after_string, 3)
        if (not found_next_field):
            print "Skipping hit at " + hex(hit) + " - cannot find PHONE3 field"
            continue # can't find next field so skip this hit
        funi.seek(fb.tell())
        phonestring3 = read_nullterm_unistring(funi)
        if (phonestring3 == ""):
            print "Skipping hit at " + hex(hit) + " - cannot read PHONE3 field"
            continue # skip this hit if empty string
        #print phonestring3
        #print "Number(s): " + phonestring1 + ", " + phonestring2 + ", " + phonestring3

        offset_after_string = funi.tell()
        found_next_field = goto_next_field(fb, offset_after_string, 3)
        if (not found_next_field):
            print "Skipping hit at " + hex(hit) + " - cannot find Received text field"
            continue # can't find next field so skip this hit

        string_offset = fb.tell()
        funi.seek(string_offset)
        unistring = read_nullterm_unistring(funi)
        #print "Text (" + hex(string_offset).rstrip("L")  +"): " + unistring

    timeval = 0
    if (nums_listed == 0):
        # Original method: Manual adjustment of FILETIME2 offset value
        # Offsets between begin of FILETIME2 and begin of "SMStext" string for Sent SMS 
        # MAD: 0xBF | OH: 0xB4 | DUB1: 0xBF | DUB2: 0xB4 bytes
        # WARNING: Might need to adjust the 0xBF value to suit your data ...
        # Note: Remember there's no PHONE0 field to account for in Sent SMS.
        #filetime2_offset = 0xBF
        #fb.seek(hit - filetime2_offset)
        #timeval = read_filetime(fb)

        # Experimental method. Use test data offsets +/-5 
        # From test data, minimum offset was 0xB4. 
        # Allowing for some tolerance => 0xB4 - 5 = 0xAF as min offset
        # From test data, maximum offset was 0xBF. 
        # Allowing for some tolerance => 0xBF + 5 = 0xC4 as max offset
        # Some adjustment may be required for other data sets
        fb.seek(hit)
        #timeval = find_timestamp(fb, 0xC4, 0xAF)
        timeval = find_timestamp(fb, 0xEA+0x5, 0x7D) # Based on 30AUG DUB data, change the max offset to 0xEA + 5, Based on 1SEP data change min to x7D (from 0xAF)
    if (nums_listed == 1):
        # Old method: This doesnt handle variable length phone numbers
        # Offsets between begin of FILETIME2 and begin of "SMStext" string for Recvd SMS 
        # MAD: 0xEA | OH: 0xDF | DUB1: 0xEC | DUB2: 0xDF bytes
        #fb.seek(hit - 0xEA)
        #timeval = read_filetime(fb)
        #
        # Updated method of calculating FILETIME2 offset using the "PHONE0" field length.
        # This means the script can handle received SMS with variable length phone numbers
        # offset = length of string in bytes + (NULL bytes + "IPM." + 0x01 byte = 0xB) + offset from beginning of FILETIME2 to start of phonestring (=0xC7)
        # This assumes "PHONE0" is same length as "PHONE1" (phonestring)
        # WARNING: Might need to adjust the 0xC7 value to suit your data ... 
        # 0xEA = 12 digit phone number (0x18 bytes) + 0xB + 0xC7
        # 0xEC = 13 digit phone number (0x1A bytes) + 0xB + 0xC7
        #filetime2_offset = len(phonestring)*2 + (0xB) + 0xC7
        #print "filetime2_offset = " + hex(filetime2_offset)
        #fb.seek(hit - filetime2_offset)
        #timeval = read_filetime(fb)
        
        # Experimental method: Use projected min/max from test data
        # From the test data, we can see a maximum offset of 0xEC (236 dec) for 13 digits (ie DUB1). 
        # So for the theoretical maximum of 15 digits, this projects to 0xD4 (240 dec) for 15 digits.
        # Add in some tolerance and we will use 0xFA (250 dec) for our max offset between FILETIME2 and "SMStext"
        # From the test data, we can see a minimum offset of 0xDF (223 dec) for 13 digits (ie DUB2). 
        # So for the theoretical minimum of 1 digit, this projects to 0xC7 (199 dec).
        # Add in some tolerance and we will use 0xBD (189 dec) for our min offset between FILETIME2 and "SMStext"
        fb.seek(hit)
        #timeval = find_timestamp(fb, 0xFA, 0xBD)
        timeval = find_timestamp(fb, 0xFA, 0x9B) # Based on 30AUG DUB data, change the min offset to 0xB8 - 5
        # Based on MPD log file data, changed min offset to 0x9B

    timestring = ""
    if (timeval != 0):
        #print "timeval = " + hex(timeval)
        try:
            # returns time referenced to local system timezone
            #timestring = datetime.datetime.fromtimestamp(timeval).isoformat()
            # returns UTC time
            timestring = datetime.datetime.utcfromtimestamp(timeval).isoformat()
        except:
            timestring = "Error"
    else:
        # something bad happened reading time
        timestring = "Error"
    #print "Time2 (UTC) = " + timestring + "\n"
    
    # If no number listed (ie sent SMS), try grabbing the PHONEX phone number based on the FILETIME2 timestamp retrieved
    if ( (nums_listed == 0) and (timestring != "Error") ):
        phonestring = "Unknown"
        if (timestring in smslogdict.keys()):
            phonestring = smslogdict[timestring]
    
    # Store parsed data in dictionary keyed by SMS string offset
    sms_entries[string_offset] = (timestring, sentflag, phonestring, unistring)

#ends for hits loop

print "\nProcessed " + str(len(hits)) + " SMStext hits\n"

# sort by filetime
sorted_messages_keys = sorted(sms_entries, key = lambda x : (sms_entries[x][0], sms_entries[x][0])) 

# print to TSV
# open contacts output file if reqd
if (options.tsvfile != None):
    try:
        tsvof = open(options.tsvfile, "w")
    except:
        print ("Trouble Opening TSV Output File")
        exit(-1)
    tsvof.write("Text_Offset\tUTC_Time2\tDirection\tPhone_No\tText\n")
    for key in sorted_messages_keys:
        tsvof.write(hex(key).rstrip("L") + "\t" + sms_entries[key][0] + "\t" + sms_entries[key][1] + "\t" + sms_entries[key][2] + "\t" + sms_entries[key][3] + "\n")
    print "\nFinished writing out " + str(len(sorted_messages_keys)) + " TSV entries\n"
    tsvof.close()

funi.close()
fb.close()

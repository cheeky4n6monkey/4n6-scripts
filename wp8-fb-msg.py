#! /usr/bin/env python

# Python script to parse selected Facebook message JSON fields from ASCII & Unicode file dumps
# Initially targeted for WinPhone 8 pagefile.sys.
# It should also handle escaped (ie backslashed) fields. 
#
# Author: cheeky4n6monkey@gmail.com (Adrian Leong)
#
# Special Thanks to Brian McGarry (Garda) for suggesting the script, providing sample test data and testing feedback.

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

# Issues:
# - If the script finds the field marker (eg "author_name") but then there's unprintable values, the script outputs an empty string.
#   However, if the field marker is missing, then it outputs NOT_EXTRACTED.
#   So if you see an empty string in one of the output fields, it probably means that there's some bogus unprintable values for that field.
# - Some adjustment of FUDGE values may be required if you are seeing one of the following messages on the command line:
# "No corresponding author_name field found in range of hit at ..."
# "No corresponding message field found in range of hit at ..."
# "No corresponding timestamp field found in range of hit at ..."
#
# History
# v2014-08-24 Initial version
# v2014-10-05 Renamed script from "fb-msg-parser.py" to "wp8-fb-msg.py"

import sys
import codecs
import datetime
import string
from optparse import OptionParser

version_string = "wp8-fb-msg.py v2014-10-05"

# Max Offset Tolerance (bytes) between author_name and author_fbid fields
AUTHOR_NAME_FUDGE = 40
AUTHOR_NAME_ESC_FUDGE = 60
# Max Offset Tolerance (bytes) between message and author_fbid fields
MSG_FUDGE = 180
MSG_ESC_FUDGE = 240
# Max Offset Tolerance (bytes) between timestamp and author_fbid fields
TIMESTAMP_FUDGE = 2000
TIMESTAMP_ESC_FUDGE = 2500

# Find all indices of a substring in a given string (Python recipe) 
# From http://code.activestate.com/recipes/499314-find-all-indices-of-a-substring-in-a-given-string/
def all_indices(bigstring, substring, listindex=[], offset=0):
    i = bigstring.find(substring, offset)
    while i >= 0:
        listindex.append(i)
        i = bigstring.find(substring, i + 1)

    return listindex

# Reads ASCII/Unicode encoded string given file.
# Returns read string or "Error!"
def extract_string(f, isASCII=True):
    flag = True
    readstrg = ""
    readchar = ""
    quotecount = 0
    begin = f.tell()

    while (flag):
        try:
            readchar = f.read(1)
            if (readchar not in string.printable):
                flag = False # Bailout on unprintable character
            elif (readchar == "\""): 
                quotecount = quotecount + 1 # Keep track of " quotes
                readstrg += readchar
            elif ((readchar == ",") and ((quotecount % 2) == 0)): # bailout if , char and not in " quotes
                flag = False
            elif (flag):
                readstrg += readchar
        except:
            if (isASCII):
                print "Bad ASCII string at offset " + hex(begin).rstrip("L")
            else:
                print "Bad Unicode string at offset " + hex(begin).rstrip("L")
            exctype, value = sys.exc_info()[:2]
            print ("Exception type = ",exctype,", value = ",value) 
            readstrg = "Error!"
            return readstrg

    return readstrg

# Main
print "Running " + version_string + "\n"
usage = "Usage: %prog -f inputfile -o outputfile -u"

# Handle command line args
parser = OptionParser(usage=usage)
parser.add_option("-f", dest="filename", 
                  action="store", type="string",
                  help="Input File To Be Searched")
parser.add_option("-o", dest="tsvfile",
                  action="store", type="string",
                  help="Tab Separated Output Filename")
parser.add_option("-u", dest="unicode",
                  action="store_true", 
                  help="(Optional) Input file is Unicode encoded")
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

try:
    # Open input file for binary reads
    fb = open(options.filename, mode="rb")
    if (options.unicode):
        # Open input file for unicode encoded text reads (if required)
        funi = codecs.open(options.filename, encoding="utf-16-le", mode="r")
except:
    print ("Problems Opening Input File")
    exctype, value = sys.exc_info()[:2]
    print ("Exception type = ",exctype,", value = ",value) 
    exit(-1)

# read file into one big BINARY string
filestring = fb.read()
# search the big file string for the hex equivalent of the required labels
# ASCII "author_fbid": = \x22\x61\x75\x74\x68\x6F\x72\x5F\x66\x62\x69\x64\x22\x3A
if (options.unicode):
    author_fbid_label =  "\x22\x00\x61\x00\x75\x00\x74\x00\x68\x00\x6F\x00\x72\x00\x5F\x00\x66\x00\x62\x00\x69\x00\x64\x00\x22\x00\x3A\x00"
    author_fbid_label_esc =  "\x5C\x00\x22\x00\x61\x00\x75\x00\x74\x00\x68\x00\x6F\x00\x72\x00\x5F\x00\x66\x00\x62\x00\x69\x00\x64\x00\x5C\x00\x22\x00\x3A\x00"
else:
    author_fbid_label =  "\x22\x61\x75\x74\x68\x6F\x72\x5F\x66\x62\x69\x64\x22\x3A"
    author_fbid_label_esc =  "\x5C\x22\x61\x75\x74\x68\x6F\x72\x5F\x66\x62\x69\x64\x5C\x22\x3A"

author_fbid_hits = all_indices(filestring, author_fbid_label, [])
author_fbid_esc_hits = all_indices(filestring, author_fbid_label_esc, [])

# ASCII "author_name": = \x22\x61\x75\x74\x68\x6F\x72\x5F\x6E\x61\x6D\x65\x22\x3A
if (options.unicode):
    author_name_label = "\x22\x00\x61\x00\x75\x00\x74\x00\x68\x00\x6F\x00\x72\x00\x5F\x00\x6E\x00\x61\x00\x6D\x00\x65\x00\x22\x00\x3A\x00"
    author_name_label_esc = "\x5C\x00\x22\x00\x61\x00\x75\x00\x74\x00\x68\x00\x6F\x00\x72\x00\x5F\x00\x6E\x00\x61\x00\x6D\x00\x65\x00\x5C\x00\x22\x00\x3A\x00"
else:
    author_name_label = "\x22\x61\x75\x74\x68\x6F\x72\x5F\x6E\x61\x6D\x65\x22\x3A"
    author_name_label_esc = "\x5C\x22\x61\x75\x74\x68\x6F\x72\x5F\x6E\x61\x6D\x65\x5C\x22\x3A"

author_name_hits = all_indices(filestring, author_name_label, [])
author_name_esc_hits = all_indices(filestring, author_name_label_esc, [])

# ASCII "message": = \x22\x6D\x65\x73\x73\x61\x67\x65\x22\x3A
if (options.unicode):
    message_label = "\x22\x00\x6D\x00\x65\x00\x73\x00\x73\x00\x61\x00\x67\x00\x65\x00\x22\x00\x3A\x00"
    message_label_esc = "\x5C\x00\x22\x00\x6D\x00\x65\x00\x73\x00\x73\x00\x61\x00\x67\x00\x65\x00\x5C\x00\x22\x00\x3A\x00"
else:
    message_label = "\x22\x6D\x65\x73\x73\x61\x67\x65\x22\x3A"
    message_label_esc = "\x5C\x22\x6D\x65\x73\x73\x61\x67\x65\x5C\x22\x3A"

message_hits = all_indices(filestring, message_label, [])
message_esc_hits = all_indices(filestring, message_label_esc, [])

# ASCII "timestamp": = \x22\x74\x69\x6D\x65\x73\x74\x61\x6D\x70\x22\x3A
if (options.unicode):
    timestamp_label = "\x22\x00\x74\x00\x69\x00\x6D\x00\x65\x00\x73\x00\x74\x00\x61\x00\x6D\x00\x70\x00\x22\x00\x3A\x00" 
    timestamp_label_esc = "\x5C\x00\x22\x00\x74\x00\x69\x00\x6D\x00\x65\x00\x73\x00\x74\x00\x61\x00\x6D\x00\x70\x00\x5C\x00\x22\x00\x3A\x00"
else:
    timestamp_label = "\x22\x74\x69\x6D\x65\x73\x74\x61\x6D\x70\x22\x3A" 
    timestamp_label_esc = "\x5C\x22\x74\x69\x6D\x65\x73\x74\x61\x6D\x70\x5C\x22\x3A"

timestamp_hits = all_indices(filestring, timestamp_label, [])
timestamp_esc_hits = all_indices(filestring, timestamp_label_esc, [])

print "Found author_fbid_hits = " + str(len(author_fbid_hits))
print "Found author_fbid_esc_hits = " + str(len(author_fbid_esc_hits))

print "\nFound author_name_hits = " + str(len(author_name_hits))
print "Found author_name_esc_hits = " + str(len(author_name_esc_hits))

print "\nFound message_hits = " + str(len(message_hits))
print "Found message_esc_hits = " + str(len(message_esc_hits))

print "\nFound timestamp_hits = " + str(len(timestamp_hits))
print "Found timestamp_esc_hits = " + str(len(timestamp_esc_hits))

messages = {}

# Handle non-escaped hits
for idx in range(len(author_fbid_hits)):
    if (options.unicode):
        funi.seek(author_fbid_hits[idx]+0x1C)
        author_fbid = extract_string(funi, False)

        closest_author_name_hit = 0
        author_name = "NOT_EXTRACTED"
        for i in range(len(author_name_hits)):
            if ( (author_name_hits[i] > author_fbid_hits[idx]) and 
                ((author_name_hits[i] - author_fbid_hits[idx]) < 2*AUTHOR_NAME_FUDGE) ):
                closest_author_name_hit = author_name_hits[i]
                break;
        if (closest_author_name_hit != 0):
            funi.seek(closest_author_name_hit+0x1C)
            author_name = extract_string(funi, False)
        else:
            print "No corresponding author_name field found in range of hit at " +  hex(author_fbid_hits[idx]).rstrip("L")

        closest_message_hit = 0
        message = "NOT_EXTRACTED"
        for i in range(len(message_hits)):
            if ( (message_hits[i] > author_fbid_hits[idx]) and 
                ((message_hits[i] - author_fbid_hits[idx]) < 2*MSG_FUDGE) ):
                closest_message_hit = message_hits[i]
                break;
        if (closest_message_hit != 0):
            funi.seek(closest_message_hit+0x14)
            message = extract_string(funi, False)
        else:
            print "No corresponding message field found in range of hit at " +  hex(author_fbid_hits[idx]).rstrip("L")

        closest_timestamp_hit = 0
        timestamp_src = "NOT_EXTRACTED"
        for i in range(len(timestamp_hits)):
            if ( (timestamp_hits[i] > author_fbid_hits[idx]) and 
                ((timestamp_hits[i] - author_fbid_hits[idx]) < 2*TIMESTAMP_FUDGE) ):
                closest_timestamp_hit = timestamp_hits[i]
                break;
        if (closest_timestamp_hit != 0):
            funi.seek(closest_timestamp_hit+0x18)
            timestamp_src = extract_string(funi, False)
        else:
            print "No corresponding timestamp field found in range of hit at " +  hex(author_fbid_hits[idx]).rstrip("L")
    else:
        # ASCII processing
        fb.seek(author_fbid_hits[idx]+0xE)
        author_fbid = extract_string(fb)

        closest_author_name_hit = 0
        author_name = "NOT_EXTRACTED"
        for i in range(len(author_name_hits)):
            if ( (author_name_hits[i] > author_fbid_hits[idx]) and 
                ((author_name_hits[i] - author_fbid_hits[idx]) < AUTHOR_NAME_FUDGE) ):
                closest_author_name_hit = author_name_hits[i]
                break;
        if (closest_author_name_hit != 0):
            fb.seek(closest_author_name_hit+0xE)
            author_name = extract_string(fb)
        else:
            print "No corresponding author_name field found in range of hit at " +  hex(author_fbid_hits[idx]).rstrip("L")

        closest_message_hit = 0
        message = "NOT_EXTRACTED"
        for i in range(len(message_hits)):
            if ( (message_hits[i] > author_fbid_hits[idx]) and 
                ((message_hits[i] - author_fbid_hits[idx]) < MSG_FUDGE) ):
                closest_message_hit = message_hits[i]
                break;
        if (closest_message_hit != 0):
            fb.seek(closest_message_hit+0xA)
            message = extract_string(fb)
        else:
            print "No corresponding message field found in range of hit at " +  hex(author_fbid_hits[idx]).rstrip("L")
        
        closest_timestamp_hit = 0
        timestamp_src = "NOT_EXTRACTED"
        for i in range(len(timestamp_hits)):
            if ( (timestamp_hits[i] > author_fbid_hits[idx]) and 
                ((timestamp_hits[i] - author_fbid_hits[idx]) < TIMESTAMP_FUDGE) ):
                closest_timestamp_hit = timestamp_hits[i]
                break;
        if (closest_timestamp_hit != 0):
            fb.seek(closest_timestamp_hit+0xC)
            timestamp_src = extract_string(fb)
        else:
            print "No corresponding timestamp field found in range of hit at " +  hex(author_fbid_hits[idx]).rstrip("L")

    timestamp_str = "Unknown"
    if ((timestamp_src != "Error!") and (timestamp_src != "NOT_EXTRACTED")):
        try:
            ts_int = int(timestamp_src) # convert str to int
            timestamp_flt = float( ts_int // 1000 ) # convert ms to seconds
            #print "timestamp_flt = " + str(timestamp_flt)
            timestamp_str = datetime.datetime.utcfromtimestamp(timestamp_flt).isoformat()
        except:
            exctype, value = sys.exc_info()[:2]
            print ("Timestamp Exception type = ",exctype,", value = ",value) 
            timestamp_str = "Error" # if we get here, the date at this offset is not valid
    else:
        timestamp_str = "NOT_EXTRACTED"

    # print "author_fbid = " + author_fbid
    # print "author_name = " + author_name
    # print "message = " + message
    # print "timestamp_src = " + timestamp_src
    # print "timestamp_str = " + timestamp_str

    messages[author_fbid_hits[idx]] = (author_fbid, author_name, message, timestamp_src, timestamp_str)
#ends for non-escaped hits

# Handle escaped hits
for idx in range(len(author_fbid_esc_hits)):
    if (options.unicode):
        funi.seek(author_fbid_esc_hits[idx]+0x20)
        author_fbid = extract_string(funi, False)

        closest_author_name_hit = 0
        author_name = "NOT_EXTRACTED"
        for i in range(len(author_name_esc_hits)):
            if ( (author_name_esc_hits[i] > author_fbid_esc_hits[idx]) and 
                ((author_name_esc_hits[i] - author_fbid_esc_hits[idx]) < 2*AUTHOR_NAME_ESC_FUDGE) ):
                closest_author_name_hit = author_name_esc_hits[i]
                break;
        if (closest_author_name_hit != 0):
            funi.seek(closest_author_name_hit+0x20)
            author_name = extract_string(funi, False)
        else:
            print "No corresponding author_name field found in range of hit at " +  hex(author_fbid_esc_hits[idx]).rstrip("L")

        closest_message_hit = 0
        message = "NOT_EXTRACTED"
        for i in range(len(message_esc_hits)):
            if ( (message_esc_hits[i] > author_fbid_esc_hits[idx]) and 
                ((message_esc_hits[i] - author_fbid_esc_hits[idx]) < 2*MSG_ESC_FUDGE) ):
                closest_message_hit = message_esc_hits[i]
                break;
        if (closest_message_hit != 0):
            funi.seek(closest_message_hit+0x18)
            message = extract_string(funi, False)
        else:
            print "No corresponding message field found in range of hit at " +  hex(author_fbid_esc_hits[idx]).rstrip("L")

        closest_timestamp_hit = 0
        timestamp_src = "NOT_EXTRACTED"
        for i in range(len(timestamp_esc_hits)):
            if ( (timestamp_esc_hits[i] > author_fbid_esc_hits[idx]) and 
                ((timestamp_esc_hits[i] - author_fbid_esc_hits[idx]) < 2*TIMESTAMP_ESC_FUDGE) ):
                closest_timestamp_hit = timestamp_esc_hits[i]
                break;
        if (closest_timestamp_hit != 0):
            funi.seek(closest_timestamp_hit+0x1C)
            timestamp_src = extract_string(funi, False)
        else:
            print "No corresponding timestamp field found in range of hit at " +  hex(author_fbid_esc_hits[idx]).rstrip("L")
    else:
        # ASCII processing
        fb.seek(author_fbid_esc_hits[idx]+0x10)
        author_fbid = extract_string(fb)

        closest_author_name_hit = 0
        author_name = "NOT_EXTRACTED"
        for i in range(len(author_name_esc_hits)):
            if ( (author_name_esc_hits[i] > author_fbid_esc_hits[idx]) and 
                ((author_name_esc_hits[i] - author_fbid_esc_hits[idx]) < AUTHOR_NAME_ESC_FUDGE) ):
                closest_author_name_hit = author_name_esc_hits[i]
                break;
        if (closest_author_name_hit != 0):
            fb.seek(closest_author_name_hit+0x10)
            author_name = extract_string(fb)
        else:
            print "No corresponding author_name field found in range of hit at " +  hex(author_fbid_esc_hits[idx]).rstrip("L")

        closest_message_hit = 0
        message = "NOT_EXTRACTED"
        for i in range(len(message_esc_hits)):
            if ( (message_esc_hits[i] > author_fbid_esc_hits[idx]) and 
                ((message_esc_hits[i] - author_fbid_esc_hits[idx]) < MSG_ESC_FUDGE) ):
                closest_message_hit = message_esc_hits[i]
                break;
        if (closest_message_hit != 0):
            fb.seek(closest_message_hit+0xC)
            message = extract_string(fb)
        else:
            print "No corresponding message field found in range of hit at " +  hex(author_fbid_esc_hits[idx]).rstrip("L")
        
        closest_timestamp_hit = 0
        timestamp_src = "NOT_EXTRACTED"
        for i in range(len(timestamp_esc_hits)):
            if ( (timestamp_esc_hits[i] > author_fbid_esc_hits[idx]) and 
                ((timestamp_esc_hits[i] - author_fbid_esc_hits[idx]) < TIMESTAMP_ESC_FUDGE) ):
                closest_timestamp_hit = timestamp_esc_hits[i]
                break;
        if (closest_timestamp_hit != 0):
            fb.seek(closest_timestamp_hit+0xE)
            timestamp_src = extract_string(fb)
        else:
            print "No corresponding timestamp field found in range of hit at " +  hex(author_fbid_esc_hits[idx]).rstrip("L")

    timestamp_str = "Unknown"
    if ((timestamp_src != "Error!") and (timestamp_src != "NOT_EXTRACTED")):
        try:
            ts_int = int(timestamp_src) # convert str to int
            timestamp_flt = float( ts_int // 1000 ) # convert ms to seconds
            #print "timestamp_flt = " + str(timestamp_flt)
            timestamp_str = datetime.datetime.utcfromtimestamp(timestamp_flt).isoformat()
        except:
            exctype, value = sys.exc_info()[:2]
            print ("Timestamp Exception type = ",exctype,", value = ",value) 
            timestamp_str = "Error" # if we get here, the date at this offset is not valid
    else:
        timestamp_str = "NOT_EXTRACTED"

    # print "author_fbid = " + author_fbid
    # print "author_name = " + author_name
    # print "message = " + message
    # print "timestamp_src = " + timestamp_src
    # print "timestamp_str = " + timestamp_str

    messages[author_fbid_esc_hits[idx]] = (author_fbid, author_name, message, timestamp_src, timestamp_str)
# end for escaped hits

# sort by timestamp_src
sorted_calls_keys = sorted(messages, key = lambda x : (messages[x][3], messages[x][3])) 

# print to TSV (utf8 encoded)
# open contacts output file if reqd
if (options.tsvfile != None):
    try:
        tsvof = open(options.tsvfile, "w")
    except:
        print ("Trouble Opening TSV Output File")
        exit(-1)
    tsvof.write("author_fbid_Offset\tauthor_fbid\tauthor_name\tmessage\ttimestamp_src\ttimestamp_str\n")
    for key in sorted_calls_keys:
        tsvof.write(hex(key).rstrip("L") + "\t" + messages[key][0] + "\t" + messages[key][1] + "\t" + messages[key][2] + \
        "\t" + messages[key][3]+ "\t" + messages[key][4] + "\n")
    print "\nFinished writing out TSV"
    tsvof.close()


if (options.unicode):
    funi.close()
fb.close()

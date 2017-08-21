#! /usr/bin/env python

"""
Author: Adrian Leong (cheeky4n6monkey@gmail.com)

Tutorial Python v2/v3 script to print (fictional) Contact records from test file.

Fictional Contact Record format:
Record Entry Marker field "ctx!" = x63x74x78x21 in Hex
Index Number field (2 byte LE unsigned int)
Name Length field (1 byte unsigned int)
Name String field (UTF16LE encoded string)
Phone Length field (1 byte unsigned int)
Phone String field (UTF8 encoded string)
Unix Timestamp field (4 byte LE unsigned int)

"""

import struct
import datetime

version_string = "unpack-tute.py v2017-08-19"
print("Running " + version_string + "\n")

filename = "testctx.bin"
try:
	fb = open(filename, "rb") # read-only in binary mode
except:
    print("Error - Input file failed to open!")
    exit(-1)

# Read file into one variable (file should not/cannot be too large)
filecontent = fb.read()

# Search the filecontent variable for the hex equivalent of "ctx!" which appears in each record.
# Doing it this way allows us to change the searchstring variable to search for different raw hex patterns eg "\x11\x22\x00"
searchstring = "\x63\x74\x78\x21" # "ctx!" in ASCII/UTF8

# For Python2, we could just use: nexthit = filecontent.find(searchstring, 0)
# However, Python3 compatibility requires we call the searchstring.encode() to encode searchstring to UTF8 before calling "find". 
nexthit = filecontent.find(searchstring.encode('utf-8'), 0) # returns -1 if substring not found otherwise returns offset where hit found
hitlist = []

# loop iterates thru filecontent looking for hits and
# bailsout the first time it does not find the searchstring
while nexthit >= 0: 
    hitlist.append(nexthit)
    nexthit = filecontent.find(searchstring.encode(), nexthit + 1)

# hitlist should now contain a list of offsets where "ctx!" was found
for hit in hitlist:
    print("\nHit found at offset: " + str(hit) + " decimal = " + hex(hit) + " hex")
    # 1st field ("Index Number") occurs 4 bytes AFTER beginning of "ctx!" and uses 2 LE bytes
    indexnum_offset = hit + 4
    # "indexnum_offset:(indexnum_offset+2)" means indexnum_offset, indexnum_offset+1 ONLY. It does not include (indexnum_offset+2) byte
    indexnum = struct.unpack("<H", filecontent[indexnum_offset:(indexnum_offset+2)])[0] # LE 2 byte unsigned integer
    print("indexnum = " + str(indexnum))
    # 2nd field ("Name Length") starts after 2 byte "Index Number" field
    namelength_offset = indexnum_offset + 2
    print("namelength_offset = " + str(namelength_offset))
    namelength = struct.unpack("B", filecontent[namelength_offset:(namelength_offset+1)])[0] # 1 byte contains size of name string (in bytes)
    print("namelength = " + str(namelength))
    # 3rd field ("Name String") starts after 1 byte "Name Length" field
    namestring_offset = namelength_offset + 1
    # decode string slice as UTF16LE
    namestring = filecontent[namestring_offset:(namestring_offset+namelength)].decode('utf-16-le')
    print("namestring = " + namestring)
    # 4th field ("Phone Length") starts after "Name String" field ends ("Name Length" bytes)
    phonelength_offset = namestring_offset + namelength
    phonelength = struct.unpack("B", filecontent[phonelength_offset:(phonelength_offset+1)])[0] # 1 byte contains size of phone string (in bytes)
    print("phonelength = " + str(phonelength))
    # 5th field ("Phone String") starts after 1 byte "Phone Length" field 
    phonestring_offset = phonelength_offset + 1
    print("phonestring_offset = " + str(phonestring_offset))
    # decode string slice as UTF8 (could also just print slice without the decode call)
    phonestring = filecontent[phonestring_offset:(phonestring_offset+phonelength)].decode('utf-8')
    print("phonestring = " + phonestring)
    # 6th field ("Unix Timestamp") starts after "Phone String" field ends
    timestamp_offset = phonestring_offset + phonelength
    print("timestamp_offset = " + str(timestamp_offset))
    # Unix timestamp is LE unsigned 4 byte representing seconds since 1JAN1970
    # eg LE x56xDBxCDx26 = 1457245478 decimal = Sun, 06 March 2016 06:24:38 UTC
    timestamp = struct.unpack("<I", filecontent[timestamp_offset:(timestamp_offset+4)])[0] 
    print("raw timestamp decimal value = " + str(timestamp))
    # Now we call the datetime.utcfromtimestamp function to return a human readable ISO formatted string from the raw timestamp value
    timestring = datetime.datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%dT%H:%M:%S")
    print("timestring = " + timestring)

fb.close() 

print("\nProcessed " + str(len(hitlist)) + " ctx! hits. Exiting ...\n")

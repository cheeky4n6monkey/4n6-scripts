#! /usr/bin/env python

# dextract.py = Python script to extract data according to a template definition file
#
# Copyright (C) 2013 Adrian Leong (cheeky4n6monkey@gmail.com)
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
# Version History:
# v2013-12-11 Initial Version

# Instructions:
# (Mandatory) Use the -f argument to specify the input file you wish to search
# (Mandatory) Use the -t argument to specify the template definition file (specifies field offsets from a known search term field)
# (Optional) Use the -o argument to output results to the specified Tab Seperated Variable file
# (Optional) Use the -a argument to specify a start offset (decimal). Default value is 0.
# (Optional) Use the -z argument to specify an end offset (decimal). Default value is end of file.
#
# It was developed/tested on SIFT v2.14 (Ubuntu 9.10 Karmic) running Python v2.6.4.
#
# Usage Example:
# python dextract.py -f /mnt/hgfs/SIFT_WORKSTATION_2.14_SHARE/meow.bin -d meow.def -o meow.tsv -a 350 -z 428
#
# References:
# http://sandersonforensics.com/forum/content.php?131-A-brief-history-of-time-stamps
#

import sys
import datetime
import struct
from optparse import OptionParser
import os
import string

import pprint

version_string = "dextract v2013-12-11 Initial Version"

# Global variables for storing template definition file values
field_names = [] # stores field_names 
num_types_dict = {} # stores num_types (keyed by field_name)
type_dict = {} # stores types (keyed by field_name)

# Function to return unpack string & size of type declared in template definition file.
# Will return 0 for unknown types and deferred types. eg something with size set
# to "msgsize"
def find_type_size(strg):
    #print strg + ", len = " + str(len(strg))
    if (strg.upper() == ">Q" or strg.upper() == "Q" or strg.upper() == "<Q"):
        return strg, 8
    elif (strg.upper() == ">D" or strg.upper() == "D" or strg.upper() == "<D"):
        return strg, 8
    elif (strg.upper() == ">F" or strg.upper() == "F" or strg.upper() == "<F"):
        return strg, 4    
    elif (strg.upper() == ">L" or strg.upper() == "L" or strg.upper() == "<L"):
        return strg, 4
    elif (strg.upper() == ">I" or strg.upper() == "I" or strg.upper() == "<I"):
        return strg, 4
    elif (strg.upper() == ">H" or strg.upper() == "H" or strg.upper() == "<H"):
        return strg, 2
    elif (strg.upper() == "B"):
        return strg, 1
    elif (strg.upper() == "C"):
        return strg, 1
    elif (strg.upper() == "S"):
        return strg, 1
    elif (strg.upper() == "X"):
        return strg, 1
    elif ((strg.upper() == "UTF16BE") or (strg.upper() == "UTF16LE")):
        return strg, 2
    elif ("OSX32" in strg.upper() or "UNIX32" in strg.upper() or 
            "GPS32" in strg.upper() or "AOL32" in strg.upper() or
            "HFS" in strg.upper()):
        if strg.startswith(">"):
            return ">I", 4
        elif strg.startswith("<"):
            return "<I", 4
        else:
            return "I", 4
    elif ("UNIX48MS" in strg.upper()):
        return "6B", 6 # this is just a placeholder so UNIX48MS doesn't return 0 (error)
    elif ("UNIX10DIGDEC" in strg.upper()):
        return "5B", 5 # this is just a placeholder so doesn't return 0 (error)
    elif ("UNIX13DIGDEC" in strg.upper()):
        return "7B", 7 # this is just a placeholder so doesn't return 0 (error)
    elif ("BCD12" in strg.upper()):
        return "6B", 6 # this is just a placeholder so doesn't return 0 (error)
    elif ("BCD14" in strg.upper()):
        return "7B", 7 # this is just a placeholder so doesn't return 0 (error)        
    elif ("DOSDATE" in strg.upper()):
        return "<I", 4 # this is just a placeholder so doesn't return 0 (error)
    else:
        return "Unknown", 0
#ends find_type_size

# Returns ISO date string (YYY-MM-DDThh:mm:ss) given a raw value and date field type.
# "val" will usually be an integer value. Except for BCD type datetimes which require a string
# and DOSDATE which requires 2 shorts combined in 1 int.
def calc_date(val, field):
    datetimestr = ""
    if ("OSX32" in type_dict[field].upper()):
        # difference between 1jan1970 and 1jan2001 = 978307200 secs
        #print "OSX32 date string is: " + datetime.datetime.fromtimestamp(val + 978307200).strftime('%Y-%m-%dT%H:%M:%S')
        try: 
            datetimestr = datetime.datetime.fromtimestamp(val + 978307200).strftime('%Y-%m-%dT%H:%M:%S')
        except:
            datetimestr = "Unknown"
        return (datetimestr)
    elif ( ("UNIX32" in type_dict[field].upper()) or ("UNIX10DIGDEC" in type_dict[field].upper()) ):
        #print "UNIX date string is: " + datetime.datetime.fromtimestamp(val).strftime('%Y-%m-%dT%H:%M:%S')
        try: 
            datetimestr = datetime.datetime.fromtimestamp(val).strftime('%Y-%m-%dT%H:%M:%S')
        except:
            datetimestr = "Unknown"
        return (datetimestr)        
    elif ("GPS32" in type_dict[field].upper()):
        # difference between 1jan1970 and 6jan1980 = 315964800 secs
        #print "GPS32 date string is: " + datetime.datetime.fromtimestamp(val + 315964800).strftime('%Y-%m-%dT%H:%M:%S')
        try: 
            datetimestr = datetime.datetime.fromtimestamp(val + 315964800).strftime('%Y-%m-%dT%H:%M:%S')
        except:
            datetimestr = "Unknown"
        return (datetimestr)
    elif ("AOL32" in type_dict[field].upper()):
        # difference between 1jan1970 and 1jan1980 = 315532800 secs
        #print "AOL32 date string is: " + datetime.datetime.fromtimestamp(val + 315532800).strftime('%Y-%m-%dT%H:%M:%S')
        try: 
            datetimestr = datetime.datetime.fromtimestamp(val + 315532800).strftime('%Y-%m-%dT%H:%M:%S')
        except:
            datetimestr = "Unknown"
        return (datetimestr)
    elif ("HFS32" in type_dict[field].upper()):
        # difference between 1jan1904 and 1jan1970 = 2082844800 secs
        #print "HFS32 date string is: " + datetime.datetime.fromtimestamp(val - 2082844800).strftime('%Y-%m-%dT%H:%M:%S')
        try: 
            datetimestr = datetime.datetime.fromtimestamp(val - 2082844800).strftime('%Y-%m-%dT%H:%M:%S')
        except:
            datetimestr = "Unknown"
        return (datetimestr)
    elif ( ("UNIX48MS" in type_dict[field].upper()) or ("UNIX13DIGDEC" in type_dict[field].upper()) ):
        #print "UNIX48MS/UNIX13DIGDEC date string is: " + datetime.datetime.fromtimestamp(val/1000.0).strftime('%Y-%m-%dT%H:%M:%S')
        try: 
            datetimestr = datetime.datetime.fromtimestamp(val/1000.0).strftime('%Y-%m-%dT%H:%M:%S')
        except:
            datetimestr = "Unknown"
        return (datetimestr)
    elif ("BCD12" in type_dict[field].upper()):
        #print "Raw BCD12 string is: " + val
        # Assumes BCD12 is BE eg 071231125423 = 31DEC2007T12:54:23 = yymmddhhmnss
        try:
            yy = int(val[0:2])
            mm = int(val[2:4])
            dd = int(val[4:6])
            hh = int(val[6:8])
            mn = int(val[8:10])
            ss = int(val[10:])
            year = 2000 + yy
            #print "BCD12 date is: " + datetime.datetime(year, mm, dd, hh, mn, ss).strftime('%Y-%m-%dT%H:%M:%S')
            datetimestr = datetime.datetime(year, mm, dd, hh, mn, ss).strftime('%Y-%m-%dT%H:%M:%S')
        except:
            datetimestr = "Unknown"
        return (datetimestr)
    elif ("BCD14" in type_dict[field].upper()):
        #print "Raw BCD14 string is: " + val
        # Assumes BCD14 is BE eg 20071231125423 = 31DEC2007T12:54:23 = yyyymmddhhmnss
        try:
            yy = int(val[0:4])
            mm = int(val[4:6])
            dd = int(val[6:8])
            hh = int(val[8:10])
            mn = int(val[10:12])
            ss = int(val[12:])
            #print "BCD14 date is: " + datetime.datetime(yy, mm, dd, hh, mn, ss).strftime('%Y-%m-%dT%H:%M:%S')
            datetimestr = datetime.datetime(yy, mm, dd, hh, mn, ss).strftime('%Y-%m-%dT%H:%M:%S')
        except:
            datetimestr = "Unknown"
        return (datetimestr)
    elif ("DOSDATE" in type_dict[field].upper()):
        # For ease of processing, relies on extract_DOSdate returning an int in LE form 
        # (regardless of raw hex string being BE/LE)
        # The "default" LE int data struct has 2 words (in order) DATE, TIME
        # The "word swapped" LE int data struct has 2 words (in order) TIME, DATE
        # Where DATE = 16 bit word => (msb) 7bit Year since 1980, 4bit month, 5bit day (lsb)
        # Where TIME = 16 bit word => (msb) 5bit Hours, 6bit minutes, 5bit seconds x 2 (lsb)
        #print "DD val = %0x" % val
        if ("DOSDATE_DEFAULT" in type_dict[field].upper()): # "normal" DOSDATE
            datehalf = val >> 16
            timehalf = val & 0xFFFF
        elif ("DOSDATE_WORDSWAPPED" in type_dict[field].upper()): # word swapped DOSDATE
            timehalf = val >> 16
            datehalf = val & 0xFFFF
        else:
            return ("Unknown")
        #print "datehalf = %0x" % datehalf
        #print "timehalf = %0x" % timehalf
                
        ss = ( (timehalf & 0b11111)*2); #LSB 5bits (0...4) x 2 equals secs
        if (ss == 60):
            ss = 59
        mn = ( ((timehalf & 0b11111100000) >> 5)); #6bits (5...10) equals minutes
        hh = ( ((timehalf & 0b1111100000000000) >> 11)); #5bits (11...15) equals hours
        dd = ( (datehalf & 0b11111)); #5bits (0...4) equals day
        mm = ( ((datehalf & 0b111100000) >> 5)); #4bits (5...8) equals month
        yy = ( ((datehalf & 0b1111111000000000) >> 9)+1980); #7bits (9...16)+1980 equals year    
        
        try:
            datetimestr = datetime.datetime(yy, mm, dd, hh, mn, ss).strftime('%Y-%m-%dT%H:%M:%S')
        except:
            datetimestr = "Unknown"
        return (datetimestr)
    else:
        #print "Unknown Date Format!"
        return ("Unknown Date Format")
#ends calc_date

# Extract 6 byte ms since 1JAN1970. No python type for 6 byte int so we roll our own :(
# Returns the number of ms since 1JAN1970
def extract_unix48ms(f, isLE):
    stringval = ""
    for j in range(6):
        val = struct.unpack("B", f.read(1))[0]
        stringval += ("%02x" % val)
        
    stringval = "%012x" % int(stringval, 16)
    # We should now have a hex string we can calculate a value from 
    # BE eg "013C1E44FC18" = dec 1357717503000
    # LE eg "18FC441E3C01"
    if (isLE):
        adjustedstring = ""
        # LE requires some monkeying around ... reverse string (in groups of 2 chars) and then process
        for j in range(12, 0, -2):
            adjustedstring += stringval[j-2:j]
        value = int(adjustedstring, 16)
    else:
        # BE is easier
        value = int(stringval, 16)
    return(value)
#ends extract_unix48ms

# Extract 10 digit decimal secs since 1JAN1970. Assumes BE for now eg 0x1170245478 = 1170245478 decimal secs
# Returns the number of secs since 1JAN1970
def extract_unix10digdec(f):
    unix_decimal_10_string = ""
    for j in range(5):
        val = struct.unpack("B", f.read(1))[0]
        unix_decimal_10_string += ("%02x" % val)
    
    try:    
        unix_decimal_10_int = int(unix_decimal_10_string) # now convert string "1170245478" to decimal int
    except:
        print "Bad int cast in extract_unix10digdec"
        unix_decimal_10_int = -1
    return(unix_decimal_10_int)
#ends extract_unix10digdec

# Extract 13 digit decimal ms since 1JAN1970. Assumes BE for now eg 0x01170245478000 = 01170245478000 ms
# Returns the number of ms since 1JAN1970
def extract_unix13digdec(f):
    unix_decimal_13_string = ""
    for j in range(7):
        val = struct.unpack("B", f.read(1))[0]
        unix_decimal_13_string += ("%02x" % val)
    
    try:    
        unix_decimal_13_int = int(unix_decimal_13_string) # now convert string "01170245478000" to decimal int
    except:
        print "Bad int cast in extract_unix13digdec"
        unix_decimal_13_int = -1
    return(unix_decimal_13_int)
#ends extract_unix13digdec

# Extract 6 byte raw BCD 12 digit date. Assumes BE for now eg 071231125423 = 31DEC2007T12:54:23
# Returns raw date string eg 071231125423
def extract_BCD12(f):
    BCD_date_string = ""
    for j in range(6):
        val = struct.unpack("B", f.read(1))[0]
        BCD_date_string += ("%02x" % val)

    return (BCD_date_string)
#ends extract_BCD12

# Extract 7 byte raw BCD 14 digit date. Assumes BE for now eg 20071231125423 = 31DEC2007T12:54:23
# Returns raw date string eg 20071231125423
def extract_BCD14(f):
    BCD_date_string = ""
    for j in range(7):
        val = struct.unpack("B", f.read(1))[0]
        BCD_date_string += ("%02x" % val)

    return (BCD_date_string)
#ends extract_BCD14

# Extracts DOSDATE. Returns a LE int representing the 2 shorts (Date and Time).
def extract_DOSdate(f, isLE):
    result = 0
    result1 = 0
    result2 = 0
    if (isLE):
        # eg date is 2007-05-04T12:09:42
        # For LE "normal" DOSDATE raw value 0x36 A4 61 35
        # 36A4 = Date and 6135 = Time 
        # eg For LE "word swapped" DOSDATE raw value 0x61 35 36 A4
        # 36A4 = Date and 6135 = Time
        try:
            result1, result2 = struct.unpack(">HH", f.read(4))
            result = (result1 << 16) + result2
        except:
            print "Error extracting LE DOSdate"
        # result retains original word order ie Date, Time for "normal" and
        # Time, Date for "word swapped"
    else:
        # eg date is 2007-05-04T12:09:42
        # For BE "normal" DOSDATE raw value 0x35 61 A4 36
        # 36A4 = Date and 6135 = Time
        # For BE "word swapped" DOSDATE raw value 0xA4 36 35 61
        # 36A4 = Date and 6135 = Time
        # So need to swap words around and also swap byte order
        # to get result in form of Date, Time for "normal" or
        # Time, Date form for "word swapped"
        try:
            result1, result2 = struct.unpack("<HH", f.read(4)) 
            result = (result2 << 16) + result1
        except:
            print "Error extracting BE DOSdate"
    #consequently "result" returned should look like 0x36 A4 61 35
    # ie date then time for BE "normal" and
    # 0x61 35 36 A4 for BE "word swapped"
    return(result)
#ends extract_DOSdate

# Extract strings with known sizes (ie numeric strings only. Not null terminated or deferred)
def extract_defined_string(field, f, filename):
    value = ""
    size = int(num_types_dict[field])
    fieldoffset = f.tell()
    if (type_dict[field].upper() == "S"):
        pattern = num_types_dict[field] + type_dict[field] # eg pattern is "140s" for "140 | s" template
        try:
            value = struct.unpack(pattern, f.read(size))[0]
            # ensure string is printable
            if (all(c in string.printable for c in value)):
                print filename + ":" + str(fieldoffset) + ", defined str field = " + field + ", value = " + str(value)
            else:
                value = ""
                print filename + ":" + str(fieldoffset) + " " + field + " is unprintable"
        except:
            value = ""
            print filename + ":" + str(fieldoffset) + " " + field + " - Error extracting string"
    elif ( (type_dict[field].upper() == "UTF16BE") or (type_dict[field].upper() == "UTF16LE") ):
        data = f.read(size)
        decodestr = ""
        if (type_dict[field].upper() == "UTF16LE"):
            decodestr = "UTF-16LE"
        else:
            decodestr = "UTF-16BE"
        try:
            value = data.decode(decodestr)
            if (all(c in string.printable for c in value)):
                print filename + ":" + str(fieldoffset) + ", defined " + decodestr + " str field = " + field + ", value = " + str(value)
            else:
                value = ""
                print filename + ":" + str(fieldoffset) + " " + field + " is unprintable"
        except:
            print filename + ":" + str(fieldoffset) + " " + field + " - Error extracting " + decodestr + " str field"
            value = ""
    return(value)
#ends extract_defined_string

# Extract strings with deferred sizes only. Not null terminated or numerical
def extract_deferred_string(field, f, size, filename):
    value = ""
    fieldoffset = f.tell()
    if (type_dict[field].upper() == "S"):
        pattern = str(size) + "s" # eg pattern is "140s" for "msgsize | s" template where msgsize = 140
        try:
            value = struct.unpack(pattern, f.read(size))[0]
            # ensure string is printable
            if (all(c in string.printable for c in value)):
                print filename + ":" + str(fieldoffset) + ", deferred str field = " + field + ", value = " + str(value)
            else:
                value = ""
                print filename + ":" + str(fieldoffset) + " " + field + " is unprintable"
        except:
            value = ""
            print filename + ":" + str(fieldoffset) + " " + field + " - Error extracting deferred string"
    elif ( (type_dict[field].upper() == "UTF16BE") or (type_dict[field].upper() == "UTF16LE") ):
        data = f.read(size)
        decodestr = ""
        if (type_dict[field].upper() == "UTF16LE"):
            decodestr = "UTF-16LE"
        else:
            decodestr = "UTF-16BE"
        try:
            value = data.decode(decodestr)
            if (all(c in string.printable for c in value)):
                print filename + ":" + str(fieldoffset) + ", deferred " + decodestr + " str field = " + field + ", value = " + str(value)
            else:
                value = ""
                print filename + ":" + str(fieldoffset) + " " + field + " is unprintable"
        except:
            print filename + ":" + str(fieldoffset) + " " + field + " - Error extracting deferred "+ decodestr + " str field"
            value = ""
    return(value)
#ends extract_deferred_string

# Extract strings with null terminations only. Not deferred or numerical
def extract_nullterm_string(field, f, filename):
    # Handle null terminated ascii strings with unknown sizes, ignores unprintable chars
    value = ""
    tmp = ""
    fieldoffset = f.tell()
    fileinfo = os.stat(filename)
    #print "Input file " + filename + " is %d bytes" % fileinfo.st_size + "\n"
    if (type_dict[field].upper() == "S"): # ascii string
        while ((tmp != "\x00") and (f.tell() < fileinfo.st_size)):
            tmp = f.read(1)
            if ((tmp != "\x00") and (tmp in string.printable)):
                value += tmp
        print filename + ":" + str(fieldoffset) + ", nullterm str field = " + field + ", value = " + str(value)
    elif ( (type_dict[field].upper() == "UTF16BE") or (type_dict[field].upper() == "UTF16LE") ):
        stringdata = ""
        decodestr = ""
        if (type_dict[field].upper() == "UTF16LE"):
            decodestr = "UTF-16LE"
        else:
            decodestr = "UTF-16BE"
            
        while ((tmp != "\x00\x00") and (f.tell() < fileinfo.st_size)):
            tmp = f.read(2)
            if ((tmp != "\x00\x00")):
                stringdata += tmp
        try:
            value = stringdata.decode(decodestr)
            if (all(c in string.printable for c in value)):
                print filename + ":" + str(fieldoffset) + ", nullterm " + decodestr + " str field = " + field + ", value = " + str(value)
            else:
                value = ""
                print filename + ":" + str(fieldoffset) + " " + field + " is unprintable"
        except:
            print filename + ":" + str(fieldoffset) + " " + field + " - Error extracting nullterm " + decodestr + " str field"
            value = ""
    return(value)
#ends extract_nullterm_string    
    
# Function to parse each record and extract/print data according to the template file
# returns True if record fields parsed OK, False if there were major errors parsing
def parse_record(f, hit):
    extracted_vals = {} # local dict of numerical extracted values keyed by field name (used for storing/retrieving deferred sized strings)
    fileinfo = os.stat(filename) # used for determining filesize
    
    for field in field_names:
        #check field isn't past end of file
        fieldoffset = f.tell()
        if (fieldoffset > fileinfo.st_size):
            print "Calculated Field offset for " + field + " is greater than " + str(fileinfo.st_size) + " ... stopping"
            return False

        patn, tsize = find_type_size(type_dict[field])
        #print "pattern = " + patn + ", tsize = " + str(tsize)
        # Check field type size, if 0 check it hasn't been deferred eg "msgsize"
        if (tsize == 0):
            if not (field in extracted_vals.keys()):
                print "Bad Type declared for " + field + " ... Skipping"
                continue # skip to next field
                
        if (type_dict[field].upper() == "X"): # Dont care about these X bytes ...
            skipsize = 0
            if (not num_types_dict[field].isdigit()):
                # handle deferred X sizes (allows for dynamic skipping vs fixed length skipping)
                skipsize = int(extracted_vals[num_types_dict[field]]) # retrieve size from previously extracted values dict
            else:
                skipsize = int(num_types_dict[field])
            if ((fieldoffset + skipsize) < fileinfo.st_size):
                print "Skipping " + str(skipsize) + " bytes ..."
                newseek = fieldoffset+ skipsize
                f.seek(newseek)
            else:
                print "Cannot skip " + field + " - specified offset (" + str(fieldoffset+skipsize) + ") too large!"
                return False # Bailout of function cos something is wrong
        elif ( (num_types_dict[field] == "0") and ((type_dict[field].upper() == "S") or (type_dict[field].upper() == "UTF16BE") or
                (type_dict[field].upper() == "UTF16LE")) ):
            # Handle null terminated strings with unknown (ie 0) sizes, ignores unprintable chars
            unknownstring = extract_nullterm_string(field, f, filename)
            if (tsvoutput):
                of.write(filename + "\t" + str(fieldoffset) + "\t" + field + "\t" + 
                         unknownstring + "\t\n")
        elif ( (not num_types_dict[field].isdigit()) and ((type_dict[field].upper() == "S") or (type_dict[field].upper() == "UTF16BE") or
                (type_dict[field].upper() == "UTF16LE")) ):
            # Handle strings with deferred size eg "msgsize" is defined in another field
            if (num_types_dict[field] in extracted_vals):
                size = int(extracted_vals[num_types_dict[field]]) # retrieve size from previously extracted values dict
                value = extract_deferred_string(field, f, size, filename)
                if (tsvoutput):
                    of.write(filename + "\t" + str(fieldoffset) + "\t" + field + "\t" + str(value) + "\t\n")
            else:
                print num_types_dict[field] + " is unknown and cannot be used to extract the " + field + " field ... skipping"
        elif ( (num_types_dict[field].isdigit()) and ((type_dict[field].upper() == "S") or (type_dict[field].upper() == "UTF16BE") or
                (type_dict[field].upper() == "UTF16LE")) ):
            # Handle strings with numeric sizes declared
            value = extract_defined_string(field, f, filename)
            if (tsvoutput):
                of.write(filename + "\t" + str(fieldoffset) + "\t" + field + "\t" + str(value) + "\t\n")
        elif ("UNIX48MS" in type_dict[field].upper()):
            # Handle 6 byte ms since 1JAN1970.
            value = extract_unix48ms(f, type_dict[field].startswith("<"))
            datefield = calc_date(value, field)
            print filename + ":" + str(fieldoffset) + ", UNIX48MS field = " + field + ", value = " + str(value) + ", interpreted value = " + datefield
            if (tsvoutput):
                of.write(filename + "\t" + str(fieldoffset) + "\t" + field + "\t" + 
                         str(value) + "\t" + datefield + "\n")
        elif ("UNIX10DIGDEC" in type_dict[field].upper()):
            # Handle 10 digit decimal secs since 1JAN1970. eg 0x1170245478
            value = extract_unix10digdec(f)
            datefield = calc_date(value, field)
            print filename + ":" + str(fieldoffset) + ", UNIX10DIGDEC field = " + field + ", value = " + str(value) + ", interpreted value = " + datefield
            if (tsvoutput):
                of.write(filename + "\t" + str(fieldoffset) + "\t" + field + "\t" + 
                         str(value) + "\t" + datefield + "\n")
        elif ("UNIX13DIGDEC" in type_dict[field].upper()):
            # Handle 13 digit decimal ms since 1JAN1970. eg 0x1170245478000
            value = extract_unix13digdec(f)
            datefield = calc_date(value, field)
            print filename + ":" + str(fieldoffset) + ", UNIX13DIGDEC field = " + field + ", value = " + str(value) + ", interpreted value = " + datefield
            if (tsvoutput):
                of.write(filename + "\t" + str(fieldoffset) + "\t" + field + "\t" + 
                         str(value) + "\t" + datefield + "\n")
        elif ("BCD12" in type_dict[field].upper()):
            # Handle 6 byte 12 digit BCD date eg 071231125423 = 31DEC2007T12:54:23
            value = extract_BCD12(f)
            datefield = calc_date(value, field)
            print filename + ":" + str(fieldoffset) + ", BCD12 field = " + field + ", value = " + str(value) + ", interpreted value = " + datefield
            if (tsvoutput):
                of.write(filename + "\t" + str(fieldoffset) + "\t" + field + "\t" + 
                         str(value) + "\t" + datefield + "\n")
        elif ("BCD14" in type_dict[field].upper()):
            # Handle 7 byte 14 digit BCD date eg 020071231125423 = 31DEC2007T12:54:23
            value = extract_BCD14(f)
            datefield = calc_date(value, field)
            print filename + ":" + str(fieldoffset) + ", BCD14 field = " + field + ", value = " + str(value) + ", interpreted value = " + datefield
            if (tsvoutput):
                of.write(filename + "\t" + str(fieldoffset) + "\t" + field + "\t" + 
                         str(value) + "\t" + datefield + "\n")
        elif ("DOSDATE" in type_dict[field].upper()):
            value = extract_DOSdate(f, type_dict[field].startswith("<"))
            datefield = calc_date(value, field)
            print filename + ":" + str(fieldoffset) + ", DOSDATE field = " + field + ", value = " + str(value) + ", interpreted value = " + datefield
            if (tsvoutput):
                of.write(filename + "\t" + str(fieldoffset) + "\t" + field + "\t" + 
                         str(value) + "\t" + datefield + "\n")
        else:
            # handle everything else with single fields that can be "unpacked" 
            # ie other dates and numbers which don't require specialized interpretation
            size = int(tsize)
            try:
                value = struct.unpack(patn, f.read(size))[0]
                extracted_vals[field] = value # store numerical values in case we need it later eg deferred string sizes
                #print "extracted field = " + field + "... value = " + str(value)
            except:
                print "Error extracting data! Offset = " + str(fieldoffset) + ", Field = " + field
                print patn
                return False # bailout of function. We're getting errors for the simplest case. 
                
            # output 32 bit int dates
            if ("OSX32" in type_dict[field].upper() or "UNIX32" in type_dict[field].upper() or
                "GPS32" in type_dict[field].upper() or "AOL32" in type_dict[field].upper() or
                "HFS32" in type_dict[field].upper()):
                datefield = calc_date(value, field)
                
                print filename + ":" + str(fieldoffset) + ", field = " + field + ", value = " + str(value) + ", interpreted date value = " + datefield
                if (tsvoutput):
                    of.write(filename + "\t" + str(fieldoffset) + "\t" + field + "\t" + 
                             str(value) + "\t" + datefield + "\n")
            else:
                # output other non-string / non-date values (ints, floats)
                print filename + ":" + str(fieldoffset) + ", field = " + field + ", value = " + str(value)
                if (tsvoutput):
                    of.write(filename + "\t" + str(fieldoffset) + "\t" + field + "\t" + 
                             str(value) + "\t\n")
    return True # ie all fields for record parsed without major error
#ends parse_record fn

# ==============================================================================
# Main
print "Running " + version_string + "\n"

usage = "\n" + "Usage#1: %prog -d defnfile -f inputfile\n" + "Usage#2: %prog -d defnfile -f inputfile -a 350 -z 428 -o outputfile"

parser = OptionParser(usage=usage)
parser.add_option("-d", dest="defn",
                  action="store", type="string",
                  help="Template Definition File")
parser.add_option("-f", dest="filename", 
                  action="store", type="string",
                  help="Input File To Be Searched")
parser.add_option("-o", dest="tsvfile",
                  action="store", type="string",
                  help="(Optional) Tab Seperated Output Filename")
parser.add_option("-a", dest="startoffset", default=0,
                  action="store", type="int",
                  help="(Optional) Starting File Offset (decimal). Default is 0.")
parser.add_option("-z", dest="endoffset",
                  action="store", type="int", default=-1,
                  help="(Optional) End File Offset (decimal). Default is the end of file.")
(options, args) = parser.parse_args()

# Check if no arguments given by user, exit
if len(sys.argv) == 1:
    parser.print_help()
    exit(-1)
if ( (options.filename == None) or (options.defn == None) ):
    parser.print_help()
    print "\nDefinition/Input filename incorrectly specified!"
    exit(-1)

filename = options.filename
defnfile = options.defn
tsvoutput = options.tsvfile
startoffset = options.startoffset

fileinfo = os.stat(filename)
print "Input file " + filename + " is %d bytes" % fileinfo.st_size + "\n"
if (options.endoffset == -1): # default case ie end offset "z" was not specified
    endoffset = fileinfo.st_size
else:
    endoffset = options.endoffset
    
#open template definition file
try:
    tmpf = open(defnfile, "r")
except:
    print ("Template File Not Found")
    exit(-1)

tmpf.seek(0)

# open source data file
try:
    f = open(filename, "rb")
except:
    print ("Input File Not Found")
    exit(-1)
f.seek(0)

# open output file if reqd
if (tsvoutput != None):
    try:
        of = open(tsvoutput, "w")
    except:
        print ("Trouble Opening Output File")
        exit(-1)

# write header for output file
if (tsvoutput != None):
    of.write("Filename\tFile_Offset\tField_Name\tRaw_Value\tInterpreted_Value\n")

#read in types from definition file and store
ln = "init"
while ln != "":
    ln = tmpf.readline()
    #print ln
    if ( (not ln.startswith("#")) and (" | " in ln) and (ln != "\n") ):
        name, size, vartype = ln.rstrip('\n').split(" | ", 2)
        field_names.append(name)
        num_types_dict[name] = size # has to handle "msgsize"
        type_dict[name] = vartype
        #print "name = " + name + ", size = " + num_types_dict[name] + ", vartype = " + type_dict[name]
    #elif ln != "":
        #print "Comment is: " + ln

tmpf.close()

if (len(field_names) == 0) :
    print "No fields specified in template definition file. Exiting"
    exit(-1)

# From startoffset until endoffset, extract the record data
curroffset = startoffset
status = True
f.seek(curroffset)
while ((curroffset < endoffset) and status):
    status = parse_record(f, curroffset)
    curroffset = f.tell()
    
f.close()

if (tsvoutput):
    of.close()

print "\nExiting ..."
exit(0)

# Ends Main
# ==============================================================================

#! /usr/bin/env python

# Python script to print Android Manifest permission strings from an .apk file/directory containing .apk files
# Copyright (C) 2015 Adrian Leong (cheeky4n6monkey@gmail.com)
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
# Tested on Ubuntu x64 with Python 2.7 and .apks from Android 4.4.2 and 5.1.1 devices
#
# Resources:
# http://www.olafdietsche.de/2015/05/11/exploring-android-binary-xml-file-format
# http://blog.androidsec.org/index.php/2013/06/17/the-binary-androidmanifest-xml-file-part-1/
# http://blog.androidsec.org/index.php/2014/01/24/binary-androidmanifest-xml-file-part-2/
# http://developer.android.com/guide/topics/manifest/manifest-intro.html#perms

import os
import sys
import argparse
import zipfile
import struct

RESXMLTREE_HDR_OFFSET = 0
RESXMLTREE_HDR_SZ_OFFSET = 2
RESSTRINGPOOL_HDR_OFFSET = 8
RESSTRINGPOOL_STR_COUNT_OFFSET = 16
RESSTRINGPOOL_STR_START_OFFSET = 28 # offset to start of 1st pool string (ie first string's size LE 2 bytes)
RESSTRINGPOOL_STR_0_OFFSET = 36 # offset to section of string offsets (each offset is LE 4 bytes)


# Functions
# ==========================
# Given filename, parses it for Android Permission strings and prints it in file offset order (by default).
# If sort_by_name is True, permissions are printed in alphabetical order.
# If printall is True, all strings are printed (for debugging).
def parse_apk_perms(filename, sort_by_name=False, printall=False) :
    if zipfile.is_zipfile(filename):
        print("Input apk file " + filename + " checked OK!")
    else:
        print(filename + " = Bad Input apk file!")
        return

    z = zipfile.ZipFile(filename, "r")
    for j in z.infolist(): # for each file in zipfile
        #print (j.filename + ", " + str(j.file_size))
        if ("AndroidManifest.xml" in j.filename):
            manifestfile = z.open(j.filename, "r")
            manifestdata = manifestfile.read()

            # Manifest file struct is: 64 bit ResXMLTree_header [type (u16), headerSize (u16), size (u32)]
            # then 64 bit ResStringPool_header [type (u16), headerSize (u16), size (u32), 
            #  stringCount (u32), styleCount (u32), flags (u32), stringsStart (u32), stylesStart (u32)]
            # then stringCount x u32 offsets

            # Check ResXMLTree_header type field
            first_hdr_type = struct.unpack("<H", \
                manifestdata[RESXMLTREE_HDR_OFFSET : RESXMLTREE_HDR_OFFSET+2])[0]
            if (first_hdr_type != 0x03):
                print("Bad ResXMLTree header type (not 0x0003)")
                return
            else:
                print("First header type check OK!")

            # Check ResStringPool header type field
            sec_hdr_type = struct.unpack("<H", \
                manifestdata[RESSTRINGPOOL_HDR_OFFSET : RESSTRINGPOOL_HDR_OFFSET+2])[0]
            if (sec_hdr_type != 0x01):
                print("Bad ResStringPool header type (not 0x0001)")
                return
            else:
                print("Second header type check OK!")

            # Extract string count
            string_count = struct.unpack("<I", \
                manifestdata[RESSTRINGPOOL_STR_COUNT_OFFSET : \
                             RESSTRINGPOOL_STR_COUNT_OFFSET+4])[0]
            #print("string_count = " + str(string_count))

            # Extract offset to first pool string (relative to RESSTRINGPOOL_HDR_OFFSET)
            string_start_offset = struct.unpack("<I", \
                manifestdata[RESSTRINGPOOL_STR_START_OFFSET : \
                             RESSTRINGPOOL_STR_START_OFFSET+4])[0]
            #print("string_start_offset = " + str(string_start_offset))

            # Extract string offsets section into a list
            # These offsets are relative to RESSTRINGPOOL_STR_START_OFFSET
            # ie For String 0, go to RESSTRINGPOOL_STR_START_OFFSET then add String 0 offset
            # to get to String 0's size (followed by UTF16LE encoded String 0).
            string_offsets = []
            for n in range(string_count):
                offset = struct.unpack("<I", \
                    manifestdata[RESSTRINGPOOL_STR_0_OFFSET+n*4 : \
                                 RESSTRINGPOOL_STR_0_OFFSET+(n*4)+4])[0]
                string_offsets.append(offset)

            #print string_offsets
            permsdict = {} # storage dict keyed by file offset for later printing

            # Read strings using string_offset addresses
            # Each string is preceded by a LE u16 size (in number of chars)
            # This does not include the NULL term at the end of the string.
            # So when reading the actual string, the read length in bytes = string_size*2
            for n in range(string_count):
                string_size = struct.unpack("<H", \
                    manifestdata[RESSTRINGPOOL_HDR_OFFSET+string_start_offset+string_offsets[n] : \
                                 RESSTRINGPOOL_HDR_OFFSET+string_start_offset+string_offsets[n]+2])[0]
                #print("string_size = " + str(string_size))
                permstring = manifestdata[RESSTRINGPOOL_HDR_OFFSET+string_start_offset+string_offsets[n]+2 : \
                    RESSTRINGPOOL_HDR_OFFSET+string_start_offset+string_offsets[n]+2+string_size*2]
                #print("permstring = " + permstring)

                if (printall):
                    # Store every UTF16LE string in dict for later printing
                    permsdict[RESSTRINGPOOL_HDR_OFFSET+string_start_offset+string_offsets[n]+2] = permstring 
                # manifestdata and permstring is utf_16_le encoded so need 
                # to utf_16_le encode our substring search terms before testing for
                # any string containing ".permission" or "com.android."
                elif ((".permission".encode('utf_16_le') in permstring) or \
                     ("com.android.".encode('utf_16_le') in permstring)) :
                    # only store string if it contains a permission related strings
                    permsdict[RESSTRINGPOOL_HDR_OFFSET+string_start_offset+string_offsets[n]+2] = permstring

            if (sort_by_name):
               # Sort keys by permission name then print in that order
                print("Sorted by permname ...")
                print("Filename\tPermission_Offset\tPermission_String")
                print("==============================================================")
                # sorted() returns dict key list sorted by the permission name (permsdict[x])
                sorted_by_perm_keys = sorted(permsdict, key = lambda x : permsdict[x])
                for key in sorted_by_perm_keys:
                    print(filename + ":AndroidManifest.xml\t" + str(hex(key)) + "\t" + permsdict[key])
            else :
                print("Sorted by offset ...")
                print("Filename\tPermission_Offset\tPermission_String")
                print("==============================================================")
                # sorted() returns dict key list sorted by the file offset (x)
                sorted_by_offset_keys = sorted(permsdict, key = lambda x : x)
                for key in sorted_by_offset_keys:
                    print(filename + ":AndroidManifest.xml\t" + str(hex(key)) + "\t" + permsdict[key])
 
    return
# ends parse_apk_perms


# Main
# ==========================
parser = argparse.ArgumentParser(description='Print Android Manifest permission strings from an .apk file/directory containing .apk files')
parser.add_argument("target", help='Target .apk / directory containing .apks')
parser.add_argument('-s', action="store_true", default=False, help='Print permissions sorted by name (default is sorted by offset)')
parser.add_argument('-d', action="store_true", default=False, help='Prints ALL strings for debugging (default is OFF)')
args = parser.parse_args()

version_string = "print_apk_perms.py v2015-06-13"
print "\nRunning " + version_string

print("Source file = " + args.target)
if (args.s):
    print("Output will be ordered by Permission string")
else:
    print("Output will be ordered by AndroidManifest.xml file offset")

if (os.path.isdir(args.target)):
    # for each file in folder (includes subfolders)
    parsecount = 0
    for root, dirs, files in os.walk(args.target):
        for name in files:
            fullname = os.path.join(root, name)
            print("\nAttempting to parse " + fullname)
            try:
               parse_apk_perms(fullname, args.s, args.d)
               parsecount += 1
            except :
                print("*** WARNING Cannot parse " + fullname + "\n")
                exctype, value = sys.exc_info()[:2]
                print("Exception type = ",exctype,", value = ",value) 
                continue # keep looping if theres an error
    print("\nParsed " + str(parsecount) + " .apk files")
else:
    # must be a single file arg
    print("\nAttempting to open single file " + args.target)
    try:
        parse_apk_perms(args.target, args.s, args.d)
    except :
        print("*** WARNING Cannot parse " + args.target + "\n")
        exctype, value = sys.exc_info()[:2]
        print("Exception type = ",exctype,", value = ",value) 



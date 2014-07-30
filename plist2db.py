
# plist2db.py = Python script to extract XML/binary plist data to an SQLite Database
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
# Version History:
#  Initial Version - Requires plistlib from Python 3.4
# 
# Instructions:
# (Mandatory) Use the -f argument to specify the plist file/directory to extract from
# (Mandatory) Use the -d argument to specify the output SQLite Database
#
# Usage Examples:
# python3 plist2db.py -f /home/cheeky/plistdir -d plist.sqlite
# python3 plist2db.py -f com.apple.example.plist -d plist.sqlite
#
# References:
# http://en.wikipedia.org/wiki/Property_list
# https://developer.apple.com/library/mac/documentation/CoreFoundation/Conceptual/CFPropertyLists/Articles/StructureAndContents.html#//apple_ref/doc/uid/20001171-CJBEJBHH
# http://docs.python.org/3.4/library/plistlib.html#module-plistlib
#

import sys
import plistlib
import sqlite3
import datetime
import os
from optparse import OptionParser

rowdata = []

# Recursive function populates global "rowdata" list with data from given plist object 
# ("obj") as initially returned by plistlib.readPlist.
# "re-used/adapted" from:
# http://code.activestate.com/recipes/578094-recursively-print-nested-dictionaries/
# Inputs:
#   plistfilename = filename of plist
#   obj = object to print (can be dict, list, string, boolean, datetime, int)
#   key = Default "". Stores dict key name eg "City". Used also to build nested paths
#   path = Default "". Stores full path for key value eg "\\City\\Suburb"
#
def print_object(plistfilename, obj, key = "", path = ""):
    if isinstance(obj, dict):
        # Handles CFDictionary
        for keyname, value in obj.items():
            p = path + "\\" + str(keyname)
            # Call function again for each item value in dict 
            # eg each key/value in dict (including sub-dicts).
            print_object(plistfilename, value, keyname, p)
    elif isinstance(obj, list):
        # Handles CFArray
        #print(str(obj) + " obj is a list = " + str(len(obj)))
        if len(obj) > 0:
            for litem in obj:
                print_object(plistfilename, litem, key, path)
        else:
            #print(str(plistfilename) + ":" + str(path) + " is an empty list")
            row = [plistfilename, str(path), ""] # top level of array has no value
            rowdata.extend([row])
    elif isinstance(obj, str): # Handles CFStrings
        #print(str(path) + " = " + str(obj))
        row = [plistfilename, str(path), str(obj)]
        rowdata.extend([row])
    elif isinstance(obj, int): # Handles CFNumbers (int). CFBooleans also appear as ints
        #print("int: " + str(path) + " = " + str(obj))
        row = [plistfilename, str(path), str(obj)]
        rowdata.extend([row])
    elif isinstance(obj, float): # Handles CFNumbers (real)
        #print("float: " + str(path) + " = " + str(obj))
        row = [plistfilename, str(path), str(obj)]
        rowdata.extend([row])        
    elif isinstance(obj, datetime.datetime): # CFDate extracted as Python datetime
        #print("datetime: " + str(path) + " = " + str(obj))
        row = [plistfilename, str(path), str(obj)]
        rowdata.extend([row])    
    elif isinstance(obj, bytes): # CFData handled/extracted as Python "bytes"
        # create hex string by printing each byte in bytes object as a 2 digit hex string
        newstr = ' '.join(["%02X" % x for x in obj])
        #print("bytes: " + str(path) + " = " + newstr)
        row = [plistfilename, str(path), newstr]
        rowdata.extend([row])
    else:
        # Most 3rd party types (eg MS Office FileAlias) should resolve as "bytes" above.
        # If we get here, something is funky ... so make a note of it in both the DB and output
        print("*** WARNING " + str(plistfilename) + ":" + str(path) + " is an Unknown type " + str(type(obj)))
        row = [plistfilename, str(path), "*** Unknown Type ***"]
        rowdata.extend([row]) 
    #endelse
#end print_object function


# Main
# ==============================================================================
version_string = "plist2db.py v2014-07-24"
print ("Running ", version_string, "\n")

usage = "Usage: %prog -f plist -d database"

parser = OptionParser(usage=usage)
parser.add_option("-f", dest="filename", 
                  action="store", type="string",
                  help="XML/Binary Plist file or directory containing Plists")
parser.add_option("-d", dest="dbase",
                  action="store", type="string",
                  help="SQLite database to extract Plist data to")

(options, args) = parser.parse_args()

#no arguments given by user, exit
if len(sys.argv) == 1:
    parser.print_help()
    exit(-1)

if (options.filename == None) or (options.dbase == None):
    parser.print_help()
    print("\nPlist filename or Database not specified!")
    exit(-1)

if (os.path.isdir(options.filename)):
    # for each file in folder (includes subfolders)
    for root, dirs, files in os.walk(options.filename):
        for name in files:
                fullname = os.path.join(root, name)
                f = open(fullname, "rb")
                try:
                    pl = plistlib.load(f)
                    f.close()
                    print_object(fullname, pl)
                except plistlib.InvalidFileException:
                    print("*** WARNING " + fullname + " is not a valid Plist!\n")
                    continue
else:
    # must be a single Plist file
    try:
        f = open(options.filename, "rb")
        pl = plistlib.load(f)
        f.close()
        print_object(options.filename, pl)
    except plistlib.InvalidFileException:
        print("*** WARNING " + options.filename + " is not a valid Plist!\n")
    
if (len(rowdata)):
    con = sqlite3.connect(options.dbase)
    # Create the table
    con.execute("CREATE TABLE IF NOT EXISTS plists(filename TEXT NOT NULL, name TEXT NOT NULL, value TEXT NOT NULL, PRIMARY KEY (filename, name, value) )")
    # Fill the table
    con.executemany("REPLACE INTO plists(filename, name, value) VALUES (?, ?, ?)", rowdata)
    con.commit()
    con.close()
else:
    print("No Plist items were found / Database has not been created/updated\n")

exit(0)


#! /usr/bin/env python

# samsung_gallery3d_trash_parser_v10.py = Python script to parse a Samsung com.sec.android.gallery3d's (v10) local.db trash table
#
# Based on research by Michael Lacombe (iacismikel@gmail.com)
#
# Author: cheeky4n6monkey@gmail.com
#
# Version History:
# v2021-11-06 Initial Version
# v2021-11-12 Changed timestamp strings to be separated by space not T
#
# Developed/tested on Ubuntu 20x64 running Python 3.8 using sample data provided by Michael Lacombe.
#
# Usage Example:
# python samsung_gallery3d_trash_parser_v10.py -d local.db -o output.TSV
#

import argparse
import sqlite3
from os import path
import base64
import re
import datetime
import json

version_string = "samsung_gallery3d_trash_parser_v10.py v2021-11-12"


def main():
    usagetxt = " %(prog)s [-d inputfile -o outputfile]"
    parser = argparse.ArgumentParser(description='Extracts/parses data from com.sec.android.gallery3d\'s (v10) local.db\'s trash table to output TSV file', usage=usagetxt)
    parser.add_argument("-d", dest="database", action="store", required=True, help='SQLite DB filename i.e. local.db')
    parser.add_argument("-o", dest="output", action="store", required=True, help='Output file name for Tab-Separated-Value report')

    args = parser.parse_args()

    print("Running " + version_string + "\n")
    
    if not args.database or not args.output:
        parser.exit("ERROR - Input file or Output file NOT specified")
    
    # Check DB file exists before trying to connect
    if path.isfile(args.database):
        dbcon = sqlite3.connect(args.database)
    else:
        print(args.database + " DB file does not exist!")
        exit(-1)

    query = "SELECT __absID, __absPath, __Title, __originPath, __originTitle, __deleteTime, __restoreExtra FROM trash ORDER BY __deleteTime ASC;"
    cursor = dbcon.cursor()
    cursor.execute(query)
    row = cursor.fetchone()

    entries = []

    while row:
        __absID = str(row[0])
        __absPath = row[1]
        __Title = row[2]
        __originPath = row[3]
        __originTitle = row[4]
        __deleteTime = row[5] / 1000 # assume in ms since 1JAN1970
        __deleteTimeStr = datetime.datetime.utcfromtimestamp(__deleteTime).strftime("%Y-%m-%d %H:%M:%S.%f")
        #print(__deleteTimeStr)
        __restoreExtra = row[6] # ass-ume JSON formatted data
        restore_data = json.loads(__restoreExtra)
        __cloudTimestamp = restore_data["__cloudTimestamp"] / 1000 # assume in ms since 1JAN1970
        __cloudTimestampStr = datetime.datetime.utcfromtimestamp(__cloudTimestamp).strftime("%Y-%m-%d %H:%M:%S.%f")
        #print(__cloudTimestampStr)
        __dateTaken = restore_data["__dateTaken"] / 1000 # assume in ms since 1JAN1970
        __dateTakenStr = datetime.datetime.utcfromtimestamp(__dateTaken).strftime("%Y-%m-%d %H:%M:%S.%f")
        #print(__dateTakenStr)
        __size = str(restore_data["__size"])
        __mimeType = restore_data["__mimeType"]
        __latitude = str(restore_data["__latitude"])
        __longitude = str(restore_data["__longitude"])
        
        # store each row returned    
        entries.append((__absID, __absPath, __Title, __originPath, __originTitle, __deleteTimeStr, __cloudTimestampStr, __dateTakenStr, __size, __mimeType, __latitude, __longitude))
        
        row = cursor.fetchone()

    cursor.close()
    dbcon.close()

    # Write TSV report
    with open(args.output, "w") as outputTSV:
        outputTSV.write("__absID\t__absPath\t__Title\t__originPath\t__originTitle\t__deleteTime\t__cloudTimestamp\t__dateTaken\t__size\t__mimeType\t__latitude\t__longitude\n")
        
        for entry in entries:
            __absID = entry[0]
            __absPath = entry[1]
            __Title = entry[2]
            __originPath = entry[3]
            __originTitle = entry[4]
            __deleteTimeStr = entry[5]
            __cloudTimestampStr = entry[6]
            __dateTakenStr = entry[7]
            __size = entry[8]
            __mimeType = entry[9]
            __latitude = entry[10]
            __longitude = entry[11]
            
            outputTSV.write(str(__absID + "\t" + __absPath + "\t" + __Title + "\t" + __originPath + "\t" + __originTitle + "\t" + __deleteTimeStr + \
                           "\t" + __cloudTimestampStr + "\t" + __dateTakenStr + "\t" + __size + "\t" + __mimeType + "\t" + __latitude + "\t" + __longitude + "\n"))

    print("\nProcessed/Wrote " + str(len(entries)) + " entries to: " + args.output + "\n")
    print("Exiting ...\n")


if __name__ == "__main__":
    main()




#! /usr/bin/env python

# samsung_gallery3d_filesysmon_parser_v11.py = Python script to parse a Samsung com.sec.android.gallery3d's (v11) filesystem_monitor log table
#
# Based on research by Michael Lacombe (iacismikel@gmail.com)
#
# Author: cheeky4n6monkey@gmail.com
#
# Version History:
# v2021-11-13 Initial Version
# v2021-11-20 Modified decode_path using reversing knowledge
#
# Developed/tested on Ubuntu 20x64 running Python 3.8 using sample data provided by Michael Lacombe.
#
# Usage Example:
# python samsung_gallery3d_filesysmon_parser_v11.py -d local.db -o output.TSV
#

import argparse
import sqlite3
from os import path
import base64
import datetime

version_string = "samsung_gallery3d_filesysmon_parser_v11.py 2021-11-20"


def decode_path(pathstring):
    # function to base64 decode given path string
    found = False
    finalstredit ="ERROR! Failed to decode path"
    #print("input = " + pathstring)
    # remove last 7 letters
    truncated_strg = pathstring[0:-7]
    #print(truncated_strg)
    #print("trunc len = " + str(len(truncated_strg)))

    for i in range(3,7): # remove between 3 to 6 chars from start
        test_strg = truncated_strg[i:] # starts at 4th char at index 3 ... 7th char is at index 6
        try:
            #print("test_strg = " + test_strg)
            b64decodedstr = base64.b64decode(test_strg)
            utf8str = b64decodedstr.decode('UTF-8')
            finalstr = utf8str.replace('\u2605', '').replace('\u25CF', '').replace('\u25C6', '') # remove "Black Star", "Black Circle", "Black Diamond" chars
            if (finalstr.isascii() and finalstr.isprintable() and not ('\"' in finalstr) and not ('\'' in finalstr)):
                print("Found valid path for finalstr = " + finalstr + "\n for: " + test_strg) # found a valid path ...
                finalstredit = finalstr
                found = True
                break
        except Exception as e:
                # error generated trying to decode, keep going
                #print("exception = " + repr(e))
                continue
    
    if not found:
        print("ERROR! Failed to decode path")
    
    return(finalstredit)    
#end decode_path


def main():
    usagetxt = " %(prog)s [-d inputfile -o outputfile]"
    parser = argparse.ArgumentParser(description='Extracts/parses data from com.sec.android.gallery3d\'s (v11) local.db\'s filesystem_monitor table to output TSV file', usage=usagetxt)
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

    query = "SELECT _id, package, date_event_occurred, directory, __data, event_type FROM filesystem_monitor ORDER BY date_event_occurred ASC;"
    cursor = dbcon.cursor()
    cursor.execute(query)
    row = cursor.fetchone()

    entries = []

    while row:
        _id = row[0]
        package = row[1]
        date_event_occurred = row[2]
        directory = row[3]
        __data = row[4]
        event_type = row[5]

        # store each row returned    
        entries.append((_id, package, date_event_occurred, directory, __data, event_type))
        
        row = cursor.fetchone()

    cursor.close()
    dbcon.close()

    # Write TSV report
    with open(args.output, "w") as outputTSV:
        outputTSV.write("__id\tpackage\tdate_event_occurred(readable)\tdirectory\t__data\tevent_type\tbase64_decoded_data\n")
        
        for entry in entries:
            __id = entry[0]
            package = entry[1]
            date_event_occurred = entry[2] # assume ms since 1JAN1970 (unix epoch)
            date_event_occurred_str = datetime.datetime.utcfromtimestamp(int(date_event_occurred)/1000).strftime("%Y-%m-%d %H:%M:%S.%f")
            directory = entry[3]
            __data = entry[4]
            event_type = entry[5]
            
            print("_id = " + str(__id))
            path_str = decode_path(__data)
            #print(path_str)
            
            outputTSV.write(str(__id) + "\t" + package + "\t" + date_event_occurred_str + "\t" + directory + \
                "\t" + __data + "\t" + event_type + "\t" + path_str + "\n")

    print("\nProcessed/Wrote " + str(len(entries)) + " entries to: " + args.output + "\n")
    print("Exiting ...\n")


if __name__ == "__main__":
    main()




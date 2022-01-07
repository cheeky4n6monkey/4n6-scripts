#! /usr/bin/env python

# samsung_gallery3d_log_parser_v10.py = Python script to parse a Samsung com.sec.android.gallery3d's (v10) local.db log table
#
# Based on research by Michael Lacombe (iacismikel@gmail.com)
#
# Author: cheeky4n6monkey@gmail.com
#
# Version History:
# v2021-11-06 Initial Version
# v2021-11-12 Non-padded path length shortened by 7 chars (hardcoded) & location URL parsing
# v2021-11-20 Modified decode_logitem using reversing knowledge
#
# Developed/tested on Ubuntu 20x64 running Python 3.8 using sample data provided by Michael Lacombe.
#
# Usage Example:
# python samsung_gallery3d_log_parser_v10.py -d local.db -o output.TSV
#

import argparse
import sqlite3
from os import path
import base64
import re
import urllib.parse

version_string = "samsung_gallery3d_log_parser_v10.py 2021-11-20"


def decode_logitem(itemstring):
    # function to base64 decode given itemstring
    # eg gZ2M4pePL3Pil490b+KYhXLil49h4piFZ+KYhWXimIUvZeKYhW11bOKYhWHimIV04piFZWTimIUvMC/il49EQ+KXj0nil49N4piFL+KXj0PimIVh4piFbWVy4piFYS/il48y4piFMOKYhTLimIUw4pePMOKXjznil48x4piFNOKYhV8x4piFNuKYhTU04pePMeKXjzYuauKYhXDil49nuJlMxZq

    found = False
    finalstredit ="ERROR! Failed to decode path"
    #print("input = " + itemstring)
    # remove last 7 letters
    truncated_strg = itemstring[0:-7]
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
                print("Found valid path = " + finalstr + "\n for: " + test_strg) # found a valid path ...
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
#end decode_logitem


def process_log(logstring):
    # parse string like:
    # [DELETE_SINGE][1][0][location://albums/fileList?disableRealRatio=true&ids=-1739773001%2C984300772%2C-2131734286&quickView=true&disableTimeLine=true&fromNow=true&position=0&mediaItem=&from_expand=false][gZ2M4pePL3Pil490b+KYhXLil49h4piFZ+KYhWXimIUvZeKYhW11bOKYhWHimIV04piFZWTimIUvMC/il49EQ+KXj0nil49N4piFL+KXj0PimIVh4piFbWVy4piFYS/il48y4piFMOKYhTLimIUw4pePMOKXjznil48x4piFNOKYhV8x4piFNuKYhTU04pePMeKXjzYuauKYhXDil49nuJlMxZq]
    logentries = []
    
    # regex from https://www.geeksforgeeks.org/python-extract-substrings-between-brackets/
    res = re.findall(r'\[.*?\]', logstring)
    numitems = len(res)

    opstring = res[0].replace("[", "").replace("]", "") 
    idx1 = res[1].replace("[", "").replace("]", "") 
    idx2 = res[2].replace("[", "").replace("]", "") 
    location = res[3].replace("[", "").replace("]", "") 
    if not location.startswith("location"): # filters out [EMPTY_EXPIRED][22][22][2020-05-14 00:00:00] & [MOUNTED][57][0][0][/storage/emulated/0]
        location = ""
    #print(location)
    timeline_pos = ""
    timeline_mediaItem = ""
    albums_id = ""
    albums_pos = ""
    albums_count = ""
    # eg [location://timeline?position=9&mediaItem=data%3A%2F%2FmediaItem%2F-575841975&from_expand=false]
    if location.startswith("location://timeline?position"):
        decoded_loc = urllib.parse.parse_qs(location)
        #print(decoded_loc)
        timeline_pos = ' '.join(decoded_loc["location://timeline?position"]) # parse_qs returns a list
        timeline_mediaItem = ' '.join(decoded_loc["mediaItem"])
    # eg [location://albums/fileList?id=-532863272&position=1&count=4]    
    if location.startswith("location://albums/fileList?id"):
        decoded_loc = urllib.parse.parse_qs(location)
        #print(decoded_loc)
        albums_id = ' '.join(decoded_loc["location://albums/fileList?id"])
        albums_pos = ' '.join(decoded_loc["position"])
        if "count=" in location: # count not always present
            albums_count = ' '.join(decoded_loc["count"])
    # eg [location://albums/fileList?disableRealRatio=true&ids=-1739773001%2C984300772%2C-2131734286&quickView=true&disableTimeLine=true&fromNow=true&position=0&mediaItem=&from_expand=false]
    if location.startswith("location://albums/fileList?disableRealRatio=true"):
        decoded_loc = urllib.parse.parse_qs(location)
        #print(decoded_loc)
        albums_id = ' '.join(decoded_loc["ids"])
        albums_pos = ' '.join(decoded_loc["position"])

    decoded_paths = "No Base64 Paths Detected"
    if (numitems > 4):
        # ass-ume at least 5 items in [] so at least one path to base64 decode
        b64items = []
        for idx in range(4, numitems):
            b64items.append(res[idx].replace("[", "").replace("]", "")) # items should store base64 decoded paths
    
        # parse out each base64 encoded path item
        decoded_items = []    
        #print("process_log = " + str(b64items))
        for b64item in b64items:
            if not (b64item.startswith("/storage/emulated/0")): # no base64 decode required if starts with this
                decoded_item = decode_logitem(b64item)
                decoded_items.append(decoded_item)
    
        if (len(decoded_items) > 0):
            decoded_paths = ' '.join(decoded_items)
        
    # almalgamate log data and return data
    logentries.append((opstring, idx1, idx2, location, timeline_pos, timeline_mediaItem, albums_id, albums_pos, albums_count, decoded_paths))
            
    return(logentries)
#end process_log


def main():
    usagetxt = " %(prog)s [-d inputfile -o outputfile]"
    parser = argparse.ArgumentParser(description='Extracts/parses data from com.sec.android.gallery3d\'s (v10) local.db\'s log table to output TSV file', usage=usagetxt)
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

    query = "SELECT _id, __category, __timestamp, __log FROM log ORDER BY __timestamp ASC;"
    cursor = dbcon.cursor()
    cursor.execute(query)
    row = cursor.fetchone()

    entries = []

    while row:
        _id = row[0]
        __category = row[1]
        __timestamp = row[2]
        __log = row[3]

        # store each row returned    
        entries.append((_id, __category, __timestamp, __log))
        
        row = cursor.fetchone()

    cursor.close()
    dbcon.close()

    # Write TSV report
    with open(args.output, "w") as outputTSV:
        outputTSV.write("__id\t__category\t__timestamp\t__log\toperation\tlocation\ttimeline_pos\ttimeline_mediaItem\talbums_id\talbums_pos\talbums_count\tbase64_decoded_paths\n")
        
        for entry in entries:
            _idx = entry[0]
            __category = entry[1]
            __timestamp = entry[2]
            __log = entry[3]
            
            print("_id = " + str(_idx))
            # logdata stores (opstring, idx1, idx2, location, timeline_pos, timeline_mediaItem, albums_id, albums_pos, albums_count, decoded_paths)
            logdata = process_log(__log)
            #print(logdata)
            
            op = ""
            loc = ""
            time_pos = ""
            time_item = ""
            album_id = ""
            album_pos = ""
            album_count = ""
            decoded_paths = ""
            if len(logdata):
                op = logdata[0][0]
                loc = logdata[0][3]
                time_pos = logdata[0][4]
                time_item = logdata[0][5]
                album_id = logdata[0][6]
                album_pos = logdata[0][7]
                album_count = logdata[0][8]
                decoded_paths = logdata[0][9] 
            
            outputTSV.write(str(_idx) + "\t" + str(__category) + "\t" + __timestamp + "\t" + __log + \
                "\t" + op + "\t" + loc + "\t" + time_pos + "\t" + time_item + \
                "\t" + album_id + "\t" + album_pos + "\t" + album_count + "\t" + decoded_paths + "\n")

    print("\nProcessed/Wrote " + str(len(entries)) + " entries to: " + args.output + "\n")
    print("Exiting ...\n")


if __name__ == "__main__":
    main()




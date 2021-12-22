#! /usr/bin/env python
#
# Python script to parse Ford Sync3 unifiedsearch.log for location coordinates
# Based on test data provided by J. EDDY
#
# Author: cheeky4n6monkey@gmail.com
#
# Version History:
# v2021-12-02 Initial Version
# v2021-12-03 Timestamp functionality added
#
# Developed/tested on Win10x64 running Python 3.9.2/3.10 and Ubuntu 20x64 running Python 3.8.10
#
# Usage Example:
# python sync3-unisearch.py -i unifiedsearch.log -o output.TSV
#

import argparse
import re
import datetime

version_string = "sync3-unisearch.py 2021-12-03"

def main():
    usagetxt = " %(prog)s [-i inputfile -o outputfile]"
    parser = argparse.ArgumentParser(description='Parses Ford Sync3 unifiedsearch.log for location coordinates', usage=usagetxt)
    parser.add_argument("-i", dest="inputlog", action="store", required=True, help='unifiedsearch.log')
    parser.add_argument("-o", dest="output", action="store", required=True, help='Output file name for Tab-Separated-Value report')

    args = parser.parse_args()

    print("Running " + version_string + "\n")
    
    locations = []
    current_dt = datetime.datetime(1970, 1, 1)
    
    # Scan log file
    with open(args.inputlog, 'r') as logp:
        data = logp.readlines()
        linenum = 0
        for line in data:
            linenum += 1
            # Find timestamps
            if "end of initialization unified onebox engine" in line:
                timestamp = re.search(r'^(\d+)-(\d+)-(\d+) (\d+):(\d+):(\d+)', line)
                #print(timestamp)
                if not (timestamp is None):
                    year = int(timestamp[1])
                    month = int(timestamp[2])
                    day = int(timestamp[3])
                    hr = int(timestamp[4])
                    min = int(timestamp[5])
                    sec = int(timestamp[6])
                    current_dt = datetime.datetime(year, month, day, hr, min, sec)
                    print("Found Timestamp = " + current_dt.isoformat() + " at line " + str(linenum) )
            
            res = re.search(r'&current_location=(.*?),(.*?)&', str(line)) #ass-ume only one current_location per line
            if not (res is None):
                print("Found lat, long in "+ str(args.inputlog) + " at line " + str(linenum) + " : " + str(res[1]) + ", " + str(res[2]))
                #locations.append((str(linenum), str(res[1]), str(res[2]), current_dt.strftime("%Y-%m-%d %H:%M:%S")))
                locations.append((str(linenum), str(res[1]), str(res[2]), current_dt.isoformat()))
    
    # Write TSV report
    with open(args.output, "w") as outputTSV:
        outputTSV.write("filename\tline\tlatitude\tlongitude\ttimestamp\n")
        
        for loc in locations:
            linenum = loc[0]
            lat = loc[1]
            llg = loc[2]
            time = loc[3]
            outputTSV.write(str(args.inputlog) + "\t" + linenum + "\t" + lat + "\t" + llg + "\t" + time + "\n") 
        
    print("\nProcessed/Wrote " + str(len(locations)) + " locations to: " + args.output + "\n")
    print("Exiting ...\n")
    
if __name__ == "__main__":
    main()



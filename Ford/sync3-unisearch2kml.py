#! /usr/bin/env python
#
# Python script to parse Ford Sync3 unifiedsearch.log for location coordinates and output KML for first lat/long after initialization timestamp
# Based on test data provided by J. EDDY
#
# Author: cheeky4n6monkey@gmail.com
#
# Version History:
# v2021-12-03 Initial Version
#
# Developed/tested on Win10x64 running Python 3.10 and Ubuntu 20x64 running Python 3.8.10
#
# Usage Example:
# python sync3-unisearch2kml.py -i unifiedsearch.log -o output.KML
#

import argparse
import re
import datetime

version_string = "sync3-unisearch2kml.py 2021-12-03"

def main():
    usagetxt = " %(prog)s [-i inputfile -o outputfile]"
    parser = argparse.ArgumentParser(description='Parses Ford Sync3 unifiedsearch.log for location coordinates and outputs KML for first lat/long after initialization timestamp', usage=usagetxt)
    parser.add_argument("-i", dest="inputlog", action="store", required=True, help='unifiedsearch.log')
    parser.add_argument("-o", dest="output", action="store", required=True, help='Output KML filename')
    
    args = parser.parse_args()
    
    print("Running " + version_string + "\n")
    
    locations = []
    current_dt = datetime.datetime(1970, 1, 1)
    found_1st_location = False
    
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
                    found_1st_location = False
            
            if not found_1st_location:
                res = re.search(r'&current_location=(.*?),(.*?)&', str(line)) #ass-ume only one current_location per line
                if not (res is None):
                    print("Found First lat, long in "+ str(args.inputlog) + " at line " + str(linenum) + " : " + str(res[1]) + ", " + str(res[2]))
                    #locations.append((str(linenum), str(res[1]), str(res[2]), current_dt.strftime("%Y-%m-%d %H:%M:%S")))
                    locations.append((str(linenum), str(res[1]), str(res[2]), current_dt.isoformat()))
                    found_1st_location = True
    
    # Write KML report
    with open(args.output, "w") as outputKML:
        outputKML.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
        outputKML.write("<kml xmlns=\"http://www.opengis.net/kml/2.2\">\n")
        outputKML.write("<Document>")
        outputKML.write("\n<name>" + args.inputlog + "</name><open>1</open>\n")
        outputKML.write("<Folder><name>" + args.inputlog + "</name><open>0</open>\n")
        
        for linecount, llat, llg, timestamp in locations: 
            outputKML.write("\n<Placemark>\n")
            outputKML.write("<Style><IconStyle><Icon><href>http://maps.google.com/mapfiles/ms/micons/red-dot.png</href></Icon></IconStyle></Style>\n") # red dot
            outputKML.write("<name>" + timestamp + "</name>\n")        
            outputKML.write("<description> " + args.inputlog + " line: " + linecount + "\nlat = " + llat + ", long = " + llg + "\ntimestamp: " + timestamp + "</description>\n")
            outputKML.write("<Point><coordinates>" + llg + ", " + llat + "</coordinates></Point>\n")
            outputKML.write("<Timestamp><when>" + timestamp + "</when></Timestamp>\n")
            outputKML.write("</Placemark>")
        
        outputKML.write("</Folder>\n")
        outputKML.write("\n</Document>\n")
        outputKML.write("</kml>\n")
    
    print("\nProcessed/Wrote " + str(len(locations)) + " First Locations to: " + args.output + "\n")
    print("Exiting ...\n")
    
if __name__ == "__main__":
    main()



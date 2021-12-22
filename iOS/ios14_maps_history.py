#!/usr/bin/env python3

# Python3 script to query iOS 14 MapsSync_0.0.1 and extract selected BLOBs
#
# Author: cheeky4n6monkey@gmail.com
# Created/Tested on Ubuntu 20.04 LTS / Python 3.8.2 and Win10x64 / Python 3.6
#
# Thanks to @heathermahalik for her research into iOS14 Apple Maps. 
#

import sys
import argparse
import sqlite3
import os
from os import path

version_string = "ios14_maps_history.py v2020-09-19"
print("Running " + version_string + "\n")

parser = argparse.ArgumentParser(description='Queries iOS 14 MapsSync_0.0.1 and extracts selected BLOBs')
parser.add_argument("-d", "--database", action="store", required=True, help='SQLite DB filename i.e. MapsSync_0.0.1')
parser.add_argument("-o", "--outputdir", action="store", required=True, help='Output directory name for HTML report and extracted BLOBs')

args = parser.parse_args()

# Check DB file exists before trying to connect
if path.isfile(args.database):
    dbcon = sqlite3.connect(args.database)
else:
    print(args.database + " DB file does not exist!")
    exit(-1)

if not os.path.isdir(args.outputdir):
    print("Creating output directory ... "+ args.outputdir)
    os.mkdir(args.outputdir)


# Query written by Heather Mahalik - see https://smarterforensics.com/2020/09/rotten-to-the-core-nah-ios14-is-mostly-sweet/
query = """SELECT
ZHISTORYITEM.z_pk AS 'Item Number',
CASE
when ZHISTORYITEM.z_ent = 14 then 'coordinates of search'
when ZHISTORYITEM.z_ent = 16 then 'location search'
when ZHISTORYITEM.z_ent = 12 then 'navigation journey'
end AS 'Type',
datetime(ZHISTORYITEM.ZCREATETIME+978307200,'UNIXEPOCH','localtime') AS 'Time Created',
datetime(ZHISTORYITEM.ZMODIFICATIONTIME+978307200,'UNIXEPOCH','localtime') AS 'Time Modified',
ZHISTORYITEM.ZQUERY AS 'Location Search',
ZHISTORYITEM.ZLOCATIONDISPLAY AS 'Location City',
ZHISTORYITEM.ZLATITUDE AS 'Latitude',
ZHISTORYITEM.ZLONGITUDE AS 'Longitude',
ZHISTORYITEM.ZROUTEREQUESTSTORAGE AS 'Journey BLOB',
ZMIXINMAPITEM.ZMAPITEMSTORAGE as 'Map Item Storage BLOB'
from ZHISTORYITEM
left join ZMIXINMAPITEM on ZMIXINMAPITEM.Z_PK=ZHISTORYITEM.ZMAPITEM;"""

cursor = dbcon.cursor()
cursor.execute(query)
row = cursor.fetchone()

entries = []

while row:
    itemnum = row[0]
    maptype = row[1]
    created = row[2]
    modified = row[3]
    locsearch = row[4]
    loccity = row[5]
    lat = row[6]
    llong = row[7]
    journeyblob = row[8]
    mapitemblob = row[9]
    
    # store each row returned    
    entries.append((itemnum, maptype, created, modified, locsearch, loccity, lat, llong, journeyblob, mapitemblob))
    
    row = cursor.fetchone()

cursor.close()
dbcon.close()

# Write HTML report
with open(os.path.join(args.outputdir, "iOS14-MapsReport.html"), "w") as outputHTML:
    outputHTML.write("<html><table border=\"3\" style=\"width:100%\"><tr>" + \
                     "<th>Item Number</th><th>Type</th>" + \
                     "<th>Time Created</th><th>Time Modified</th>" + \
                     "<th>Location Search</th><th>Location City</th>" + \
                     "<th>Latitude</th><th>Longitude</th>" + \
                     "<th>Journey BLOB</th><th>Map Item Storage BLOB</th></tr>")

    #print(str(len(entries)))
    for entry in entries:
        itemnum = entry[0]
        maptype = entry[1]
        created = entry[2]
        modified = entry[3]
        locsearch = "NULL"
        if entry[4] is not None:
            locsearch = str(entry[4])
        loccity = "NULL"
        if entry[5] is not None:
            loccity = str(entry[5])
        lat = "NULL"
        if entry[6] is not None:
            lat = str(entry[6])
        llong = "NULL"
        if entry[7] is not None:
            llong = str(entry[7])

        jblob = "NULL"
        jblobhtml = "NULL"      
        if entry[8] is not None: # ie BLOB present
            jblob = str(itemnum) +"_journey.BLOB"
            with open(os.path.join(args.outputdir, jblob), "wb") as jblobfile:
                jblobfile.write(entry[8])
            jblobhtml = "<a href=\"" + jblob + "\">" + jblob + "</a>"
            
        mblob = "NULL"
        mblobhtml = "NULL"        
        if entry[9] is not None: # ie BLOB present
            mblob = str(itemnum) +"_mapitem.BLOB"
            with open(os.path.join(args.outputdir, mblob), "wb") as mblobfile:
                mblobfile.write(entry[9])
            mblobhtml = "<a href=\"" + mblob + "\">" + mblob + "</a>"
       
        outputHTML.write("<tr><td>" + str(itemnum) + "</td><td>" + maptype + "</td><td>" + \
                         created + "</td><td>" + modified + "</td><td>" + \
                         locsearch + "</td><td>" + loccity + "</td><td>" + \
                         lat + "</td><td>" + llong + "</td>" + \
                         "<td>" + jblobhtml + "</td>" + \
                         "<td>" + mblobhtml + "</td></tr>")

    outputHTML.write("</table></html>")

print("Processed " + str(len(entries)) + " entries\n")
print("Please refer to iOS14-MapsReport.html in \"" + args.outputdir + "\" directory") 
print("Exiting ...\n")



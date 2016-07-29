#! /usr/bin/env python

"""
Author: Adrian Leong (cheeky4n6monkey@gmail.com)

Python script to extract JPG's from Android Gallery3D app imgcache, mini and micro cache files.
Script also creates a HTML table containing the extracted JPGs and image metadata.

Special Thanks to: LSB, Rob (@TheHexNinja), Terry Olson, Jason Eddy, Jeremy Dupuis and Cindy Murphy for their assistance and insights into the imgcache behaviour.

The record format observed for a Samsung Note 4 (SM-910G) running Android 5.1.1 with Gallery3D ver2.0.8131802 is:

[19 unknown bytes (1st record has 20 bytes before)]
[4 byte LE Record Size]
[UTF16LE Item Path string]
[UTF16LE Index Number String]
[UTF16LE encoded "+"]
[UTF16LE Unix Timestamp (UTC) string]
[UTF16LE encoded "+"]
[UTF16LE Unknown Number String]
[Cached JPG image]

eg
[19 unknown bytes]
[0x6D71 0000 LE]
["/local/image/item/"]
["44"]
["+"]
["1469075274"]
["+"]
["1"]
[JPEG starts with xFFD8 ... ends with xFFD9]

The record size (eg 0x6D71 0000 LE = 0x716D = 29037 dec. bytes) includes everything between the start of the record size field and the last byte of the embedded JPG 

There can be more than one imagecache file located in /data/com.sec.android.gallery3d/cache/
eg imagecache.0 and imagecache.1
Other files may also contain cached images (eg mini.0, micro.0).
The script should handle these as they use the same record structure.

Running the script example:
python imgcache-parse.py -f imgcache.0 -o output.html

"""

import sys
import os
import struct
import datetime
import hashlib
from optparse import OptionParser

version_string = "imgcache-parse.py v2016-07-22"

# Find all indices of a substring in a given string (Python recipe) 
# From http://code.activestate.com/recipes/499314-find-all-indices-of-a-substring-in-a-given-string/
def all_indices(bigstring, substring, listindex=[], offset=0):
    i = bigstring.find(substring, offset)
    while i >= 0:
        listindex.append(i)
        i = bigstring.find(substring, i + 1)

    return listindex

print("Running " + version_string + "\n")

usage = " %prog -f inputfile -o outputfile"

# Handle command line args
parser = OptionParser(usage=usage)
parser.add_option("-f", dest="filename", 
                  action="store", type="string",
                  help="imgcache file to be searched")
parser.add_option("-o", dest="htmlfile",
                  action="store", type="string",
                  help="HTML table File")
(options, args) = parser.parse_args()

# Check if no arguments given by user, exit
if len(sys.argv) == 1:
    parser.print_help()
    exit(-1)
if (options.filename == None) :
    parser.print_help()
    print("\nInput imgcache filename incorrectly specified!")
    exit(-1)
if (options.htmlfile == None) :
    parser.print_help()
    print("\nOutput HTML filename incorrectly specified!")
    exit(-1)

# Open imgcache file for binary read
try:
	fb = open(options.filename, "rb")
except:
    print("Error - Input file failed to open!")
    exit(-1)

filesize = os.stat(options.filename).st_size # get imgcache filesize  

# Read file into one BINARY string (shouldn't be too large)
filestring = fb.read()
# Search the binary string for the hex equivalent of "/local/image/item/" which appears in each imgcache record
substring1 = "\x2F\x00\x6C\x00\x6F\x00\x63\x00\x61\x00\x6C\x00\x2F\x00\x69\x00\x6D\x00\x61\x00\x67\x00\x65\x00\x2F\x00\x69\x00\x74\x00\x65\x00\x6D\x00\x2F\x00"
hits = all_indices(filestring, substring1, [])
print("Paths found = " + str(len(hits)) + "\n")

MAXPATH = 200 # 100 x UTF16 chars = max path size
outputlist = []
for hit in hits:
    pathfound = False
    charcount = 0
    jpgstart = 0 # imgcache file offset for this image's FFD8
    pathname = ""

    fb.seek(hit)
    fb.seek(hit-4) # record size occurs 4 bytes before path
    recsize = struct.unpack("<I", fb.read(4))[0] # size includes these 4 bytes until xFFD9 at end of JPG file
    jpgend = hit - 4 + recsize + 1 # should point to the byte after FFD9
    if (jpgend > filesize):
        print("Bad end of JPG offset calculated for JPG starting at " + hex(hit).rstrip("L").upper() + " ... skipping!\n")
        break

    # Path string processing
    fb.seek(hit)
    # Read in 2 byte chunks until we come across xFF xD8 OR MAXPATH characters are read
    while not pathfound:
        rawtmp = fb.read(2)
        readint = struct.unpack("<H", rawtmp)[0]
        #print(hex(readint).rstrip("L").upper())
        charcount += 2;
        if (charcount > MAXPATH):
            print("Max number of characters read for path - skipping this hit\n")
            break
        if (readint == 0xD8FF): # Have run into the LE xFFxD8 JPG Header
            pathfound = True
            jpgstart = fb.tell()-2
            print(pathname + " from offset = " + hex(hit).rstrip("L").upper())
            break
        pathname += rawtmp.decode('utf-16-le') # convert binary 2 bytes to UTF16LE string

    pathlist = pathname.split("/")
    pathitem = pathlist[len(pathlist)-1] # last item in list should look like 33+1390351440+1
    #print("pathitem = " + pathitem) 

    # Extract timestamp from path eg 1390351440
    tmplist = pathitem.split("+")
    timestamp = tmplist[1] # Timestamp *should* be the 2nd item
    #print("timestamp = " + timestamp) # eg 1390351440
    # Convert timestamp into human readable ISO format (UTC). Replace ":" with "-" (more filename friendly)
    try:
        timestring = datetime.datetime.utcfromtimestamp(int(timestamp)).strftime("%Y-%m-%dT%H-%M-%S")
    except:
        timestring = "Error"

    #print("JPG start = " + hex(jpgstart).rstrip("L").upper())
    #print("JPG end = " + hex(jpgend).rstrip("L").upper())
    # Extract JPG to file
    if (jpgstart > 0):
        rawjpgoutput = filestring[jpgstart:jpgend]
        # filename = input imgcache filename + JPG start hex offset + decimal UNIX timestamp string + human readable timestamp in UTC
        outputfilename = options.filename + "_" + hex(jpgstart).rstrip("L").upper() + "_" + str(timestamp) + "_" + timestring + ".jpg"
        try:
            outputjpg = open(outputfilename, "wb")
        except:
            print("Trouble Opening JPEG Output File: ", outputfilename)
            exit(-1)
        print("JPG output size(bytes) = " + str(len(rawjpgoutput)) + " from offset = " + hex(jpgstart).rstrip("L").upper() + "\n")
        outputjpg.write(rawjpgoutput)
        outputjpg.close()

        # Calculate MD5 of picture file we just wrote
        md5hash = ""
        with open(outputfilename, 'rb') as pic:
            md5 = hashlib.md5()
            md5.update(pic.read()) # file shouldn't be that large so just read into memory
            md5hash = md5.hexdigest().upper()

        # pic size
        picsize = os.stat(outputfilename).st_size

        # store filename, size, item path string and MD5 tuple in output HTML table list
        outputlist.append((outputfilename, str(picsize), pathname, md5hash))
# End of hits loop
fb.close()

# Write output HTML table
try:
    outputHTML = open(options.htmlfile, "wb")
except:
    print("Trouble Opening HTML Output File: ", outputhtml)
    exit(-1)

# HTML table header
outputHTML.write("<html><table border=\"3\" style=\"width:100%\"><tr>" + \
                 "<th>Extracted JPG Filename</th><th>Filesize(bytes)</th>" + \
                 "<th>Item Path String</th><th>MD5 Hash</th><th>Extracted Picture</th></tr>")

for filename, size, itempath, md5 in outputlist:
    outputHTML.write("<tr><td>" + filename + "</td><td>" + size + "</td><td>" + \
                     itempath + "</td><td>" + md5 + "</td>" + \
                     "<td><img src=\"" + filename + "\"></img><td></tr>")

outputHTML.write("</table></html>")
outputHTML.close()

print("Processed " + str(len(outputlist)) + " cache pictures. Exiting ...\n")

#! /usr/bin/env python
# Python script to chronologically list (last modified) MMS .dat files from an exported Windows Phone 8.10 directory 
# ie from DATA partition: /SharedData/Comms/Unistore/data/7
# It will also list the .dat file's SHA256 hash, size and type.
# Selected output values will be printed to command line (no SHA256 values).
# Full output can be optionally written to HTML and/or TSV files.
#
# Author: cheeky4n6monkey@gmail.com (Adrian Leong)
# 
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

import sys
from optparse import OptionParser
import os
import datetime
import struct
import xml.etree.ElementTree as ET
import hashlib

version_string = "wp8-1-mms-filesort.py v2015-11-24"

# Main
print("Running " + version_string + "\n")

usage = " %prog -i inputfiledir -t output.tsv (Optional) -o output.html (Optional)"

# Handle command line args
parser = OptionParser(usage=usage)
parser.add_option("-i", dest="dirname", 
                  action="store", type="string",
                  help="Input Directory To Be Processed")
parser.add_option("-t", dest="outputTSV", 
                  action="store", type="string",
                  help="Output Tab Separated Variable (TSV) filename (Optional)")
parser.add_option("-o", dest="outputHTML", 
                  action="store", type="string",
                  help="Output HTML filename (Optional)")
(options, args) = parser.parse_args()

# Check if no arguments given by user, exit
if len(sys.argv) == 1:
    parser.print_help()
    exit(-1)
if (options.dirname == None) :
    parser.print_help()
    print("\nInput directory incorrectly specified! Exiting ...\n")
    exit(-1)
if not os.path.isdir(options.dirname):
    print("Input directory does not exist! Exiting ...\n")
    exit(-1)
if (options.outputTSV != None):
    try:
        outputTSV = open(options.outputTSV, "w")
    except:
        print("Cannot create specified output TSV file! Exiting ...\n")
        exit(-1)
if (options.outputHTML != None):
    try:
        outputHTML = open(options.outputHTML, "w")
    except:
        print("Cannot create specified output HTML file! Exiting ...\n")
        exit(-1)
        
filelist = {} # dict of tuple lists containing .dat filenames keyed by modifed date
timestamplist = [] # list of distinct ISO timestamps eg 2015-11-24T15:25:44

# Iterate through sub directories and record path, filename, modified time
parsecount = 0
for root, dirs, files in os.walk(options.dirname):
    for name in files:
        fullname = os.path.join(root, name)
        if (name.endswith("73701.dat")): # MMS specific file naming convention
            tmp = ()
            #print("\nAttempting to parse .dat = " + name)
            epochsecs = os.path.getmtime(fullname)
            modtime = datetime.datetime.utcfromtimestamp(epochsecs).isoformat()
            #print("Modified time = " + modtime)
            if not (modtime in timestamplist):
                timestamplist.append(modtime)
                filelist[modtime] = list() # there may be more than one file per modtime so use a list

            filelist[modtime].append(fullname)
            parsecount += 1

print("Parsed " + str(parsecount) + " files\n")
timestamplist.sort()
#print("timestamplist = ")
#for j in timestamplist:
#    print(j + "\n")

# Write headers for Command line, TSV, HTML output
print("Mod. Timestamp\tFilename\tSize(bytes)\tType\tComments")

if (options.outputTSV != None):
    outputTSV.write("Mod. Timestamp\tFilename\tSize(bytes)\tType\tSHA256 Hash\tComments\n")
                    
if (options.outputHTML != None):
    outputHTML.write("<html><table border=\"3\" style=\"width:100%\"><tr>" + \
                    "<th>Last Modified Time(UTC)</th><th>Filename</th><th>Filesize(bytes)</th><th>Type</th><th>SHA256 Hash</th><th>Comments</th></tr>")
                    
# Peek in .dat files (sorted chronologically) to see what each contains
sortedkeys = sorted(filelist.keys())
for j in sortedkeys: # each date key
    #print("\nDate = " + j + ", Files with same date = " + str(len(filelist[j])))

    for k in range(len(filelist[j])): # each filename with same date key
        #print(filelist[j][k])
        fsize = 0
        is_smil = 0
        is_jpg = 0
        is_amr = 0
        is_png = 0
        is_mp4 =0
        is_vc = 0
        commentstr = ""
        sha256hashstr = ""
        
        try:
            fb = open(filelist[j][k], "rb")
            fsize = os.stat(filelist[j][k]).st_size # get filesize  
            fb.seek(0)
            contents = fb.read() # reading the whole file shouldn't be memory intensive for small files
            sha256hashstr = hashlib.sha256(contents).hexdigest().upper() # get SHA256 hash string
        except:
            print("Unable to open .dat file = " + filelist[j][k])
            exctype, value = sys.exc_info()[:2]
            print("Exception type = ",exctype,", value = ",value)
            fb.close()
            continue
            
        # First bytes could be UTF16-LE "<smil>" or UTF16-LE text or binary attachment (eg xFF xD8 for .JPG)
        if (fsize > 11): # need 12 bytes minimum for "<smil>"
            try:
                #print("<smil> test")
                # Handle if file is one byte long?
                b0, b1, b2, b3, b4, b5, b6, b7, b8, b9, b10, b11 = struct.unpack('BBBBBBBBBBBB', contents[0:12])
                # Check for "<smil>" = 3C0073006D0069006C003E00
                if (b0 == 0x3C and b1 == 0 and b2 == 0x73 and b3 == 0 and \
                    b4 == 0x6D and b5 == 0 and b6 == 0x69 and b7 == 0 and \
                    b8 == 0x6C and b9 == 0 and b10 == 0x3E and b11 == 0):
                    #print(filelist[j][k] + " is a <smil> file with size = " + str(fsize))
                    #print(j + "\t" + filelist[j][k] + "\t" +str(fsize) + "\t<smil>")
                    is_smil = 1

                    tree = ET.parse(filelist[j][k]) # process the smil XML tree
                    root = tree.getroot()
                    picsrc = []
                    textsrc = []
                    vidsrc = []
                    audsrc = []
                    ctxsrc = []

                    piclist = root.findall("./body/par/img")
                    for pic in piclist:
                        name = pic.get("src") 
                        if (name is not None):
                            picsrc.append(name)
                    picsrcstr = ", ".join(picsrc)
                    txtlist = root.findall("./body/par/text")
                    for txt in txtlist:
                        name = txt.get("src") 
                        if (name is not None):
                            textsrc.append(name)
                    textsrcstr = ", ".join(textsrc)
                    vidlist = root.findall("./body/par/video")
                    for vid in vidlist:
                        name = vid.get("src") 
                        if (name is not None):
                            vidsrc.append(name)
                    vidsrcstr = ", ".join(vidsrc)
                    audlist = root.findall("./body/par/audio")
                    for aud in audlist:
                        name = aud.get("src") 
                        if (name is not None):
                            audsrc.append(name)
                    audsrcstr = ", ".join(audsrc)
                    ctxlist = root.findall("./body/par/ref")
                    for ctx in ctxlist:
                        name = ctx.get("src") 
                        if (name is not None):
                            ctxsrc.append(name)
                    ctxsrcstr = ", ".join(ctxsrc)

                    if (len(picsrc)):
                        commentstr = "img = " + picsrcstr
                    if (len(textsrc) and len(commentstr)):
                        commentstr += ", text = " + textsrcstr
                    elif (len(textsrc)):
                        commentstr += "text = " + textsrcstr
                    if (len(vidsrc) and len(commentstr)):
                        commentstr += ", video = " + vidsrcstr
                    elif (len(vidsrc)):
                        commentstr += "video = " + vidsrcstr
                    if (len(audsrc) and len(commentstr)):
                        commentstr += ", aud = " + audsrcstr
                    elif (len(audsrc)):
                        commentstr += "aud = " + audsrcstr
                    if (len(ctxsrc) and len(commentstr)):
                        commentstr += ", VCARD present"
                    elif (len(ctxsrc)):
                        commentstr += "VCARD present"

                    print(j + "\t" + filelist[j][k] + "\t" + str(fsize) + "\t<smil>\t" + commentstr)
                    if (options.outputTSV != None):
                        outputTSV.write(j + "\t" + filelist[j][k] + "\t" + str(fsize) + "\tsmil\t" + \
                                        sha256hashstr + "\t" + commentstr + "\n")
                    if (options.outputHTML != None):
                        outputHTML.write("<tr><td>" + j + "</td><td><a href=\"" + filelist[j][k] + "\"><b>" + \
                                        filelist[j][k] + "</b></a></td><td>" + str(fsize) + "</td><td>smil</td><td>" + \
                                        sha256hashstr + "</td><td>" + commentstr + "</td></tr>")                    
            except:
                print("Bad <smil> filetype detection for " + filelist[j][k])
                exctype, value = sys.exc_info()[:2]
                print("Exception type = ",exctype,", value = ",value)
                fb.close()
                continue
        if (is_smil == 0) : # Not a <smil>, assume its an attachment (eg text, jpeg/png picture, video, voicenote) 
            if (fsize > 2):
                try:
                    b0, b1 = struct.unpack('BB', contents[0:2])
                    if (b0 == 0xFF and b1 == 0xD8):
                        #print(filelist[j][k] + " is a JPG file with size = " + str(fsize))
                        print(j + "\t" + filelist[j][k] + "\t" + str(fsize) + "\tJPEG")
                        is_jpg = 1
                        if (options.outputTSV != None):
                            outputTSV.write(j + "\t" + filelist[j][k] + "\t" + str(fsize) + "\tJPEG\t" + \
                                        sha256hashstr + "\t" + commentstr + "\n")

                        if (options.outputHTML != None):
                            outputHTML.write("<tr><td>" + j + "</td><td><a href=\"" + filelist[j][k] + "\"><b>" + \
                                            filelist[j][k] + "</b></a></td><td>" + str(fsize) + "</td><td>JPEG</td><td>" + \
                                            sha256hashstr + "</td><td></td></tr>")
                except:
                    print("Bad JPG filetype detection for file = " + filelist[j][k] + " with size = " + str(fsize))
                    exctype, value = sys.exc_info()[:2]
                    print("Exception type = ",exctype,", value = ",value)
                    fb.close()
                    continue
            if (fsize > 5) and (is_jpg == 0): # Voicenote / AMR file signature is 0x23 0x21 0x41 0x4D 0x52
                try:
                    b0, b1, b2, b3, b4 = struct.unpack('BBBBB', contents[0:5])
                    if (b0 == 0x23 and b1 == 0x21 and b2 == 0x41 and b3 == 0x4D and b4 == 0x52):
                        #print(filelist[j][k] + " is an AMR file with size = " + str(fsize))
                        print(j + "\t" + filelist[j][k] + "\t" + str(fsize) + "\tAMR")
                        is_amr = 1
                        if (options.outputTSV != None):
                            outputTSV.write(j + "\t" + filelist[j][k] + "\t" + str(fsize) + "\tAMR\t" + \
                                        sha256hashstr + "\t" + commentstr + "\n")
                        if (options.outputHTML != None):
                            outputHTML.write("<tr><td>" + j + "</td><td><a href=\"" + filelist[j][k] + "\"><b>" + \
                                            filelist[j][k] + "</b></a></td><td>" + str(fsize) + "</td><td>AMR</td><td>" + \
                                            sha256hashstr + "</td><td></td></tr>")
                except:
                    print("Bad AMR filetype detection for file = " + filelist[j][k] + " with size = " + str(fsize))
                    exctype, value = sys.exc_info()[:2]
                    print("Exception type = ",exctype,", value = ",value)
                    fb.close()
                    continue
            if (fsize > 8) and (is_jpg == 0) and (is_amr == 0): # PNG file signature is 0x89 0x50 0x4E 0x47 0x0D 0x0A 0x1A 0x0A
                try:
                    b0, b1, b2, b3, b4, b5, b6, b7 = struct.unpack('BBBBBBBB', contents[0:8])
                    if (b0 == 0x89 and b1 == 0x50 and b2 == 0x4E and b3 == 0x47 and \
                        b4 == 0x0D and b5 == 0x0A and b6 == 0x1A and b7 == 0x0A):
                        #print(filelist[j][k] + " is a PNG file with size = " + str(fsize))
                        print(j + "\t" + filelist[j][k] + "\t" + str(fsize) + "\tPNG")
                        is_png = 1
                        if (options.outputTSV != None):
                            outputTSV.write(j + "\t" + filelist[j][k] + "\t" + str(fsize) + "\tPNG\t" + \
                                        sha256hashstr + "\t" + commentstr + "\n")
                        if (options.outputHTML != None):
                            outputHTML.write("<tr><td>" + j + "</td><td><a href=\"" + filelist[j][k] + "\"><b>" + \
                                            filelist[j][k] + "</b></a></td><td>" + str(fsize) + "</td><td>PNG</td><td>" + \
                                            sha256hashstr + "</td><td></td></tr>")
                except:
                    print("Bad PNG filetype detection for file = " + filelist[j][k] + " with size = " + str(fsize))
                    exctype, value = sys.exc_info()[:2]
                    print("Exception type = ",exctype,", value = ",value)
                    fb.close()
                    continue
            if (fsize > 12) and (is_jpg == 0) and (is_amr == 0) and (is_png == 0): # Video MMS can be MP4/QT. The file signature is 0x00 0x00 0x00 0x18 0x66 0x74 0x79 0x70 0x6D 0x70 0x34 0x32.
                try:
                    b0, b1, b2, b3, b4, b5, b6, b7, b8, b9, b10, b11 = struct.unpack('BBBBBBBBBBBB', contents[0:12])
                    if (b0 == 0 and b1 == 0 and b2 == 0 and b3 == 0x18 and b4 == 0x66 and b5 == 0x74 and b6 == 0x79 and \
                        b7 == 0x70 and b8 == 0x6D and b9 == 0x70 and b10 == 0x34 and b11 == 0x32):
                        #print(filelist[j][k] + " is a MP4 file with size = " + str(fsize))
                        print(j + "\t" + filelist[j][k] + "\t" + str(fsize) + "\tMP4")
                        is_mp4 = 1
                        if (options.outputTSV != None):
                            outputTSV.write(j + "\t" + filelist[j][k] + "\t" + str(fsize) + "\tMP4\t" + \
                                        sha256hashstr + "\t" + commentstr + "\n")
                        if (options.outputHTML != None):
                            outputHTML.write("<tr><td>" + j + "</td><td><a href=\"" + filelist[j][k] + "\"><b>" + \
                                            filelist[j][k] + "</b></a></td><td>" + str(fsize) + "</td><td>MP4</td><td>" + \
                                            sha256hashstr + "</td><td></td></tr>")
                except:
                    print("Bad MP4 filetype detection for file = " + filelist[j][k] + " with size = " + str(fsize))
                    exctype, value = sys.exc_info()[:2]
                    print("Exception type = ",exctype,", value = ",value)
                    fb.close()
                    continue
            if (fsize > 13) and (is_jpg == 0) and (is_amr == 0) and (is_png == 0) and (is_mp4 == 0): # VCARD signature is 0x42 0x45 0x47 0x49 0x4E 0x3A 0x56 0x43 0x41 0x52 0x44 0x0D 0x0A.
                try:
                    b0, b1, b2, b3, b4, b5, b6, b7, b8, b9, b10, b11, b12 = struct.unpack('BBBBBBBBBBBBB', contents[0:13])
                    if (b0 == 0x42 and b1 == 0x45 and b2 == 0x47 and b3 == 0x49 and b4 == 0x4E and b5 == 0x3A and b6 == 0x56 and \
                        b7 == 0x43 and b8 == 0x41 and b9 == 0x52 and b10 == 0x44 and b11 == 0x0D and b12 == 0x0A):
                        #print(filelist[j][k] + " is a VCARD file with size = " + str(fsize))
                        print(j + "\t" + filelist[j][k] + "\t" + str(fsize) + "\tVCARD")
                        is_vc = 1
                        if (options.outputTSV != None):
                            outputTSV.write(j + "\t" + filelist[j][k] + "\t" + str(fsize) + "\tVCARD\t" + \
                                        sha256hashstr + "\t" + commentstr + "\n")
                        if (options.outputHTML != None):
                            outputHTML.write("<tr><td>" + j + "</td><td><a href=\"" + filelist[j][k] + "\"><b>" + \
                                            filelist[j][k] + "</b></a></td><td>" + str(fsize) + "</td><td>VCARD</td><td>" +
                                            sha256hashstr + "</td><td></td></tr>")
                except:
                    print("Bad VCARD filetype detection for file = " + filelist[j][k] + " with size = " + str(fsize))
                    exctype, value = sys.exc_info()[:2]
                    print("Exception type = ",exctype,", value = ",value)
                    fb.close()
                    continue

            if (is_jpg == 0 and is_amr == 0 and is_png == 0 and is_mp4 == 0 and is_vc == 0):
                # unknown attachment (includes text message as emoji dont' fall into typical "XX 00" hex pattern)
                #print(filelist[j][k] + " file type is UNKNOWN! size = " + str(fsize))
                print(j + "\t" + filelist[j][k] + "\t" + str(fsize) + "\tUnknown")
                if (options.outputTSV != None):
                            outputTSV.write(j + "\t" + filelist[j][k] + "\t" + str(fsize) + "\tUnknown\t" + \
                                        sha256hashstr + "\t" + commentstr + "\n")
                if (options.outputHTML != None):
                    outputHTML.write("<tr><td>" + j + "</td><td><a href=\"" + filelist[j][k] + "\"><b>" + filelist[j][k] + \
                                    "</b></a></td><td>" + str(fsize) + "</td><td>Unknown</td><td>" + \
                                    sha256hashstr + "</td><td></td></tr>")

        fb.close()

print("\nNote1: Type \"Unknown\" Types possibly indicate MMS message text files")
print("\nNote2: Not all .dat files may belong to an MMS message (eg Received Email Attachments, Drafts)")

# Finish printing tables to file
if (options.outputTSV != None) :
    outputTSV.write("\nNote1: \"Unknown\" Types possibly indicate MMS message text files\n" + \
                    "Note2: Not all .dat files may belong to an MMS message (eg Received Email Attachments, Drafts)\n")
    outputTSV.close() 

if (options.outputHTML != None) :
    outputHTML.write("</table><p><b>Note1: \"Unknown\" Types possibly indicate MMS message text files</b></p>" + \
                    "<b>Note2: Not all .dat files may belong to an MMS message (eg Received Email Attachments, Drafts)</b></p></html>")
    outputHTML.close() 

print("\nFinished processing MMS .dat files ... Exiting ...")

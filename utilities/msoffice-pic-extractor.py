#! /usr/bin/env python

# Python script to extract picture content from MS Office 2007 .docx, .xlsx, .pptx files
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
# Tested on Win7 x64 & Ubuntu 14.04 x64 with Python 2.7 and MS Office 2007 .docx, .xlsx, .pptx 
#
# Issues: 
# - Cannot parse sub-directories containing MS Office files. It ass-umes, all Office files are in the specified
# target directory (in a single level).
#

import os
import sys
import argparse
import zipfile
import xml.etree.ElementTree as ET

# Functions
def parse_docx(filename) :
    if (zipfile.is_zipfile(filename)):
        print("Input MS Office file " + filename + " checked OK!")
    else:
        print(filename + " = Bad Input MS Office file!")
        return

    z = zipfile.ZipFile(filename, "r")
    internal_imagepath = "word/media/image" # All pics should be stored under the word/media dir

    for j in z.infolist():
        #print (j.filename + ", " + str(j.file_size))
        if ("word/document.xml" in j.filename):
            # read for filename metadata
            docdata = z.open(j.filename)
            tree = ET.parse(docdata)
            root = tree.getroot()
            #ET.dump(root)
            try:
                namespace = {"wp" : "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"}
                picdatas = root.findall(".//wp:docPr", namespace)
                print("Processing " + j.filename + " for picture metadata")
                for picdata in picdatas: #name="Picture 1" descr="Koala.jpg"
                    name = picdata.get("name")
                    descr = picdata.get("descr")
                    if (name is not None) and (descr is not None):
                        print(filename + " : " + j.filename + ", name = " + name + ", descr = " + descr)
            except:
                print("Error - Cannot parse document.xml pic info")
                exctype, value = sys.exc_info()[:2]
                print("Exception type = ",exctype,", value = ",value) 
        elif (internal_imagepath in j.filename):
            #print j.filename
            outputfilepath = os.path.join(args.destdir, filename)
            if (not os.path.exists(outputfilepath)) : 
                os.mkdir(outputfilepath)
            try:
                # read zipped picture and write it out to destination dir
                dirs, shortname = os.path.split(j.filename) # ass-ume pic path is separated with "/" eg word/media/image1.jpeg
                print("Extracting picture " + shortname + " to " + outputfilepath)
                picdata = z.read(j.filename)
                outputfilename = os.path.join(outputfilepath, shortname)
                outputfile = open(outputfilename, "wb")
                outputfile.write(picdata)
                outputfile.close()
            except:
                print("Error - Cannot write output pic")
                exctype, value = sys.exc_info()[:2]
                print("Exception type = ",exctype,", value = ",value) 

    z.close()
    return
#ends parse_docx

def parse_pptx(filename) :
    if zipfile.is_zipfile(filename):
        print("Input MS Office file " + filename + " checked OK!")
    else:
        print(filename + " = Bad Input MS Office file!")
        return

    z = zipfile.ZipFile(filename, "r")
    internal_imagepath = "ppt/media/image" # All pics should be stored under the ppt/media dir

    for j in z.infolist():
        #print (j.filename + ", " + str(j.file_size))
        if ("ppt/slides/slide" in j.filename) and (j.filename.endswith(".xml")):
            # read for filename metadata
            pptdata = z.open(j.filename)
            tree = ET.parse(pptdata)
            root = tree.getroot()
            #ET.dump(root)
            try:
                namespace = {"p" : "http://schemas.openxmlformats.org/presentationml/2006/main"}
                picdatas = root.findall(".//p:cNvPr", namespace)
                #print picdatas
                print("Processing " + j.filename + " for picture metadata")
                for picdata in picdatas: #id="4" name="Picture 3" descr="Penguins.jpg"
                    name = picdata.get("name")
                    descr = picdata.get("descr")
                    if (name is not None) and (descr is not None):
                        print(filename + " : " + j.filename + ", name = " + name + ", descr = " + descr)
                #print
            except:
                print("Error - Cannot parse pic info from " + j.filename)
                exctype, value = sys.exc_info()[:2]
                print("Exception type = ",exctype,", value = ",value) 
        elif (internal_imagepath in j.filename):
            #print j.filename
            outputfilepath = os.path.join(args.destdir, filename)
            if (not os.path.exists(outputfilepath)) : 
                os.mkdir(outputfilepath)
            try:
                # read zipped picture and write it out to destination dir
                dirs, shortname = os.path.split(j.filename) # ass-ume pic path is separated with "/" eg ppt/media/image1.jpeg
                print("Extracting picture " + shortname + " to " + outputfilepath)
                picdata = z.read(j.filename)
                outputfilename = os.path.join(outputfilepath, shortname)
                outputfile = open(outputfilename, "wb")
                outputfile.write(picdata)
                outputfile.close()
            except:
                print("Error - Cannot write output pic")
                exctype, value = sys.exc_info()[:2]
                print("Exception type = ",exctype,", value = ",value) 

    z.close()
    return
#ends parse_pptx

def parse_xlsx(filename) :
    if zipfile.is_zipfile(filename):
        print("Input MS Office file " + filename + " checked OK!")
    else:
        print(filename + " = Bad Input MS Office file!")
        return

    z = zipfile.ZipFile(filename, "r")
    internal_imagepath = "xl/media/image" # All pics should be stored under the xl/media dir

    for j in z.infolist():
        #print (j.filename + ", " + str(j.file_size))
        if ("xl/drawings/drawing" in j.filename) and (j.filename.endswith(".xml")):
            # read for filename metadata
            pptdata = z.open(j.filename)
            tree = ET.parse(pptdata)
            root = tree.getroot()
            #ET.dump(root)
            try:
                namespace = {"xdr" : "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"}
                picdatas = root.findall(".//xdr:cNvPr", namespace)
                #print picdatas
                print("Processing " + j.filename + " for picture metadata")
                for picdata in picdatas: #id="2" name="Picture 1" descr="Lighthouse.jpg"
                    name = picdata.get("name")
                    descr = picdata.get("descr")
                    if (name is not None) and (descr is not None):
                        print(filename + " : " + j.filename + ", name = " + name + ", descr = " + descr)
                #print
            except:
                print("Error - Cannot parse pic info from " + j.filename)
                exctype, value = sys.exc_info()[:2]
                print("Exception type = ",exctype,", value = ",value) 
        elif (internal_imagepath in j.filename):
            #print j.filename
            outputfilepath = os.path.join(args.destdir, filename)
            if (not os.path.exists(outputfilepath)) : 
                os.mkdir(outputfilepath)
            try:
                # read zipped picture and write it out to destination dir
                dirs, shortname = os.path.split(j.filename) # ass-ume pic path is separated with "/" eg xl/media/image1.jpeg
                print("Extracting picture " + shortname + " to " + outputfilepath)
                picdata = z.read(j.filename)
                outputfilename = os.path.join(outputfilepath, shortname)
                outputfile = open(outputfilename, "wb")
                outputfile.write(picdata)
                outputfile.close()
            except:
                print("Error - Cannot write output pic")
                exctype, value = sys.exc_info()[:2]
                print("Exception type = ",exctype,", value = ",value) 

    z.close()
    return
#ends parse_xlsx

#Main
parser = argparse.ArgumentParser(description='Extracts pics from given MS Office document')
parser.add_argument("target", help='MS Office document / directory of Office documents to be searched')
parser.add_argument("destdir", help='output dir')
args = parser.parse_args()

version_string = "msoffice-pic-extractor.py v2015-05-23"
print "\nRunning " + version_string

print("Source file = " + args.target)
print("Output dir = " + args.destdir)

if not os.path.isdir(args.destdir):
    print("Creating destination directory ...")
    os.mkdir(args.destdir)

if (os.path.isdir(args.target)):
    # for each file in folder (includes subfolders)
    parsecount = 0
    for root, dirs, files in os.walk(args.target):
        for name in files:
            #fullname = os.path.join(root, name)
            if (name.endswith(".docx")):
                print("\nAttempting to parse docx = " + name)
                try:
                   parse_docx(name)
                   parsecount += 1
                except :
                    print("*** WARNING Cannot parse docx " + name + "\n")
                    exctype, value = sys.exc_info()[:2]
                    print("Exception type = ",exctype,", value = ",value) 
                    continue # keep looping if theres an error
            elif (name.endswith(".pptx")):
                print("\nAttempting to parse pptx = " + name)
                try:
                   parse_pptx(name)
                   parsecount += 1
                except :
                    print("*** WARNING Cannot parse pptx " + name + "\n")
                    exctype, value = sys.exc_info()[:2]
                    print("Exception type = ",exctype,", value = ",value) 
                    continue # keep looping if theres an error
            elif (name.endswith(".xlsx")):
                print("\nAttempting to parse xlsx = " + name)
                try:
                   parse_xlsx(name)
                   parsecount += 1
                except :
                    print("*** WARNING Cannot parse xlsx " + name + "\n")
                    exctype, value = sys.exc_info()[:2]
                    print("Exception type = ",exctype,", value = ",value) 
                    continue # keep looping if theres an error
    print("\nParsed " + str(parsecount) + " MS Office files")
else:
    # must be a single file arg
    print("\nAttempting to open single file " + args.target)
    if (args.target.endswith(".docx")):
        print("\nAttempting to parse docx = " + args.target)
        try:
            parse_docx(args.target)
        except :
            print("*** WARNING Cannot parse docx " + args.target + "\n")
            exctype, value = sys.exc_info()[:2]
            print("Exception type = ",exctype,", value = ",value) 
    elif (args.target.endswith(".pptx")):
        print("\nAttempting to parse pptx = " + args.target)
        try:
           parse_pptx(args.target)
        except :
            print("*** WARNING Cannot parse pptx " + args.target + "\n")
            exctype, value = sys.exc_info()[:2]
            print("Exception type = ",exctype,", value = ",value) 
    elif (args.target.endswith(".xlsx")):
        print("\nAttempting to parse xlsx = " + args.target)
        try:
            parse_xlsx(args.target)
        except :
            print("*** WARNING Cannot parse xlsx " + args.target + "\n")
            exctype, value = sys.exc_info()[:2]
            print("Exception type = ",exctype,", value = ",value) 



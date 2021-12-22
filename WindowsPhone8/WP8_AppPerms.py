#! /usr/bin/env python

# Python script to parse App permissions from a Windows 8.1 phone via (recursively) reading WMAppManifest.xml files.
# The test phone was a factory reset Nokia Lumia 530.

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

# Issues: 
# - Python / the XML parser (xml.etree.ElementTree) does not handle paths with commas in them (so you may need to rename your source folder structure).
# - The XML parser also doesn't like NULLs so ensure your source files don't include file slack when you export them (ie logical contents only).

import os
import sys
import argparse
import xml.etree.ElementTree as ET

def Parse_Capabilities(filename) :
    tree = ET.parse(filename)
    root = tree.getroot()
    #for child in root:
    #    print child.tag, child.attrib
    #ET.dump(root)
    try:
        print("App Name = " + root.find("App").get("Title"))
    except:
        print("Error - Cannot parse App Name")
    try:
        print("App ProductID = " + root.find("App").get("ProductID"))
    except:
        print("Error - Cannot parse App ProductID")
    try:
        print("App Version = " + root.find("App").get("Version"))
    except:
        print("Error - Cannot parse App Version")
    try:
        print("App Description = " + root.find("App").get("Description"))
    except:
        print("Error - Cannot parse App Description")
    try:
        print("App Author = " + root.find("App").get("Author"))
    except:
        print("Error - Cannot parse App Author")

    try:
        caps = root.iterfind("./App/Capabilities/Capability")
        print("App Capabilities = ")
        for cap in caps:
            print(cap.get("Name"))
    except:
        print("Error - Cannot parse Capabilities")
# ends Parse_Capabilities function

version_string = "WP8_AppPerms.py v2015-04-24"
print "Running " + version_string

parser = argparse.ArgumentParser(description="Prints Windows phone 8 Capabilities from given App Manifest XML file (or directory of files).")
parser.add_argument("target", help="File or directory of files to be parsed")

args = parser.parse_args()

if (os.path.isdir(args.target)):
    # for each file in folder (includes subfolders)
    parsecount = 0
    for root, dirs, files in os.walk(args.target):
        for name in files:
            fullname = os.path.join(root, name)
            if (fullname.endswith("WMAppManifest.xml")):
                print("\nAttempting to open " + fullname)
                try:
                   Parse_Capabilities(fullname)
                   parsecount += 1
                except :
                    print("*** WARNING Cannot parse " + fullname + "\n")
                    exctype, value = sys.exc_info()[:2]
                    print("Exception type = ",exctype,", value = ",value) 
                    continue # keep looping if theres an error
    print("\nParsed " + str(parsecount) + " WMAppManifest.xml files")
else:
    # must be a single file arg
    try:
        print("\nAttempting to open single file " + args.target)
        Parse_Capabilities(args.target)
    except :
        print("*** WARNING Cannot parse " + args.target + "\n")
        exctype, value = sys.exc_info()[:2]
        print("Exception type = ",exctype,", value = ",value) 

print("\nFor a list of Capability definitions see https://msdn.microsoft.com/en-us/library/windows/apps/jj206936%28v=vs.105%29.aspx")
print("\nExiting ...")

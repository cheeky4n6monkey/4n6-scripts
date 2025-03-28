
from fastkml import kml
from fastkml import utils
from fastkml import Placemark, Folder

import re
import os
import pathlib
import argparse


# Python3 script to split a Berla Export to KML into smaller (subsized) KMLs
# Currently handles TrackPoints only (TBD: Waypoints / Tracks / Events)
# Author: A.Leong (tested/developed on Win10x64 w/ Python 3.12)
# cheeky4n6monkey@gmail.com
#
# Version: v2025-03-07 = Initial (tested with Ford Sync4 KML export ~83 MB)
#          v2025-03-21 Updated so NaN Altitudes are omitted and not set to zero + 
#           fixed bug where last Placemark was not being written +
#           Added outputdir argument.
#           Also tested with Toyota 17 MMU (1 GB) + Ford SYNC 3 KML (126 MB) exports.
#
version_string = "Berla_KML_export_splitter.py v2025-03-21"

usagetxt = " %(prog)s inputKML subsize outputdir"
parser = argparse.ArgumentParser(description='Reads given Berla Export KML file and splits the TrackPoints into subsize KML files stored in outputdir.', usage=usagetxt)
parser.add_argument("inputfile", action="store", help='Input Berla Export KML filename')
parser.add_argument("subsize", action="store", type=int, help='Number of Placemarks per sub-file')
parser.add_argument("outputdir", action="store", help='Output directory')

args = parser.parse_args()

print("\nRunning " + version_string + "\n")

if not os.path.exists(args.outputdir):
    os.makedirs(args.outputdir)

print("Parsing KML file (can take several minutes) ...")

with open(args.inputfile, 'r', encoding='utf-8') as f:
    # Hack so that FastKML parses Placemarks OK. NaN values seem to cause Placemarks to not be parsed
    # ie convert file to string then replace any NaN values with "" (re: Placemark altitude values)
    txt = f.read().replace(",NaN", "") 
    readkml = kml.KML.from_string(txt.encode('utf-8'), strict=False)
    
    print("Searching for TrackPoints folder ...")
    trackfolder = utils.find(readkml, of_type=Folder, name="TrackPoints")

    numfiles = 1 # total sub-KML files written

    for item in list(trackfolder.features):
        if isinstance(item, Folder): # for each track folder, save track point info to buffer
            runcount = 1 # placemark count resets with every sub-file
            subindex = 1 # sub-KML files written for this track
            towrite = [] # list of Placemarks to write to next file

            # Extract count from description field eg Count</th><td>119</td>
            
            # eg "Count</th><td>163</td></tr><tr><th align="left">Start Time</th><td>21/11/2024 6:21:30 AM</td>"
            m = re.search(r"Count</th><td>(\d+)</td></tr><tr><th align=\"left\">Start Time</th><td>(.+?)</td>", item.description)
            if (m):
                stime = "None"
                if not (str(m.group(2)).startswith("</td></tr><tr><th")):
                    stime = str(m.group(2))
                print("Track: " + str(item.name) + " [" + str(m.group(1)) + " Placemarks Declared] " + ", Start time = " + stime)
            
            for pm in item.features: # Each Placemark under Track Folder
                if isinstance(pm, Placemark):
                    if (runcount % (args.subsize) != 0): # store up to subsize Placemarks in towrite list ...
                        #print(pm)
                        #print(str(runcount) + " : Placemark name = " + pm.name ) #" at: lat = " + str(pm.geometry.coords[0][1]) + ", llg = " + str(pm.geometry.coords[0][0]) + ", alt = " + str(pm.geometry.coords[0][2]))
                        #print(pm.description)
                        #print(pm.times)
                        towrite.append(pm)
                        runcount += 1
                        
                        # check if last read Placemark from source file, write remainder to last file
                        if pm is item.features[-1]:
                            print("====> FINAL Sub-file, No. Placemarks to write = " + str(len(towrite)))
                            k = kml.KML()
                            d = kml.Document()
                            f = kml.Folder(id = item.id, name = item.name, description = item.description)
                            k.append(f)
                            for p in towrite:
                                f.append(p)
                            basename = os.path.splitext(os.path.basename(args.inputfile))[0]
                            # Add pm.name to filename because there can be multiple Tracks with the same name eg "Route 184". 
                            # The pm.name should prevent overwrites and acts as check (the last Placemark in sub-file should have this id).
                            subfilename = os.path.join(args.outputdir, basename + "_" + str(item.name) + "_" + str(subindex) + "_" + str(pm.name) + ".kml")
                            
                            pth = pathlib.Path(subfilename)
                            print("Creating FINAL sub-file: " + subfilename + "\n")
                            k.write(pth) # Expects a pathlib.Path object
                            numfiles += 1
                    
                    else:
                        towrite.append(pm) # bugfix - add current placemark to list 
                        print("====> NEW Sub-file, No. Placemarks = "  + str(len(towrite)))
                        
                        k = kml.KML()
                        d = kml.Document()
                        f = kml.Folder(id = item.id, name = item.name, description = item.description)
                        k.append(f)
                        for p in towrite:
                            f.append(p)
                        basename = os.path.splitext(os.path.basename(args.inputfile))[0]
                        subfilename = os.path.join(args.outputdir, basename + "_" + str(item.name) + "_" + str(subindex) + "_" + str(pm.name) + ".kml")
                        
                        pth = pathlib.Path(subfilename)
                        print("Creating sub-file: " + subfilename)
                        k.write(pth)
                        
                        towrite.clear()
                        runcount = 1 # reset runcount with each full sub-file
                        numfiles += 1
                        subindex += 1

    print("No. TrackPoints declared in TrackPoints folder = " + trackfolder.description)
    print("Actual No. Track folders detected in TrackPoints folder = " + str(len(list(trackfolder.features))))
    print("No. Placemarks per file limit = " + str(args.subsize))
    print("Total No. Outputted Sub-Files = " + str(numfiles-1))

print("\nFinished processing - see: " + args.outputdir + " folder for split KMLs.\nExiting ...")



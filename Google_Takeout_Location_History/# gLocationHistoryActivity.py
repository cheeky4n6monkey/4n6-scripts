#! /usr/bin/env python

# gLocationHistoryActivity.py = Python script reads Google Takeout "Location History.json" and processes Detected Activity entries
#
# Author: cheeky4n6monkey@gmail.com
#
# Version History:
# v2022-01-21 Initial Version
# v2022-02-12 Code Refactoring/Cleanup
# v2022-02-27 More code Refactoring/Cleanup (does not use ijson)
#
# Developed/tested on Ubuntu 20x64 running Python 3.8 using Android12 data (https://thebinaryhick.blog/public_images/) provided by Josh Hickman (@josh_hickman1) 
#
# Usage Example:
# python gLocationHistoryActivity.py -i "Location History.json" -o output_dir
#

import argparse
import json
import datetime
import os 

version_string = "gLocationHistoryActivity.py v2022-02-27"

def main():
    usagetxt = " %(prog)s [-i inputfile -o output_dir -a start_isodate -b end_isodate]"
    parser = argparse.ArgumentParser(description='Extracts/parses "Detected Activity" data from Google Takeout "Location History.json" and outputs TSV & KML files to output_dir', usage=usagetxt)
    parser.add_argument("-i", dest="input", action="store", required=True, help='Input Location History filename')
    parser.add_argument("-o", dest="output", action="store", required=True, help='Output KML/TSV directory')
    parser.add_argument("-a", dest="start", action="store", required=False, help='Filter FROM (inclusive) Start ISO date (YYYY-MM-DD)', default='0000-01-01')
    parser.add_argument("-b", dest="end", action="store", required=False, help='Filter BEFORE (inclusive) End ISO date (YYYY-MM-DD)', default='9999-12-31')
    
    args = parser.parse_args()

    print("Running " + version_string + "\n")
    
    if not args.input or not args.output:
        parser.exit("ERROR - Input file or Output files NOT specified")
    
    # Check input file exists before trying to connect
    if not os.path.isfile(args.input):
        print(args.input + " input file does not exist!")
        exit(-1)
    # Output dir check
    if not os.path.isdir(args.output):
        print("Creating output directory: " + args.output)
        os.mkdir(args.output)

    #activities = []
    folder_dict = {} # dict of element lists containing tuples. dict keyed by isodate yyyy-mm-dd
    
    # read input JSON file
    with open(args.input) as inputdata:
        jsondata = json.load(inputdata)
        count_element = 0
        count_element_activity = 0
        count_sub_total = 0
        count_multiple_activitys = 0
        
        # JSON data consists of list of elements. 
        # Each element may/may not have an activity list.
        # Each activity list will have 1 or more subactivities
        for element in jsondata["locations"]:
            count_element += 1
            #print(element["timestampMs"]) # parent element timestamp
            element_timestamp = element["timestampMs"]
            element_timestamp_str = datetime.datetime.utcfromtimestamp(int(element_timestamp)/1000).isoformat()
            element_lat = float(element["latitudeE7"]/10000000)
            element_llg = float(element["longitudeE7"]/10000000)
            element_accuracy = element["accuracy"]
            
            element_alt = "NOT_SPECIFIED"
            if "altitude" in element: # altitude not always specified
                element_alt = float(element["altitude"])
            
            element_verticalaccuracy = "NOT_SPECIFIED"
            if "verticalAccuracy" in element: # verticalAccuracy not always specified
                element_verticalaccuracy = element["verticalAccuracy"]
            
            element_heading = "NOT_SPECIFIED"
            if "heading" in element: # heading not always specified
                element_heading = element["heading"]
                    
            element_velocity = "NOT_SPECIFIED"
            if "velocity" in element: # velocity not always specified
                element_velocity = element["velocity"]
            
            element_source = element["source"]
            element_device = str(element["deviceTag"])
            
            element_platform = "NOT_SPECIFIED"
            if "platformType" in element: # platformType not always specified
                element_platform = element["platformType"]
            
            print("\nElement index: " + str(count_element) + " with Element timestamp = " + element_timestamp + " => Element timestamp str = " + element_timestamp_str)
            
            if "activity" in element: # parent activity list
                count_element_activity += 1
                print("Element Activity data = " + str(element["activity"]))
                print("No. (sub)activitys => " + str(len(element["activity"])))
                if (len(element["activity"]) > 1):
                    count_multiple_activitys += 1 
                    
                # Each element activity has at least one child activity which is represented as a list of type/confidence dicts
                count_child = 0
                for activity in element["activity"]:
                    count_child += 1
                    print("(sub)activity index no. = " + str(count_child))
                    print("(sub)activity data = " + str(activity))
                    activity_timestamp = activity["timestampMs"]
                    activity_timestamp_str = datetime.datetime.utcfromtimestamp(int(activity_timestamp)/1000).isoformat()
                                        
                    # Each (sub)activity can have multiple types:
                    # IN_VEHICLE	The device is in a vehicle, such as a car.
                    # ON_BICYCLE	The device is on a bicycle.
                    # ON_FOOT	The device is on a user who is walking or running.
                    # RUNNING	The device is on a user who is running.
                    # STILL	The device is still (not moving).
                    # TILTING	The device angle relative to gravity changed significantly.
                    # UNKNOWN	Unable to detect the current activity.
                    # WALKING	The device is on a user who is walking.
                    #
                    # confidence    value from 0 to 100 indicating how likely it is that the user is performing this activity.
                    #
                    # Source: https://developers.google.com/android/reference/com/google/android/gms/location/DetectedActivity
                    count_sub = 0
                    subactivity_str = ""
                    for subact in activity["activity"]:
                        count_sub += 1
                        subactivity_str += str(subact["type"] + " [" + str(subact["confidence"]) + "], ")
                    
                    print("No. Sub-Activity types: " + str(count_sub))
                    
                    # Store each activity & its subactivitys    
                    folderid = element_timestamp_str.split("T")[0] # eg 2022-02-04T09:56:36.253Z
                    if (folderid >= args.start and folderid <= args.end): # only add elements from given date range (if no range entered, start='0000-01-01', end='9999-12-31')
                        if folderid not in folder_dict.keys(): # add entry 1 if key has not been created before
                            folder_dict[folderid] = [(element_source, element_device, element_platform, element_timestamp, element_timestamp_str, element_lat, element_llg, element_alt, element_heading, element_velocity, element_accuracy, element_verticalaccuracy, count_sub, activity_timestamp, activity_timestamp_str, subactivity_str[:-2])]
                        else:
                            # add n-th entry to existing folder
                            folder_dict[folderid].append((element_source, element_device, element_platform, element_timestamp, element_timestamp_str, element_lat, element_llg, element_alt, element_heading, element_velocity, element_accuracy, element_verticalaccuracy, count_sub, activity_timestamp, activity_timestamp_str, subactivity_str[:-2]))
                    count_sub_total += count_sub
                # end for activity in element loop
        # end for element loop
    # end open file
    
    print("\nTotal no. of elements with at least one Activity = " + str(count_element_activity))
    print("No. of elements with multiple Activitys = " + str(count_multiple_activitys))
    
    print("\nNumber of days extracted = " + str(len(folder_dict.keys())))
    
    entry_checksum = 0            
    # Write KML report
    # For each day, write a KML and a TSV
    for isodate in folder_dict.keys():
        kmlfile = os.path.join(args.output, str(isodate + ".kml"))
        tsvfile = os.path.join(args.output, str(isodate + ".tsv"))
        
        entry_list = folder_dict[isodate] # can be more than one tuple in list ie multiple entries per day
        entry_checksum += len(entry_list)
        print("Processing " + isodate + " = " + str(len(entry_list)) + " entries")
        
        # Write KML report
        with open(kmlfile, "w") as outputKML:
            outputKML.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
            outputKML.write("<kml xmlns=\"http://www.opengis.net/kml/2.2\">\n")
            outputKML.write("<Document>")
            outputKML.write("\n<name>" + kmlfile + "</name><open>1</open>\n")
            outputKML.write("<Folder><name>" + isodate + "</name><open>1</open>\n")
            outputKML.write("<Style id=\"BalloonStyle\">\n")
            outputKML.write("<BalloonStyle>\n")
            outputKML.write("<text><b>$[name]</b><br></br>$[description]</text>\n") # to disable Directions to/from here in balloon
            outputKML.write("</BalloonStyle>\n")
            outputKML.write("</Style>\n")

            # for each activity @ the isodate                
            for element_source, element_device, element_platform, element_timestamp, element_timestamp_str, element_lat, element_llg, element_alt, element_heading, element_velocity, element_accuracy, element_verticalaccuracy, count_sub, activity_timestamp, activity_timestamp_str, subactivity_str in entry_list:
                outputKML.write("<Placemark>\n")
                outputKML.write("<visibility>0</visibility>\n")  
                outputKML.write("<styleUrl>#BalloonStyle</styleUrl>\n")
                outputKML.write("<Style><IconStyle><Icon><href>http://maps.google.com/mapfiles/ms/micons/red-dot.png</href></Icon></IconStyle></Style>\n") # red dot
                outputKML.write("<name>" + element_timestamp_str + " [" + str(element_timestamp) + "], num_subactivity_types = " + str(count_sub) + "</name>\n")

                outputKML.write("<description>" + "<b>source: </b>" + element_source + ", <b>deviceTag: </b>" + element_device + ", <b>platformType: </b>" + element_platform + "<br/><b>lat: </b>" + str(element_lat) + ", <b>long: </b>" + str(element_llg) + ", <b>alt: </b>" + str(element_alt) + \
                    ", <b>heading: </b>" + str(element_heading) + ", <b>velocity: </b>" + str(element_velocity) + ", <b>accuracy: </b>" + str(element_accuracy) + ", <b>verticalAccuracy: </b>" + str(element_verticalaccuracy) + \
                    "<br/><b>activity timestamp: </b>" + activity_timestamp_str + " [" + str(activity_timestamp) + "] <br/><b>detected activity(s): </b>" + subactivity_str + "</description>\n")
                outputKML.write("<Point><coordinates>" + str(element_llg) + ", " + str(element_lat) + ", " + str(element_alt) + "</coordinates></Point>\n")
                outputKML.write("<Timestamp><when>" + element_timestamp_str + "</when></Timestamp>\n")
                outputKML.write("</Placemark>\n")
                
            outputKML.write("</Folder>\n") #  folder
            outputKML.write("\n</Document>\n")
            outputKML.write("</kml>\n")

        # Write TSV report
        with open(tsvfile, "w") as outputTSV: 
            outputTSV.write("source\tdeviceTag\tplatformType\telement_timestamp\telement_timestamp_str\tlatitude\tlongitude\taltitude\theading\tvelocity\taccuracy\tverticalAccuracy\tnum_subactivity_types\tactivity_timestamp\tactivity_timestamp_str\tdetected_activity\n")
            # for each activity @ the isodate
            for element_source, element_device, element_platform, element_timestamp, element_timestamp_str, element_lat, element_llg, element_alt, element_heading, element_velocity, element_accuracy, element_verticalaccuracy, count_sub, activity_timestamp, activity_timestamp_str, subactivity_str in entry_list:
                outputTSV.write(element_source + "\t" + element_device  + "\t" + element_platform  + "\t" + str(element_timestamp) + "\t" + element_timestamp_str + "\t" + str(element_lat)  + "\t" + str(element_llg)  + "\t" + str(element_alt) + "\t" + str(element_heading) + "\t" + str(element_velocity) + "\t" + str(element_accuracy) + "\t" + str(element_verticalaccuracy) + "\t" + str(count_sub) + "\t" + str(activity_timestamp) + "\t" + activity_timestamp_str + "\t" + subactivity_str + "\n") 
    # end for each day loop
    
    print("\nProcessed/Wrote " + str(entry_checksum) + " Total Activity entries to: " + args.output + "\n")
    print("Exiting ...\n")

if __name__ == "__main__":
    main()




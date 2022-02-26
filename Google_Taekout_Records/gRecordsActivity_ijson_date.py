#! /usr/bin/env python

# gRecordsActivity_ijson_date.py = Python script reads Google Takeout "Records.json" and processes Detected Activity entries
#
# Author: cheeky4n6monkey@gmail.com
#
# Version History:
# v2022-02-11 Initial Version adapted for large input JSON
# v2022-02-13A Added heading, velocity, accuracy, vertical accuracy fields
# v2022-02-13B Modified to output to directory of per day KML/TSV files
# v2022-02-18 Modified to read to dict and accept date filter args
# v2022-02-26 Modified TSV/KML field names to better match json field names
# 
# Developed/tested on Ubuntu 20x64 running Python 3.8
# Requires ijson package [pip3 install ijson]
#
# Usage Example:
# python gRecordsActivity_ijson_date.py -i "Records.json" -o output_dir -a start_isodate -b end_isodate
#

import argparse
import os 
import ijson

version_string = "gRecordsActivity_ijson_date.py v2022-02-26"

def main():
    usagetxt = " %(prog)s [-i input_file -o output_dir -a start_isodate -b end_isodate]"
    parser = argparse.ArgumentParser(description='Extracts/parses "Detected Activity" data from Google Takeout "Records.json" (large files) and outputs TSV and KML files to given output dir', usage=usagetxt)
    parser.add_argument("-i", dest="input", action="store", required=True, help='Input Records filename')
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

    count_element = 0
    count_element_activity = 0
    count_multiple_activitys = 0
    folder_dict = {} # dict of element lists containing tuples. dict keyed by isodate yyyy-mm-dd
    
    # read input JSON file
    with open(args.input) as inputdata:
        element_items = ijson.items(inputdata, 'locations.item')
        #print(list(element_items))
       
        for element in element_items: # each element
            #print("\n" + str(element))
            count_element += 1

            if 'activity' in element: # each element which has an activty
                count_element_activity += 1
                print("\nACTIVITY => ")
                print(element['activity'])
                
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
                if "platformType" in element: # altitude not always specified
                    element_platform = element["platformType"]
                
                element_formFactor = "NOT_SPECIFIED"
                if "formFactor" in element: # formFactor not always specified
                    element_formFactor = element["formFactor"]
                
                element_timestamp_str = element["timestamp"]
                print("Element timestamp: " + element_timestamp_str)
                
                element_serverTimestamp_str = "NOT_SPECIFIED"
                if "serverTimestamp" in element: # serverTimestamp not always specified
                    element_serverTimestamp_str = element["serverTimestamp"]      
                print("Element serverTimestamp: " + element_serverTimestamp_str)
            
                element_deviceTimestamp_str = "NOT_SPECIFIED"
                if "deviceTimestamp" in element: # deviceTimestamp not always specified 
                    element_deviceTimestamp_str = element["deviceTimestamp"]
                print("Element deviceTimestamp: " + element_deviceTimestamp_str)
                
                print("No. (sub)Activitys => " + str(len(element["activity"])))
                if (len(element["activity"]) > 1):
                    count_multiple_activitys += 1
                
                count_activity = 0
                for act in element["activity"]: # for each activity in element. multiple (sub)activitys can be in 1 element.
                    count_activity += 1                    
                    activity_timestamp_str = "Not found"
                    if "timestamp" in act: # search for Activity Timestamp
                        activity_timestamp_str = act["timestamp"]
                    print("(sub)Activity #" + str(count_activity) + " timestamp = " + activity_timestamp_str)
                    
                    # For each sub-activity listed, there can be multiple type/confidence pairs
                    # (sub)activity type can be:
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
                    for subact in act["activity"]:
                        count_sub += 1
                        #print("subactivity no. = " + str(count_sub))
                        #print("type: " + subact["type"])
                        #print("conf: " + str(subact["confidence"]))
                        subactivity_str += str(subact["type"] + " [" + str(subact["confidence"]) + "], ")
                    print("No. (sub)Activity types: " + str(count_sub))
                    
                    # Store each activity & its subactivitys    
                    folderid = element_timestamp_str.split("T")[0] # eg 2022-02-04T09:56:36.253Z
                    if (folderid >= args.start and folderid <= args.end): # only add elements from given date range (if no range entered, start='0000-01-01', end='9999-12-31')
                        if folderid not in folder_dict.keys(): # add entry 1 if key has not been created before
                            folder_dict[folderid] = [(element_source, element_device, element_platform, element_formFactor, element_serverTimestamp_str, element_deviceTimestamp_str, element_timestamp_str, element_lat, element_llg, element_alt, element_heading, element_velocity, element_accuracy, element_verticalaccuracy, count_sub, activity_timestamp_str, subactivity_str[:-2])]
                        else:
                            # add n-th entry to existing folder
                            folder_dict[folderid].append((element_source, element_device, element_platform, element_formFactor, element_serverTimestamp_str, element_deviceTimestamp_str, element_timestamp_str, element_lat, element_llg, element_alt, element_heading, element_velocity, element_accuracy, element_verticalaccuracy, count_sub, activity_timestamp_str, subactivity_str[:-2]))
                
                # end for activity in element loop
        # ends for element loop
        
    print("\n\nTotal no. of elements with at least one Activity = " + str(count_element_activity))
    print("No. of elements with multiple Activitys = " + str(count_multiple_activitys))
   
    print("\nProcessing Activitys ... Number of days = " + str(len(folder_dict.keys())))
    
    entry_checksum = 0
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
            for element_source, element_device, element_platform, element_formFactor, element_serverTimestamp_str, element_deviceTimestamp_str, element_timestamp_str, element_lat, element_llg, element_alt, element_heading, element_velocity, element_accuracy, element_verticalaccuracy, count_sub, activity_timestamp_str, subactivity_str in entry_list:
                outputKML.write("<Placemark>\n")
                outputKML.write("<visibility>0</visibility>\n")  
                outputKML.write("<styleUrl>#BalloonStyle</styleUrl>\n")
                outputKML.write("<Style><IconStyle><Icon><href>http://maps.google.com/mapfiles/ms/micons/red-dot.png</href></Icon></IconStyle></Style>\n") # red dot
                outputKML.write("<name>" + element_timestamp_str + ", num_subactivity_types = " + str(count_sub) + "</name>\n")

                outputKML.write("<description>" + "<b>source: </b>" + element_source + ", <b>deviceTag: </b>" + element_device + ", <b>formFactor: </b>" + element_formFactor + ", <b>platformType: </b>" + element_platform + "<br/><b>lat: </b>" + str(element_lat) + ", <b>long: </b>" + str(element_llg) + ", <b>alt: </b>" + str(element_alt) + \
                    ", <b>heading: </b>" + str(element_heading) + ", <b>velocity: </b>" + str(element_velocity) + ", <b>accuracy: </b>" + str(element_accuracy) + ", <b>verticalAccuracy: </b>" + str(element_verticalaccuracy) + \
                    "<br/><b>serverTimestamp: </b>" + element_serverTimestamp_str + "<br/><b>deviceTimestamp: </b>" + element_deviceTimestamp_str + "<br/><b>activity timestamp: </b>" + activity_timestamp_str + "<br/><b>detected activity(s): </b>" + subactivity_str + "</description>\n")
                outputKML.write("<Point><coordinates>" + str(element_llg) + ", " + str(element_lat) + ", " + str(element_alt) + "</coordinates></Point>\n")
                outputKML.write("<Timestamp><when>" + element_timestamp_str + "</when></Timestamp>\n")
                outputKML.write("</Placemark>\n")
                
            outputKML.write("</Folder>\n") #  folder
            outputKML.write("\n</Document>\n")
            outputKML.write("</kml>\n")

        # Write TSV report
        with open(tsvfile, "w") as outputTSV: 
            outputTSV.write("source\tdeviceTag\tplatformType\tformFactor\tserverTimestamp\tdeviceTimestamp\telement_timestamp\tlatitude\tlongitude\taltitude\theading\tvelocity\taccuracy\tverticalAccuracy\tnum_subactivity_types\tactivity_timestamp\tdetected_activity\n")
            # for each activity @ the isodate
            for element_source, element_device, element_platform, element_formFactor, element_serverTimestamp_str, element_deviceTimestamp_str, element_timestamp_str, element_lat, element_llg, element_alt, element_heading, element_velocity, element_accuracy, element_verticalaccuracy, count_sub, activity_timestamp_str, subactivity_str in entry_list:
                outputTSV.write(element_source + "\t" + element_device  + "\t" + element_platform  + "\t" +  element_formFactor + "\t" + element_serverTimestamp_str + "\t" + element_deviceTimestamp_str + "\t" + element_timestamp_str + "\t" + str(element_lat)  + "\t" + str(element_llg)  + "\t" + str(element_alt) + "\t" + str(element_heading) + "\t" + str(element_velocity) + "\t" + str(element_accuracy) + "\t" + str(element_verticalaccuracy) + "\t" + str(count_sub) + "\t" + activity_timestamp_str + "\t" + subactivity_str + "\n") 
    # end for each day loop
    
    print("\nProcessed/Wrote " + str(entry_checksum) + " Total Activity entries to: " + args.output + "\n")
    print("Exiting ...\n")                       
                
if __name__ == "__main__":
    main()




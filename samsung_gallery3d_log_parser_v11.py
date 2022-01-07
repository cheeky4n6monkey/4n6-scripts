#! /usr/bin/env python

# samsung_gallery3d_log_parser_v11.py = Python script to parse a Samsung com.sec.android.gallery3d's (v11) local.db log table
#
# Based on research by Michael Lacombe (iacismikel@gmail.com)
#
# Author: cheeky4n6monkey@gmail.com
#
# Version History:
# v2021-11-14 Initial Version
# v2021-11-20 Modified decode_logitem using reversing knowledge + added Thumbnail/validate file/publishDecodedBitmap/FileOplog handling
#
# Developed/tested on Ubuntu 20x64 running Python 3.8 using sample data provided by Michael Lacombe.
#
# Usage Example:
# python samsung_gallery3d_log_parser_v11.py -d local.db -o output.TSV
#

import argparse
import sqlite3
from os import path
import base64
import re
import urllib.parse

version_string = "samsung_gallery3d_log_parser_v11.py 2021-11-20"


def decode_path(pathstring):
    # function to base64 decode given path string
    # eg gZ2M4pePL3Pil490b+KYhXLil49h4piFZ+KYhWXimIUvZeKYhW11bOKYhWHimIV04piFZWTimIUvMC/il49EQ+KXj0nil49N4piFL+KXj0PimIVh4piFbWVy4piFYS/il48y4piFMOKYhTLimIUw4pePMOKXjznil48x4piFNOKYhV8x4piFNuKYhTU04pePMeKXjzYuauKYhXDil49nuJlMxZq

    found = False
    finalstredit ="ERROR! Failed to decode path"
    #print("input = " + pathstring)
    # remove last 7 letters
    truncated_strg = pathstring[0:-7]
    #print(truncated_strg)
    #print("trunc len = " + str(len(truncated_strg)))

    for i in range(3,7): # remove between 3 to 6 chars from start
        test_strg = truncated_strg[i:] # starts at 4th char at index 3 ... 7th char is at index 6
        try:
            #print("test_strg = " + test_strg)
            b64decodedstr = base64.b64decode(test_strg)
            utf8str = b64decodedstr.decode('UTF-8')
            finalstr = utf8str.replace('\u2605', '').replace('\u25CF', '').replace('\u25C6', '') # remove "Black Star", "Black Circle", "Black Diamond" chars
            if (finalstr.isascii() and finalstr.isprintable() and not ('\"' in finalstr) ):
                print("Found valid path = " + finalstr + "\n for: " + test_strg) # found a valid path ...
                finalstredit = finalstr
                found = True
                break
        except Exception as e:
                # error generated trying to decode, keep going
                #print("exception = " + repr(e))
                continue
    
    if not found:
        print("ERROR! Failed to decode path")
    
    return(finalstredit)    
#end decode_path


def process_log(logstring):
    logentries = []
    decoded_paths = "No base64 Paths detected"

    # Process different log formats containing base64 encoded paths
    if logstring.startswith("[DELETE_SINGE]"):
        print("[DELETE_SINGE]")
        # [DELETE_SINGE][1][0][location://timeline?position=49&mediaItem=data%3A%2F%2FmediaItem%2F-457825738&from_expand=false][AoT4pePL+KXj3PimIV0b+KYhXLil49h4pePZ2XimIUv4pePZeKXj23imIV14pePbOKYhWHimIV04piFZeKXj2TimIUv4pePMOKXjy/il49E4pePQ+KYhUlN4pePL+KXj0NhbeKYhWVy4piFYeKXjy8y4piFMDIxMOKXjzbil48xMeKYhV8x4pePOOKYhTDimIU44pePMzQubeKXj3DimIU0JTSOXSS]
        # [DELETE_SINGE][1][0][location://albums/fileList?id=-1739773001&position=86&count=216&mediaItem=data%3A%2F%2FmediaItem%2F-1550340550&from_expand=false][lizP4pePL+KXj3N04piFb+KXj3Lil49h4pePZ+KXj2UvZeKYhW3imIV14piFbGHil4904pePZeKYhWQvMOKXjy/imIVE4pePQ+KYhUnil49N4piFL+KXj0PimIVh4pePbeKXj2Xil49y4pePYS/imIUyMOKYhTIxMDfil48x4pePNeKXj1/il48x4pePMOKXjzAzNOKYhTXimIUu4piFauKXj3BnkLKz4jR]
        # regex from https://www.geeksforgeeks.org/python-extract-substrings-between-brackets/
        res = re.findall(r'\[.*?\]', logstring)
        # numitems = len(res)
        # should always be 4 items for DELETE_SINGE
        opstring = "DELETE_SINGE"
        idx1 = res[1].replace("[", "").replace("]", "") 
        idx2 = res[2].replace("[", "").replace("]", "")
        location = res[3].replace("[", "").replace("]", "")
        timeline_pos = ""
        timeline_mediaItem = ""
        albums_id = ""
        albums_pos = ""
        albums_count = ""
        albums_mediaItem = ""
        if location.startswith("location://timeline?position"):
            decoded_loc = urllib.parse.parse_qs(location)
            #print(decoded_loc)
            timeline_pos = ' '.join(decoded_loc["location://timeline?position"]) # parse_qs returns a list
            timeline_mediaItem = ' '.join(decoded_loc["mediaItem"])
        if location.startswith("location://albums/fileList?id"):
            decoded_loc = urllib.parse.parse_qs(location)
            #print(decoded_loc)
            albums_id = ' '.join(decoded_loc["location://albums/fileList?id"]) # parse_qs returns a list
            albums_pos = ' '.join(decoded_loc["position"]) 
            albums_count = ' '.join(decoded_loc["count"])  
            albums_mediaItem = ' '.join(decoded_loc["mediaItem"])  
        # 5th item should store base64 path (assume only one path)
        decoded_paths = decode_path(res[4].replace("[", "").replace("]", ""))
        #print(decoded_paths)
        logentries.append((opstring, idx1, idx2, location, timeline_pos, timeline_mediaItem, albums_id, albums_pos, albums_count, albums_mediaItem, decoded_paths))
        
    if logstring.startswith("[DELETE_SINGLE]"):
        print("[DELETE_SINGLE]")
        # [DELETE_SINGLE] Req Total[1] LI[1] CI[0] LCI[0] LV[0] CV[0] LCV[0] Success LI[1] CI[0] LCI[0] LV[0] CV[0] LCV[0] Fail LI[0] CI[0] LCI[0] LV[0] CV[0] LCV[0] Path[fBIlpEL3Pil490b+KYhXLil49h4piFZ+KYhWXimIUv4piFZeKYhW3imIV14pePbOKXj2HimIV04piFZeKXj2Qv4pePMC/imIVT4pePYeKYhW3imIVz4piFdeKXj27il49n4piFL+KYhU3imIV14pePc+KYhWnil49jL+KXj0lN4piFR+KYhV/il48y4piFMOKXjzLil48x4piFMeKXjzAwNOKYhV8xMTTimIU14piFNOKXjzbimIUu4piFauKXj3Dil49nKOKXjzLimIU04pePNeKYhTfimIUpRInC0SQ ] Scan[] LD[1] CD[0] MF[0] AB[0] ABR[false] [location://timeline?position=4&media_item=data%3A%2F%2FmediaItem%2F1396640027&from_expand=false]
        # [DELETE_SINGLE] Req Total[1] LI[1] CI[0] LCI[0] LV[0] CV[0] LCV[0] Success LI[1] CI[0] LCI[0] LV[0] CV[0] LCV[0] Fail LI[0] CI[0] LCI[0] LV[0] CV[0] LCV[0] Path[P/3t84piFL+KXj3PimIV04piFb+KXj3Jh4pePZ2Xil48v4pePZW3il4914pePbOKXj2HimIV04pePZeKXj2Til48v4piFMOKYhS9Q4pePaeKYhWPil490deKYhXLimIVl4piFc+KXjy9p4piFbuKYhXNob+KYhXTil48vSeKYhW7il49TaG/il490X+KXjzLimIUw4piFMuKXjzHil48wN+KYhTAyX+KYhTEy4pePNeKXjzTimIUx4pePNuKYhTHil483NeKXjy5q4pePcOKYhWfimIUoNuKYhTfimIUx4piFNeKYhTQpGH/PZAT ] Scan[] LD[1] CD[0] MF[0] AB[0] ABR[false] [location://albums/fileList?id=-1035483745&position=3&count=4&media_item=data%3A%2F%2FmediaItem%2F61752542&from_expand=false]
        # extract [Path ...] and [location://timeline?position=4&media_item=data%3A%2F%2FmediaItem%2F1396640027&from_expand=false]
        # or
        # extract [Path ...] and [location://albums/fileList?id=-1035483745&position=3&count=4&media_item=data%3A%2F%2FmediaItem%2F61752542&from_expand=false]
        # requires different regexes to DELETE_SINGE
        opstring = "DELETE_SINGLE"
        idx1 = ""
        idx2 = ""
        loc = ""
        timeline_pos = ""
        timeline_mediaItem = ""
        albums_id = ""
        albums_pos = ""
        albums_count = ""
        albums_mediaItem = ""
        
        # Extract path and decode
        respath = re.findall(r'Path\[.*? \]', logstring)
        path = respath[0].replace("Path[", "").replace(" ]", "")
        #print(path)
        #numpathitems = len(respath) # should be single path
        decoded_paths = decode_path(path)
        #print(decoded_paths)
        
        if "[location://timeline?position=" in logstring:
            print("[DELETE_SINGLE] - timeline")
            # URI decode location string 
            locterm = re.findall(r'\[location:\/\/timeline\?position=.*?\]', logstring)
            #numlocitems = len(locterm)
            #print(locterm)
            loc = locterm[0].replace("[", "").replace("]", "") # should only be one location item
            parsed_loc = urllib.parse.parse_qs(loc)
            #print(parsed_loc)
            timeline_pos = ' '.join(parsed_loc["location://timeline?position"]) # parse_qs returns a list
            timeline_mediaItem = ' '.join(parsed_loc["media_item"])
        
        if "[location://albums/fileList?id=" in logstring:
            print("[DELETE_SINGLE] - albums")
            # URI decode location string 
            locterm = re.findall(r'\[location:\/\/albums\/fileList\?id=.*?\]', logstring)
            #numlocitems = len(locterm)
            #print(locterm)
            loc = locterm[0].replace("[", "").replace("]", "") # should only be one location item
            parsed_loc = urllib.parse.parse_qs(loc)
            #print(parsed_loc)
            albums_id = ' '.join(parsed_loc["location://albums/fileList?id"]) # parse_qs returns a list
            albums_pos = ' '.join(parsed_loc["position"])
            albums_count = ' '.join(parsed_loc["count"])
            albums_mediaItem = ' '.join(parsed_loc["media_item"])
        
        logentries.append((opstring, idx1, idx2, loc, timeline_pos, timeline_mediaItem, albums_id, albums_pos, albums_count, albums_mediaItem, decoded_paths)) 
    
    if logstring.startswith("[MOVE_TO_TRASH_SINGLE]"):
        #print("[MOVE_TO_TRASH_SINGLE]")
        #[MOVE_TO_TRASH_SINGLE] Req Total[1] LI[1] CI[0] LCI[0] LV[0] CV[0] LCV[0] Success LI[1] CI[0] LCI[0] LV[0] CV[0] LCV[0] Fail LI[0] CI[0] LCI[0] LV[0] CV[0] LCV[0] Path[rXrH8L+KYhXN04pePb+KYhXLil49h4piFZ2Xil48vZW3il4914piFbOKXj2F0ZWQv4pePMOKXjy/imIVEQ0nimIVN4piFL+KXj1Pil49jcmXimIVl4pePbuKYhXPil49o4pePb3Rz4pePL+KYhVNj4pePcmXimIVl4piFbnPil49ob+KXj3TimIVf4pePMuKXjzDimIUy4piFMTDil4834pePMTQtMTHimIUw4piFOeKYhTPil480X01h4pePcOKXj3PimIUu4piFauKXj3DimIVn4piFKDXil48y4piFMuKYhSk=h6L9LnR ] Scan[] LD[1] CD[0] MF[0] AB[0] ABR[false] [location://timeline?position=327&media_item=data%3A%2F%2FmediaItem%2F-1038595013&from_expand=false]
        # extract [Path ...] and [location: ...]
        opstring = "MOVE_TO_TRASH_SINGLE"
        idx1 = ""
        idx2 = ""
        loc = ""
        timeline_pos = ""
        timeline_mediaItem = ""
        albums_id = ""
        albums_pos = ""
        albums_count = ""
        albums_mediaItem = ""
        
        # extract Path and decode
        respath = re.findall(r'Path\[.*? \]', logstring)
        path = respath[0].replace("Path[", "").replace(" ]", "")
        #print(path)
        #numpathitems = len(respath) # should be only one path
        decoded_paths = decode_path(path)
        #print(decoded_paths)
        
        # extract location
        locterm = re.findall(r'\[location:\/\/timeline\?position=.*?\]', logstring)
        #numlocitems = len(locterm)
        #print(locterm)
        loc = locterm[0].replace("[", "").replace("]", "") # should only be one location item
        parsed_loc = urllib.parse.parse_qs(loc)
        #print(parsed_loc)
        timeline_pos = ' '.join(parsed_loc["location://timeline?position"]) # parse_qs returns a list
        timeline_mediaItem = ' '.join(parsed_loc["media_item"])
        
        logentries.append((opstring, idx1, idx2, loc, timeline_pos, timeline_mediaItem, albums_id, albums_pos, albums_count, albums_mediaItem, decoded_paths)) 
        
    if logstring.startswith("[DELETE_MULTIPLE]"):
        #print("[DELETE_MULTIPLE]")
        # [DELETE_MULTIPLE] Req Total[3] LI[3] CI[0] LCI[0] LV[0] CV[0] LCV[0] Success LI[3] CI[0] LCI[0] LV[0] CV[0] LCV[0] Fail LI[0] CI[0] LCI[0] LV[0] CV[0] LCV[0] Path[ih6L3PimIV04piFb3Lil49h4pePZ+KYhWXimIUv4pePZeKXj23il491bGHimIV0ZeKYhWQv4pePMOKXjy/il49T4piFYW3il49z4pePdeKXj27imIVn4pePL03imIV1c+KXj2lj4pePL+KYhUnimIVNR+KYhV/imIUyMOKXjzLimIUx4piFMOKYhTkyOOKYhV8x4pePNuKXjzLil48yNeKYhTPimIUu4piFanDimIVnKOKYhTIx4pePNjkp08aML/f 2vySL+KYhXPil490b+KYhXLil49h4pePZ2Uv4pePZeKYhW3il4914pePbOKXj2F0ZeKXj2TimIUvMC9T4pePYeKYhW1z4piFdW7imIVnL+KYhU114pePc2nimIVjL+KXj0nimIVN4piFR+KXj18y4piFMOKXjzIxMOKXjznil48yOOKXj18xMeKXjzUx4pePNOKXjzbimIUu4piFanDimIVn4piFKDIxN+KXjzIpg392iPI 7DKgRL+KXj3Pil4904piFb+KYhXJhZ+KYhWXimIUvZeKYhW114pePbOKYhWHil490ZWTil48v4pePMC/imIVT4pePYeKXj23imIVzdW5n4piFL+KYhU3imIV14pePc+KYhWnimIVj4piFL+KYhUnimIVN4pePR1/il48yMDIx4piFMDnimIUy4piFNl/imIUxOTHimIU44pePM+KYhTAu4pePauKYhXDil49n4pePKOKXjzLil48x4piFMjEpsfkp8HE ] Scan[] LD[3] CD[0] MF[0] AB[0] ABR[false] [location://albums/fileList?id=-2034941642&position=5&count=116]
        # [DELETE_MULTIPLE][2][0][location://timeline][wJ0dBV4pePL+KXj3Pil4904piFb3JhZ2Xil48v4pePZW3il4914pePbGF04pePZWTimIUv4piFMOKYhS9E4pePQ+KXj0nil49NL0NhbeKXj2Xil49y4piFYeKYhS8y4piFMDLil48x4pePMOKXjzfil48y4pePM1/il48x4pePOeKXjzPil48z4pePMOKXjzXil48u4pePbeKYhXDil480Ygz5uIG][ueghL+KYhXPil490b+KYhXLimIVhZ+KYhWXimIUv4pePZeKYhW3il491bGHimIV04pePZeKYhWQvMOKXjy/il49E4piFQ0nimIVN4pePL+KXj0Nh4pePbeKXj2VyYS/imIUy4pePMOKXjzLimIUx4pePMOKYhTfimIUy4pePM+KXj1/il48xOeKXjzPil48z4pePMjQu4piFbeKXj3Dil480KvGiyr/] 
        # extract path and location fields
        opstring = "DELETE_MULTIPLE"
        idx1 = ""
        idx2 = ""
        loc = ""
        timeline_pos = ""
        timeline_mediaItem = ""
        albums_id = ""
        albums_pos = ""
        albums_count = ""
        albums_mediaItem = ""
        
        path_list = []
        decoded_path_list = []
        
        if logstring.startswith("[DELETE_MULTIPLE] Req Total["):
            print("DELETE_MULTIPLE with Req")
            # [DELETE_MULTIPLE] Req Total[3] LI[3] CI[0] LCI[0] LV[0] CV[0] LCV[0] Success LI[3] CI[0] LCI[0] LV[0] CV[0] LCV[0] Fail LI[0] CI[0] LCI[0] LV[0] CV[0] LCV[0] Path[ih6L3PimIV04piFb3Lil49h4pePZ+KYhWXimIUv4pePZeKXj23il491bGHimIV0ZeKYhWQv4pePMOKXjy/il49T4piFYW3il49z4pePdeKXj27imIVn4pePL03imIV1c+KXj2lj4pePL+KYhUnimIVNR+KYhV/imIUyMOKXjzLimIUx4piFMOKYhTkyOOKYhV8x4pePNuKXjzLil48yNeKYhTPimIUu4piFanDimIVnKOKYhTIx4pePNjkp08aML/f 2vySL+KYhXPil490b+KYhXLil49h4pePZ2Uv4pePZeKYhW3il4914pePbOKXj2F0ZeKXj2TimIUvMC9T4pePYeKYhW1z4piFdW7imIVnL+KYhU114pePc2nimIVjL+KXj0nimIVN4piFR+KXj18y4piFMOKXjzIxMOKXjznil48yOOKXj18xMeKXjzUx4pePNOKXjzbimIUu4piFanDimIVn4piFKDIxN+KXjzIpg392iPI 7DKgRL+KXj3Pil4904piFb+KYhXJhZ+KYhWXimIUvZeKYhW114pePbOKYhWHil490ZWTil48v4pePMC/imIVT4pePYeKXj23imIVzdW5n4piFL+KYhU3imIV14pePc+KYhWnimIVj4piFL+KYhUnimIVN4pePR1/il48yMDIx4piFMDnimIUy4piFNl/imIUxOTHimIU44pePM+KYhTAu4pePauKYhXDil49n4pePKOKXjzLil48x4piFMjEpsfkp8HE ] Scan[] LD[3] CD[0] MF[0] AB[0] ABR[false] [location://albums/fileList?id=-2034941642&position=5&count=116]
            # extract from string with format Path[ x y ] and location://albums/fileList?id
            
            #extract path
            # regex from https://www.geeksforgeeks.org/python-extract-substrings-between-brackets/
            res = re.findall(r'Path\[.*?\]', logstring)
            #numitems = len(res) 
            #print(res)
            # should be one Path item but it can have multiple encoded paths separated by space eg Path[x y ]
            paths = res[0].replace("Path[", "").replace(" ]", "")
            path_list = paths.split(" ")
            #print(path_list)
            
            #extract location
            if (logstring.endswith("[location://timeline]")):
                loc = "location://timeline"
            if ("location://albums/fileList?id" in logstring):
                # [location://albums/fileList?id=-2034941642&position=5&count=116]
                locterm = re.findall(r'\[location:\/\/albums\/fileList\?id=.*?\]', logstring)
                #numlocitems = len(locterm) 
                #print(locterm)
                loc = locterm[0].replace("[", "").replace("]", "") # should only be one location item
                parsed_loc = urllib.parse.parse_qs(loc)
                #print(parsed_loc)
                albums_id = ' '.join(parsed_loc["location://albums/fileList?id"]) # parse_qs returns a list
                albums_pos = ' '.join(parsed_loc["position"])
                albums_count = ' '.join(parsed_loc["count"])
            if ("location://albums/fileList?count" in logstring):
                # [location://albums/fileList?count=97&id=336270141&position=3]
                locterm = re.findall(r'\[location:\/\/albums\/fileList\?count=.*?\]', logstring)
                #numlocitems = len(locterm) 
                #print(locterm)
                loc = locterm[0].replace("[", "").replace("]", "") # should only be one location item
                parsed_loc = urllib.parse.parse_qs(loc)
                #print(parsed_loc)
                albums_count = ' '.join(parsed_loc["location://albums/fileList?count"]) # parse_qs returns a list
                albums_pos = ' '.join(parsed_loc["position"])
                albums_id = ' '.join(parsed_loc["id"])
                
        if logstring.startswith("[DELETE_MULTIPLE]["):
           print("DELETE_MULTIPLE with []")
           # [DELETE_MULTIPLE][2][0][location://timeline][wJ0dBV4pePL+KXj3Pil4904piFb3JhZ2Xil48v4pePZW3il4914pePbGF04pePZWTimIUv4piFMOKYhS9E4pePQ+KXj0nil49NL0NhbeKXj2Xil49y4piFYeKYhS8y4piFMDLil48x4pePMOKXjzfil48y4pePM1/il48x4pePOeKXjzPil48z4pePMOKXjzXil48u4pePbeKYhXDil480Ygz5uIG][ueghL+KYhXPil490b+KYhXLimIVhZ+KYhWXimIUv4pePZeKYhW3il491bGHimIV04pePZeKYhWQvMOKXjy/il49E4piFQ0nimIVN4pePL+KXj0Nh4pePbeKXj2VyYS/imIUy4pePMOKXjzLimIUx4pePMOKYhTfimIUy4pePM+KXj1/il48xOeKXjzPil48z4pePMjQu4piFbeKXj3Dil480KvGiyr/] 
           # extract from string with format [location://timeline] then [pathx][pathy]
           
           # extract location (test data was set to location://timeline or location://albums/fileList?count=97&id=336270141&position=3 )
           res = re.findall(r'\[.*?\]', logstring)
           #print(res)
           numitems = len(res)
           idx1 = res[1].replace("[", "").replace("]", "") 
           idx2 = res[2].replace("[", "").replace("]", "")
           loc = res[3].replace("[", "").replace("]", "")
           if not ("location://timeline" in loc):
               parsedloc = urllib.parse.parse_qs(location)
               #print(parsedloc)
               if ("albums" in loc):
                   albums_count = ' '.join(parsed_loc["location://albums/fileList?count"]) # parse_qs returns a list
                   albums_pos = ' '.join(parsed_loc["position"])
                   albums_id = ' '.join(parsed_loc["id"])
           
           # extract base64 paths from 5th [item] onwards
           # should be in format [pathx][pathy]
           for j in range(4, numitems):
               path = res[j].replace("[", "").replace("]", "") 
               path_list.append(path)
        
        #print(path_list)
        for path in path_list:
            decoded_path = decode_path(path)
            decoded_path_list.append(decoded_path)
        if (len(decoded_path_list) > 0):
            decoded_paths = ' '.join(decoded_path_list)

        logentries.append((opstring, idx1, idx2, loc, timeline_pos, timeline_mediaItem, albums_id, albums_pos, albums_count, albums_mediaItem, decoded_paths)) 

        
    if logstring.startswith("Thumbnail:"):
        # Thumbnail: WnWpfD4pePL3N0b+KXj3JhZ2XimIUvZW114piFbOKXj2Hil4904piFZeKXj2Til48vMOKXjy9T4piFaWxl4piFbuKXj3TimIVWaeKYhWTil49l4pePby/imIUy4pePMDIxMOKYhTjil48x4piFNuKYhV8x4pePN+KYhTLil4844pePMTfil48w4piFMOKXjznimIUubXDil480axueCy//1209/true
        opstring = "Thumbnail"
        initstring = logstring.replace("Thumbnail: ", "")
        middlestring = '/'.join(initstring.split("/")[:-2])
        #print("middlestring = " + middlestring)
        decoded_path = decode_path(middlestring)
        print("Thumbnail path = " + decoded_path)
        logentries.append((opstring, "", "", "", "", "", "", "", "", "", decoded_path)) 
    
    if logstring.startswith("publishDecodedBitmap:"):
        # publishDecodedBitmap: mALrq4piFL3N04piFb+KYhXJh4piFZ+KYhWUvMOKXjzHimIUyM+KYhS004pePNeKXjzbimIU3L0nil49u4piFU+KYhWjimIVv4pePdCDimIVU4pePcuKXj2HimIVuc+KYhWbil49l4pePcuKXj3MvSeKXj27il49T4piFaOKYhW/imIV04pePX+KXjzIw4piFMuKYhTAwOTPil48wX+KYhTHil480Mzbil48w4piFNOKYhTDimIUx4piFNOKXjy5tcOKXjzQ=c7myP2I/2147505005/false/Local
        opstring = "publishDecodedBitmap"
        initstring = logstring.replace("publishDecodedBitmap: ", "")
        middlestring = "/".join(initstring.split("/")[:-3])
        #print("middlestring = " + middlestring)
        decoded_path = decode_path(middlestring)
        print("publishDecodedBitmap path = " + decoded_path)
        logentries.append((opstring, "", "", "", "", "", "", "", "", "", decoded_path)) 
    
    if logstring.startswith("Detail: validate file :"):
        # Detail: validate file : ix2Nh4pePL3PimIV04piFb+KXj3Lil49h4piFZ+KYhWUvMDHimIUy4pePM+KYhS00NTY34pePL0nimIVuU+KYhWjimIVv4piFdCDil49UcmFu4piFc+KYhWbil49l4pePcuKXj3PimIUvSeKXj25TaOKYhW/il490X+KYhTLimIUw4pePMuKXjzDil48xMOKYhTAx4piFXzHimIU2NTXimIU04piFNeKYhTLimIUy4piFOOKYhS5t4piFcOKXjzQ=GFcYd2S, exist=false, size=0,file not found
        opstring = "Detail: validate file"
        initstring = logstring.replace("Detail: validate file : ", "")
        if "header(non-jpeg)" in initstring:
            middlestring = ",".join(initstring.split(",")[:-4])
        else:
            middlestring = ",".join(initstring.split(",")[:-3])    
        #print("middlestring = " + middlestring)
        decoded_path = decode_path(middlestring)
        print("Detail: validate file path = " + decoded_path)
        logentries.append((opstring, "", "", "", "", "", "", "", "", "", decoded_path)) 
        
    if logstring.startswith("[FileOpLog_ver3][type=move][OP_LOCAL_OK][src_path]"):
        # [FileOpLog_ver3][type=move][OP_LOCAL_OK][src_path][93T2C4pePKOKYhS9zdOKXj2/il49yYWdlL2Xil49tdWxh4pePdOKXj2VkL+KYhTDil48vTeKYhW/il492aeKXj2VzL2nimIVu4piFc2jil49v4piFdCk=YMquYjz][dst_path][J2ajdh4piFL+KXj3Pil4904piFb+KXj3Lil49hZ2XimIUvOeKXj0Pil48z4pePM+KYhS3imIU24pePQuKXj0LimIVE4pePL+KXj0Zp4piFbmnil49z4piFaOKYhWXimIVkIEnil49u4piFU+KXj2jimIVv4piFdOKYhSDil49U4pePcuKXj2Hil49u4pePc+KYhWZl4piFcuKYhXM=prodW0Z][total=2][success=2][fail=0][replace=0][rename_file=0][skip=0][ppp_fail(src)=0][selected_album_id=-1][empty_album=false][new_album=false][src_path_null=0][msg=null]
        opstring = "[FileOpLog_ver3][type=move][OP_LOCAL_OK]"
        initstring = logstring.replace("[FileOpLog_ver3][type=move][OP_LOCAL_OK]", "")
        # regex from https://www.geeksforgeeks.org/python-extract-substrings-between-brackets/
        res = re.findall(r'\[.*?\]', initstring)
        src_path = res[1].replace("[", "").replace("]", "") 
        dst_path = res[3].replace("[", "").replace("]", "")
        src_decoded_path = decode_path(src_path)
        dst_decoded_path = decode_path(dst_path)
        print("[FileOpLog_ver3][type=move] src file path = " + src_decoded_path)
        print("[FileOpLog_ver3][type=move] dst file path = " + dst_decoded_path)
        decoded_paths = "src_path: " + src_decoded_path + " dst_path: " + dst_decoded_path
        logentries.append((opstring, "", "", "", "", "", "", "", "", "", decoded_paths)) 
        
    return(logentries)
#end process_log


def main():
    usagetxt = " %(prog)s [-d inputfile -o outputfile]"
    parser = argparse.ArgumentParser(description='Extracts/parses data from com.sec.android.gallery3d\'s (v11) local.db\'s log table to output TSV file', usage=usagetxt)
    parser.add_argument("-d", dest="database", action="store", required=True, help='SQLite DB filename i.e. local.db')
    parser.add_argument("-o", dest="output", action="store", required=True, help='Output file name for Tab-Separated-Value report')

    args = parser.parse_args()

    print("Running " + version_string + "\n")
    
    if not args.database or not args.output:
        parser.exit("ERROR - Input file or Output file NOT specified")
    
    # Check DB file exists before trying to connect
    if path.isfile(args.database):
        dbcon = sqlite3.connect(args.database)
    else:
        print(args.database + " DB file does not exist!")
        exit(-1)

    query = "SELECT _id, __category, __timestamp, __log FROM log ORDER BY __timestamp ASC;" # volume and hash fields are NULL
    cursor = dbcon.cursor()
    cursor.execute(query)
    row = cursor.fetchone()

    entries = []

    while row:
        _id = row[0]
        __category = row[1]
        __timestamp = row[2] # text string
        __log = row[3]

        # store each row returned    
        entries.append((_id, __category, __timestamp, __log))
        
        row = cursor.fetchone()

    cursor.close()
    dbcon.close()

    # Write TSV report
    with open(args.output, "w") as outputTSV:
        outputTSV.write("__id\t__category\t__timestamp\t__log\toperation\tlocation\ttimeline_pos\ttimeline_mediaItem\talbums_id\talbums_pos\talbums_count\talbums_mediaItem\tbase64_decoded_paths\n")
        
        for entry in entries:
            _idx = entry[0]
            __category = entry[1]
            __timestamp = entry[2]
            __log = entry[3].replace("\n", "[NEWLINE_CHAR]") # for formattings
            
            print("_id = " + str(_idx))
            # logdata stores (opstring, idx1, idx2, location, timeline_pos, timeline_mediaItem, albums_id, albums_pos, albums_count, albums_mediaItem, decoded_paths)
            logdata = process_log(__log)
            #print(logdata)
            
            op = ""
            loc = ""
            time_pos = ""
            time_item = ""
            album_id = ""
            album_pos = ""
            album_count = ""
            album_mediaItem = ""
            decoded_paths = ""
            if len(logdata):
                op = logdata[0][0]
                loc = logdata[0][3]
                time_pos = logdata[0][4]
                time_item = logdata[0][5]
                album_id = logdata[0][6]
                album_pos = logdata[0][7]
                album_count = logdata[0][8]
                album_mediaItem = logdata[0][9] 
                decoded_paths = logdata[0][10] 
            
            outputTSV.write(str(_idx) + "\t" + str(__category) + "\t" + __timestamp + "\t" + __log + \
                "\t" + op + "\t" + loc + "\t" + time_pos + "\t" + time_item + \
                "\t" + album_id + "\t" + album_pos + "\t" + album_count + "\t" + album_mediaItem + "\t" + decoded_paths + "\n")

    print("\nProcessed/Wrote " + str(len(entries)) + " entries to: " + args.output + "\n")
    print("Exiting ...\n")


if __name__ == "__main__":
    main()




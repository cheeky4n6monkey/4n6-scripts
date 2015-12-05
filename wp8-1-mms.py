#! /usr/bin/env python
# Python script to parse IPM.MMS messages from a Windows 8.10 phone's store.vol file
# Intended to be used in conjunction with "wp8-1-mms-filesort.py"
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
import glob
import struct
import datetime
import string
import re
import codecs
import binascii

version_string = "wp8-1-mms.py v2015-11-14"

# Find all indices of the "pattern" regular expression in a given string (using regex)
# Where pattern is a compiled Python re pattern object (ie the output of "re.compile")
def regsearch(bigstring, pattern, listindex=[]):
    hitsit = pattern.finditer(bigstring)
    for it in hitsit:
        # iterators only last for one shot so we capture the offsets to a list
        listindex.append(it.start())
    return(listindex)

# Read in unicode chars one at a time until a null char ie "0x00 0x00"
# Returns empty string on error otherwise it filters out return/newlines and returns the string read
def read_nullterm_unistring(f):
    readstrg = ""
    readchar = 0xABCD
    flag = True
    unprintablechars = False
    begin = f.tell()
    
    while (flag):
        try:
            #print("char at " + hex(f.tell()).rstrip("L"))
            readchar = f.read(1)
            if (readchar == unichr(0)): # bailout if null char
                flag = False
            if (flag):
                if (readchar in string.printable) and (readchar != "\r") and (readchar != "\n"):
                    readstrg += readchar
                else:
                    readstrg += " "
                    unprintablechars = True
                    print("Unprintable byte value = " + binascii.hexlify(readchar) + " at " + hex(f.tell()-2).rstrip("L"))
        except:
            print("Warning ... bad unicode string at offset " + hex(begin).rstrip("L"))
            exctype, value = sys.exc_info()[:2]
            print("Exception type = ",exctype,", value = ",value) 
            #readstrg = ""
            return(readstrg) # returns partial strings
    
    if (unprintablechars):
        print("String substitution(s) due to unrecognized/unprintable characters starting at " + hex(begin).rstrip("L"))
        print("Revised string is: " + readstrg + "\n")
    return(readstrg)

# Read in 8 byte MS FILETIME (number of 100 ns since 1 Jan 1601) and 
# Returns equivalent unix epoch offset or 0 on error
def read_filetime(f):
    begin = f.tell()
    try:
        #print("time at offset: " + str(begin))
        mstime = struct.unpack('<Q', f.read(8))[0]
    except:
        print("Bad FILETIME extraction at " + hex(begin).rstrip("L"))
        exctype, value = sys.exc_info()[:2]
        print("Exception type = ",exctype,", value = ",value) 
        return(0)
    #print(mstime)
    #print(hex(mstime))

    # Date Range Sanity Check
    # min = 0x01CD000000000000 ns = 03:27 12MAR2012 (Win8 released 29OCT2012)
    # max = 0x01D9000000000000 ns = 12:26 24NOV2022 (give it 10 years?)
    if (mstime < 0x01CD000000000000) or (mstime > 0x01D9000000000000):
        #print("Bad filetime value!")
        return(0)
    # From https://libforensics.googlecode.com/hg-history/a41c6dfb1fdbd12886849ea3ac91de6ad931c363/code/lf/utils/time.py
    # Function filetime_to_unix_time(filetime)
    unixtime = (mstime - 116444736000000000) // 10000000
    return(unixtime)


# Searches backwards for a valid timestamp from a given file ptr and range
# Returns 0 if error or not found otherwise returns unix timestamp value
def find_timestamp(f, maxoffset, minoffset):
    begin = f.tell()
    # maxoffset is inclusive => need range from minoffset : maxoffset+1
    for i in range(minoffset, maxoffset+1, 1):
        if ((begin - i) < 0):
            return(0) # FILETIME can't be before start of file
        else:
            f.seek(begin-i)
            value = read_filetime(f)
            if (value != 0):
                return(value)
            #otherwise keep searching until maxoffset
    # if we get here, we haven't found a valid timestamp, so return 0
    return(0)

# Main
print("Running " + version_string + "\n")

usage = " %prog -s store.vol -o output.tsv(Optional)"

# Handle command line args
parser = OptionParser(usage=usage)
parser.add_option("-s", dest="storefile", action="store", type="string", help="store.vol file")
parser.add_option("-o", dest="outputfilename", 
                  action="store", type="string",
                  help="Output Tab Separated Variable filename (Optional)")
(options, args) = parser.parse_args()

# Check if no arguments given by user, exit
if len(sys.argv) == 1:
    parser.print_help()
    exit(-1)
if not os.path.isfile(options.storefile):
    print("Specified file " + options.storefile + " does not exist! Exiting ...\n")
    exit(-1)

print("Opening " + options.storefile + "...\n")
# Open store.vol for binary byte ops (eg searching for hex bytes, reading timestamps)
try:
    fbstore = open(options.storefile, "rb")
except:
    print(options.storefile + " File Not Opened (binary attempt)")
    exit(-1)

fbstore.seek(0)
rawstore = fbstore.read() # reads whole file into memory so probably don't want to use this with whole image

# Open store.vol for unicode encoded text reads
try:
	funistore = codecs.open(options.storefile, encoding="utf-16-le", mode="r")
except:
    print(options.storefile + " File Not Opened (unicode attempt)")
    exit(-1)

if (options.outputfilename != None):
    try:
        outputfile = open(options.outputfilename, "w")
    except:
        print("Cannot create specified output TSV file Exiting ...\n")
        exit(-1)

print("Processing Attachment table ...")
# Search for Attachment rows containing "<cid" or <d+> in store.vol and note hit offsets. 
attachterm1 = "\x3C\x00\x63\x00\x69\x00\x64\x00"
attachpattern1 = re.compile(attachterm1, re.DOTALL)
attach_hitlist1 = regsearch(rawstore, attachpattern1, [])
print(str(len(attach_hitlist1)) + " Attachment \"<cid\" hits found in store.vol\n")
attachterm2 = "\x3C\x00[\x30\x00|\x31\x00|\x32\x00|\x33\x00|\x34\x00|\x35\x00|\x36\x00|\x37\x00|\x38\x00|\x39\x00]+\x3E\x00\x00\x00" # eg match "<0000>" or <1>
attachpattern2 = re.compile(attachterm2, re.DOTALL)
attach_hitlist2 = regsearch(rawstore, attachpattern2, [])
print(str(len(attach_hitlist2)) + " Attachment \"<d+>\" hits found in store.vol\n")
attach_hitlist = attach_hitlist1 + attach_hitlist2

print(str(len(attach_hitlist)) + " Total Attachment hits found in store.vol\n")
# These should correspond to MMS records in the "Attachment" table.
# Each record looks like:
# [X][4 byte rowid][0x07000000][0x03000000][[4 byte msgid][10 bytes][4 byte Size][31 bytes][ "<cidText" or "<cidSmil" or "<cidImage" ][1][filename1][1][filename2][1][filetype][X]
attachments = {} # dict of tuple lists containing attachment data keyed by msgid
attachhitcount = 0
for ahit in attach_hitlist:
    try:
        # Read in filename strings from "<cid" onwards
        funistore.seek(ahit)
        file0 = read_nullterm_unistring(funistore)
        file2off = funistore.tell()+1
        funistore.seek(file2off)
        file1 = read_nullterm_unistring(funistore)
        file3off = funistore.tell()+1
        funistore.seek(file3off)
        file2 = read_nullterm_unistring(funistore)
        typeoff = funistore.tell()+1
        funistore.seek(typeoff)
        typeval = read_nullterm_unistring(funistore)
    except:
        print("Bad Attachment Filename string extraction at/around " + hex(ahit).rstrip("L"))
        exctype, value = sys.exc_info()[:2]
        print("Exception type = ",exctype,", value = ",value) 
        continue # skip hit if bad read
   
    asize = 0
    try:
        # size field is 0x23 bytes (35 dec) before "<cid" hit
        fbstore.seek(ahit - 0x23)
        asize = struct.unpack('<I', fbstore.read(4))[0] # 4 byte size
    except:
        print("Bad ASIZE extraction at " + hex(ahit - 0x23).rstrip("L"))
        exctype, value = sys.exc_info()[:2]
        print("Exception type = ",exctype,", value = ",value) 
        continue # skip hit if bad size
        
    if (asize == 0x2A2A2A2A) or (asize == 0):
        # This offset can yield 0x2A2A2A2A = 707406378 ie gone too far back OR if zero something is wrong
        # Not sure what to do? Need more test data ...
        print("Attachment ASIZE ERROR! at offset " + hex(ahit - 0x23).rstrip("L") + " ... skipping this hit")  # no point going further if asize error? eg can't find msgid
        continue
    else:
        #print("\nASIZE = " + str(asize) + " at offset " + hex(ahit - 0x23).rstrip("L"))
        astore = -1
        try:
            # To check, try finding "0x07" x39 (57 dec) bytes before "<cid"
            fbstore.seek(ahit - 0x39)
            astore = struct.unpack('<I', fbstore.read(4))[0]
            #print("astore = " + str(astore) + " at offset " + hex(ahit - 0x39).rstrip("L"))
        except:
            print("Bad astore extraction at " + hex(ahit - 0x39).rstrip("L"))
            exctype, value = sys.exc_info()[:2]
            print("Exception type = ",exctype,", value = ",value)
            continue # skip hit
        if (astore == 7):
            amsgid = -1
            try:
                # Try finding msgid 0x31 (49 dec) bytes before "<cid"
                fbstore.seek(ahit - 0x31)
                amsgid = struct.unpack('<I', fbstore.read(4))[0]
            except:
                print("Bad amsgid extraction at " + hex(ahit - 0x31).rstrip("L"))
                exctype, value = sys.exc_info()[:2]
                print("Exception type = ",exctype,", value = ",value)
                continue # skip hit
            #print("amsgid = " + str(amsgid) + " at offset " + hex(ahit - 0x31).rstrip("L"))
            
            # Store attachment data if we get this far
            if not (amsgid in attachments.keys()):
                attachments[amsgid] = list()
            attachments[amsgid].append((file0, file1, file2, typeval, asize))
            attachhitcount += 1
        else:
            print("Cannot find Attachment msgid! Skipping this hit ...")
    #print("file0 = " + file0 + ", file1 = " + file1 + ", file2 = " + file2 + ", typeval = " + typeval + ", asize = " + str(asize))

print("\nAttachments sorted by msgid ...")
print("===================================")
sortedattachkeys = sorted(attachments.keys())
for j in sortedattachkeys:
    print("\nNo. Attachments = " + str(len(attachments[j])))
    for k in range(len(attachments[j])):
        print("msgid = " + str(j) + " : " + str(attachments[j][k]))

print("\nProcessed/Stored " + str(attachhitcount) + " out of " + str(len(attach_hitlist)) + " Attachment hits\n")

print("Processing Recipient table ...")
# Search for Recipient table rows containing "@.SMS" (MMS rows also contain this)
smsterm = "\x40\x01\x53\x00\x4d\x00\x53\x00\x00\x00" # "@.SMS" where . is 0x01
smspattern = re.compile(smsterm, re.DOTALL)
sms_hitlist = regsearch(rawstore, smspattern, [])
print(str(len(sms_hitlist)) + " Recipient hits found in " + options.storefile + "\n")
# These should correspond to sent records in the "Recipient" table. 
# Each record looks like:
# [X][4 byte rowid][0x07000000][0x03000000][4 byte msgid][4 bytes][8 byte Timestamp3][25 bytes]["@.SMS"][1][DestPhone][X]
# Store the Timestamp3 and Phone No. in a dictionary keyed by msgid.
recipients = {} # dictionary of SMS recipients (ie destinations) keyed by msgid
recipcount = 0
# Process Recipient table
for hit in sms_hitlist:
    phonefield = ""
    try:
        # Read Destination Phone Number string 0xB (11 dec) bytes from start of "@.SMS"
        funistore.seek(hit + 0xB)
        phonefield = read_nullterm_unistring(funistore)
    except:
        print("Bad Recipient Phone No extraction at " + hex(hit).rstrip("L"))
        exctype, value = sys.exc_info()[:2]
        print("Exception type = ",exctype,", value = ",value) 
        continue # skip hit if bad read
    
    if (phonefield is ""):
        print("No phone number detected for this Recipient! Skipping hit at " + hex(hit).rstrip("L") + "\n")  # Sent MMS should have a number
        continue # skip to next hit
    else:
        timestampSMSraw = 0
        try:
            fbstore.seek(hit)
            timestampSMSraw = find_timestamp(fbstore, 0x21, 0x19) # timestamp should start 0x21 (33 dec) bytes before hit
        except:
            print("Bad Recipient Timestamp extraction at/around " + hex(hit).rstrip("L") + " ... Skipping hit ...")
            exctype, value = sys.exc_info()[:2]
            print("Exception type = ",exctype,", value = ",value) 
            continue # skip hit if bad read
        
        timestampSMSstr = "NA"
        if (timestampSMSraw != 0):
                #print("timestampSMSraw = " + hex(timestampSMSraw))
                try:
                    # returns UTC ISO time string
                    timestampSMSstr = datetime.datetime.utcfromtimestamp(timestampSMSraw).isoformat()
                except:
                    print("Bad Recipient Timestamp calculation at/around " + hex(hit).rstrip("L") + " ... Skipping hit ...")
                    continue # skip hit if bad read
            #print("SMSTime (UTC) = " + timestampSMSstr)
    
    storevalue = -1
    try:
        # Now go back 0x31 (49 dec) bytes from "@.SMS" and check for the 0x07000000 value
        fbstore.seek(hit - 0x31)
        storevalue = struct.unpack('<I', fbstore.read(4))[0]
    except:
        print("Bad Recipient Store extraction at " + hex(hit - 0x31).rstrip("L"))
        exctype, value = sys.exc_info()[:2]
        print("Exception type = ",exctype,", value = ",value) 
        continue # skip hit if bad read
        
    # If OK, grab the msgid
    if (storevalue == 7):
        #print("SMS Store value OK")
        msgidvalue = -1
        try:
            # msgid should be 0x29 (41 dec) bytes back from hit
            fbstore.seek(hit - 0x29)
            msgidvalue = struct.unpack('<I', fbstore.read(4))[0]
        except:
            print("Bad Recipient msgid extraction at " + hex(hit - 0x29).rstrip("L"))
            exctype, value = sys.exc_info()[:2]
            print("Exception type = ",exctype,", value = ",value) 
            continue # skip hit if bad read
        #print "SMS msgidvalue = " + str(msgidvalue) + " at offset " + hex(hit - 0x29).rstrip("L")
        
        # Store Recipient Sent MMS data
        recipients[msgidvalue] = (timestampSMSstr, phonefield)
        recipcount += 1
    else:
        print("Recipient Store value not valid! Skipping hit at " + hex(hit).rstrip("L") + "\n") # could be unexpected layout

print("\nRecipients sorted by msgid ...")
print("===================================")
sortedrepkeys = sorted(recipients.keys())
for j in sortedrepkeys:
    print("msgid = " + str(j) + " : " + str(recipients[j]))

print("\nProcessed/Stored " + str(recipcount) + " out of " + str(len(sms_hitlist)) + " Recipient hits\n")

print("Processing Message table ...")
# Search for Message table rows containing "IPM.MMS"
mmsterm = "\x49\x00\x50\x00\x4D\x00\x2E\x00\x4D\x00\x4D\x00\x53\x00\x00\x00" 
mmspattern = re.compile(mmsterm, re.DOTALL)
ipmmms_hitlist = regsearch(rawstore, mmspattern, [])
print(str(len(ipmmms_hitlist)) + " IPM.MMS Message hits found in " + options.storefile + "\n")
# Search for "IPM.MMS" in given file (store.vol, pagefile.sys?) and note hit offsets. 
# These should correspond to MMS records in the "Message" table.
# Each Received MMS record looks like:
# [X][4 byte msgid][0x07000000][162 bytes][Timestamp0][36 bytes][Timestamp1][4 byte Flag][4 bytes][4 byte Size][172 bytes][Timestamp2][226 bytes][Phone0][1]["IPM.MMS"][1][Phone1][1][Phone2][1][Phone3][14 bytes][Timestamp3][X includes Timestamp4]
# Each Sent MMS record (contains no phone numbers) looks like:
# [X][4 byte msgid][0x07000000][162 bytes][Timestamp0][36 bytes][Timestamp1][4 byte Flag][4 bytes][4 byte Size][172 bytes][Timestamp2][206 bytes]["IPM.MMS"][14 bytes][Timestamp3][X does NOT include Timestamp4]
mmsdict = {} # dict of mms keyed by msgid
mmscount = 0
for hit in ipmmms_hitlist:
    phonefield = ""
    try:
        # Check for Phone1 string 0x11 bytes (17 dec) after hit
        funistore.seek(hit + 0x11) # should be start of Phone1 string for received MMS or x00 x00 if sent/invalid
        phonefield = read_nullterm_unistring(funistore)
    except:
        print("Bad Message Phone1 extraction at " + hex(hit + 0x11).rstrip("L"))
        exctype, value = sys.exc_info()[:2]
        print("Exception type = ",exctype,", value = ",value) 
        continue # skip hit if error
    
    if (phonefield is ""):
        # if no number field, this is a sent MMS so find Timestamp3 which is 0xB (11 dec) bytes from last read byte
        #print("\nNo phone number detected in Message record at " + hex(hit).rstrip("L") + "\n")
        
        try:
            timestamp3off = funistore.tell() + 0xB
            fbstore.seek(timestamp3off)
            timestamp3raw = read_filetime(fbstore)
            timestamp3str = datetime.datetime.utcfromtimestamp(timestamp3raw).isoformat()
        except:
            print("Bad Sent Message Timestamp3 extraction at " + hex(timestamp3off).rstrip("L"))
            exctype, value = sys.exc_info()[:2]
            print("Exception type = ",exctype,", value = ",value) 
            continue # skip hit if error
        #print("Sent Time3 (UTC) = " + timestamp3str + " at " + hex(timestamp3off).rstrip("L"))

        # Now go back from "IPM.MMS" hit to find Timestamp2. Should start 0xD6 (214 dec) bytes before "IPM.MMS"
        timestamp2str = "NA"
        try:
            fbstore.seek(hit)
            timestamp2raw = find_timestamp(fbstore, 0xD6, 0xCE) # timestamp2 is 0xD6 (214 dec) bytes before "IPM.MMS"
            #print("timestamp2raw = " + hex(timestamp2raw))
            if (timestamp2raw != 0):
                # returns ISO UTC time string
                timestamp2str = datetime.datetime.utcfromtimestamp(timestamp2raw).isoformat()
            else:
                continue # skip this hit, timestamp2 should not be 0
        except:
            print("Bad Sent Message Timestamp2 extraction for hit at " + hex(hit).rstrip("L"))
            exctype, value = sys.exc_info()[:2]
            print("Exception type = ",exctype,", value = ",value) 
            continue # skip hit if error
        #print("Sent Time2 (UTC) = " + timestamp2str)

        # Now go back to find Timestamp1
        timestamp1str = "NA"
        flagoffset = 0
        try:
            fbstore.seek(hit)
            timestamp1raw = find_timestamp(fbstore, 0x196, 0x18E) # timestamp1 is 0x196 (406 dec) bytes before "IPM.MMS"
            if (timestamp1raw != 0):
                #print("timestamp1raw = " + hex(timestamp1raw))
                # returns ISO UTC time string
                timestamp1str = datetime.datetime.utcfromtimestamp(timestamp1raw).isoformat()
                flagoffset = fbstore.tell() # flag offset occurs just after timestamp1
            else:
                # something bad happened reading time
                continue # skip this hit, timestamp1 should not be 0
        except:
            print("Bad Sent Message Timestamp1 extraction for hit at " + hex(hit).rstrip("L"))
            exctype, value = sys.exc_info()[:2]
            print("Exception type = ",exctype,", value = ",value) 
            continue # skip hit if error                
        #print("Sent Time1 (UTC) = " + timestamp1str)

        # Now read Flag value (1 byte just after Timestamp1)
        flagvalue = -1
        try:
            fbstore.seek(flagoffset)
            flagvalue = struct.unpack('<I', fbstore.read(4))[0]
        except:
            print("Bad Sent Message Flag extraction at " + hex(flagoffset).rstrip("L"))
            exctype, value = sys.exc_info()[:2]
            print("Exception type = ",exctype,", value = ",value)
            continue # skip hit if error  
        #print("Sent Flag = " + str(flagvalue) + " at offset " + hex(flagoffset).rstrip("L"))

        # Go forward 8 bytes from Flag and read MMS message size in bytes
        sizevalue = -1
        try:
            fbstore.seek(flagoffset + 0x8)
            sizevalue = struct.unpack('<I', fbstore.read(4))[0]
        except:
            print("Bad Sent Message Size extraction at " + hex(flagoffset + 0x8).rstrip("L"))
            exctype, value = sys.exc_info()[:2]
            print("Exception type = ",exctype,", value = ",value) 
            continue # skip hit if error 
        #print("Sent Size = " + str(sizevalue) + " at offset " + hex(flagoffset + 0x8).rstrip("L"))

        # Go back 0xDA bytes (218 dec) from Flag and check this store value is 0x07000000 (for SMS/MMS)
        storevalue = -1
        try:
            fbstore.seek(flagoffset - 0xDA)
            storevalue = struct.unpack('<I', fbstore.read(4))[0]
        except:
            print("Bad Sent Message Store extraction at " + hex(flagoffset - 0xDA).rstrip("L"))
            exctype, value = sys.exc_info()[:2]
            print("Exception type = ",exctype,", value = ",value) 
            continue # skip hit if error
        #print("Sent Store = " + str(storevalue) + " at offset " + hex(flagoffset - 0xDA).rstrip("L"))

        # If OK, go back 4 bytes before 0x07000000 value. ie Go back 0xDE (222 dec) bytes from flag and read 4 byte msgid
        if (storevalue == 7):
            #print("Sent Store value OK")
            msgidvalue = -1
            try:
                fbstore.seek(flagoffset - 0xDE)
                msgidvalue = struct.unpack('<I', fbstore.read(4))[0]
            except:
                print("Bad Sent Message Msgid extraction at " + hex(flagoffset - 0xDE).rstrip("L"))
                exctype, value = sys.exc_info()[:2]
                print("Exception type = ",exctype,", value = ",value) 
                continue # skip hit if error
            #print("Sent Msgidvalue = " + str(msgidvalue) + " at offset " + hex(flagoffset - 0xDE).rstrip("L"))
            
            try:
                # Look up Recipient table phone number based on msgid
                recip = recipients[msgidvalue]
                #print(recip)
                phonestr = recip[1]
            except:
                print("Bad Sent Message Phone No. search")
                exctype, value = sys.exc_info()[:2]
                print("Exception type = ",exctype,", value = ",value) 
                continue # skip hit if error
                
            # If we get here, all Sent MMS Message data was extracted OK. So store it.
            mmsdict[msgidvalue] = (timestamp3str, timestamp2str, phonestr, flagvalue, sizevalue)
            mmscount += 1
        else:
            print("Sent Message Store value not valid for MMS\n") # could be unexpected layout or attachment for another app (eg email)
            continue # skip hit if error
    else:
        # This must be a received MMS as it has a Phone1 string set
        phonestr = phonefield
        #print("Recv Message Phone1 = " + phonestr + " around " + hex(hit).rstrip("L"))
        
        try:
            # Read Phone2 and Phone3 strings. Phone2 starts 1 byte after Phone1 ends 
            phone2off = funistore.tell()+1
            funistore.seek(phone2off)
            phonefield2 = read_nullterm_unistring(funistore)
            #print("Recv Message Phone2 = " + phonefield2 + " at " + hex(phone2off).rstrip("L"))
            phone3off = funistore.tell()+1 # Phone3 starts 1 byte after Phone2 ends 
            funistore.seek(phone3off)
            phonefield3 = read_nullterm_unistring(funistore)
            #print("Recv Message Phone3 = " + phonefield3 + " at " + hex(phone3off).rstrip("L"))
        except:
            print("Bad Recv Message Phone2/Phone3 extraction around " + hex(hit).rstrip("L"))
            exctype, value = sys.exc_info()[:2]
            print("Exception type = ",exctype,", value = ",value) 
            continue # skip hit if error
        
        try:
            # Timestamp3 should occur 0xE (14 dec) bytes after the end of Phone3.
            timestamp3off = funistore.tell() + 0xE
            fbstore.seek(timestamp3off)
            timestamp3raw = read_filetime(fbstore)
            timestamp3str = datetime.datetime.utcfromtimestamp(timestamp3raw).isoformat()
        except:
            print("Bad Recv Message Timestamp3 extraction at " + hex(hit + 0xE).rstrip("L"))
            exctype, value = sys.exc_info()[:2]
            print("Exception type = ",exctype,", value = ",value) 
            continue # skip hit if error
        #print("Recv Message Time3 (UTC) = " + timestamp3str + " at " + hex(timestamp3off).rstrip("L"))

        # Now search back from "IPM.MMS" hit to find Timestamp2. We ass-ume Phone0 length = Phone1 length = Phone2 length = Phone3 length.
        # So we start searching for Timestamp2 from (hit - time2offsetdelta)
        # len+1 is multiplied by 2 as 2 bytes per char (incl. NULL). +1 accounts for 1 byte between Phone0 and "IPM.MMS".
        # 
        time2offsetdelta = (len(phonestr)+1)*2 + 1 + 0xEA # There are 0xEA (234 dec) bytes between start of Timestamp2 and start of Phone0
        timestamp2str = "NA"
        try:
            fbstore.seek(hit)
            timestamp2raw = find_timestamp(fbstore, time2offsetdelta, time2offsetdelta-8) # fd, max offset back, min offset back
            if (timestamp2raw != 0):
                #print("timestamp2raw = " + hex(timestamp2raw))
                # returns ISO UTC time string
                timestamp2str = datetime.datetime.utcfromtimestamp(timestamp2raw).isoformat()
            else:
                continue # skip this hit, timestamp2 should not be 0
        except:
            print("Bad Recv Message Timestamp2 extraction for hit around " + hex(hit).rstrip("L"))
            exctype, value = sys.exc_info()[:2]
            print("Exception type = ",exctype,", value = ",value) 
            continue # skip hit if error
        #print("Recv Message Time2 (UTC) = " + timestamp2str + " around " + hex(hit).rstrip("L"))

        # Now go back to find Timestamp1 which should be 0xC0 (192 dec) bytes before Timestamp2
        timestamp1str = "NA"
        flagoffset = 0
        try:
            time1offset = fbstore.tell() - 8 # Start of Timestamp2
            #print(hex(time1offset))
            fbstore.seek(time1offset)
            timestamp1raw = find_timestamp(fbstore, 0xC0, 0xB8)
            if (timestamp1raw != 0):
                #print("timestamp1raw = " + hex(timestamp1raw))
                timestamp1str = datetime.datetime.utcfromtimestamp(timestamp1raw).isoformat()
                flagoffset = fbstore.tell()
            else:
                continue # timestamp1 should not be 0
        except:
            print("Bad Recv Message Timestamp1 extraction for hit at " + hex(time1offset).rstrip("L"))
            exctype, value = sys.exc_info()[:2]
            print("Exception type = ",exctype,", value = ",value) 
            continue # skip hit if error
        #print("Recv Message Time1 (UTC) = " + timestamp1str + " at " + hex(time1offset).rstrip("L"))

        # Now read Flag value (just after Timestamp1)
        flagvalue = -1
        try:
            fbstore.seek(flagoffset)
            flagvalue = struct.unpack('<I', fbstore.read(4))[0]
        except:
            print("Bad Recv Message Flag extraction at " + hex(flagoffset).rstrip("L"))
            exctype, value = sys.exc_info()[:2]
            print("Exception type = ",exctype,", value = ",value) 
            continue # skip hit if error
        #print("Flag = " + str(flagvalue) + " at offset " + hex(flagoffset).rstrip("L"))

        # Go forward 8 bytes from Flag and read MMS message size in bytes
        sizevalue = -1
        try:
            fbstore.seek(flagoffset + 0x8)
            sizevalue = struct.unpack('<I', fbstore.read(4))[0]
        except:
            print("Bad Recv Message Size extraction at " + hex(flagoffset + 0x8).rstrip("L"))
            exctype, value = sys.exc_info()[:2]
            print("Exception type = ",exctype,", value = ",value) 
            continue # skip hit if error
        #print("Size = " + str(sizevalue) + " at offset " + hex(flagoffset + 0x8).rstrip("L"))

        # Go back 0xDA (218 dec) bytes from Flag and check this store value is 0x07000000 (for SMS/MMS)
        storevalue = -1
        try:
            fbstore.seek(flagoffset - 0xDA)
            storevalue = struct.unpack('<I', fbstore.read(4))[0]
        except:
            print("Bad Recv Message Store extraction at " + hex(flagoffset - 0xDA).rstrip("L"))
            exctype, value = sys.exc_info()[:2]
            print("Exception type = ",exctype,", value = ",value) 
            continue # skip hit if error
        #print("Store = " + str(storevalue) + " at offset " + hex(flagoffset - 0xDA).rstrip("L"))

        # If OK, go back 0xDE (222 dec) bytes from Flag and read 4 byte msgid
        if (storevalue == 7):
            #print("Store value OK")
            msgidvalue = -1
            try:
                fbstore.seek(flagoffset - 0xDE)
                msgidvalue = struct.unpack('<I', fbstore.read(4))[0]
            except:
                print("Bad Recv Message Msgid extraction at " + hex(flagoffset - 0xDE).rstrip("L"))
                exctype, value = sys.exc_info()[:2]
                print("Exception type = ",exctype,", value = ",value) 
                continue # skip hit if error
            #print("msgidvalue = " + str(msgidvalue) + " at offset " + hex(flagoffset - 0xDE).rstrip("L"))
            
            # If we get here, all Recv MMS Message data was extracted OK. Store it.
            mmsdict[msgidvalue] = (timestamp3str, timestamp2str, phonestr, flagvalue, sizevalue)
            mmscount += 1
        else:
            print("Recv Message Store value not valid for MMS\n") # could be unexpected layout or attachment for another app (eg email)
            continue

fbstore.close()

print("MMS sorted by msgid ...")
print("===================================")
sortedmmskeys = sorted(mmsdict.keys())
for j in sortedmmskeys:
    print("msgid = " + str(j) + " : " + str(mmsdict[j]))

print("\nProcessed/Stored " + str(mmscount) + " out of " + str(len(ipmmms_hitlist)) + " Message hits\n")
print("Printing finalized table sorted by Timestamp2 ...")
print("===================================================")
print("Timestamp2\tMsgid\tTimestamp3\tPhone\tFlag\tTotalSize\tType\tFilesize\tFilename0\tFilename1\tFilename2")
if (options.outputfilename != None):
    outputfile.write("Timestamp2\tMsgid\tTimestamp3\tPhone\tFlag\tTotalSize\tType\tFilesize\tFilename0\tFilename1\tFilename2\n")

# Get a list of mmsdict keys sorted by filetime2 (filesystem modified time)
sorted_messages_keys = sorted(mmsdict, key = lambda x : (mmsdict[x][1], mmsdict[x][1])) 
for j in sorted_messages_keys: 
    # Print order for each MMS should start with Timestamp2, msgid, Timestamp3, phonestr, flagvalue, totalsize
    printmsgstr = str(mmsdict[j][1]) + "\t" + str(j) + "\t" + str(mmsdict[j][0]) + "\t" + str(mmsdict[j][2]) + "\t" + str(mmsdict[j][3]) + "\t" + str(mmsdict[j][4]) + "\t"
    attachstr = ""
    try:
        #print("\nNo. Attachments for msgid = " + str(j) + " is " + str(len(attachments[j])))
        for k in range(len(attachments[j])): # there may be more than 1 attachment per msgid/MMS
            # Print order (for each attachment) becomes printmsg, typeval, filesize, file0, file1, file2 
            finalstr =  printmsgstr + str(attachments[j][k][3]) + "\t" + str(attachments[j][k][4]) + "\t" + str(attachments[j][k][0]) + "\t" + str(attachments[j][k][1]) + "\t" + str(attachments[j][k][2]) + "\n"
            print(finalstr)
            if (options.outputfilename != None):
                outputfile.write(finalstr)
    except:
        print("Problems finding/writing Attachment entries for msgid = " + str(j) + " ... Skipping\n")
        exctype, value = sys.exc_info()[:2]
        print("Exception type = ",exctype,", value = ",value) 
        continue

if (options.outputfilename != None):
    outputfile.close()

print("Finished processing " + options.storefile + " ... Exiting ...")



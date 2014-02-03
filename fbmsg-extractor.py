#! /usr/bin/env python

# fbmsg-extractor.py = Python script to extract Android Facebook/Messenger app data
#
# Copyright (C) 2014 Adrian Leong (cheeky4n6monkey@gmail.com)
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
# Version History:
# v2014-01-08 Initial Version
# v2014-02-02 Removed debugging print exit statement (oops!)

# Instructions:
# (Mandatory) Use the -t argument to specify the threads_db2 SQLite database
# (Mandatory) Use the -c argument to specify the contacts_db2 SQLite database
# (Optional) Use the -x argument to contacts output to the specified Tab Seperated Variable file
# (Optional) Use the -z argument to messages output to the specified Tab Seperated Variable file
#
# It was developed/tested on SIFT v2.14 (Ubuntu 9.10 Karmic) running Python v2.6.4.
# Also run on Win7x64 running Python 2.7.6
#
# Usage Example:
# python fbmsg-extractor.py -t threads_db2 -c contacts_db2 -x contacts.tsv -z messages.tsv
#
# Special Thanks to Shafik Punja (@qubytelogic) for this idea and his feedback.
#

import sys
import sqlite3
from optparse import OptionParser
from os import path
import json
import datetime
import urllib

version_string = "fbmsg-extractor v2014-02-02"
print "Running " + version_string

usage = "Usage: %prog -t threads_db -c contacts_db -x contacts.tsv -z messages.tsv"

parser = OptionParser(usage=usage)
parser.add_option("-t", dest="threadsdb", 
                  action="store", type="string",
                  help="threads_db2 input file")
parser.add_option("-c", dest="contactsdb",
                  action="store", type="string",
                  help="contacts_db2 input file")
parser.add_option("-x", dest="contactstsv",
                  action="store", type="string",
                  help="(Optional) Contacts Tab Separated Output Filename")
parser.add_option("-z", dest="messagestsv",
                  action="store", type="string",
                  help="(Optional) Messages Tab Separated Output Filename")

(options, args) = parser.parse_args()

#no arguments given by user, print help and exit
if len(sys.argv) == 1:
    parser.print_help()
    exit(-1)

if ((options.threadsdb == None) or (options.contactsdb == None)):
    parser.print_help()
    print "\nDatabase filenames not specified!"
    exit(-1)

# check db files exist before trying to connect
if path.isfile(options.threadsdb):
    threadscon = sqlite3.connect(options.threadsdb)
else:
    print "Threads Database does not exist!"
    exit(-1)

if path.isfile(options.contactsdb):
    contactscon = sqlite3.connect(options.contactsdb)
else:
    print "Contacts Database does not exist!"
    exit(-1)

contactsquery = "select contact_id, data from contacts;"
contactscursor = contactscon.cursor()
contactscursor.execute(contactsquery)

CONTACTS_QUERY_CONTACTS_ID_COL_IDX = 0
CONTACTS_QUERY_DATA_COL_IDX = 1
contactsdict = {}
row = contactscursor.fetchone()
while row:
    #print row
    try:
        # Translate/extract data json string to a python dict
        decoded_data = json.loads(row[CONTACTS_QUERY_DATA_COL_IDX])
    except:
        print "Could not extract contact data for contact_id = " + row[CONTACTS_QUERY_CONTACTS_ID_COL_IDX]
        row = contactscursor.fetchone()
        continue # skip to next loop if error here
        
    #print(decoded_data)
    # Extract timelineCoverPhoto, photos, image_lowres, uri data
    coverphotouri = "NA"
    if (decoded_data["timelineCoverPhoto"] is not None): # ie if timelineCoverPhoto not null
        try:
            # For some unknown reason, "timelinecoverPhoto" is not processed completely
            # so we call json.loads() again. Perhaps related to escaped quotes? (\")
            coverphoto = json.loads(decoded_data["timelineCoverPhoto"])
            #print coverphoto["photo"]["image_lowres"]["uri"]
            coverphotouri = coverphoto["photo"]["image_lowres"]["uri"]
        except:
            print "No timelineCoverPhoto available for contact_id " + row[CONTACTS_QUERY_CONTACTS_ID_COL_IDX]

    # Extract "phones" data and store selected data in "contactsdict" keyed by row[0] ie by contact_id
    # decoded_data["phones"] returns a list of phone dicts (assumed to be a one item list from test data)
    # 
    displaynum = "NA"
    univnum = "NA"
    if (len(decoded_data["phones"])): # not all contacts have a phone objects
        # assume there's only one "phones" dict / use the first (0 th) "phones" dict values
        displaynum = decoded_data["phones"][0]["displayNumber"]
        univnum = decoded_data["phones"][0]["universalNumber"]

    contactsdict[row[0]] = (decoded_data["profileFbid"], decoded_data["name"]["displayName"], \
                            displaynum, univnum, decoded_data["smallPictureUrl"], \
                            decoded_data["bigPictureUrl"], decoded_data["hugePictureUrl"], \
                            coverphotouri)

    row = contactscursor.fetchone()
# ends while

contactscursor.close()
contactscon.close()

# Indexes for contactsdict dictionary (ie list order for each entry)
CONTACTS_PROFILE_ID_IDX = 0
CONTACTS_DISPLAY_NAME_ID_IDX = 1
CONTACTS_DISPLAY_PHONE_IDX = 2
CONTACTS_UNIV_PHONE_IDX = 3
CONTACTS_SML_PIC_URL_IDX = 4
CONTACTS_BIG_PIC_URL_IDX = 5
CONTACTS_HUGE_PIC_URL_IDX = 6
CONTACTS_COVER_PIC_IDX = 7

#print contactsdict

# Get list of contactsdict keys sorted by display name so we can iterate thru for printing
# See http://stackoverflow.com/questions/8966538/syntax-behind-sortedkey-lambda
# and https://wiki.python.org/moin/HowTo/Sorting
sorted_contact_keys = sorted(contactsdict, key = lambda x : contactsdict[x][CONTACTS_DISPLAY_NAME_ID_IDX]) 
#print sorted_contact_keys

# open contacts output file if reqd
if (options.contactstsv != None):
    try:
        contactsof = open(options.contactstsv, "w")
    except:
        print ("Trouble Opening Contacts Output File")
        exit(-1)

# write header for contacts output file
if (options.contactstsv != None):
    contactsof.write("contact_id\tprofileFbid\tdisplayName\tdisplayNumber\tuniversalNumber\tsmallPictureUrl\tbigPictureUrl\thugePictureUrl\ttimelineCoverPhoto\n")

print "\n========================"
print "Extracted CONTACTS Data"
print "========================"

print "\ncontact_id\tprofileFbid\tdisplayName\tdisplayNumber\tuniversalNumber\tsmallPictureUrl\tbigPictureUrl\thugePictureUrl\ttimelineCoverPhoto"
print "======================================================================================================================================="

for key in sorted_contact_keys:
    print (key + "\t" + contactsdict[key][CONTACTS_PROFILE_ID_IDX] + "\t" + contactsdict[key][CONTACTS_DISPLAY_NAME_ID_IDX] + \
        "\t" + contactsdict[key][CONTACTS_DISPLAY_PHONE_IDX] + "\t" + contactsdict[key][CONTACTS_UNIV_PHONE_IDX] + \
        "\t" + contactsdict[key][CONTACTS_SML_PIC_URL_IDX] + "\t" + contactsdict[key][CONTACTS_BIG_PIC_URL_IDX] + \
        "\t" + contactsdict[key][CONTACTS_HUGE_PIC_URL_IDX] + "\t" + contactsdict[key][CONTACTS_COVER_PIC_IDX] + "\n")

    if (options.contactstsv != None):
        contactsof.write(key + "\t" + contactsdict[key][CONTACTS_PROFILE_ID_IDX] + "\t" + contactsdict[key][CONTACTS_DISPLAY_NAME_ID_IDX] + \
        "\t" + contactsdict[key][CONTACTS_DISPLAY_PHONE_IDX] + "\t" + contactsdict[key][CONTACTS_UNIV_PHONE_IDX] + \
        "\t" + contactsdict[key][CONTACTS_SML_PIC_URL_IDX] + "\t" + contactsdict[key][CONTACTS_BIG_PIC_URL_IDX] + \
        "\t" + contactsdict[key][CONTACTS_HUGE_PIC_URL_IDX] + "\t" + contactsdict[key][CONTACTS_COVER_PIC_IDX] + "\n")

#sort by thread and then time
threadsquery = "select messages.msg_id, messages.thread_id, messages.text, messages.sender, threads.participants, messages.timestamp_ms, messages.source, messages.coordinates from messages, threads where messages.thread_id=threads.thread_id order by messages.thread_id, messages.timestamp_ms;"
threadscursor = threadscon.cursor()
threadscursor.execute(threadsquery)

# Column indexes to returned row query values
MESGS_QUERY_MSG_ID_COL_IDX = 0
MESGS_QUERY_THREAD_ID_COL_IDX = 1
MESGS_QUERY_TEXT_COL_IDX = 2
MESGS_QUERY_SENDER_COL_IDX = 3
MESGS_QUERY_PARTIES_COL_IDX = 4
MESGS_QUERY_TIMESTAMP_COL_IDX = 5
MESGS_QUERY_SOURCE_COL_IDX = 6
MESGS_QUERY_COORDS_COL_IDX = 7

messagesdict = {}
row = threadscursor.fetchone()
while row:
    #print row
    sender = "NA"
    parties = []
    coords_lat = "NA"
    coords_long = "NA"
    coords_accuracy = "NA"
    coords_hdg = "NA"
    coords_speed = "NA"
    coords_altitude = "NA"
    textstr = ""
    sourcestr = ""
        
    try:
        decoded_sender = json.loads(row[MESGS_QUERY_SENDER_COL_IDX])
        #print decoded_sender["name"]
        sender = decoded_sender["name"]
    except:
        print "Could not extract sender data!"
        print row[MESGS_QUERY_SENDER_COL_IDX]

    try:
        #print row[MESGS_QUERY_PARTIES_COL_IDX]
        decoded_parties = json.loads(row[MESGS_QUERY_PARTIES_COL_IDX])
        for party in decoded_parties: # extract name from each dict in list
            parties.append(party["name"])
    except:
        print "Could not extract participants data!"
        print row[MESGS_QUERY_PARTIES_COL_IDX]
        
    if (row[MESGS_QUERY_COORDS_COL_IDX] is not None): # coords col can be blank
        try:
            decoded_coords = json.loads(row[MESGS_QUERY_COORDS_COL_IDX])
            coords_lat = decoded_coords["latitude"]
            coords_long = decoded_coords["longitude"]
            coords_accuracy = decoded_coords["accuracy"]
            
            #print decoded_coords.keys()
            # heading, speed, altitude are optional
            if ("heading" in decoded_coords.keys()):
                coords_hdg = decoded_coords["heading"]
                #print "hdg = " + str(hdg)
            if ("speed" in decoded_coords.keys()):
                coords_speed = decoded_coords["speed"]
                #print "speed = " + str(speed)
            if ("altitude" in decoded_coords.keys()):
                coords_altitude = decoded_coords["altitude"]
                #print "alt = " + str(altitude)
        except:
            print "Could not extract coords data!"
            print row[MESGS_QUERY_COORDS_COL_IDX]
    #endif coords    

    if (row[MESGS_QUERY_TEXT_COL_IDX] is not None):
        textstr = row[MESGS_QUERY_TEXT_COL_IDX] # message text
        textstr = textstr.replace("\r\n", " ") # change any newlines to spaces
        textstr = textstr.replace("\n", " ")
        
    if (row[MESGS_QUERY_SOURCE_COL_IDX] is not None):
        sourcestr = row[MESGS_QUERY_SOURCE_COL_IDX]

    # Store extracted message data in "messagesdict" dictionary keyed by msg_id
    # order should be thread_id, text, sender, participants, timestamp_ms, source, lat, long, accuracy, heading, speed, altitude 
    messagesdict[row[MESGS_QUERY_MSG_ID_COL_IDX]] = (row[MESGS_QUERY_THREAD_ID_COL_IDX], \
        textstr, sender, parties, row[MESGS_QUERY_TIMESTAMP_COL_IDX], sourcestr, \
        coords_lat, coords_long, coords_accuracy, coords_hdg, coords_speed, coords_altitude)

    row = threadscursor.fetchone()

threadscursor.close()
threadscon.close()

#print messagesdict

# Indexes for messagesdict dictionary (ie list order for each entry)
MESGS_THR_ID_IDX = 0
MESGS_TEXT_IDX = 1
MESGS_SENDER_IDX = 2
MESGS_PARTIES_IDX = 3
MESGS_TIMESTAMP_IDX = 4
MESGS_SOURCE_IDX = 5
MESGS_LAT_IDX = 6
MESGS_LONG_IDX = 7
MESGS_ACCURACY_IDX = 8
MESGS_HEADING_IDX = 9
MESGS_SPEED_IDX = 10
MESGS_ALTITUDE_IDX = 11

# Get a list of messagesdict keys sorted by thread_id then timestamp_ms for later printing
# See http://stackoverflow.com/questions/16082954/python-how-to-sort-a-list-of-dictionaries-by-several-values
sorted_messages_keys = sorted(messagesdict, key = lambda x : (messagesdict[x][MESGS_THR_ID_IDX], messagesdict[x][MESGS_TIMESTAMP_IDX])) 

# open messages output file if reqd
if (options.messagestsv != None):
    try:
        messagesof = open(options.messagestsv, "w")
    except:
        print ("Trouble Opening Messages Output File")
        exit(-1)

# write header for contacts output file
if (options.messagestsv != None):
    messagesof.write("msg_id\tthread_id\ttext\tsender\tparticipants\ttimestamp_ms\tsource\tlatitude\tlongitude\taccuracy\theading\tspeed\taltitude\tgooglemaps\n")


print "\n========================"
print "Extracted MESSAGES Data"
print "========================"

print "\nmsg_id\tthread_id\ttext\tsender\tparticipants\ttimestamp_ms\tsource\tlatitude\tlongitude\taccuracy\theading\tspeed\taltitude\tgooglemaps"
print "======================================================================================================================================================="
for key in sorted_messages_keys:
    #pp.pprint(messagesdict[key])
    partieslist = ", ".join(messagesdict[key][MESGS_PARTIES_IDX])
    if (messagesdict[key][MESGS_TIMESTAMP_IDX] > 0):
        datetimestr = datetime.datetime.fromtimestamp(messagesdict[key][MESGS_TIMESTAMP_IDX]/1000).strftime('%Y-%m-%dT%H:%M:%S')
    else:
        datetimestr = str(messagesdict[key][MESGS_TIMESTAMP_IDX]) # if 0, just print raw value.
    # GoogleMap URL eg http://maps.google.com/maps?q=37.771008,+-122.41175+%28You+can+insert+your+text+here%29&iwloc=A&hl=en
    # percent encoding example at http://www.saltycrane.com/blog/2008/10/how-escape-percent-encode-url-python/
    latlongurl = "NA"
    if ((messagesdict[key][MESGS_LAT_IDX] is not "NA") and (messagesdict[key][MESGS_LONG_IDX] is not "NA")):
        latlongurl = "http://maps.google.com/maps?q=" + str(messagesdict[key][MESGS_LAT_IDX]) + ",+" + str(messagesdict[key][MESGS_LONG_IDX]) + "+%28" + urllib.quote_plus(str(messagesdict[key][MESGS_TEXT_IDX] + " @" + datetimestr)) + "%29&iwloc=A&hl=en"

    print (key + "\t" + messagesdict[key][MESGS_THR_ID_IDX] + "\t" + \
        messagesdict[key][MESGS_TEXT_IDX] + "\t" + messagesdict[key][MESGS_SENDER_IDX] + \
        "\t" + partieslist + "\t" + datetimestr + "\t" + messagesdict[key][MESGS_SOURCE_IDX] + \
        "\t" + str(messagesdict[key][MESGS_LAT_IDX]) + "\t" + str(messagesdict[key][MESGS_LONG_IDX]) + \
        "\t" + str(messagesdict[key][MESGS_ACCURACY_IDX]) + "\t" + str(messagesdict[key][MESGS_HEADING_IDX]) + \
        "\t" + str(messagesdict[key][MESGS_SPEED_IDX]) + "\t" + str(messagesdict[key][MESGS_ALTITUDE_IDX]) + \
        "\t" + latlongurl + "\n")

    if (options.messagestsv != None):
        messagesof.write(key + "\t" + messagesdict[key][MESGS_THR_ID_IDX] + "\t" + \
        messagesdict[key][MESGS_TEXT_IDX] + "\t" + messagesdict[key][MESGS_SENDER_IDX] + \
        "\t" + partieslist + "\t" + datetimestr + "\t" + messagesdict[key][MESGS_SOURCE_IDX] + \
        "\t" + str(messagesdict[key][MESGS_LAT_IDX]) + "\t" + str(messagesdict[key][MESGS_LONG_IDX]) + \
        "\t" + str(messagesdict[key][MESGS_ACCURACY_IDX]) + "\t" + str(messagesdict[key][MESGS_HEADING_IDX]) + \
        "\t" + str(messagesdict[key][MESGS_SPEED_IDX]) + "\t" + str(messagesdict[key][MESGS_ALTITUDE_IDX]) + \
        "\t" + latlongurl + "\n")

print "\n" + str(len(contactsdict.keys())) + " contacts were processed"
print "\n" + str(len(messagesdict.keys())) + " messages were processed"
print "\nExiting..."
exit(0)

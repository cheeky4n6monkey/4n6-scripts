#! /usr/bin/env python

# wwf-chat-parser.py = Extracts Android Words With Friends v7.1.4 chat data
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
# v2014-07-11 Initial Version

import sys
import sqlite3
from optparse import OptionParser
from os import path

version_string = "wwf-chat-parser v2014-07-11"
print "Running " + version_string

usage = "Usage: %prog -d wordsframework_db -o chat_output.tsv"

parser = OptionParser(usage=usage)
parser.add_option("-d", dest="framewkdb", 
                  action="store", type="string",
                  help="WordsFramework database input file")
parser.add_option("-o", dest="outputtsv",
                  action="store", type="string",
                  help="Chat output in Tab Separated format")

(options, args) = parser.parse_args()

#no arguments given by user, print help and exit
if len(sys.argv) == 1:
    parser.print_help()
    exit(-1)

if (options.framewkdb == None):
    parser.print_help()
    print "\nFramework Database filename not specified!"
    exit(-1)

if (options.outputtsv == None):
    parser.print_help()
    print "\nOutput filename not specified!"
    exit(-1)

# check db file exists before trying to connect
if path.isfile(options.framewkdb):
    chatscon = sqlite3.connect(options.framewkdb)
else:
    print "Specified Framework Database does not exist!"
    exit(-1)

chatsquery = "SELECT chat.chat_message_id, chat.game_id, chat.created_at, users.name, chat.message, chat.user_id, users.email_address, users.phone_number, users.facebook_id, users.facebook_name, users.zynga_account_id FROM chat_messages as chat, users WHERE users.user_id = chat.user_id ORDER BY chat.created_at;"
chatscursor = chatscon.cursor()
chatscursor.execute(chatsquery)

MSGID_QRY_IDX = 0
GAMEID_QRY_IDX = 1
CREATEDAT_QRY_IDX = 2
NAME_QRY_IDX = 3
MSG_QRY_IDX = 4
USERID_QRY_IDX = 5
EMAIL_QRY_IDX = 6
PHONE_QRY_IDX = 7
FBID_QRY_IDX = 8
FBNAME_QRY_IDX = 9
ZYNGAID_QRY_IDX = 10

chatsdict = {}
chatrow = chatscursor.fetchone()
while chatrow:
    #print chatrow
    # check if facebook name, email, phone fields are null
    fbname = ""
    email = ""
    phone = ""
    if (chatrow[FBNAME_QRY_IDX] != None):
        fbname = chatrow[FBNAME_QRY_IDX]
    if (chatrow[EMAIL_QRY_IDX] != None):
        email = chatrow[EMAIL_QRY_IDX]
    if (chatrow[PHONE_QRY_IDX] != None):
        phone = chatrow[PHONE_QRY_IDX]

    chatsdict[chatrow[MSGID_QRY_IDX]] = (chatrow[GAMEID_QRY_IDX], chatrow[CREATEDAT_QRY_IDX], chatrow[NAME_QRY_IDX], chatrow[MSG_QRY_IDX], chatrow[USERID_QRY_IDX], email, phone, chatrow[FBID_QRY_IDX], fbname, chatrow[ZYNGAID_QRY_IDX])
    chatrow = chatscursor.fetchone()
# ends while chatrow

chatscursor.close()
chatscon.close()

GAMEID_DICT_IDX = 0
CREATEDAT_DICT_IDX = 1
NAME_DICT_IDX = 2
MSG_DICT_IDX = 3
USERID_DICT_IDX = 4
EMAIL_DICT_IDX = 5
PHONE_DICT_IDX = 6
FBID_DICT_IDX = 7
FBNAME_DICT_IDX = 8
ZYNGAID_DICT_IDX = 9

# Get list of chatsdict keys sorted by created_at timestamp so we can iterate thru for printing
# See http://stackoverflow.com/questions/8966538/syntax-behind-sortedkey-lambda
# and https://wiki.python.org/moin/HowTo/Sorting
sorted_chat_keys = sorted(chatsdict, key = lambda x : chatsdict[x][CREATEDAT_DICT_IDX]) # createdat timestamp is the 2nd element in the list created above
#print sorted_chat_keys

# open chat output file if reqd
if (options.outputtsv != None):
    try:
        chatsof = open(options.outputtsv, "w")
    except:
        print ("Trouble Opening Chat Output File For Writing")
        exit(-1)

# write header for contacts output file
if (options.outputtsv != None):
    chatsof.write("chat_message_id\tgame_id\tcreated_at\tname(sender)\tmessage\tuser_id(sender)\temail_address(sender)\tphone_number(sender)\tfacebook_id(sender)\tfacebook_name(sender)\tzynga_account_id(sender)\n")

for key in sorted_chat_keys:
    if (options.outputtsv != None):
        chatsof.write(str(key) + "\t" + str(chatsdict[key][GAMEID_DICT_IDX]) + "\t" + chatsdict[key][CREATEDAT_DICT_IDX] + \
        "\t" + chatsdict[key][NAME_DICT_IDX] + "\t" + chatsdict[key][MSG_DICT_IDX] + \
        "\t" + str(chatsdict[key][USERID_DICT_IDX]) + "\t" + chatsdict[key][EMAIL_DICT_IDX] + \
        "\t" + chatsdict[key][PHONE_DICT_IDX] + "\t" + str(chatsdict[key][FBID_DICT_IDX]) + \
        "\t" + chatsdict[key][FBNAME_DICT_IDX] + "\t" + str(chatsdict[key][ZYNGAID_DICT_IDX]) + "\n")


print "\nExtracted " + str(len(sorted_chat_keys)) + " chat records\n"

exit(0)


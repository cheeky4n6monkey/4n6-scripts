
# sqlite-base64-decode.py = Python script to extract/decode base64 field from SQLite DB
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
# Version History:
# v2015-06-27 Initial Version
#
# It was developed/tested on Ubuntu 14.04 LTS running Python v2.7.6.
# Also tested on Win7x64 running Python 2.7.6
#
# Usage Example:
# python sqlite-base64-decode.py targetdb.sqlite tablename base64fieldname base64count
#
# Special Thanks to Heather Mahalik (@HeatherMahalik) for the request/idea.
#

import sys
import argparse
import sqlite3
import base64
from os import path

version_string = "sqlite-base64-decode v2015-06-27"
print "Running " + version_string

parser = argparse.ArgumentParser(description='Extracts/decodes a base64 field from a SQLite DB')
parser.add_argument("db", help='Sqlite DB filename')
parser.add_argument("table", help='Sqlite DB table name containing b64field')
parser.add_argument("b64field", help='Suspected Sqlite Base64 encoded column name')
parser.add_argument("b64count", type=int, help="Number of times to run base64 decoding on b64field")

args = parser.parse_args()

# check db file exists before trying to connect
if path.isfile(args.db):
    dbcon = sqlite3.connect(args.db)
else:
    print(args.db + " file does not exist!")
    exit(-1)

# Determine Primary Key (for ordering query by), column names (for printing) and 
# base64 column index
query = "pragma table_info("+ args.table +")"
cursor = dbcon.cursor()
cursor.execute(query)
row = cursor.fetchone()

pkname = ""
columnnames = []
b64field_idx = -1
while (row):
    #print(row)
    cols = len(row)
    # ass-umes table_info returns rows in the following order:
    # ColumnID, Name, Type, NotNull, DefaultValue, PrimaryKey
    if (row[cols-1]): # last item should be PrimaryKey boolean
        pkname = row[1]
    if (row[1] == args.b64field):
        b64field_idx = row[0]
    columnnames.append(row[1])
    row = cursor.fetchone()
# ends while row

if (pkname is ""):
    print("Unable to find Primary Key in DB ... Exiting")
    exit(-1)
else:   
    print("Primary Key name is: " + pkname)

if (b64field_idx == -1):
    print("Unable to find given Base64 Fieldname in DB ... Exiting")
    exit(-1)
else:   
    print("Base64 Fieldname index is: " + str(b64field_idx))

# Print the output header
header = ""
numcols = len(columnnames)
for name in columnnames:
    if (name != columnnames[numcols-1]): # if not last column
        header += name + "\t"
    else:
        header += name + "\tB64Decoded" # last column gets extra stuff added

print(header)
underlinechars = len(header)
print("="*underlinechars + "===="*numcols + "=======")

# Grabs every column orders by primary key (ass-umes there's only 1)
query = "select * from " + args.table + " order by " + pkname + ";"
cursor = dbcon.cursor()
cursor.execute(query)

row = cursor.fetchone()
while row:
    #print(row)
    rowstring = "" # printed for each row
    result = row[b64field_idx] # set to base64 field value
    
    for j in range(numcols):
        rowstring += str(row[j]) + "\t" # Need to print each column (tab separated)
         
    try:
        # Now we can Base64 decode however many times they want
        for j in range(args.b64count) :
            temp = base64.decodestring(result)
            result = temp
        rowstring += result # Add the decoded result to the output string
        
    except :
#        print("Bad Base64 Decode for " + origresult + " ... continuing on")
#        exctype, value = sys.exc_info()[:2]
#        print ("Exception type = ",exctype,", value = ",value)
        rowstring += "*** UNKNOWN ***" # on error, set decode column to UNKNOWN
        print(rowstring) # error print
        row = cursor.fetchone()
        continue # skip to next loop if error here

    print(rowstring) # normal print
    row = cursor.fetchone()
        
cursor.close()
dbcon.close()

print "\nExiting ..."
exit(0)



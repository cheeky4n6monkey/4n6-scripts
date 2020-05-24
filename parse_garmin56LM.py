#!/usr/bin/env python3

# Python3 script to extracts/convert IPA strings from given Garmin 56LM voice log to WAV files
# e.g. from FAT32/Voice/logs/vpm_log_all.log
# Author: cheeky4n6monkey@gmail.com
#
# NOTE: Requires espeak-ng exe to be installed
# e.g. sudo apt-get install espeak-ng
#
# Created/Tested on Ubuntu 20.04 LTS
#

import os
import sys
import subprocess
import argparse
import re

version="parse_garmin56LM.py 2020-05-17 Initial"

# Converts (X-SAMPA?) IPA symbols used in voice log to IPA Kirshenbaum symbols recognized by espeak-ng
# See:
# https://github.com/espeak-ng/espeak-ng 
# https://en.wikipedia.org/wiki/ESpeak#eSpeak_NG
# http://manpages.ubuntu.com/manpages/focal/man1/espeak-ng.1.html
# https://en.wikipedia.org/wiki/Kirshenbaum
# https://docs.aws.amazon.com/polly/latest/dg/ref-phoneme-tables-shell.html
# Work in progress ... if in doubt check log string with http://ipa-reader.xyz/ (Thankyou "@katie_k7r")
def process_voicestring(inputstr):
    procstring = "[[" + inputstr + "]]" # wrap term in [[ ]] so espeak-ng knows to interpret input as IPA

    #procstring = procstring.replace('{', '&') # theoretical
    procstring = procstring.replace('{', 'a') # practical

    #procstring = procstring.replace('Q', 'A.') # theoretical (no test data so commented out)- open back rounded vowel

    procstring = procstring.replace('"', "'") # theoretical - primary stress converted from X-SAMPA to Kirshenbaum
    procstring = procstring.replace('%', ',') # theoretical - secondary stress eg "rE|z@|%vwA *"rod
    procstring = procstring.replace('A', 'a') # practical - eg "[['glEn|%mO *'pAk|%we]]" = glenmore [spoken only]
    
    #print(procstring)
    return(procstring)
#end fn



if sys.version_info[0] < 3:
    print("Must be using Python 3! Exiting ...")
    exit(-1)
    
parser = argparse.ArgumentParser(description="Extracts/converts IPA strings from given Garmin voice log file to WAV files")
parser.add_argument("-f", action="store", dest="infile",
                    help="Input filename e.g. vpm_log_all.log", required=True)
parser.add_argument("-o", action="store", dest="opdir",
                    help="Output directory to store results", required=True)
args = parser.parse_args()

print(version)

# Create output dir if not present
if not os.path.exists(args.opdir):
    os.mkdir(args.opdir)
    print("Directory ", args.opdir, " Created")
else:    
    print("Directory ", args.opdir, " Already Exists!")

voiceguides = []
outputdir = os.path.join(os.getcwd(), args.opdir)

with open(args.infile, 'r') as fp:
    data = fp.readlines()

    os.chdir(outputdir)
    linecount = 0
    for line in data:
        linecount += 1
        if "Map Phonetics:" in line:
            # Extract voice string using code based on:
            # https://stackoverflow.com/questions/3368969/find-string-between-two-substrings
            result = re.search('] Map Phonetics: (.*) \(MDB Lang:', line)
            extractedstr = result.group(1)
            
            voicestr = process_voicestring(extractedstr)
            #print((voicestr))
 
            # Write converted string to .txt file for later conversion into WAV
            with open(os.path.join(str(linecount)+ ".txt"), "w") as outputtext:
                outputtext.write(voicestr)
                           
            # Ass-umes espeak-ng exe is in path
            # -s = speed, -w WAV output filename, -f input text string 
            status = subprocess.call(['espeak-ng', '-s 100', '-w' + str(linecount) + '.WAV', '-f' + str(linecount) + ".txt"], timeout=3)
            if status < 0:
                print("ERROR returned = " + str(status) + " = Bad conversion ... Skipping line "+ str(linecount))
                continue
            
            # Store line info temporarily for later output into HTML table    
            voiceguides.append((str(linecount), line, voicestr, str(linecount) + '.WAV'))
            print(str(linecount) + '.WAV = ' + voicestr)
            
# Write HTML report to output dir
opfile = os.path.join(outputdir, "Report.html")
with open(opfile, "w") as outputHTML:
    # HTML table header
    outputHTML.write("<html><table border=\"3\" style=\"width:100%\"><tr>" + \
                 "<th>Log Line No.</th><th>Log Line Text</th>" + \
                 "<th>Processed espeak-ng string</th><th>Audio File</th></tr>")

    for entry in voiceguides:
        linenum = str(entry[0])
        linetext = entry[1]
        voicestr = entry[2]
        wavfile = entry[3]
        outputHTML.write("<tr><td>" + linenum + "</td><td>" + linetext + \
                         "</td><td><a href=\"" + linenum + ".txt" + "\">"+voicestr + "</td>" + \
                         "<td><a href=\"" + wavfile + "\">"+wavfile+"</a></td></tr>")
    outputHTML.write("</table></html>")

print("\nProcessed " + str(len(voiceguides)) + " voice entries. Exiting ...\n")




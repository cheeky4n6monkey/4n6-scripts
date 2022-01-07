#! /usr/bin/env python
#
# Python script to read input strings/paths from a text file (one per line) and prints out the equivalent Java hashcode
# Author: cheeky4n6monkey@gmail.com
#
# Version History:
# v2021-12-23 Initial Version
#
# Developed/tested on Ubuntu 20x64 running Python 3.8
#
# Usage Example:
# python java-hashcode.py -i input.txt
# python java-hashcode.py -i input.txt -l
# python java-hashcode.py -i input.txt -u

import argparse
from os import path

version_string = "java-hashcode.py 2021-12-23"

# Java hashcode function
# From https://gist.github.com/hanleybrand/5224673
def java_string_hashcode(s):
    h = 0
    for c in s:
        h = (31 * h + ord(c)) & 0xFFFFFFFF
    return ((h + 0x80000000) & 0xFFFFFFFF) - 0x80000000


def main():
    usagetxt = " %(prog)s [-l | -u] -i inputfile"
    parser = argparse.ArgumentParser(description='Read input strings/paths from a text file (one per line) and prints out the equivalent Java hashcode', usage=usagetxt)
    parser.add_argument("-i", dest="inputfile", action="store", required=True, help='Input text filename')
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-l", dest="lowercase", action="store_true", default=False, help='(Optional) Converts input string to lower case before hashing')
    group.add_argument("-u", dest="uppercase", action="store_true", default=False, help='(Optional) Converts input string to UPPER case before hashing')
    args = parser.parse_args()

    print("Running " + version_string + "\n")

    if not args.inputfile:
        parser.exit("ERROR - Input file NOT specified")
    
    # Check input file exists before trying to read
    if not path.isfile(args.inputfile):
        print(args.inputfile + " - file does not exist!")
        exit(-1)

    with open(args.inputfile, 'r') as inputfile:
        data = inputfile.readlines()
        linenum = 0
        for line in data:
            linenum += 1
            procstring = line.rstrip()
            if args.lowercase:
                procstring = line.rstrip().lower()
            if args.uppercase:
                procstring = line.rstrip().upper()    
            print(str(procstring) + " = " + str(java_string_hashcode(procstring)))
        
        print("\nProcessed " + str(linenum) + " lines - Exiting ...")   


if __name__ == "__main__":
    main()




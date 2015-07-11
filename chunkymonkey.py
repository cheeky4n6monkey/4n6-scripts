#! /usr/bin/env python
#
# Python script helps find optimal chunk sizes & search algorithm when searching binary files for a known hex string.
# Author: cheeky4n6monkey@gmail.com (Adrian Leong)
# 
# Special Thanks to "Rob The Boss" for allowing me to share his/this idea.
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
# Example: python -m cProfile chunkymonkey test.bin 53004d00530074006500780074000000 2000000000 1000
# Searches for the hex 53004d00530074006500780074000000 using a chunk size of 2000000000 decimal bytes 
# with a 1000 byte sized delta buffer.
#
# Issues: For Python 2, there's appears to be a size limitation on (chunksize + delta). It must be less than ~2147483647
# This is probably because a Python int is implemented via a C long which is limited to 2^32 bits (ie max range is +/-2147483647).
# See: https://docs.python.org/2/library/stdtypes.html#numeric-types-int-float-long-complex
# Python 3 apparently does not have this limitation.
#

import os
import sys
import string
import re
import argparse
import binascii

# Find all indices of a substring in a given string (using string.find) 
# From http://code.activestate.com/recipes/499314-find-all-indices-of-a-substring-in-a-given-string/
def all_indices(bigstring, substring, listindex=[], offset=0):
    i = bigstring.find(substring, offset)
    while i >= 0:
        listindex.append(i)
        i = bigstring.find(substring, i + 1)
    return listindex

# Find all indices of the "pattern" regular expression in a given string (using regex)
# Where pattern is a compiled Python re pattern object (ie the output of "re.compile")
def regsearch(bigstring, pattern, listindex=[]):
    hitsit = pattern.finditer(bigstring)
    for it in hitsit:
        # iterators only last for one shot so we capture the offsets to a list
        listindex.append(it.start())
    return listindex

# Searches chunks of a file and returns file offsets of any hits.
# Intended for searching of large files where we cant read the whole thing into memory
# This function calls the "all_indices" search method
def sliceNsearch(filename, chunksize, delta, term):
    final_hitlist = [] # list of file offsets which contain the search term
    try:
        fd = open(filename, mode="rb")
    except:
        print("Problems Opening Input File")
        exctype, value = sys.exc_info()[:2]
        print("Exception type = ",exctype,", value = ",value) 
        exit(-1)

    stats = os.stat(filename)
    #print("sliceNsearch Input file " + filename + " is " + str(stats.st_size) + " bytes\n")
    begin_chunk = 0

    # Handle if filesize is less than CHUNK_SIZE (eg store.vol instead of image.bin)
    # Should be able to read whole file in 1 chunk 
    if (chunksize >= stats.st_size):
        fd.seek(begin_chunk)
        raw = fd.read()
        final_hitlist = all_indices(raw, term, [])
        #print(str(len(final_hitlist)) + " hits found in 1 chunk for " + str(term))
    else:
        # Filesize is greater than 1 chunk, need to loop thru
        while ((begin_chunk + chunksize) <= stats.st_size) :
            chunk_size_to_read = chunksize + delta # read a bit more than the chunk size in case a search hit crosses chunk boundaries
            if ((chunk_size_to_read + begin_chunk) > stats.st_size):
                chunk_size_to_read = stats.st_size - begin_chunk # reads rest of file at EOF and/or whole file if chunk is greater than filesize
            #print("seeking " + str(begin_chunk) + " with size = " + str(chunk_size_to_read))
            fd.seek(begin_chunk)
            rawchunk = fd.read(chunk_size_to_read)
            subhits = all_indices(rawchunk, term, [])
            #print(str(len(subhits)) + " hits found at " + str(subhits))
            # Items in subhits will be offsets relative to the start of the rawchunk (not relative to the file)
            # Need to adjust offsets ...
            for hit in subhits :
                if (hit < chunksize) :
                    final_hitlist.append(begin_chunk + hit)
                    #print("adding " + str(begin_chunk + hit) + " to list")
                elif (hit >= chunksize) :
                    #print("ignoring " + str(begin_chunk + hit) + " to list")
                    break # don't care if we get here because hit should be processed in next chunk
                    # subhits can start at index 0 so possible hit offsets are 0 to chunksize-1 inclusive
            begin_chunk += chunksize
        #print("final_hitlist = " + str(final_hitlist))
    fd.close()
    return(final_hitlist)

# Searches chunks of a file (using RE) and returns file offsets of any hits.
# Intended for searching of large files where we cant read the whole thing into memory
# This function calls the "regsearch" search method
def sliceNsearchRE(filename, chunksize, delta, term):
    final_hitlist = [] # list of file offsets which contain the search term
    pattern = re.compile(term, re.DOTALL) # should only really call this once at start, if same substring.

    try:
        fd = open(filename, mode="rb")
    except:
        print("Problems Opening Input File")
        exctype, value = sys.exc_info()[:2]
        print("Exception type = ",exctype,", value = ",value) 
        exit(-1)

    stats = os.stat(filename)
    #print("sliceNsearchRE Input file " + filename + " is " + str(stats.st_size) + " bytes\n")
    begin_chunk = 0

    # Handle if filesize is less than CHUNK_SIZE (eg store.vol instead of image.bin)
    # Should be able to read whole file in 1 chunk 
    if (chunksize >= stats.st_size):
        fd.seek(begin_chunk)
        raw = fd.read()
        final_hitlist = regsearch(raw, pattern, [])
        #print(str(len(final_hitlist)) + " hits found in 1 chunk for " + str(term))
    else:
        # Filesize is greater than 1 chunk, need to loop thru
        while ((begin_chunk + chunksize) <= stats.st_size) :
            chunk_size_to_read = chunksize + delta
            if ((chunk_size_to_read + begin_chunk) > stats.st_size):
                chunk_size_to_read = stats.st_size - begin_chunk
            #print("seeking " + str(begin_chunk) + " with size = " + str(chunk_size_to_read))
            fd.seek(begin_chunk)
            rawchunk = fd.read(chunk_size_to_read)
            subhits = regsearch(rawchunk, pattern, [])
            #print(str(len(subhits)) + " hits found at " + str(subhits))
            # Items in subhits will be offsets relative to the start of the rawchunk (not relative to the file)
            # Need to adjust offsets ...
            for hit in subhits :
                if (hit < chunksize) :
                    final_hitlist.append(begin_chunk + hit)
                    #print("adding " + str(begin_chunk + hit) + " to list")
                elif (hit >= chunksize) :
                    #print("ignoring " + str(begin_chunk + hit) + " to list")
                    break # don't care if we get here because hit should be processed in next chunk
                    # subhits can start at index 0 so possible hit offsets are 0 to chunksize-1 inclusive
            begin_chunk += chunksize
        #print("final_hitlist = " + str(final_hitlist))
    fd.close()
    return(final_hitlist)

# Basic read everything and wait method (calls "all_indices" function)
def wholeread(filename, substring):
    hits = []
    try:
        fd = open(filename, mode="rb")
    except:
        print("Problems Opening Input File")
        exctype, value = sys.exc_info()[:2]
        print("Exception type = ",exctype,", value = ",value) 
        exit(-1)
    filestring = fd.read()
    hits = all_indices(filestring, substring, [])
    fd.close()
    return hits

# Basic read everything and wait method (calls "regsearch" function)
def wholereadRE(filename, substring):
    hits = []
    try:
        fd = open(filename, mode="rb")
    except:
        print("Problems Opening Input File")
        exctype, value = sys.exc_info()[:2]
        print("Exception type = ",exctype,", value = ",value) 
        exit(-1)
    filestring = fd.read()
    pattern = re.compile(substring, re.DOTALL) # should only really call this once at start, if same substring.
    hits = regsearch(filestring, pattern, [])
    fd.close()
    return hits

# Main
version_string = "chunkymonkey.py v2015-07-10"
print("Running " + version_string + "\n")

parser = argparse.ArgumentParser(description='Helps find optimal chunk sizes when searching large binary files for a known hex string')
parser.add_argument("inputfile", help='File to be searched')
parser.add_argument("term", help='Hex Search string eg 53004d00')
parser.add_argument("chunksize", type=int, help="Size of each chunk (in decimal bytes)")
parser.add_argument("delta", type=int, help="Size of the extra read buffer (in decimal bytes)")

args = parser.parse_args()
searchterm = binascii.unhexlify(args.term) # convert input hex string into its binary representation to use in searches
print("Search term is: " + binascii.hexlify(searchterm))

# For benchmark monitoring (via the "-m cProfile" arg), we have each string search method called from its own function
hits = sliceNsearch(args.inputfile, args.chunksize, args.delta, searchterm)
rehits = sliceNsearchRE(args.inputfile, args.chunksize, args.delta, searchterm)
print("Chunky sliceNsearch hits = " + str(len(hits)) + ", Chunky sliceNsearchRE hits = " + str(len(rehits)))
if (len(hits) != len(rehits)):
    print("Hit length mismatch for chunky searches!")
else:
    # check hit offsets are same
    for jj in range(len(hits)):
        if (hits[jj] != rehits[jj]):
            print("Chunky hit MISMATCH at index " + str(jj) + ", sliceNsearch hit at " + str(hits[jj]) + ", sliceNsearchRE hit at " + str(rehits[jj]))
#        else:
#            print("Chunky hit at index " + str(jj) + ", sliceNsearch hit at " + str(hits[jj]) + ", sliceNsearchRE hit at " + str(rehits[jj]))

# Simple read for comparison (no chunking, reads file into one big BINARY string before calling "all_indices"
whits = wholeread(args.inputfile, searchterm)
# Simple read for comparison (no chunking, reads file into one big BINARY string before calling "regsearch"
whitsre = wholereadRE(args.inputfile, searchterm)
print("Wholeread all_indices hits = " + str(len(whits)) + ", Wholeread regsearch hits = " + str(len(whitsre)) )
if (len(whits) != len(whitsre)):
    print("Hit length mismatch for simple searches!")
else:
    # check hit offsets are same
    for jj in range(len(whits)):
        if (whits[jj] != whitsre[jj]):
            print("Simple hit MISMATCH at index " + str(jj) + ", all_indices hit at " + str(whits[jj]) + ", regsearch hit at " + str(whitsre[jj]))
#        else:
#            print("Simple hit at index " + str(jj) + ", all_indices hit at " + str(whits[jj]) + ", regsearch hit at " + str(whitsre[jj]))



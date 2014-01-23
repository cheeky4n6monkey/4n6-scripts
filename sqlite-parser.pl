#!/usr/bin/perl -w

# sqlite-parser.pl = Perl script to parse selected SQLite Database header fields
# Based on the Database Header section of http://www.sqlite.org/fileformat2.html
#
# Copyright (C) 2012 Adrian Leong (cheeky4n6monkey@gmail.com)
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

# Version History:
# v2012-03-21 Initial Version

use strict;

use Getopt::Long;
use Encode;

my $version = "sqlite-parser.pl v2012-03-21";
my $help = 0;
my $filename = "";

GetOptions('help|h' => \$help,
	'file=s' => \$filename);

if ($help || $filename eq "")
{
	print("\nHelp for $version\n\n");
	print("Perl script to parse selected SQLite header fields\n"); 
	print("\nUsage: sqlite-parser.pl [-h|help] [-file filename]\n");
	print("-h|help .......... Help (print this information). Does not run anything else.\n");
	print("-file filename ... sqlite filename to be parsed.\n");
	print("\nExample: sqlite-parser.pl -file /cases/firefox/places.sqlite\n");
	exit;
}

print "\nRunning $version\n\n";

# Try read-only opening the SQLite file to extract various header information
my $rawsqliteheader;

open(my $sqlitefile, "<".$filename) || die("Unable to open $filename for header parsing\n");
#binmode($sqlitefile);
sysread ($sqlitefile, $rawsqliteheader, 100) || die("Unable to read $filename for header parsing\n");; 
close($sqlitefile);

# First check that we have a valid header 1st 16 bytes should read "SQLite format 3\000" in UTF8
# or alternatively "53 51 4c 69 74 65 20 66 6f 72 6d 61 74 20 33 00" in hex
my $rawsqlitestring = substr($rawsqliteheader, 0, 16);
my $sqlitestring = decode("UTF8", $rawsqlitestring);
if ($sqlitestring eq "SQLite format 3\000")
{
	print "SQLite String Parsed OK - Continuing Processing of $filename ...\n";
}
else
{
	print "$filename does NOT have a Valid SQLite String in Header! Bailing out ...\n\n";
	exit;
}


# Extract the database page size in bytes
# Should/Must be a power of two between 512 and 32768 inclusive, or the value 1 representing a page size of 65536
my $rawdbpagesize = substr($rawsqliteheader, 16, 2);
my $dbpagesize = unpack("n", $rawdbpagesize); # Use "n" for 2 byte int
if ($dbpagesize eq 1)
{
	print("Database Page Size (bytes) = 65536\n");
}
else
{
	print("Database Page Size (bytes) = $dbpagesize\n");
}


# Extract the size of the database file in pages.
my $rawnumpages = substr($rawsqliteheader, 28, 4);
my $numpages = unpack("N", $rawnumpages); # use "N" for 4 byte int
if ($numpages ne 0)
{
	# Must check that changecounter = validversionfor 
	# as validversionfor stores the current changecounter value after the SQLite version number was written
	# (eg at creation)
	my $rawchangecounter = substr($rawsqliteheader, 24, 4);
	my $changecounter = unpack("N", $rawchangecounter);

	my $rawvalidversionfor = substr($rawsqliteheader, 92, 4);
	my $validversionfor = unpack("N", $rawvalidversionfor);

#	print "changecounter = $changecounter\n";
#	print "validversionfor = $validversionfor\n";

	if ($changecounter eq $validversionfor)
	{
		print("Valid Number of Pages = $numpages\n");
	}
	else
	{
		print("Invalid Number of Pages! (mismatched changecounter value)\n");
	}
}
else
{
	print("Invalid Number of Pages! (zero)\n");
}


# Extract the total number of freelist pages. 
my $rawnumfreelistpages = substr($rawsqliteheader, 36, 4);
my $numfreelistpages = unpack("N", $rawnumfreelistpages); # use "N" for 4 byte int
print("Total Number of Freelist Pages = $numfreelistpages\n");


# Extract the schema format number. Supported schema formats are 1, 2, 3, and 4. 
my $rawschemaformatnum = substr($rawsqliteheader, 44, 4);
my $schemaformatnum = unpack("N", $rawschemaformatnum); # use "N" for 4 byte int
#print("Schema Format Number = $schemaformatnum\n");
if ($schemaformatnum == 1)
{
	print("Schema Format = SQLite v3.0.0\n");
}
elsif ($schemaformatnum == 2)
{
	print("Schema Format = SQLite v3.1.3 (2005)\n");
}
elsif ($schemaformatnum == 3)
{
	print("Schema Format = SQLite v3.1.4 (2005)\n");
}
elsif ($schemaformatnum == 4)
{
	print("Schema Format = SQLite v3.3.0 (2006) or higher\n");
}
else
{
	print("Invalid Schema Format!\n");
}


# Extract the database text encoding. A value of 1 means UTF-8. A value of 2 means UTF-16le. A value of 3 means UTF-16be. 
my $rawtextencode = substr($rawsqliteheader, 56, 4);
my $textencode = unpack("N", $rawtextencode); # use "N" for 4 byte int

#print("Text Encoding = $textencode\n");
if ($textencode == 1)
{
	print("Text Encoding = UTF-8\n");
}
elsif ($textencode == 2)
{
	print("Text Encoding = UTF-16le\n");
}
elsif ($textencode == 3)
{
	print("Text Encoding = UTF-16be\n");
}
else
{
	print("Invalid Text Encoding!\n");
}


# Extract the SQLite Version number as a 4 byte Big Endian Integer at bytes 96-100
# The version number will be in the form (X*1000000 + Y*1000 + Z) 
# where X is the major version number (3 for SQLite3), Y is the minor version number and Z is the release number 
# eg 3007004 for 3.7.4
my $rawsqliteversion = substr($rawsqliteheader, 96, 4);
my $sqlversion = unpack("N", $rawsqliteversion);
print("SQLite Version is: $sqlversion\n\n");


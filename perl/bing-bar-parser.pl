#!/usr/bin/perl -w

# bing-bar-parser.pl = Perl script to parse Bing Bar searchhs.dat files
# Based on:
# - The processBingToolbar function from the "sep-history-viewer" C# Google code project 
# (http://code.google.com/p/sep-history-viewer/source/browse/trunk/SEPHistoryViewer/Main.cs)
# - Mari DeGrazia's blog post on interpreting the Bing Bar's Searchhs.dat file 
# (http://az4n6.blogspot.com/2012/07/searchhsdat-and-bing-bar.html)
# - The SystemTime 128 bit data structure as defined by Microsoft 
# (http://msdn.microsoft.com/en-us/library/windows/desktop/ms724950%28v=vs.85%29.aspx)
# - Mark Stosberg's blog on Percent-encoding URIs in Perl
# (http://mark.stosberg.com/blog/2010/12/percent-encoding-uris-in-perl.html)
#
# Note: According to "sep-history-viewer" page, the Bing Bar's searchhs.dat file is typically located
#
# For XP in:
# \Documents and Settings\<user>\Local Settings\Application Data\Microsoft\Search Enhancement Pack\Search Box Extension
#
# For Vista/7 in:
# \Users\<user>\AppData\LocalLow\Microsoft\Search Enhancement Pack\Search Box Extension 
#
# Also note that for a Win7 system, an additional searchhs.dat file (with URI encoding) has been found in:
# \Users\<user>\AppData\Local\Microsoft\BingBar\Apps\Search_6f21d9007fa34bc78d94309126de58f5\VersionIndependent
# You can use the -d option to decode the URI encoding to something readable
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
#
# Version History:
# v2012-11-10 Initial Version

use strict;
#use warnings;

use Getopt::Long;
# to minimise package installation we'll use "CGI::Util::unescape" for URI decoding
# Instead of something like "URI::Encode::uri_decode"
use CGI::Util qw(unescape);

my $version = "bing-bar-parser.pl v2012-11-10";
my $help = 0;
my $filename = "";
my $decode = 0;
my @daysofweek = ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"); # 0(sun)... 6(sat)

GetOptions('help|h' => \$help,
	'd' => \$decode,
	'f=s' => \$filename);

if ($help || $filename eq "")
{
	print("\nHelp for $version\n\n");
	print("Perl script to parse selected fields from a given Bing Bar searchhs.dat file\n"); 
	print("\nUsage: bing-bar-parser.pl [-h|help] [-file filename]\n");
	print("-h|help ... Help (print this information). Does not run anything else.\n");
	print("-f file ... Bing Bar searchhs.dat file to be parsed.\n");
	print("-d ........ Applies URI decoding to search terms (eg replaces %20 with space).\n");
	print("\nExample: bing-bar-parser.pl -f /cases/searchhs.dat -d\n");
	exit;
}

print "\nRunning $version\n\n";

open(my $searchfile, "<".$filename) || die("Unable to open $filename\n");
binmode($searchfile);

my $filehdrbuffer;
# Read 1st 28 bytes = File Header
sysread ($searchfile, $filehdrbuffer, 28, 0) || die("Unable to read $filename for header parsing\n");; 

my $rawfilehdrstr = substr($filehdrbuffer, 0, 4);
my $hdr = unpack("V", $rawfilehdrstr);
printf ("File Header field check (should be \"FACADE0\"): %X\n", $hdr);

my $rawfileverstr = substr($filehdrbuffer, 4, 4);
my $ver = unpack("V", $rawfileverstr);
print "Bing Bar File Version: $ver\n";

my $rawnextrecstr = substr($filehdrbuffer, 8, 4);
my $nextrec = unpack("V", $rawnextrecstr);
print "Record ID for next new record: $nextrec\n";

my $rawreccountstr = substr($filehdrbuffer, 20, 4);
my $count = unpack("V", $rawreccountstr);
print "Number of Records in this file: $count\n\n";

# Read each Record entry in a loop
my $currpos = 28;
my $buffer;

for (my $loopcount = 0; $loopcount < $count; $loopcount++)
{
	sysseek($searchfile, $currpos, 0);
	sysread($searchfile, $buffer, 4, 0);
	my $facefeedstr = substr($buffer, 0, 4);
	my $facefeed = unpack("V", $facefeedstr);
	#sprintf ("Records First Header field: %X\n", $facefeed);

	$currpos += 4;

	sysseek($searchfile, $currpos, 0);
	sysread($searchfile, $buffer, 4, 0);
	my $recsizestr = substr($buffer, 0, 4);
	my $recsize = unpack("V", $recsizestr);
	#print "Record size: $recsize\n";

	$currpos += 4;
	# calculate the beginning of the next record for use at end of this loop iter
	my $nextrec = $currpos + $recsize;

	# skip processing the 0x19031991 fixed value field
	$currpos += 4;

	sysseek($searchfile, $currpos, 0);
	sysread($searchfile, $buffer, 4, 0);
	my $recidstr = substr($buffer, 0, 4);
	my $recid = unpack("V", $recidstr);
	print "Record id: $recid | ";

	$currpos += 4;
	# skip processing the next field
	$currpos += 4;

	sysseek($searchfile, $currpos, 0);
	sysread($searchfile, $buffer, 4, 0);
	my $searchcountstr = substr($buffer, 0, 4);
	my $searchcount = unpack("V", $searchcountstr);
	# Search count appears to increment with each subsequent search (from Mari's blog)
	print "Search Count: $searchcount | ";

	$currpos += 4;

	# Date appears to be in 128 bit SystemTime format 
	# (compare the MS definition and the code in "sep-history-viewer") 
	# Year (2 bytes)
	sysseek($searchfile, $currpos, 0);
	sysread($searchfile, $buffer, 2, 0);
	my $yearstr = substr($buffer, 0, 2);
	my $year = unpack("v", $yearstr);
	#print "Year: $year\n";

	$currpos += 2;

	# Month [1...12] (2 bytes)
	sysseek($searchfile, $currpos, 0);
	sysread($searchfile, $buffer, 2, 0);
	my $monthstr = substr($buffer, 0, 2);
	my $month = unpack("v", $monthstr);
	#print "Month: $month\n";

	$currpos += 2;

	# Day of Week [0 (sun)... 6(sat)] (2 bytes)
	# Appears to be implemented OK
	sysseek($searchfile, $currpos, 0);
	sysread($searchfile, $buffer, 2, 0);
	my $daystr = substr($buffer, 0, 2);
	my $day = unpack("v", $daystr);
	#print "Day-week: $day\n";

	$currpos += 2;

	# Day of month [1...31] (2 bytes)
	sysseek($searchfile, $currpos, 0);
	sysread($searchfile, $buffer, 2, 0);
	my $daymonthstr = substr($buffer, 0, 2);
	my $daymonth = unpack("v", $daymonthstr);
	#print "Day-month: $daymonth\n";

	$currpos += 2;

	# Hour (2 bytes)
	sysseek($searchfile, $currpos, 0);
	sysread($searchfile, $buffer, 2, 0);
	my $hourstr = substr($buffer, 0, 2);
	my $hour = unpack("v", $hourstr);
	#print "Hour: $hour\n";

	$currpos += 2;

	# Min (2 bytes)
	sysseek($searchfile, $currpos, 0);
	sysread($searchfile, $buffer, 2, 0);
	my $minstr = substr($buffer, 0, 2);
	my $min = unpack("v", $minstr);
	#print "Min: $min\n";

	$currpos += 2;

	# Sec (2 bytes)
	sysseek($searchfile, $currpos, 0);
	sysread($searchfile, $buffer, 2, 0);
	my $secstr = substr($buffer, 0, 2);
	my $sec = unpack("v", $secstr);
	#print "Sec: $sec\n";

	$currpos += 2;

	# msec (2 bytes) => Unused? Appears to always be 0, we'll leave it out for now
	#sysseek($searchfile, $currpos, 0);
	#sysread($searchfile, $buffer, 2, 0);
	#my $msecstr = substr($buffer, 0, 2);
	#my $msec = unpack("v", $msecstr);
	#print "mSec: $msec\n";

	printf "Last Search Time (UTC) = %.4d-%.2d-%.2d ".$daysofweek[$day]." %.2d:%.2d:%.2d | ", $year, $month, $daymonth, $hour, $min, $sec;

	$currpos += 2;

	# Search Term Length (4 bytes) = number of characters in search term
	sysseek($searchfile, $currpos, 0);
	sysread($searchfile, $buffer, 4, 0);
	my $termlengthstr = substr($buffer, 0, 4);
	my $termlength = unpack("V", $termlengthstr);
	#print "Termlength: $termlength\n";
	$currpos += 4;

	# $buffer has $termlength x 2 bytes read in as theres 2 bytes for each character
	# ie 0x7700 represents "w" so treat 1st byte (0x77) as ascii string and ignore 2nd byte (0x00)
	# alternatively, ignore 0x00 bytes and only use the non-zero bytes for string
	sysseek($searchfile, $currpos, 0);
	sysread($searchfile, $buffer, $termlength*2, 0);
	my $term;
	$term = unpack("a*", substr($buffer, 0, $termlength*2));
	$term =~ s/\00//g; # strip out any 0x00 from string so it can be printed/parsed properly

	if ($decode)
	{
		my $dterm = unescape($term); # get rid of URI encoding
		print "Term (decoded): $dterm\n";
	}
	else
	{
		print "Term: $term\n";
	}

	$currpos = $nextrec;

} # ends for loop

close($searchfile);

print "\n$version Finished!\n\n";

#ends main


#!/usr/bin/perl -w

# timediff32.pl = Perl script calculates number of seconds between a reference date/time and a target date/time (assumes 32 bit field).
#
# Copyright (C) 2013 Adrian Leong (cheeky4n6monkey@gmail.com)
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
# v2013-07-23 Initial Version (tested with SANS SIFT v2.14 and ActiveState Perl v5.16.1 on Win7 64bit)
#
# References:
# http://sandersonforensics.com/forum/content.php?131-A-brief-history-of-time-stamps
# So this script should work for any 32 bit integer time fields used to count seconds since a particular date.
# ie Unix epoch (1JAN1970), AOL time* (1JAN1980), GPS time (6JAN1980), HFS/HFS+ (1JAN1904), Apple Mac Absolute time/OS X Epoch (1JAN2001)
# Note: *AOL is untested but it should work same as others 
# HFS+ is UTC, HFS is Local time per http://www.forensicswiki.org/wiki/Mac_OS_X
#
# See also http://en.wikipedia.org/wiki/Epoch_%28reference_date%29 for further dates of significance 
#
# Tested using values from the table at http://www.digital-detective.co.uk/freetools/decode.asp
#
# Issues:
# Not sure how accurate results are when target dates occur BEFORE the reference date (had no test data to compare to).
#

use strict;
use warnings;
use Getopt::Long;
use Date::Calc qw(Delta_DHMS);

my $version = "timediff32.pl v2013.07.23";
my $help = 0; # help flag
my $ref="";
my $target="";

GetOptions('help|h' => \$help,
	'ref=s' => \$ref,
	'target=s' => \$target);

if ($help || $ref eq "" || $target eq "" || not ($ref =~ /(\d+)-(\d+)-(\d+)T(\d+):(\d+):(\d+)/) || not ($target =~ /(\d+)-(\d+)-(\d+)T(\d+):(\d+):(\d+)/))
{
	print("\nCalculates number of seconds between a reference date/time and a target date/time (assumes 32 bit field).\n");
	print("$version\n");
	print("\nUsage: timediff32.pl [-h|help] [-ref YYYY-MM-DDTHH:mm:ss] [-target YYYY-MM-DDTHH:mm:ss]\n");
	print("-h|help ........ Help (print this information). Does not run anything else.\n");
	print("-ref date ...... Reference date in YYYY-MM-DDTHH:mm:ss format.\n");
	print("-target date ... Target date in YYYY-MM-DDTHH:mm:ss format.\n\n");
	print("Example: timediff32.pl -ref 1970-01-01T00:00:00 -target 2013-07-01T00:00:00\n");
	print("Note: The T separating the date (eg 1970-01-01) from the time field (eg 00:00:00)\n\n");
	exit;
}

print "\nRunning $version\n\n";

$ref =~ /(\d+)-(\d+)-(\d+)T(\d+):(\d+):(\d+)/;
my $refyear = $1;
my $refmonth = $2;
my $refday = $3;
my $refhour = $4;
my $refmin = $5;
my $refsec = $6;

$target =~ /(\d+)-(\d+)-(\d+)T(\d+):(\d+):(\d+)/;
my $targetyear = $1;
my $targetmonth = $2;
my $targetday = $3;
my $targethour = $4;
my $targetmin = $5;
my $targetsec = $6;

# Delta_DHMS
# ($Dd,$Dh,$Dm,$Ds) = Delta_DHMS($year1,$month1,$day1,$hour1,$min1,$sec1, $year2,$month2,$day2,$hour2,$min2,$sec2);
# Find difference between ref and target in secs (can be positive/negative offset)
my ($Dd,$Dh,$Dm,$Ds) = Date::Calc::Delta_DHMS($refyear, $refmonth, $refday, $refhour, $refmin, $refsec, 
											$targetyear, $targetmonth, $targetday, $targethour, $targetmin,$targetsec);
my $epochoffset = $Dd*24*60*60+$Dh*60*60+$Dm*60+$Ds; # convert difference into number of secs

printf("$target is $epochoffset (decimal)\n");
printf("$target is 0x%.8X (BE hex)\n", $epochoffset); # also ensure number is padded to 8 digits

my $epochoffset_LE = unpack("L<", pack("L>", $epochoffset)); # byte swap ie pack as BE, unpack as LE (should work regardless of actual arch)
printf("$target is 0x%.8X (LE hex)\n\n", $epochoffset_LE); # also ensure number is padded to 8 digits

# Test example => 0x51D0C680 BE = 0x80C6D051 LE = 1372636800 decimal secs (for 1JUL2013 ref 1JAN1970)

# Note to self - for determining PC endian-ness
# From http://perldoc.perl.org/Config.html#byacc
# Use Config;
# $Config{byteorder} = 1234 = LE, $Config{byteorder} = 4321 = BE
#printf ("Byte order = $Config{byteorder}\n");



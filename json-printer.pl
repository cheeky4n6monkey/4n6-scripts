#!/usr/bin/perl -w

# json-printer.pl = Perl script to pretty print JSON files
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
# v2012-04-08 Initial Version

use strict;

use Getopt::Long;
use JSON;

my $version = "json-printer.pl v2012-04-08";
my $help = 0;
my $filename="";
my @jsonlist;

GetOptions('help|h' => \$help,
			'f=s' => \$filename);

if ($help || $filename eq "")
{
	print("\nHelp for $version\n\n");
	print("Perl script to pretty print JSON files.\n");
	print("Example: json-printer.pl -f search-5.json\n");
	exit;
}

open(my $tfile, "<", $filename) or die "Can't Open $filename JSON File!";
@jsonlist = <$tfile>; # extract each line to a list element
chomp(@jsonlist); # get rid of newlines 
close($tfile);

my $json_string = join(' ', @jsonlist); # join list elements into one big happy scalar string

my $json = JSON->new->allow_nonref; # create a new JSON object which converts non-references into their values for encoding
my $perl_scalar = $json->decode($json_string); # converts JSON string into Perl hash(es)

# at this point (if you wanted to) you can add code to iterate thru the hash(es) to extract/use values.

my $pretty_printed = $json->pretty->encode( $perl_scalar ); # re-encode the hash just so we can then pretty print it (hack-tacular!)
print $pretty_printed;


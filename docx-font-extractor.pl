#!/usr/bin/perl -w

# docx-font-extractor.pl = A Perl script to extract font information from .DOCX & .XLSX.
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
# v2012.04.29 Initial Version

# MS Office 2010 fonts
# http://support.microsoft.com/kb/2121313

# MS Office 2k7 fonts
# http://support.microsoft.com/kb/924623

# MS Office2k3, 2k, 97 fonts
# http://support.microsoft.com/kb/837463


use strict;

use Getopt::Long;
use XML::XPath;

my $version = "docx-font-extractor.pl v2012.04.29";
my $help = 0; # help flag
my $isdocx = 0;
my $isxlsx = 0;
my $fontfile = "";

# TODO my @OFFICE2007_FONTS = ();
# TODO my @OFFICE2010_FONTS = ();


GetOptions('help|h' => \$help,
	'd' => \$isdocx,
	'x' => \$isxlsx,
	'f=s' => \$fontfile);

if ($help || $fontfile eq "" || ($isdocx eq 0 and $isxlsx eq 0) || ($isdocx eq 1 and $isxlsx eq 1) )
{
	print("\n$version\n");
	print("Perl script to list fonts used in an MS Office .docx or .xlsx file\n");
	print("Assumes .docx or .xlsx has already been unzipped to a local directory\n\n");
	print("Example: docx-font-extractor.pl -d -f /home/sansforensics/word2k7/word/fontTable.xml\n");
	print("Example: docx-font-extractor.pl -x -f /home/sansforensics/excelbk1/xl/styles.xml\n");
	exit;
}

my $xpath = XML::XPath->new(filename => $fontfile);
my $nodeset;
my $xmlfontfield;

if ($isdocx)
{
	$nodeset = $xpath->find("/w:fonts/w:font");
	$xmlfontfield = "w:name";
}
elsif ($isxlsx)
{
	$nodeset = $xpath->find("/styleSheet/fonts/font/name");
	$xmlfontfield = "val";
}

print "Found ".$nodeset->size." results\n";

foreach my $node ($nodeset->get_nodelist)
{
	my $fontname = $node->getAttribute($xmlfontfield);
	print "Found font = $fontname\n";

	# TODO Lookup $fontname in list of stored Office fonts

	# TODO Print "The ... font is installed on MS Office ..."

}



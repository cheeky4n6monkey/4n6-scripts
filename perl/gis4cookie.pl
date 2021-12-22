#!/usr/bin/perl -w

# gis4cookie.pl = Perl script to grep a file/directory of files for selected Google Analytic parameters
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
# v2013-05-20 Initial Version
# v2013-06-02 Added path argument (single directory processing)
# v2013-07-15 Added parsing for utmz, utmr, flash ver, java enabled
# v2013-07-17 Cleaned up code/increased $MAX_SZ_STRING to 2000/fixed utmz_utmcct URI decoding
#
# Special Thanks:
# This script was inspired by the research of Mari DeGrazia
# and then further improved based upon her testing comments.
# See http://az4n6.blogspot.com/2013/07/google-analytic-values-in-cache-files.html
#
# References:
# Jon Nelson's DFINews article on Google Analytic Cookies:
# http://www.dfinews.com/articles/2012/02/google-analytics-cookies-and-forensic-implications
# and the Google Analytics documentation
# https://developers.google.com/analytics/resources/concepts/gaConceptsTrackingOverview?hl=en

use strict;
use warnings;
use Getopt::Long;
# to minimise package installation we'll use "CGI::Util::unescape" for URI decoding
# Instead of something like "URI::Encode::uri_decode"
use CGI::Util qw(unescape);

my $version = "gis4cookie.pl v2013-07-17";

# input arguments
my $help = 0;
my $filename = "";
my $pathname = "";
my $decodeflag="";
my $outputflag = "";

# Global vars
my $MAX_SZ_STRING = 2000; # URL string extraction loop limit
my %STORAGE; # hash keyed by "filename_offset", value is an array of filename, offset, URL request string
my $FILENAME_IDX=0; # array index to the filename
my $OFFSET_IDX=1; # array index to the file offset
my $URL_IDX=2; # array index to the URL request string

GetOptions('help|h' => \$help,
	'f:s' => \$filename,
	'p:s' => \$pathname,
	'd' => \$decodeflag,
	'o:s' => \$outputflag);

if ($help || ($filename eq "" and $pathname eq "") || ($filename ne "" and $pathname ne ""))
{
	print("\nHelp for $version\n\n");
	print("Perl script to grep a file/directory of files for selected Google Analytic parameters\n"); 
	print("\nUsage: gis4cookie.pl [-h|help] [-f filename] [-p path] [-d] [-o output]\n");
	print("-h|help ... Help (print this information). Does not run anything else.\n");
	print("-f file ... Individual File to be parsed.\n");
	print("-p path ... Directory (absolute path) containing Files to be parsed.\n");
	print("-d ........ (Optional) Decode URI encoded strings (eg replace %20 with space).\n");
	print("-o output . (Optional) Output to specified Tab separated file. Will overwrite any existing file.\n");
	print("\nExample: gis4cookie.pl -f cookiefile -o output.tsv -d\n");
	print("\nExample: gis4cookie.pl -p /home/sansforensics/unallocated_dir\n");
	print("NOTE1: If values are not present/extracted OK, \"NA\" is displayed.\n");
	print("NOTE2: Use -f or -p to specify input file(s) but NOT both.\n\n");
	exit;
}

my $starttime = time();

print "\nRunning $version\n\n";

if (-d $pathname)
{
	print "path = $pathname\n";
	ProcessDir($pathname);
}
elsif (-f $filename)
{
	ProcessFile($filename); # 1 file 
}
else
{
	print ("Bad directory or filename specified!");
	exit();
}

# output
# Check if outputting to output file or to screen
my $outputfile;
if ($outputflag eq "")
{
	print "No output file specified. Printing results to screen ...\n\n";
}
else
{
	open($outputfile, ">", $outputflag) || die("Unable to open output file $outputflag\n");
	print "Printing results to $outputflag ...\n";
}

# Print column titles
if ($outputflag eq "")
{
	printf ("Filename\tOffset\tutma_first\tutma_previous\tutma_last\tudmt_page_title\tutmhn_hostname\tutmp_page_request\tutmr_referral\tutmz_last_time\tutmz_sessions\tutmz_sources\tutmz_utmcsr\tutmz_utmcmd\tutmz_utmctr\tutmz_utmcct\tutmfl\tutmje\n"); # start with file offset column title

}
else
{
	printf ($outputfile "Filename\tOffset\tutma_first\tutma_previous\tutma_last\tudmt_page_title\tutmhn_hostname\tutmp_page_request\tutmr_referral\tutmz_last_time\tutmz_sessions\tutmz_sources\tutmz_utmcsr\tutmz_utmcmd\tutmz_utmctr\tutmz_utmcct\tutmfl\tutmje\n");
}

# Now process each URL string according to 
# https://developers.google.com/analytics/resources/concepts/gaConceptsTrackingOverview?hl=en
# For now we'll extract utmcc (selected cookie values for utma), utmdt (page title), utmhn (Hostname), utmp (page request). 
# ie utma_first, utma_previous, utma_last, (TBD: utma_session), udmt_page_title, utmhn_hostname, utmp_page_request
# utma = <domain hash>.<visitor ID>.<first visit>.<previous>.<last>.<# of sessions>
# # of sessions is the number of new sessions created for that Web site. This number is not incremented when the site is reloaded.
# If present, utma will be part of utmcc arg so we search for that format between "__utma%3D" and trailing "%3B". (%3D is URI encoded "=", %3B is ";")
# Also extract utmz = <domain hash>.<last time>.<sessions>.<sources>.<variables>
# variables are "|" (ie %7C) separated and include utmcsr (source used to access target site), utmctr (keywords used in search), utmcmd (organic/referral/direct), utmcct (path to referral page used)

# Used to sort %STORAGE keys by their filename and then by offset (before extracting data & printing)
sub byfileoffset { $STORAGE{$a}[$FILENAME_IDX] cmp $STORAGE{$b}[$FILENAME_IDX] ||  $STORAGE{$a}[$OFFSET_IDX] <=> $STORAGE{$b}[$OFFSET_IDX]}

foreach my $key (sort byfileoffset keys %STORAGE)
{
	my $utma_first_time="NA";
	my $utma_prev_time="NA";
	my $utma_last_time="NA";	
	#my $utma_session=-1;
	
	# finds patterns like "__utma=173272373.392125766.1296482149.1296482149.1296482162.2;"
	# ie <domain hash>.<visitor ID>.<first visit>.<previous>.<last>.<# of sessions>
	if ( $STORAGE{$key}[$URL_IDX] =~ /__utma%3D(\d+).(\d+).(\d+).(\d+).(\d+).(\d+)%3B/) 
	{
		my $utma_domain=$1;
		my $utma_visitorID=$2;
		my $utma_first=$3;
		my $utma_prev=$4;
		my $utma_last=$5;
		#$utma_session=$6;
		
		# convert time fields to human readable strings
		my ($sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst); 
		($sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst) = gmtime($utma_first);
		$utma_first_time = sprintf("%04d-%02d-%02d %02d:%02d:%02d", $year+1900, $mon+1, $mday, $hour, $min, $sec);

		($sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst) = gmtime($utma_prev);
		$utma_prev_time = sprintf("%04d-%02d-%02d %02d:%02d:%02d", $year+1900, $mon+1, $mday, $hour, $min, $sec);

		($sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst) = gmtime($utma_last);
		$utma_last_time = sprintf("%04d-%02d-%02d %02d:%02d:%02d", $year+1900, $mon+1, $mday, $hour, $min, $sec);
	}

	my $utmz_last_time="NA";
	my $utmz_sessions="NA";
	my $utmz_sources="NA";
	my $utmz_utmcsr="NA"; # source site
	my $utmz_utmcmd="NA"; # access type
	my $utmz_utmctr="NA"; # search terms
	my $utmz_utmcct="NA"; # path
	# finds patterns like "39791409.1290439913.1.1.utmcsr=amer-ml26.amer.csc.com|utmccn=(referral)|utmcmd=referral|utmcct=/mail/jnelsonxxxx.nsf/($Inbox)/xxx"
	# ie <domain hash>.<last time>.<sessions>.<sources>.<variables> 
	# where variables is everything printable from "utmcsr=" onwards.
	if ( $STORAGE{$key}[$URL_IDX] =~ /__utmz%3D(\d+).(\d+).(\d+).(\d+).([[:print:]]+)/)
	{
		my $utmz_domain=$1;
		my $utmz_last_time_secs=$2;
		$utmz_sessions=$3;
		$utmz_sources=$4;
		my $utmz_variables=$5;
		# Parse URI encoded variables section (each var is separated with a URI encoded "|" ie %7C). 
		# Note: %3D is "=" encoded.
		if ($utmz_variables =~ /utmcsr%3D([[:print:]]+?)%7C/) # source/site used to access website
		{
			$utmz_utmcsr = $1; # actual string does not appear to be URI encoded
		}
		my $utmcmd="NA"; # we skip parsing utmccn as its a duplicate of utmcmd
		if ($utmz_variables =~ /utmcmd%3D([[:print:]]+?)%7C/) # last type of access (organic/referral/direct)
		{
			$utmz_utmcmd = $1;
		}
		if ($utmz_variables =~ /utmctr%3D([[:print:]]+?)%3B/) # search keywords. %3B is ";" encoded
		{
			if ($decodeflag)
			{
				$utmz_utmctr = unescape($1); # terms are URI encoded
			}
			else
			{
				$utmz_utmctr = $1;
			}
		}
		# From test data, arg is URI encoded and terminated with ";"
		if ($utmz_variables =~ /utmcct%3D([[:print:]]+?)%3B/) # path to page on site of referring link
		{
			if ($decodeflag)
			{
				$utmz_utmcct = unescape($1); # path is URI encoded
			}
			else
			{
				$utmz_utmcct = $1;
			}
		}
		# Get a human readable string from utmz_last_time
		my ($sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst); 
		($sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst) = gmtime($utmz_last_time_secs);
		$utmz_last_time = sprintf("%04d-%02d-%02d %02d:%02d:%02d", $year+1900, $mon+1, $mday, $hour, $min, $sec);
	}

	my $utmdt = "NA"; # URI encoded page title
	if ( $STORAGE{$key}[$URL_IDX] =~ /utmdt=([[:print:]]+?)&/) # Note "=" and trailing "&" are not URI encoded
	{
		if ($decodeflag)
		{
			$utmdt = unescape($1); # title is URI encoded
		}
		else
		{
			$utmdt = $1;
		}
	}
	#printf("utmdt page title = %s\n", $utmdt);

	my $utmfl = "NA"; # URI encoded Flash ver
	if ( $STORAGE{$key}[$URL_IDX] =~ /utmfl=([[:print:]]+?)&/ ) # Note "=" and trailing "&" are not URI encoded
	{
		if ($decodeflag)
		{
			$utmfl = unescape($1); # Flash ver string is URI encoded
		}
		else
		{
			$utmfl = $1;
		}
	}
	#printf("utmfl Flash ver = %s\n", $utmfl);

	my $utmhn = "NA"; # Hostname
	if ( $STORAGE{$key}[$URL_IDX] =~ /utmhn=([[:print:]]+?)&/) # Note "=" and trailing "&" are not URI encoded
	{
		$utmhn = $1; # this string is NOT URI encoded
	}
	#printf("utmhn Hostname = %s\n", $utmhn);

	my $utmje = "NA"; # Java enabled flag
	if ( $STORAGE{$key}[$URL_IDX] =~ /utmje=([[:print:]]+?)&/) # Note "=" and trailing "&" are not URI encoded
	{
		$utmje = $1;
	}
	#printf("utmje Java Enabled = %s\n", $utmje);

	my $utmp = "NA"; # URI encoded page request
	if ( $STORAGE{$key}[$URL_IDX] =~ /utmp=([[:print:]]+?)&/) # Note "=" and trailing "&" are not URI encoded
	{
		if ($decodeflag)
		{
			$utmp = unescape($1); #  request is URI encoded
		}
		else
		{
			$utmp = $1;
		}
	}
	#printf("utmp page request = %s\n", $utmp);

	my $utmr = "NA"; # URI encoded referral URL
	# Note "=" and trailing "&" are not URI encoded
	if ( $STORAGE{$key}[$URL_IDX] =~ /utmr=([[:print:]]+?)(&|\x00)/) # have seen utmr terminated with either "&" or "00"
	{
		if ($decodeflag)
		{
			$utmr = unescape($1); # referral is URI encoded
		}
		else
		{
			$utmr = $1;
		}
	}
	#printf("utmr referral URL = %s\n", $utmr);

	# Now output extracted details in tab separated format ...
	if ($outputflag eq "") # to screen
	{
		printf ("%s\t0x%X\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n", $STORAGE{$key}[$FILENAME_IDX], $STORAGE{$key}[$OFFSET_IDX], $utma_first_time, $utma_prev_time, $utma_last_time, $utmdt, $utmhn, $utmp, $utmr, $utmz_last_time,$utmz_sessions, $utmz_sources, $utmz_utmcsr, $utmz_utmcmd, $utmz_utmctr, $utmz_utmcct, $utmfl, $utmje);
	}
	else # or to file
	{	
		printf ($outputfile "%s\t0x%X\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n", $STORAGE{$key}[$FILENAME_IDX], $STORAGE{$key}[$OFFSET_IDX], $utma_first_time, $utma_prev_time, $utma_last_time, $utmdt, $utmhn, $utmp, $utmr, $utmz_last_time,$utmz_sessions, $utmz_sources, $utmz_utmcsr, $utmz_utmcmd, $utmz_utmctr, $utmz_utmcct, $utmfl, $utmje);
	}

} # ends foreach hit loop

my $finishtime = time();
printf ("\n%d hits processed in %d seconds\n\n", scalar(keys(%STORAGE)), ($finishtime-$starttime));

exit;

# Functions
# Takes absolute file path and calls ProcessFile for each file it finds in that directory
sub ProcessDir
{
	my $path = shift;

	opendir(my $DIR, $path) or die "Cannot open directory $path\n";
	while (defined(my $file = readdir($DIR)))
	{
		next if $file =~ /^\.\.?$/;
		ProcessFile($path."/".$file); # must add path prefix
	}
	closedir($DIR);
}

# Takes a filename and stores the filename, hit offset and partial url request string
# in STORAGE hash.
sub ProcessFile
{
	my $filen = shift;

	my $filesize = -s $filen;
	if (not defined $filesize)
	{
		print ("Undefined filesize: $!\n");
		return;
	}
	else
	{
		print "$filen is $filesize bytes\n";
	}

	my $searchstring = "google-analytics.com\/__utm.gif\?";
	my @hits = qx(grep -oba $searchstring $filen | cut -d \":" -f1); # launches grep and retrieves list of hit file offsets
	printf ("%d hits found\n", scalar(@hits));

	# Start parsing the input file ...
	open(my $filehandle, "<", $filen) || die("Unable to open $filen\n");
	binmode ($filehandle, ":raw");
	
	foreach my $hit (@hits)
	{
		#printf ("Hit found at offset 0x%X\n", $hit);
		my $count=0;
		my $endfound=0;
		my $urlstring="";
		my $char;

		# Find length of each url string / start at hit and continue until non-ascii value is seen
		while ( ($endfound ne 1) and ($count < $MAX_SZ_STRING) and ($hit+$count < $filesize) )
		{
			#grab next character and test if printable ascii
			seek($filehandle, $hit+$count, 0);
			read($filehandle, $char, 1);
			if ($char !~ /[[:print:]]/)
			{
				$endfound = 1; #bailout if not printable ascii
			}
			$urlstring .= $char;
			$count++;
		}

		# count should now equal length of URL string
		if ($count < $MAX_SZ_STRING)
		{
			#printf ("Hit at offset 0x%X has string length %d = %s\n", $hit, $count, $urlstring);
			#printf ("Hit at offset 0x%X has string length %d\n", $hit, $count);
			$STORAGE{$filen."_".$hit}[$FILENAME_IDX] = $filen;
			$STORAGE{$filen."_".$hit}[$OFFSET_IDX] = $hit;
			$STORAGE{$filen."_".$hit}[$URL_IDX] = $urlstring;
		}
		else 
		{
			printf ("UH-OH! The URL string at offset 0x%X appears to be too large! (>$MAX_SZ_STRING chars). Ignoring ...\n", $hit);
		}
	}
	close($filehandle);

}


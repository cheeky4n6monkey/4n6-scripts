#!/usr/bin/perl -w

# vmail-db-2-html.pl = Perl script to conjure up an HTML table from the contents 
# of an iPhone's voicemail.db SQLite database.
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
# v2012.12.28 Initial Version

#Note: This is what the voicemail.db schema is ...
#sqlite> .schema
#CREATE TABLE _SqliteDatabaseProperties (key TEXT, value TEXT, UNIQUE(key));
#CREATE TABLE voicemail (ROWID INTEGER PRIMARY KEY AUTOINCREMENT, remote_uid INTE
#GER, date INTEGER, token TEXT, sender TEXT, callback_num TEXT, duration INTEGER,
# expiration INTEGER, trashed_date INTEGER, flags INTEGER);
#CREATE INDEX date_index on voicemail(date);
#CREATE INDEX remote_uid_index on voicemail(remote_uid);
#sqlite>

use strict;
use DBI;
use HTML::QuickTable;
use Getopt::Long;
use File::Spec;
#use Data::Dump qw(dump);

my $version = "vmail-db-2-html.pl v2012.12.28";
my $CF_EPOCH_OFFSET = 978307200; # number of seconds from unix epoch until 1 jan 2001 00:00:00
my %results_hash = ();
my $numresults;

my $help = ''; # help flag
my $folder = "";
my $database = "";

GetOptions('help|h' => \$help,
	'f=s' => \$folder,
	'db=s' => \$database);

if ($help || ($database eq ""))
{
	print ("$version\n\n");
	print ("Perl script to conjure up an HTML table from the contents of an iPhone's voicemail.db SQLite database.\n"); 
	print ("\nUsage: vmail-db-2-html.pl [-h|help] [-db database] [-f folder]\n");
	print ("-h|help ........ Help (print this information). Does not run anything else.\n");
	print ("-db database ... SQLite database to extract voicemail data from.\n");
	print ("-f folder ...... Optional foldername containing the .amr files for linking. If not specified,\n"); 
	print ("the script assumes the .amr files are in the current directory.\n\n");
	print ("Example: vmail-db-2-html.pl -f heavy-breather/vmails -db voicemail.db\n\n");
	print ("The script will extract the voicemail data from voicemail.db and then\n");
	print ("write HTML links to the relevant .amr using the nominated directory (eg \"heavy-breather/vmails/1.amr\")\n");
	print ("The .amr files must be copied to the nominated directory before the link(s) will work.\n\n");
	exit;
}

# Open Database
my $db = DBI->connect("dbi:SQLite:dbname=$database","","") || die( "Unable to connect to database\n" );

print "\nNow Retrieving Voicemail data ...\n";

my $sth =  $db->prepare("SELECT rowid as Rowid, sender as Sender, datetime(date, 'unixepoch') AS Date, duration as 'Duration (secs)', rowid as Filename, trashed_date as 'Deleted Date' from voicemail ORDER BY rowid ASC");

$sth->execute();

print $sth->{NUM_OF_FIELDS}." fields will be returned\n";
PrintHeadings($sth);
PrintResults($sth);

#dump (%results_hash);

$numresults = $sth->rows;
if ($numresults == 0) 
{
    print "No Voicemails found!\n\n";
}
else
{	
	print "$numresults Rows returned\n"; 
}
$sth->finish;
$db->disconnect;

# Add Table headings to hash ("#" added to ensure it appears on 1st row after HTML::QuickTable sorts)
$results_hash{"#rowid"} = ['From', 'Date', 'Duration (secs)', 'Filename', 'Deleted Date'];

# now create HTML table ...
#timestamped output filename
my $htmloutputfile = "vmail-db-2-html-output-".time.".html";
open(my $html_output_file, ">".$htmloutputfile) || die("Unable to open $htmloutputfile for writing\n");

my $htmltable = HTML::QuickTable->new(border => 1, null => '-', labels => 'T');

print $html_output_file "<HTML>";
print $html_output_file $htmltable->render(\%results_hash);
print $html_output_file "<p><b>$numresults rows returned<\/b><\/p>";
print $html_output_file "<\/HTML>";
close($htmloutputfile);

print("\nPlease refer to \"$htmloutputfile\" for a clickable link output table\n\n");

exit;


sub PrintHeadings
{
	my $sth = shift;
	# Print field headings
	for (my $i = 0; $i <= $sth->{NUM_OF_FIELDS}-1; $i++)
	{
		if ($i == $sth->{NUM_OF_FIELDS} - 1)
		{
			print $sth->{NAME}->[$i]."\n"; #last item adds a newline char
		}
		else
		{	
			print $sth->{NAME}->[$i]." | ";
		}
	}
}

# Prints query results and also stores values in %results_hash
sub PrintResults
{
	my $sth = shift;
	my @rowarray;

	# Prints row by row / field by field
	while (@rowarray = $sth->fetchrow_array() )
	{
		for (my $i = 0; $i <= $sth->{NUM_OF_FIELDS}-1; $i++)
		{
			if ($i == $sth->{NUM_OF_FIELDS} - 1 )
			{
				# last field should be deleted date which has to be converted to Unix epoch
				my $deletedate = printCFTime($rowarray[$i]);
				print "$deletedate\n";
				push(@{$results_hash{$rowarray[0]}}, $deletedate);
			}
			elsif ($i == $sth->{NUM_OF_FIELDS} - 2 )
			{
				# 2nd last field should be filename ie [folder]\rowid.amr
				my $filename = sprintf("%s.amr", $rowarray[$i]); #eg 1.amr
				my $filepathname = $filename;
				if ($folder ne "")
				{
					$filepathname = File::Spec->catfile($folder, $filename); # eg crap/1.amr
				}
				print "$filename | ";
				my $urlfilename = sprintf("<A HREF=\"%s\">%s<\/A>", $filepathname, $filename);
				push(@{$results_hash{$rowarray[0]}}, $urlfilename);
			}
			else
			{
				if ($rowarray[$i])
				{
					print $rowarray[$i]." | ";
				}
				else
				{
					print " | "; # field returned could be UNDEFINED, just print separator
				}
				if ($i > 0)
				{
					push(@{$results_hash{$rowarray[0]}}, $rowarray[$i]);
				}
			}
		}
	}
}

# Takes CF Epoch time and adds the number of seconds from 1 Jan 1970 (Unix epoch base) until 1 Jan 2001
# We need to add this offset so we can use gmtime() which is based on Unix epoch
sub printCFTime
{
	my $inputCFTime = shift;
	if ($inputCFTime == 0)
	{
		return "0";
	}
	
	my $adjustedUnixTime = $CF_EPOCH_OFFSET+$inputCFTime;
	my ($sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst) = gmtime($adjustedUnixTime);
	
	return sprintf("%04d-%02d-%02d %02d:%02d:%02d", $year+1900, $mon+1, $mday, $hour, $min, $sec);
}

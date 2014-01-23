#!/usr/bin/perl -w

# exif2map.pl = Perl script to take the output of exiftool and conjure up a web link 
# to google maps if the image has stored GPS lat/long info.
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
# v2012.02.21 Initial Version
# v2012.05.24 Removed Image::ExifTool::Location dependency (deprecated in ActiveState Perl v5.12+)
#			  Added support for relative path names for -dir directories

# Issue: On Windows, figure out why Paths start with "\" but remaining separators use "/" ???
#		 This does not appear to affect functionality - it just looks weird

use strict;

use Image::ExifTool;
use Getopt::Long;
use HTML::QuickTable;
use File::Find;
use File::Spec;

# commented out for now - apparently File:Find can issue some weird warnings
#no warnings 'File::Find';

my $version = "exif2map.pl v2012.05.24";
my $help = ''; # help flag
my $htmloutput = ''; #html flag
my @filenames; # input files from -f flag
my @absfilenames; # absolute path version of @filenames
my @directories; # input directories from -dir flag (must use absolute paths)
my @absdirectories; # absolute path version of @directories

my %file_listing; # stored results

GetOptions('help|h' => \$help,
	'html' => \$htmloutput,
	'f=s@' => \@filenames,
	'dir=s@' => \@directories);

if ($help||(@filenames == 0 && @directories == 0))
{
	print("\n$version\n");
	print("Perl script to take the output of exiftool and conjure up a web link\n"); 
	print("to google maps if the image has stored GPS lat/long info.\n");

	print("\nUsage: exif2map.pl [-h|help] [-f filename] [-html]\n");
	print("-h|help .......... Help (print this information). Does not run anything else.\n");
	print("-f filename ...... File(s) to extract lat/long from\n");
	print("-dir directory ... Absolute/Relative path to folder containing file(s) to extract lat/long from\n");
	print("-html ............ Also output results as a timestamped html file in current directory\n");

	print("\nExample: exif2map.pl -f /cases/galloping-gonzo.jpg -f /cases/krazy-kermit.jpg");
	print("\nExample: exif2map.pl -f /cases/krazy-kermit.jpg -dir /cases/rockin-rowlf-pics/ -html\n\n");
	print("Note: Outputs results to command line and (if specified) to a timestamped html file\n");
	print("in the current directory (e.g. exif2map-output-TIMESTAMP.html)\n\n");
	
	exit;
}


# Main processing loop
print("\n$version\n");
 
# Process filenames specified using the -f flag first
# Handle non absolute paths
foreach my $file (@filenames)
{
	
	if (File::Spec->file_name_is_absolute($file))
	{
		push(@absfilenames, $file);
		print "$file uses an absolute path\n";
	}
	else
	{
		# create our own abs path using cwd + relative path given by user
		push(@absfilenames, File::Spec->rel2abs($file));
		print "Converting $file to an absolute path\n";
	}
}

if (@absfilenames)
{
	foreach my $name (@absfilenames)
	{
		ProcessFilename($name);
	}
}

# Process folders specified using the -dir flag
# Note: Will NOT follow symbolic links to files
# Handle non absolute paths
foreach my $dir (@directories)
{
	
	if (File::Spec->file_name_is_absolute($dir))
	{
		push(@absdirectories, $dir);
		print "$dir is an absolute path\n";
	}
	else
	{
		# create our own abs path using cwd + relative path given by user
		push(@absdirectories, File::Spec->rel2abs($dir));
		print "Converting $dir to an absolute path\n";
	}
}

if (@absdirectories)
{
	foreach my $absdir (@absdirectories)
	{
		print "Processing Directory = $absdir\n";
		find(\&ProcessDir, $absdir);
	}
}

# If html output required AND we have actually retrieved some data ...
if ( ($htmloutput) && (keys(%file_listing) > 0) )
{	
	#timestamped output filename
	my $htmloutputfile = "exif2map-output-".time.".html";

	open(my $html_output_file, ">".$htmloutputfile) || die("Unable to open $htmloutputfile for writing\n");

	my $htmltable = HTML::QuickTable->new(border => 1, labels => 1);

	# Added preceeding "/" to "Filename" so that the HTML::QuickTable sorting doesn't result in
	# the column headings being re-ordered after / below a filename beginning with a "\". 
	$file_listing{"/Filename"} = "GoogleMaps Link";

	print $html_output_file "<HTML>";
	print $html_output_file $htmltable->render(\%file_listing);
	print $html_output_file "<\/HTML>";

	close($htmloutputfile);
	print("\nPlease refer to \"$htmloutputfile\" for a clickable link output table\n\n");
}

sub ProcessFilename
{
	my $filename = shift;

	if (-e $filename) #file must exist
	{
		my $exif = Image::ExifTool->new();
		# Extract all info from existing image
		if ($exif->ExtractInfo($filename))
		{
			my @tags = $exif->GetFoundTags($filename);
			my $metainfo = $exif->GetInfo(\@tags);

			# Ensure all 4 GPS params are present 
			# ie GPSLatitude, GPSLatitudeRef, GPSLongitude, GPSLongitudeRef
			# The Ref values indicate North/South and East/West
			if (defined ${$metainfo}{"GPSLongitude"} and defined ${$metainfo}{"GPSLatitude"} and 
				defined ${$metainfo}{"GPSLongitudeRef"} and defined ${$metainfo}{"GPSLatitudeRef"})
			{
				my $lat = $exif->GetValue("GPSLatitude", "ValueConv");
				my $lon = $exif->GetValue("GPSLongitude", "ValueConv");

				print("\n$filename contains Lat: $lat, Long: $lon\n");
				print("URL: http://maps.google.com/maps?q=$lat,+$lon($filename)&iwloc=A&hl=en\n");
				if ($htmloutput) # save GoogleMaps URL to global hashmap indexed by filename
				{
					$file_listing{$filename} = "<A HREF = \"http://maps.google.com/maps?q=$lat,+$lon($filename)&iwloc=A&hl=en\"> http://maps.google.com/maps?q=$lat,+$lon($filename)&iwloc=A&hl=en</A>";
				}
				return 1;
			}
			else
			{
				print("\n$filename : No Location Info available!\n");
				return 0;
			}
		}
		else
		{
			print("\n$filename : Cannot Extract Info!\n");
			return 0;
		}
	}
	else
	{
		print("\n$filename does not exist!\n");
		return 0;
	}
}


sub ProcessDir
{
	# $File::Find::dir is the current directory name,
	# $_ is the current filename within that directory
	# $File::Find::name is the complete pathname to the file.
	my $filename = $File::Find::name; # should contain absolute path eg /cases/pics/krazy-kermit.jpg

	if (-f $filename) # must be a file not a directory name ...
	{
		my $exif = Image::ExifTool->new();
		# Extract all info from existing image
		if ($exif->ExtractInfo($filename))
		{
			my @tags = $exif->GetFoundTags($filename);
			my $metainfo = $exif->GetInfo(\@tags);

			# Ensure all 4 GPS params are present 
			# ie GPSLatitude, GPSLatitudeRef, GPSLongitude, GPSLongitudeRef
			# The Ref values indicate North/South and East/West
			if (defined ${$metainfo}{"GPSLongitude"} and defined ${$metainfo}{"GPSLatitude"} and 
				defined ${$metainfo}{"GPSLongitudeRef"} and defined ${$metainfo}{"GPSLatitudeRef"})
			{
				my $lat = $exif->GetValue("GPSLatitude", "ValueConv");
				my $lon = $exif->GetValue("GPSLongitude", "ValueConv");

				print("\n$filename contains Lat: $lat, Long: $lon\n");
				print("URL: http://maps.google.com/maps?q=$lat,+$lon($filename)&iwloc=A&hl=en\n");
				if ($htmloutput) # save GoogleMaps URL to global hashmap indexed by filename
				{
					$file_listing{$filename} = "<A HREF = \"http://maps.google.com/maps?q=$lat,+$lon($filename)&iwloc=A&hl=en\"> http://maps.google.com/maps?q=$lat,+$lon($filename)&iwloc=A&hl=en</A>";
				}
				return 1;
			}
			else
			{
				print("\n$filename : No Location Info available!\n");
				return 0;
			}
		}
		else
		{
			print("\n$filename : Cannot Extract Info!\n");
			return 0;
		}
	}
}


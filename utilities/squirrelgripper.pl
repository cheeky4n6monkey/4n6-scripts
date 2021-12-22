#!/usr/bin/perl -w

# SquirrelGripper = A Perl script to extract ExifTool metadata from a directory's files into an SQLite Database.
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
# v2012.04.18 Initial Version
# v2012.05.13 Added -newdb and -tagname fuctionality, added DEFAULT_FIELD_VALUE initialisation, 
#			removed Image::ExifTool::Location dependency, changed FileSize field to INT (no. bytes),
#			changed GPS Lat/Long/Alt to REAL
# v2012.05.16-ALPHA Added support for relative path names for -dir directories
# v2012.05.18 Corrected for changed ExifTool v8.90 tagnames eg "LastSavedBy" is now "LastModifiedBy" for .doc
# v2012.05.24 Changed Relative/Absolute path check to use File::Spec->file_name_is_absolute($dir)

# Issue: On Windows, figure out why Paths start with "\" but remaining separators use "/" ???
#		 This does not appear to affect functionality - it just looks weird

use strict;

use DBI;
use Image::ExifTool;
use Getopt::Long;
use File::Find;
use File::Spec;

my $version = "squirrelgripper.pl v2012.05.24";
my $help = 0; # help flag
my $newdb = 0; # create a new db flag
my $dbfile = ""; # sqlite database filename
my $caseref = ""; # case tag for all files
my $tagname = ""; # default tag for all files
my @directories; # input directory from -dir flag (must use absolute path)
my @absdirectories; # absolute path version of @directories

my $DEFAULT_FIELD_VALUE = "Not Present";
my $DEBUG = 0; # flag to print out retrieved metadata fields (in case ExifTool decides to change field names again)

GetOptions('help|h' => \$help,
	'newdb' => \$newdb,
	'db=s' => \$dbfile,
	'case=s' => \$caseref,
	'tag=s' => \$tagname,
	'dir=s@' => \@directories);

if ($help || @directories == 0 || $caseref eq "" || $dbfile eq "")
{
	print("\n$version\n");
	print("Perl script to extract ExifTool metadata from a directory's files into an existing SQLite Database\n"); 

	print("\nUsage: squirrelgripper.pl [-h|help] [-newdb] [-db database] [-case casetag] [-tag tagname] [-dir directory]\n");
	print("-h|help .......... Help (print this information). Does not run anything else.\n");
	print("-newdb ........... Creates a new SQLite Database using the -db name. WARNING: Deletes existing database.\n");
	print("-db database ..... SQLite Database filename to extract information to.\n");
	print("-case casetag .... Case Tag to apply to the files in the database.\n");
	print("-tag tagname ..... Optional Tag Name to apply to selected files in the database.\n");
	print("-dir directory ... Relative/Absolute Path to folder(s) containing files to extract metadata from\n");

	print("\nExample: squirrelgripper.pl -newdb -db nuts.sqlite -case 2012-04-18-caseA -tag fraud-docs -dir /cases/evidence1 -dir /cases/evidence2\n\n");
	exit;
}


# Main processing loop
print("\n$version\n");

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

foreach my $tmp (@absdirectories)
{
	print "Directory entry for processing = $tmp\n";
}

my $exiftool = Image::ExifTool->new();
$exiftool->Options(CoordFormat => '%.6f');
# CoordFormat q{%.6f}  eg 54.989667 N

# Create new DB if requested otherwise re-use existing one
if ($newdb)
{
	# Just to be safe, we delete the database file instead of just dropping the tables
	if (-d $dbfile)
	{
		print "$dbfile is a directory not a database file! Bailing out\n";
		exit;
	}
	elsif (-e $dbfile)
	{
		print "Database already exists - Deleting $dbfile before re-creating\n";
		unlink($dbfile) or die ("Unable to delete $dbfile - check write permissions\n");
	}

	my $dbh = DBI->connect("dbi:SQLite:dbname=$dbfile","","") || die( "Unable to create new database\n" );

	# Create blank tables
	$dbh->do("CREATE TABLE FileIndex (AbsFileName TEXT PRIMARY KEY, DateTimeMetaAdded TEXT, FileType TEXT, CaseRef TEXT, UserTag TEXT);");

	$dbh->do("CREATE TABLE XLSXFiles (AbsFileName TEXT PRIMARY KEY, HeadingPairs TEXT, MIMEType TEXT, FileType TEXT, Directory TEXT, ModifyDate TEXT, LastModifiedBy TEXT, Keywords TEXT, TitlesOfParts TEXT, Subject TEXT, Creator TEXT, FileName TEXT, CreateDate TEXT, FileModifyDate TEXT, Title TEXT,	Application TEXT, AppVersion TEXT, FileSize INT, Company TEXT, Description TEXT, ExifToolVersion TEXT);");

	$dbh->do("CREATE TABLE XLSFiles (AbsFileName TEXT PRIMARY KEY, HeadingPairs TEXT, LastModifiedBy TEXT, Keywords TEXT, Author TEXT, MIMEType TEXT, FileType TEXT, Subject TEXT, ExifToolVersion TEXT, Directory TEXT, FileName TEXT,	Comments TEXT, CreateDate TEXT,	FileModifyDate TEXT, Title TEXT, AppVersion TEXT, FileSize INT,	Company TEXT, Manager TEXT,	ModifyDate TEXT, Software TEXT,	Category TEXT, TitleOfParts TEXT);");

	$dbh->do("CREATE TABLE DOCXFiles (AbsFileName TEXT PRIMARY KEY, RevisionNumber TEXT, Paragraphs INT, MIMEType TEXT,	FileType TEXT, Pages INT, ExifToolVersion TEXT, Directory TEXT, TotalEditTime TEXT, ModifyDate TEXT, LastModifiedBy TEXT, Keywords TEXT, Subject TEXT, Creator TEXT, Words INT, FileName TEXT, CreateDate TEXT, FileModifyDate TEXT, Title TEXT, Lines INT, Application TEXT, AppVersion TEXT, Characters INT, FileSize INT, Company TEXT, Template TEXT, Description TEXT);");

	$dbh->do("CREATE TABLE DOCFiles (AbsFileName TEXT PRIMARY KEY, TotalEditTime TEXT, HeadingPairs TEXT, LastModifiedBy TEXT, Paragraphs INT, Keywords TEXT, Pages INT, Author TEXT, MIMEType TEXT, FileType TEXT, Subject TEXT, ExifToolVersion TEXT, Directory TEXT, Words INT, FileName TEXT, Comments TEXT, CreateDate TEXT, FileModifyDate TEXT, RevisionNumber INT, Title TEXT, Characters INT, Lines INT, AppVersion TEXT, FileSize INT, Company TEXT, Template TEXT, LastPrinted TEXT, ModifyDate TEXT, Software TEXT, TitleOfParts TEXT);");

	$dbh->do("CREATE TABLE PPTXFiles (AbsFileName TEXT PRIMARY KEY, MIMEType TEXT, ModifyDate TEXT, Words INT, Title TEXT, AppVersion TEXT, Company TEXT, Directory TEXT, LastModifiedBy TEXT, Keywords TEXT, TitleOfParts TEXT, Creator TEXT, CreateDate TEXT, FileModifyDate TEXT, Application TEXT, FileSize INT, Notes INT, Slides INT, RevisionNumber TEXT, FileType TEXT, TotalEditTime TEXT, HiddenSlides INT, HeadingPairs TEXT, Paragraphs INT, ExifToolVersion TEXT, Subject TEXT, FileName TEXT, Description TEXT, PresentationFormat TEXT);");

	$dbh->do("CREATE TABLE PPTFiles (AbsFileName TEXT PRIMARY KEY, HiddenSlides INT, TotalEditTime TEXT, HeadingPairs TEXT, LastModifiedBy TEXT, Paragraphs INT,	Bytes INT, Author TEXT, MIMEType TEXT, FileType TEXT, CurrentUser TEXT, ExifToolVersion TEXT, Directory TEXT, Words INT, FileName TEXT, CreateDate TEXT, FileModifyDate TEXT, RevisionNumber INT, Title TEXT, AppVersion TEXT, FileSize INT, Company TEXT, Notes INT, ModifyDate TEXT, Software TEXT, Slides INT, TitleOfParts TEXT, Template TEXT);");

	$dbh->do("CREATE TABLE PDFFiles (AbsFileName TEXT PRIMARY KEY, CreateDate TEXT, FileModifyDate TEXT, Title TEXT, DocumentID TEXT, PageCount INT, FileSize INT, Author TEXT, MIMEType TEXT, PDFVersion TEXT, Subject TEXT, FileType TEXT, Creator TEXT, ExifToolVersion TEXT, ModifyDate TEXT, Directory TEXT, FileName TEXT, Producer TEXT,	CreatorTool TEXT);");

	$dbh->do("CREATE TABLE JPEGFiles (AbsFileName TEXT PRIMARY KEY, MIMEType TEXT, FileType TEXT, DateTimeOriginal TEXT, ModifyDate TEXT, GPSLongitude REAL, GPSLatitude REAL, GPSLongitudeRef TEXT, GPSLatitudeRef TEXT,	GPSAltitude REAL, GPSAltitudeRef TEXT, UserComment TEXT, GPSPosition TEXT, Model TEXT, ExifToolVersion TEXT,	Directory TEXT,	Make TEXT, ImageSize TEXT, ImageHeight INT,	ImageWidth INT,	FileNumber TEXT, Comment TEXT, FileName TEXT, CreateDate TEXT, FileModifyDate TEXT, FileSize INT, OwnerName TEXT, ImageUniqueID TEXT);");

	$dbh->disconnect();
}

# Open Database (might be just have been created above or from a previous script launch)
my $db = DBI->connect("dbi:SQLite:dbname=$dbfile","","") || die( "Unable to connect to database\n" );
my $sth;

# Look at the directory given and process each file
# Process folders specified using the -dir flag
# Note: Will NOT follow symbolic links to files
if (@absdirectories)
{
	find(\&ProcessDir, @absdirectories);
}

$db->disconnect;
# End of Main program

# Function definitions
sub ProcessDir
{
	# $File::Find::dir is the current directory name,
	# $_ is the current filename within that directory
	# $File::Find::name is the complete pathname to the file.
	my $filename = $File::Find::name; # should contain absolute path eg /cases/pics/krazy-kermit.jpg

	if (-f $filename) # must be a file not a directory name ...
	{
		print "\nNow processing $filename\n";
		# Extract all info from existing image
		if ($exiftool->ExtractInfo($filename))
		{
			my @tags = $exiftool->GetFoundTags($filename);

			my $type = $exiftool->GetValue("FileType");

			# get information for all tags returned
			# $info is a reference to a hash
    		my $info = $exiftool->GetInfo(\@tags);

			if ($type eq "XLSX")
			{
				ProcessXLSX($info, \$filename);
			}
			elsif ($type eq "XLS")
			{
				ProcessXLS($info, \$filename);
			}
			elsif ($type eq "DOCX")
			{
				ProcessDOCX($info, \$filename);
			}
			elsif ($type eq "DOC")
			{
				ProcessDOC($info, \$filename);
			}
			elsif ($type eq "PPTX")
			{
				ProcessPPTX($info, \$filename);
			}
			elsif ($type eq "PPT")
			{
				ProcessPPT($info, \$filename);
			}
			elsif ($type eq "PDF")
			{
				ProcessPDF($info, \$filename);
			}
			elsif ($type eq "JPEG")
			{
				ProcessJPEG($info, \$filename);
			}
			else
			{
				print "Cannot process FileType = $type\n";
			}
		}
		else
		{
			print("\n$filename : Cannot Extract Info!\n");
			return 0;
		}
	}
}


sub ProcessXLSX
{
	my $metainfo = shift;
	my $filename = shift;

	if ($DEBUG)
	{
		print "ProcessXLSX called\n";
		for my $key (keys %{$metainfo})
		{
			print "key = $key, value = ".${$metainfo}{$key}."\n";
		}
	}

	# Convert dates into an SQLite readable format
	my $moddate = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"ModifyDate"}) { FormatUTCDate(\${$metainfo}{"ModifyDate"}, \$moddate); }
	my $filemoddate = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"FileModifyDate"}) { FormatUTCDate(\${$metainfo}{"FileModifyDate"}, \$filemoddate); }
	my $createdate = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"CreateDate"}) { FormatUTCDate(\${$metainfo}{"CreateDate"}, \$createdate); }

	# Insert file entry in FileIndex table
	$sth =  $db->prepare_cached("REPLACE INTO FileIndex (AbsFileName, DateTimeMetaAdded, FileType, CaseRef, UserTag) VALUES (?, datetime('now'), ?, ?, ?)"); # or print "Could not prepare FileIndex INSERT: ".$db->errstr;

	# if we got to this function, "FileType" must have been defined/read OK already	
	if ($sth->execute(${$filename}, ${$metainfo}{"FileType"}, $caseref, $tagname))
	{
		print ${$filename}." inserted into FileIndex table\n";
	}
	else
	{
		print "Could not INSERT ".${$filename}." into FileIndex: ".$sth->errstr."\n";
	}
	
	# Initialise field variables before insertion
	my $headingpairs = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"HeadingPairs"}) { $headingpairs = ${$metainfo}{"HeadingPairs"}; }
	my $mimetype = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"MIMEType"}) { $mimetype = ${$metainfo}{"MIMEType"}; }
	my $directory = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Directory"}) { $directory = ${$metainfo}{"Directory"}; }
	my $lastmodifiedby = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"LastModifiedBy"}) { $lastmodifiedby = ${$metainfo}{"LastModifiedBy"}; }
	my $keywords = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Keywords"}) { $keywords = ${$metainfo}{"Keywords"}; }
	my $titlesofparts = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"TitlesOfParts"}) { $titlesofparts = ${$metainfo}{"TitlesOfParts"}; }
	my $subject = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Subject"}) { $subject = ${$metainfo}{"Subject"}; }
	my $creator = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Creator"}) { $creator = ${$metainfo}{"Creator"}; }
	my $xfilename = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"FileName"}) { $xfilename = ${$metainfo}{"FileName"}; }
	my $title = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Title"}) { $title = ${$metainfo}{"Title"}; }
	my $application = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Application"}) { $application = ${$metainfo}{"Application"}; }
	my $appversion = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"AppVersion"}) { $appversion = ${$metainfo}{"AppVersion"}; }
	my $filesize = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"FileSize"}) { $filesize = $exiftool->GetValue("FileSize", "ValueConv"); }
	my $company = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Company"}) { $company = ${$metainfo}{"Company"}; }
	my $description = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Description"}) { $description = ${$metainfo}{"Description"}; }
	my $exiftoolversion = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"ExifToolVersion"}) { $exiftoolversion = ${$metainfo}{"ExifToolVersion"}; }

	# Insert extracted metadata in XLSXFiles table (where available)
	$sth =  $db->prepare_cached("REPLACE INTO XLSXFiles (AbsFileName, HeadingPairs, MIMEType, FileType, Directory, ModifyDate, LastModifiedBy, Keywords, TitlesOfParts, Subject, Creator, FileName, CreateDate, FileModifyDate, Title, Application, AppVersion, FileSize, Company, Description, ExifToolVersion) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"); # or print "Could not Prepare for XLSXFiles INSERT: ".$db->errstr;

	if ($sth->execute(${$filename}, 
					$headingpairs, $mimetype, ${$metainfo}{"FileType"}, 
					$directory, $moddate, $lastmodifiedby, 
					$keywords, $titlesofparts, $subject, 
					$creator, $xfilename, $createdate, 
					$filemoddate, $title, $application, 
					$appversion, $filesize, $company, 
					$description, $exiftoolversion) )
	{
		print ${$filename}." inserted into XLSXFiles table\n";
	}
	else
	{
		print "Could not INSERT ".${$filename}." into XLSXFiles: ".$sth->errstr."\n";
	}

	$sth->finish;
}

sub	ProcessXLS
{
	my $metainfo = shift;
	my $filename = shift;

	if ($DEBUG)
	{
		print "ProcessXLS called\n";
		for my $key (keys %{$metainfo})
		{
			print "key = $key, value = ".${$metainfo}{$key}."\n";
		}
	}

	# Convert dates into an SQLite readable format
	my $moddate = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"ModifyDate"}) { FormatUTCDate(\${$metainfo}{"ModifyDate"}, \$moddate); }
	my $filemoddate = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"FileModifyDate"}) { FormatUTCDate(\${$metainfo}{"FileModifyDate"}, \$filemoddate); }
	my $createdate = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"CreateDate"}) { FormatUTCDate(\${$metainfo}{"CreateDate"}, \$createdate); }

	# Insert file entry in FileIndex table
	$sth =  $db->prepare_cached("REPLACE INTO FileIndex (AbsFileName, DateTimeMetaAdded, FileType, CaseRef, UserTag) VALUES (?, datetime('now'), ?, ?, ?)"); # or print "Could not prepare FileIndex INSERT: ".$db->errstr;

	# if we got to this function, "FileType" must have been defined/read OK already	
	if ($sth->execute(${$filename}, ${$metainfo}{"FileType"}, $caseref, $tagname))
	{
		print ${$filename}." inserted into FileIndex table\n";
	}
	else
	{
		print "Could not INSERT ".${$filename}." into FileIndex: ".$sth->errstr."\n";
	}
	
	# Initialise field variables before insertion
	my $headingpairs = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"HeadingPairs"}) { $headingpairs = ${$metainfo}{"HeadingPairs"}; }
	my $lastmodifiedby = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"LastModifiedBy"}) { $lastmodifiedby = ${$metainfo}{"LastModifiedBy"}; } # used to be LastSavedBy for ExifTool v8.10
	my $keywords = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Keywords"}) { $keywords = ${$metainfo}{"Keywords"}; }
	my $author = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Author"}) { $author = ${$metainfo}{"Author"}; }
	my $mimetype = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"MIMEType"}) { $mimetype = ${$metainfo}{"MIMEType"}; }
	my $subject = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Subject"}) { $subject = ${$metainfo}{"Subject"}; }
	my $exiftoolversion = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"ExifToolVersion"}) { $exiftoolversion = ${$metainfo}{"ExifToolVersion"}; }
	my $directory = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Directory"}) { $directory = ${$metainfo}{"Directory"}; }
	my $xfilename = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"FileName"}) { $xfilename = ${$metainfo}{"FileName"}; }
	my $comments = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Comments"}) { $comments = ${$metainfo}{"Comments"}; }
	my $title = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Title"}) { $title = ${$metainfo}{"Title"}; }
	my $appversion = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"AppVersion"}) { $appversion = ${$metainfo}{"AppVersion"}; }
	my $filesize = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"FileSize"}) { $filesize = $exiftool->GetValue("FileSize", "ValueConv"); }
	my $company = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Company"}) { $company = ${$metainfo}{"Company"}; }
	my $manager = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Manager"}) { $manager = ${$metainfo}{"Manager"}; }
	my $software = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Software"}) { $software = ${$metainfo}{"Software"}; }
	my $category = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Category"}) { $category = ${$metainfo}{"Category"}; }
	my $titleofparts = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"TitleOfParts"}) { $titleofparts = ${$metainfo}{"TitleOfParts"}; }

	# Insert actual metadata in XLSFiles table
	$sth =  $db->prepare_cached("REPLACE INTO XLSFiles (AbsFileName, HeadingPairs, LastModifiedBy, Keywords, Author, MIMEType, FileType, Subject, ExifToolVersion, Directory, FileName, Comments, CreateDate, FileModifyDate, Title, AppVersion, FileSize, Company, Manager, ModifyDate, Software, Category, TitleOfParts) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"); # or print "Could not Prepare for XLSFiles INSERT: ".$db->errstr;

	if ($sth->execute(${$filename}, 
					$headingpairs, $lastmodifiedby, $keywords, 
					$author, $mimetype, ${$metainfo}{"FileType"}, 
					$subject, $exiftoolversion, $directory, 
					$xfilename, $comments, $createdate, 
					$filemoddate, $title, $appversion, 
					$filesize, $company, $manager, 
					$moddate, $software, $category, 
					$titleofparts) )
	{
		print ${$filename}." inserted into XLSFiles table\n";
	}
	else
	{
		print "Could not INSERT ".${$filename}." into XLSFiles: ".$sth->errstr."\n";
	}

	$sth->finish;
}

sub ProcessDOCX
{
	my $metainfo = shift;
	my $filename = shift;
	
	if ($DEBUG)
	{
		print "ProcessDOCX called\n";
		for my $key (keys %{$metainfo})
		{
			print "key = $key, value = ".${$metainfo}{$key}."\n";
		}
	}

	# Convert dates into an SQLite readable format
	my $moddate = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"ModifyDate"}) { FormatUTCDate(\${$metainfo}{"ModifyDate"}, \$moddate); }
	my $filemoddate = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"FileModifyDate"}) { FormatUTCDate(\${$metainfo}{"FileModifyDate"}, \$filemoddate); }
	my $createdate = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"CreateDate"}) { FormatUTCDate(\${$metainfo}{"CreateDate"}, \$createdate); }

	# Insert file entry in FileIndex table
	$sth =  $db->prepare_cached("REPLACE INTO FileIndex (AbsFileName, DateTimeMetaAdded, FileType, CaseRef, UserTag) VALUES (?, datetime('now'), ?, ?, ?)"); # or print "Could not prepare FileIndex INSERT: ".$db->errstr;
	
	# if we got to this function, "FileType" must have been defined/read OK already	
	if ($sth->execute(${$filename}, ${$metainfo}{"FileType"}, $caseref, $tagname))
	{
		print ${$filename}." inserted into FileIndex table\n";
	}
	else
	{
		print "Could not INSERT ".${$filename}." into FileIndex: ".$sth->errstr."\n";
	}

	# Initialise field variables before insertion
	my $revision = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"RevisionNumber"}) { $revision = ${$metainfo}{"RevisionNumber"}; } # used to be "Revision" for ExifTool v8.10
	my $paragraphs = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Paragraphs"}) { $paragraphs = ${$metainfo}{"Paragraphs"}; }
	my $mimetype = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"MIMEType"}) { $mimetype = ${$metainfo}{"MIMEType"}; }
	my $pages = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Pages"}) { $pages = ${$metainfo}{"Pages"}; }
	my $exiftoolversion = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"ExifToolVersion"}) { $exiftoolversion = ${$metainfo}{"ExifToolVersion"}; }
	my $directory = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Directory"}) { $directory = ${$metainfo}{"Directory"}; }
	my $totaledittime = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"TotalEditTime"}) { $totaledittime = ${$metainfo}{"TotalEditTime"}; } # used to be "TotalTime" for ExifTool v8.10
	my $lastmodifiedby = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"LastModifiedBy"}) { $lastmodifiedby = ${$metainfo}{"LastModifiedBy"}; }
	my $keywords = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Keywords"}) { $keywords = ${$metainfo}{"Keywords"}; }
	my $subject = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Subject"}) { $subject = ${$metainfo}{"Subject"}; }
	my $creator = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Creator"}) { $creator = ${$metainfo}{"Creator"}; }
	my $words = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Words"}) { $words = ${$metainfo}{"Words"}; }
	my $xfilename = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"FileName"}) { $xfilename = ${$metainfo}{"FileName"}; }
	my $title = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Title"}) { $title = ${$metainfo}{"Title"}; }
	my $lines = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Lines"}) { $lines = ${$metainfo}{"Lines"}; }
	my $application = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Application"}) { $application = ${$metainfo}{"Application"}; }
	my $appversion = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"AppVersion"}) { $appversion = ${$metainfo}{"AppVersion"}; }
	my $characters = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Characters"}) { $characters = ${$metainfo}{"Characters"}; }
	my $filesize = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"FileSize"}) { $filesize = $exiftool->GetValue("FileSize", "ValueConv"); }
	my $company = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Company"}) { $company = ${$metainfo}{"Company"}; }
	my $template = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Template"}) { $template = ${$metainfo}{"Template"}; }
	my $description = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Description"}) { $description = ${$metainfo}{"Description"}; }

	# Insert actual metadata in DOCXFiles table
	$sth =  $db->prepare_cached("REPLACE INTO DOCXFiles (AbsFileName, RevisionNumber, Paragraphs, MIMEType, FileType, Pages, ExifToolVersion, Directory, TotalEditTime, ModifyDate, LastModifiedBy, Keywords, Subject, Creator, Words, FileName, CreateDate, FileModifyDate, Title,	Lines, Application,	AppVersion,
Characters, FileSize, Company, Template, Description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"); # or print "Could not Prepare for DOCXFiles INSERT: ".$db->errstr;

	if ($sth->execute(${$filename}, 
					$revision, $paragraphs, $mimetype, 
					${$metainfo}{"FileType"}, $pages, $exiftoolversion, 
					$directory, $totaledittime, $moddate, 
					$lastmodifiedby, $keywords, $subject, 
					$creator, $words, $xfilename, 
					$createdate, $filemoddate, $title, 
					$lines, $application, $appversion, 
					$characters, $filesize, $company, 
					$template, $description) )
	{
		print ${$filename}." inserted into DOCXFiles table\n";
	}
	else
	{
		print "Could not INSERT ".${$filename}." into DOCXFiles: ".$sth->errstr."\n";
	}

	$sth->finish;
}

sub ProcessDOC
{
	my $metainfo = shift;
	my $filename = shift;

	if ($DEBUG)
	{
		print "ProcessDOC called\n";
		for my $key (keys %{$metainfo})
		{
			print "key = $key, value = ".${$metainfo}{$key}."\n";
		}
	}

	# Convert dates into an SQLite readable format
	my $moddate = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"ModifyDate"}) { FormatUTCDate(\${$metainfo}{"ModifyDate"}, \$moddate); }
	my $filemoddate = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"FileModifyDate"}) { FormatUTCDate(\${$metainfo}{"FileModifyDate"}, \$filemoddate); }
	my $createdate = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"CreateDate"}) { FormatUTCDate(\${$metainfo}{"CreateDate"}, \$createdate); }
	my $lastprinteddate = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"LastPrinted"}) { FormatUTCDate(\${$metainfo}{"LastPrinted"}, \$lastprinteddate); }

	# Insert file entry in FileIndex table
	$sth =  $db->prepare_cached("REPLACE INTO FileIndex (AbsFileName, DateTimeMetaAdded, FileType, CaseRef, UserTag) VALUES (?, datetime('now'), ?, ?, ?)"); # or print "Could not prepare FileIndex INSERT: ".$db->errstr;
	
	# if we got to this function, "FileType" must have been defined/read OK already	
	if ($sth->execute(${$filename}, ${$metainfo}{"FileType"}, $caseref, $tagname))
	{
		print ${$filename}." inserted into FileIndex table\n";
	}
	else
	{
		print "Could not INSERT ".${$filename}." into FileIndex: ".$sth->errstr."\n";
	}

	# Initialise field variables before insertion
	my $totaledittime = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"TotalEditTime"}) { $totaledittime = ${$metainfo}{"TotalEditTime"}; }
	my $headingpairs = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"HeadingPairs"}) { $headingpairs = ${$metainfo}{"HeadingPairs"}; }
	my $lastmodifiedby = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"LastModifiedBy"}) { $lastmodifiedby = ${$metainfo}{"LastModifiedBy"}; } # used to be "LastSavedBy" for ExifTool v8.10
	my $paragraphs = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Paragraphs"}) { $paragraphs = ${$metainfo}{"Paragraphs"}; }
	my $keywords = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Keywords"}) { $keywords = ${$metainfo}{"Keywords"}; }
	my $pages = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Pages"}) { $pages = ${$metainfo}{"Pages"}; } # used to be "PageCount" for ExifTool v8.10
	my $author = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Author"}) { $author = ${$metainfo}{"Author"}; }
	my $mimetype = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"MIMEType"}) { $mimetype = ${$metainfo}{"MIMEType"}; }
	my $subject = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Subject"}) { $subject = ${$metainfo}{"Subject"}; }
	my $exiftoolversion = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"ExifToolVersion"}) { $exiftoolversion = ${$metainfo}{"ExifToolVersion"}; }
	my $directory = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Directory"}) { $directory = ${$metainfo}{"Directory"}; }
	my $words = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Words"}) { $words = ${$metainfo}{"Words"}; } # used to be "WordCount" for ExifTool v8.10
	my $xfilename = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"FileName"}) { $xfilename = ${$metainfo}{"FileName"}; }
	my $comments = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Comments"}) { $comments = ${$metainfo}{"Comments"}; }
	my $revisionnumber = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"RevisionNumber"}) { $revisionnumber = ${$metainfo}{"RevisionNumber"}; }
	my $title = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Title"}) { $title = ${$metainfo}{"Title"}; }
	my $characters = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Characters"}) { $characters = ${$metainfo}{"Characters"}; } # used to be "CharCount" for ExifTool v8.10
	my $lines = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Lines"}) { $lines = ${$metainfo}{"Lines"}; }
	my $appversion = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"AppVersion"}) { $appversion = ${$metainfo}{"AppVersion"}; }
	my $filesize = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"FileSize"}) { $filesize = $exiftool->GetValue("FileSize", "ValueConv"); }
	my $company = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Company"}) { $company = ${$metainfo}{"Company"}; }
	my $template = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Template"}) { $template = ${$metainfo}{"Template"}; }
	my $software = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Software"}) { $software = ${$metainfo}{"Software"}; }
	my $titleofparts = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"TitleOfParts"}) { $titleofparts = ${$metainfo}{"TitleOfParts"}; }
	
	# Insert actual metadata in DOCFiles table
	$sth =  $db->prepare_cached("REPLACE INTO DOCFiles (AbsFileName, TotalEditTime,	HeadingPairs, LastModifiedBy, Paragraphs, Keywords, Pages, Author,	MIMEType, FileType,	Subject, ExifToolVersion, Directory, Words,	FileName, Comments,	CreateDate, FileModifyDate,	RevisionNumber,	Title, Characters, Lines, AppVersion, FileSize, Company, Template, LastPrinted, ModifyDate, Software, TitleOfParts) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"); # or print "Could not Prepare for DOCFiles INSERT: ".$db->errstr;

	if ($sth->execute(${$filename}, 
					$totaledittime, $headingpairs, $lastmodifiedby, 
					$paragraphs, $keywords, $pages, 
					$author, $mimetype, ${$metainfo}{"FileType"},
					$subject, $exiftoolversion, $directory,
					$words, $xfilename, $comments,
					$createdate, $filemoddate, $revisionnumber, 
					$title, $characters, $lines, 
					$appversion, $filesize, $company, 
					$template, $lastprinteddate, $moddate, 
					$software, $titleofparts) )
	{
		print ${$filename}." inserted into DOCFiles table\n";
	}
	else
	{
		print "Could not INSERT ".${$filename}." into DOCFiles: ".$sth->errstr."\n";
	}

	$sth->finish;
}

sub ProcessPPTX
{
	my $metainfo = shift;
	my $filename = shift;

	if ($DEBUG)
	{
		print "ProcessPPTX called\n";
		for my $key (keys %{$metainfo})
		{
			print "key = $key, value = ".${$metainfo}{$key}."\n";
		}
	}

	# Convert dates into an SQLite readable format
	my $moddate = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"ModifyDate"}) { FormatUTCDate(\${$metainfo}{"ModifyDate"}, \$moddate); }
	my $filemoddate = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"FileModifyDate"}) { FormatUTCDate(\${$metainfo}{"FileModifyDate"}, \$filemoddate); }
	my $createdate = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"CreateDate"}) { FormatUTCDate(\${$metainfo}{"CreateDate"}, \$createdate); }

	# Insert file entry in FileIndex table
	$sth =  $db->prepare_cached("REPLACE INTO FileIndex (AbsFileName, DateTimeMetaAdded, FileType, CaseRef, UserTag) VALUES (?, datetime('now'), ?, ?, ?)"); # or print "Could not prepare FileIndex INSERT: ".$db->errstr;
	
	# if we got to this function, "FileType" must have been defined/read OK already	
	if ($sth->execute(${$filename}, ${$metainfo}{"FileType"}, $caseref, $tagname))
	{
		print ${$filename}." inserted into FileIndex table\n";
	}
	else
	{
		print "Could not INSERT ".${$filename}." into FileIndex: ".$sth->errstr."\n";
	}
	
	# Initialise field variables before insertion
	my $mimetype = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"MIMEType"}) { $mimetype = ${$metainfo}{"MIMEType"}; }
	my $words = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Words"}) { $words = ${$metainfo}{"Words"}; }
	my $title = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Title"}) { $title = ${$metainfo}{"Title"}; }
	my $appversion = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"AppVersion"}) { $appversion = ${$metainfo}{"AppVersion"}; }
	my $company = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Company"}) { $company = ${$metainfo}{"Company"}; }
	my $directory = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Directory"}) { $directory = ${$metainfo}{"Directory"}; }
	my $lastmodifiedby = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"LastModifiedBy"}) { $lastmodifiedby = ${$metainfo}{"LastModifiedBy"}; }
	my $keywords = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Keywords"}) { $keywords = ${$metainfo}{"Keywords"}; }
	my $titleofparts = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"TitleOfParts"}) { $titleofparts = ${$metainfo}{"TitleOfParts"}; }
	my $creator = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Creator"}) { $creator = ${$metainfo}{"Creator"}; }
	my $application = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Application"}) { $application = ${$metainfo}{"Application"}; }
	my $filesize = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"FileSize"}) { $filesize = $exiftool->GetValue("FileSize", "ValueConv"); }
	my $notes = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Notes"}) { $notes = ${$metainfo}{"Notes"}; }
	my $slides = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Slides"}) { $slides = ${$metainfo}{"Slides"}; }
	my $revision = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"RevisionNumber"}) { $revision = ${$metainfo}{"RevisionNumber"}; } # used to be "Revision" for ExifTool v8.10
	my $totaledittime = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"TotalEditTime"}) { $totaledittime = ${$metainfo}{"TotalEditTime"}; } # used to be "TotalTime" for ExifTool v8.10
	my $hiddenslides = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"HiddenSlides"}) { $hiddenslides = ${$metainfo}{"HiddenSlides"}; }
	my $headingpairs = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"HeadingPairs"}) { $headingpairs = ${$metainfo}{"HeadingPairs"}; }
	my $paragraphs = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Paragraphs"}) { $paragraphs = ${$metainfo}{"Paragraphs"}; }
	my $exiftoolversion = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"ExifToolVersion"}) { $exiftoolversion = ${$metainfo}{"ExifToolVersion"}; }
	my $subject = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Subject"}) { $subject = ${$metainfo}{"Subject"}; }
	my $xfilename = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"FileName"}) { $xfilename = ${$metainfo}{"FileName"}; }
	my $description = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Description"}) { $description = ${$metainfo}{"Description"}; }
	my $presentationformat = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"PresentationFormat"}) { $presentationformat = ${$metainfo}{"PresentationFormat"}; }

	# Insert actual metadata in PPTXFiles table
	$sth =  $db->prepare_cached("REPLACE INTO PPTXFiles (AbsFileName, MIMEType, ModifyDate, Words, Title, AppVersion, Company, Directory, LastModifiedBy,	Keywords, TitleOfParts,	Creator, CreateDate, FileModifyDate, Application, FileSize, Notes, Slides, RevisionNumber, FileType, TotalEditTime, HiddenSlides, HeadingPairs, Paragraphs, ExifToolVersion, Subject, FileName, Description, PresentationFormat) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"); # or print "Could not Prepare for PPTXFiles INSERT: ".$db->errstr;

	if ($sth->execute(${$filename}, 
					$mimetype, $moddate, $words, 
					$title, $appversion, $company, 
					$directory, $lastmodifiedby, $keywords, 
					$titleofparts, $creator, $createdate, 
					$filemoddate, $application, $filesize,  
					$notes, $slides, $revision, 
					${$metainfo}{"FileType"}, $totaledittime, $hiddenslides, 
					$headingpairs, $paragraphs, $exiftoolversion,
					$subject, $xfilename, $description, $presentationformat) )
	{
		print ${$filename}." inserted into PPTXFiles table\n";
	}
	else
	{
		print "Could not INSERT ".${$filename}." into PPTXFiles: ".$sth->errstr."\n";
	}

	$sth->finish;
}

sub	ProcessPPT
{
	my $metainfo = shift;
	my $filename = shift;

	if ($DEBUG)
	{
		print "ProcessPPT called\n";
		for my $key (keys %{$metainfo})
		{
			print "key = $key, value = ".${$metainfo}{$key}."\n";
		}
	}

	# Convert dates into an SQLite readable format
	my $moddate = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"ModifyDate"}) { FormatUTCDate(\${$metainfo}{"ModifyDate"}, \$moddate); }
	my $filemoddate = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"FileModifyDate"}) { FormatUTCDate(\${$metainfo}{"FileModifyDate"}, \$filemoddate); }
	my $createdate = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"CreateDate"}) { FormatUTCDate(\${$metainfo}{"CreateDate"}, \$createdate); }

	# Insert file entry in FileIndex table
	$sth =  $db->prepare_cached("REPLACE INTO FileIndex (AbsFileName, DateTimeMetaAdded, FileType, CaseRef, UserTag) VALUES (?, datetime('now'), ?, ?, ?)"); # or print "Could not prepare FileIndex INSERT: ".$db->errstr;
	
	# if we got to this function, "FileType" must have been defined/read OK already	
	if ($sth->execute(${$filename}, ${$metainfo}{"FileType"}, $caseref, $tagname))
	{
		print ${$filename}." inserted into FileIndex table\n";
	}
	else
	{
		print "Could not INSERT ".${$filename}." into FileIndex: ".$sth->errstr."\n";
	}
	
	# Initialise field variables before insertion
	my $hiddenslides = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"HiddenSlides"}) { $hiddenslides = ${$metainfo}{"HiddenSlides"}; }
	my $totaledittime = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"TotalEditTime"}) { $totaledittime = ${$metainfo}{"TotalEditTime"}; }
	my $headingpairs = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"HeadingPairs"}) { $headingpairs = ${$metainfo}{"HeadingPairs"}; }
	my $lastmodifiedby = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"LastModifiedBy"}) { $lastmodifiedby = ${$metainfo}{"LastModifiedBy"}; } # used to be "LastSavedBy" for ExifTool v8.10
	my $paragraphs = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Paragraphs"}) { $paragraphs = ${$metainfo}{"Paragraphs"}; }
	my $bytes = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Bytes"}) { $bytes = ${$metainfo}{"Bytes"}; }
	my $author = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Author"}) { $author = ${$metainfo}{"Author"}; }
	my $mimetype = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"MIMEType"}) { $mimetype = ${$metainfo}{"MIMEType"}; }
	my $currentuser = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"CurrentUser"}) { $currentuser = ${$metainfo}{"CurrentUser"}; }
	my $exiftoolversion = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"ExifToolVersion"}) { $exiftoolversion = ${$metainfo}{"ExifToolVersion"}; }
	my $directory = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Directory"}) { $directory = ${$metainfo}{"Directory"}; }
	my $words = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Words"}) { $words = ${$metainfo}{"Words"}; } # used to be "WordCount" for ExifTool v8.10
	my $xfilename = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"FileName"}) { $xfilename = ${$metainfo}{"FileName"}; }
	my $revisionnumber = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"RevisionNumber"}) { $revisionnumber = ${$metainfo}{"RevisionNumber"}; }
	my $title = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Title"}) { $title = ${$metainfo}{"Title"}; }
	my $appversion = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"AppVersion"}) { $appversion = ${$metainfo}{"AppVersion"}; }
	my $filesize = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"FileSize"}) { $filesize = $exiftool->GetValue("FileSize", "ValueConv"); }
	my $company = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Company"}) { $company = ${$metainfo}{"Company"}; }
	my $notes = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Notes"}) { $notes = ${$metainfo}{"Notes"}; }
	my $software = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Software"}) { $software = ${$metainfo}{"Software"}; }
	my $slides = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Slides"}) { $slides = ${$metainfo}{"Slides"}; }
	my $titleofparts = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"TitleOfParts"}) { $titleofparts = ${$metainfo}{"TitleOfParts"}; }
	my $template = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Template"}) { $template = ${$metainfo}{"Template"}; }

	# Insert actual metadata in PPTFiles table
	$sth =  $db->prepare_cached("REPLACE INTO PPTFiles (AbsFileName, HiddenSlides, TotalEditTime, HeadingPairs,	LastModifiedBy, Paragraphs, Bytes,	Author, MIMEType, FileType,	CurrentUser, ExifToolVersion, Directory, Words, FileName, CreateDate, FileModifyDate, RevisionNumber, Title, AppVersion,	FileSize, Company, Notes, ModifyDate, Software, Slides,	TitleOfParts, Template) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"); # or print "Could not Prepare for PPTFiles INSERT: ".$db->errstr;
  
	if ($sth->execute(${$filename}, 
					$hiddenslides, $totaledittime, $headingpairs, 
					$lastmodifiedby, $paragraphs, $bytes, 
					$author, $mimetype, ${$metainfo}{"FileType"},
					$currentuser, $exiftoolversion, $directory, 
					$words, $xfilename, $createdate,
					$filemoddate, $revisionnumber, $title, 
					$appversion, $filesize, $company, 
					$notes, $moddate, $software, 
					$slides, $titleofparts, $template) )
	{
		print ${$filename}." inserted into PPTFiles table\n";
	}
	else
	{
		print "Could not INSERT ".${$filename}." into PPTFiles: ".$sth->errstr."\n";
	}

	$sth->finish;
}

sub ProcessPDF
{
	my $metainfo = shift;
	my $filename = shift;

	if ($DEBUG)
	{
		print "ProcessPDF called\n";
		for my $key (keys %{$metainfo})
		{
			print "key = $key, value = ".${$metainfo}{$key}."\n";
		}
	}

	# Convert dates into an SQLite readable format
	my $moddate = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"ModifyDate"}) { FormatUTCDate(\${$metainfo}{"ModifyDate"}, \$moddate); }
	my $filemoddate = $DEFAULT_FIELD_VALUE;
	if (defined	${$metainfo}{"FileModifyDate"}) { FormatUTCDate(\${$metainfo}{"FileModifyDate"}, \$filemoddate); }
	my $createdate = $DEFAULT_FIELD_VALUE;
	if (defined	${$metainfo}{"CreateDate"}) { FormatUTCDate(\${$metainfo}{"CreateDate"}, \$createdate); }

	# Insert file entry in FileIndex table
	$sth =  $db->prepare_cached("REPLACE INTO FileIndex (AbsFileName, DateTimeMetaAdded, FileType, CaseRef, UserTag) VALUES (?, datetime('now'), ?, ?, ?)"); # or print "Could not prepare FileIndex INSERT: ".$db->errstr;
	
	# if we got to this function, "FileType" must have been defined/read OK already	
	if ($sth->execute(${$filename}, ${$metainfo}{"FileType"}, $caseref, $tagname))
	{
		print ${$filename}." inserted into FileIndex table\n";
	}
	else
	{
		print "Could not INSERT ".${$filename}." into FileIndex: ".$sth->errstr."\n";
	}
	
	# Initialise field variables before insertion
	my $title = $DEFAULT_FIELD_VALUE;
	if (defined	${$metainfo}{"Title"}) { $title = ${$metainfo}{"Title"}; }
	my $documentid = $DEFAULT_FIELD_VALUE;
	if (defined	${$metainfo}{"DocumentID"}) { $documentid = ${$metainfo}{"DocumentID"}; }
	my $pagecount = $DEFAULT_FIELD_VALUE;
	if (defined	${$metainfo}{"PageCount"}) { $pagecount = ${$metainfo}{"PageCount"}; }
	my $filesize = $DEFAULT_FIELD_VALUE;
	if (defined	${$metainfo}{"FileSize"}) { $filesize = $exiftool->GetValue("FileSize", "ValueConv"); }
	my $author = $DEFAULT_FIELD_VALUE;
	if (defined	${$metainfo}{"Author"}) { $author = ${$metainfo}{"Author"}; }
	my $mimetype = $DEFAULT_FIELD_VALUE;
	if (defined	${$metainfo}{"MIMEType"}) { $mimetype = ${$metainfo}{"MIMEType"}; }
	my $pdfversion = $DEFAULT_FIELD_VALUE;
	if (defined	${$metainfo}{"PDFVersion"}) { $pdfversion = ${$metainfo}{"PDFVersion"}; }
	my $subject = $DEFAULT_FIELD_VALUE;
	if (defined	${$metainfo}{"Subject"}) { $subject = ${$metainfo}{"Subject"}; }
	my $creator = $DEFAULT_FIELD_VALUE;
	if (defined	${$metainfo}{"Creator"}) { $creator = ${$metainfo}{"Creator"}; }
	my $exiftoolversion = $DEFAULT_FIELD_VALUE;
	if (defined	${$metainfo}{"ExifToolVersion"}) { $exiftoolversion = ${$metainfo}{"ExifToolVersion"}; }
	my $directory = $DEFAULT_FIELD_VALUE;
	if (defined	${$metainfo}{"Directory"}) { $directory = ${$metainfo}{"Directory"}; }
	my $xfilename = $DEFAULT_FIELD_VALUE;
	if (defined	${$metainfo}{"FileName"}) { $xfilename = ${$metainfo}{"FileName"}; }
	my $producer = $DEFAULT_FIELD_VALUE;
	if (defined	${$metainfo}{"Producer"}) { $producer = ${$metainfo}{"Producer"}; }
	my $creatortool = $DEFAULT_FIELD_VALUE;
	if (defined	${$metainfo}{"CreatorTool"}) { $creatortool = ${$metainfo}{"CreatorTool"}; }

	# Insert actual metadata in PDFFiles table
	$sth =  $db->prepare_cached("REPLACE INTO PDFFiles (
	AbsFileName, CreateDate, FileModifyDate, Title,	DocumentID, PageCount, FileSize, Author, MIMEType, PDFVersion, Subject,	FileType, Creator, ExifToolVersion, ModifyDate, Directory,	FileName, Producer,	CreatorTool) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"); # or print "Could not Prepare for PDFFiles INSERT: ".$db->errstr;

	if ($sth->execute(${$filename}, 
					$createdate, $filemoddate, $title, 
					$documentid, $pagecount, $filesize, 
					$author, $mimetype, $pdfversion,
					$subject, ${$metainfo}{"FileType"}, $creator, 
					$exiftoolversion, $moddate, $directory, 
					$xfilename, $producer, $creatortool) )
	{
		print ${$filename}." inserted into PDFFiles table\n";
	}
	else
	{
		print "Could not INSERT ".${$filename}." into PDFFiles: ".$sth->errstr."\n";
	}

	$sth->finish;
}

sub ProcessJPEG
{
	my $metainfo = shift;
	my $filename = shift;

	if ($DEBUG)
	{
		print "ProcessJPEG called\n";
		for my $key (keys %{$metainfo})
		{
			print "key = $key, value = ".${$metainfo}{$key}."\n";
		}
	}

	my $lat = $DEFAULT_FIELD_VALUE;
	my $latref = $DEFAULT_FIELD_VALUE;
	my $lon = $DEFAULT_FIELD_VALUE;
	my $lonref = $DEFAULT_FIELD_VALUE;
	my $pos = $DEFAULT_FIELD_VALUE;
	my $alt = $DEFAULT_FIELD_VALUE;
	my $altref = $DEFAULT_FIELD_VALUE;

	# Ensure all 4 GPS params are present 
	# ie GPSLatitude, GPSLatitudeRef, GPSLongitude, GPSLongitudeRef
	# The Ref values indicate North/South and East/West
	if (defined ${$metainfo}{"GPSLongitude"} and defined ${$metainfo}{"GPSLatitude"} and 
		defined ${$metainfo}{"GPSLongitudeRef"} and defined ${$metainfo}{"GPSLatitudeRef"})
	{
		$latref = ${$metainfo}{"GPSLatitudeRef"};
		$lonref = ${$metainfo}{"GPSLongitudeRef"} ;
		$lat = $exiftool->GetValue("GPSLatitude", "ValueConv");
		$lon = $exiftool->GetValue("GPSLongitude", "ValueConv");

		print "lat = $lat, long = $lon \n";
	}
	else
	{
		print "${$filename} : No GPS Lat/Long data present\n";
	}

	if (defined ${$metainfo}{"GPSPosition"}) { $pos = ${$metainfo}{"GPSPosition"}; }

	# Handle GPSAltitude GPSAltitudeRef - may be present independently of GPS position
	if (defined ${$metainfo}{"GPSAltitude"} and defined ${$metainfo}{"GPSAltitudeRef"})
	{
		$alt = $exiftool->GetValue("GPSAltitude", "ValueConv");
		$altref = ${$metainfo}{"GPSAltitudeRef"};

		print "alt = $alt, altref = $altref \n";
	}
	else
	{
		print "${$filename} : No GPS Altitude data present\n";
	}

	# Convert dates into an SQLite readable format
	my $moddate = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"ModifyDate"}) { FormatUTCDate(\${$metainfo}{"ModifyDate"}, \$moddate); }
	my $filemoddate = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"FileModifyDate"}) { FormatUTCDate(\${$metainfo}{"FileModifyDate"}, \$filemoddate); }
	my $createdate = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"CreateDate"}) { FormatUTCDate(\${$metainfo}{"CreateDate"}, \$createdate); }
	my $origdate = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"DateTimeOriginal"}) { FormatUTCDate(\${$metainfo}{"DateTimeOriginal"}, \$origdate); }

	# Insert file entry in FileIndex table
	$sth =  $db->prepare_cached("REPLACE INTO FileIndex (AbsFileName, DateTimeMetaAdded, FileType, CaseRef, UserTag) VALUES (?, datetime('now'), ?, ?, ?)"); # or print "Could not prepare FileIndex INSERT: ".$db->errstr;
	
	# if we got to this function, "FileType" must have been defined/read OK already	
	if ($sth->execute(${$filename}, ${$metainfo}{"FileType"}, $caseref, $tagname))
	{
		print ${$filename}." inserted into FileIndex table\n";
	}
	else
	{
		print "Could not INSERT ".${$filename}." into FileIndex: ".$sth->errstr."\n";
	}

	# Initialise field variables before insertion
	my $mimetype = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"MIMEType"}) { $mimetype = ${$metainfo}{"MIMEType"}; }
	my $usercomment = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"UserComment"}) { $usercomment = ${$metainfo}{"UserComment"}; }
	my $model = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Model"}) { $model = ${$metainfo}{"Model"}; }
	my $exiftoolversion = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"ExifToolVersion"}) { $exiftoolversion = ${$metainfo}{"ExifToolVersion"}; }
	my $directory = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Directory"}) { $directory = ${$metainfo}{"Directory"}; }
	my $make = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Make"}) { $make = ${$metainfo}{"Make"}; }
	my $imagesize = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"ImageSize"}) { $imagesize = ${$metainfo}{"ImageSize"}; }
	my $imageheight = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"ImageHeight"}) { $imageheight = ${$metainfo}{"ImageHeight"}; }
	my $imagewidth = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"ImageWidth"}) { $imagewidth = ${$metainfo}{"ImageWidth"}; }
	my $filenumber = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"FileNumber"}) { $filenumber = ${$metainfo}{"FileNumber"}; }
	my $comment = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"Comment"}) { $comment = ${$metainfo}{"Comment"}; }
	my $xfilename = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"FileName"}) { $xfilename = ${$metainfo}{"FileName"}; }
	my $filesize = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"FileSize"}) { $filesize = $exiftool->GetValue("FileSize", "ValueConv"); }
	my $ownername = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"OwnerName"}) { $ownername = ${$metainfo}{"OwnerName"}; }
	my $imageuniqueid = $DEFAULT_FIELD_VALUE;
	if (defined ${$metainfo}{"ImageUniqueID"}) { $imageuniqueid = ${$metainfo}{"ImageUniqueID"}; }

	# Insert actual metadata in JPEGFiles table
	$sth =  $db->prepare_cached("REPLACE INTO JPEGFiles (AbsFileName, MIMEType, FileType, DateTimeOriginal, ModifyDate, GPSLongitude, GPSLatitude, GPSLongitudeRef, GPSLatitudeRef, GPSAltitude, GPSAltitudeRef, UserComment, GPSPosition, Model, ExifToolVersion, Directory, Make, ImageSize, ImageHeight,	ImageWidth,	FileNumber,	Comment, FileName, CreateDate,	FileModifyDate,	FileSize, OwnerName, ImageUniqueID) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"); # or print "Could not Prepare for JPEGFiles INSERT: ".$db->errstr;

	if ($sth->execute(${$filename}, 
					$mimetype, ${$metainfo}{"FileType"}, $origdate, 
					$moddate, $lon,	$lat, 
					$lonref, $latref, $alt, 
					$altref, $usercomment, $pos, 
					$model,	$exiftoolversion, $directory, 
					$make, $imagesize, $imageheight,
					$imagewidth, $filenumber, $comment, 
					$xfilename, $createdate, $filemoddate, 
					$filesize,	$ownername, $imageuniqueid) )
	{
		print ${$filename}." inserted into JPEGFiles table\n";
	}
	else
	{
		print "Could not INSERT ".${$filename}." into JPEGFiles: ".$sth->errstr."\n";
	}

	$sth->finish;
}



# Translates ExifTool's date format to SQLite parseable format
sub FormatUTCDate
{
	my $src = shift;
	my $dst = shift;

	${$src} =~ /(\d+)\:(\d+)\:(\d+)\s(\d+):(\d+):(\d+)/;
	my $year = $1;
	my $month = $2;
	my $day = $3;
	my $hr = $4;
	my $min = $5;
	my $sec = $6;

	my $offset_hrs = 0;
	my $offset_mins = 0;
	${$dst} = "Uninitialised";

	if (${$src} =~ /[+-](\d+):(\d+)$/)
	{
		# offset
		$offset_hrs = $1;
		$offset_mins = $2;
		#print "Offset detected = ".$offset_hrs.":".$offset_mins."\n";

		if (${$src} =~ /\+(\d+):(\d+)$/)
		{
			${$dst} = $year."-".$month."-".$day." ".$hr.":".$min.":".$sec." +".$offset_hrs.":".$offset_mins;
		}
		if (${$src} =~ /\-(\d+):(\d+)$/)
		{
			${$dst} = $year."-".$month."-".$day." ".$hr.":".$min.":".$sec." -".$offset_hrs.":".$offset_mins;
		}
		#print "dest date = ".${$dst}."\n";
	}
	else
	{
		# no offset assume UTC
		${$dst} = $year."-".$month."-".$day." ".$hr.":".$min.":".$sec;
		#print "dest date = ".${$dst}."\n";
	}
}


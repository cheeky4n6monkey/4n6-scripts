#!/usr/bin/perl -w

# sms-grep.pl = Perl script to grep a file containing SQLite SMS messages using a given number
#
# Copyright (C) 2013, 2014 Adrian Leong (cheeky4n6monkey@gmail.com)
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
# v2013-02-16 Initial Version
# v2013-04-16 Added "read_payload_int" function for payload integers & -p arg
# v2014-01-20 Fixed script to handle cell header type 8 ("0") & 9 ("1") values.
#
# Special Thanks:
# This script was inspired by the research of Mari DeGrazia
# (http://az4n6.blogspot.com/2013/02/finding-and-reverse-engineering-deleted_1865.html) and then
# further improved based upon her testing comments.
#

use strict;
use warnings;
use Getopt::Long;
#use Data::Dump qw(dump);

my $version = "v2014-01-20";

# input arguments
my $help = 0;
my $filename = "";
my @searchstrings;
my $outputflag = "";
my $config = "";
my $previous_data_size = -1;

# Store any data we come across in a hash of arrays (we use the file offsets for the keys)
# The array order will be same as config file's declared schema order
my %STORAGE;

# Store the schema from the specified config file
my @SCHEMAFIELD_NAMES;
my @SCHEMAFIELD_TYPES;
my @SCHEMAFIELD_PRINTS;

GetOptions('help|h' => \$help,
	'c=s' => \$config,
	's=s' => \@searchstrings,
	'f=s' => \$filename,
	'p=i' => \$previous_data_size,
	'o:s' => \$outputflag);

if ($help || $filename eq "" || scalar(@searchstrings) eq 0 || $config eq "" || $previous_data_size eq -1)
{
	print("\nHelp for $version\n\n");
	print("Perl script to grep a file containing SQLite SMS messages using a given number\n"); 
	print("\nUsage: sms-grep.pl [-h|help] [-c config] [-f filename] [-s phonenumber] [-o output]\n");
	print("-h|help ... Help (print this information). Does not run anything else.\n");
	print("-c config . Configuration file containing db schema.\n");
	print("-f file ... File to be parsed (eg database, journal).\n");
	print("-s phone .. Phone number(s) to be searched for.\n");
	print("-p size ... Number of bytes between last cell header field and phone number (should be 1 or 2 for Android sms).\n");
	print("-o output . Optional Tab separated output file. Will overwrite an existing file.\n");
	print("\nExample: sms-grep.pl -c config.txt -f /cases/mmssms.db -s \"(555) 555-1234\" -s \"5551234\" -p 1 -o output.tsv\n");
	print("\nNote: For formatting reasons, any new line characters (\\n) in sms body fields will be replaced with a space character.\n");
	exit;
}

print "\nRunning $version\n\n";

my $filesize = -s $filename;
print "$filename is $filesize bytes\n";

# Read in config file
my $MAX_SCHEMA_COLUMNS = 3;
open(my $configfilehandle, "<", $config) || die("Unable to open $config\n");
my @configstrings = <$configfilehandle>; # read in config file, one line per array item
chomp(@configstrings);


my $PHONETYPE = ""; # global var so we know what type of phone
my $linecount = 0;
foreach my $line (@configstrings)
{
	if (not $line =~ /^#/ and $line =~ /^\w/) # ignore comments and empty lines
	{
		if ($line =~ /^c4n6type=/i)
		{
			my @typefield = split(/=/, $line);
			if ($typefield[1] =~ /android/i) {$PHONETYPE = "Android"; print "\nPhonetype specified = Android\n";}
			if ($typefield[1] =~ /iphone/i) {$PHONETYPE = "iPhone"; print "\nPhonetype specified = iPhone\n";}
			if ($PHONETYPE eq "")
			{
				print "Error! No c4n6type phone type specified (android or iphone)\n";
				exit;
			}
			next;
		}
		my @fields = split(/:/, $line);
		for (my $j=0; $j < $MAX_SCHEMA_COLUMNS; $j++)
		{
			if ($j == 0) {$SCHEMAFIELD_NAMES[$linecount] = $fields[$j];}
			if ($j == 1) {$SCHEMAFIELD_TYPES[$linecount] = $fields[$j];}
			if ($j == 2) {$SCHEMAFIELD_PRINTS[$linecount] = $fields[$j];}
		}
		$linecount++;
	}
}

my $NUMSCHEMAFIELDS = scalar(@SCHEMAFIELD_NAMES);

# Check if outputting to output file or to screen
my $outputfile;
if ($outputflag eq "")
{
	print "No output file specified. Printing results to screen ...\n";
}
else
{
	open($outputfile, ">", $outputflag) || die("Unable to open output file $outputflag\n");
	print "Printing results to $outputflag ...\n";
}

# Start parsing the input file ...
open(my $filehandle, "<", $filename) || die("Unable to open $filename\n");
binmode ($filehandle, ":raw");

# get $filehandle into one big file string
my @filestrings = <$filehandle>;
my $bigfilestring = join("", @filestrings);

# iterate thru given phone numbers and find any hit offsets
my $pos;
my @hits; # array of found searchstring hit offsets
foreach my $searchstring (@searchstrings)
{
	my $fcursor = 0;
	my $cont = 1;

	while ( ($cont eq 1) and ($fcursor < $filesize) )
	{
		$pos = index($bigfilestring, $searchstring, $fcursor);
		if ($pos != -1)
		{
			#printf ("Found hit at 0x%X\n", $pos);
			push(@hits, $pos);
			$fcursor = $pos+1; # next loop searches from last hit+1
		}
		else
		{
			# no more hits, bail out
			$cont = 0;
		}
	}
}

# Now we can use @hits as an index for all search term(s) hits
if (scalar(@hits))
{
	printf ("\n%d total hits found\n", scalar(@hits));
}
else
{
	print "\nNo hits found!\n";
	exit;
}

my $VALIDPRINT=0; # keeps track of how many hits were printed
# The main loop calls process_sms to extract/store the sms field values 
foreach my $hit (@hits)
{
	#printf ("\nFound hit at 0x%X\n", $hit);
	process_sms($filehandle, $hit, $previous_data_size);
}

# Now to sort the dates list in chronological order ie same order they were received/sent ...
# First, find the index of the 1st schema field marked as a date type
my $DATEFIELD_IDX=-1;
for (my $j=0; $j < scalar(@SCHEMAFIELD_TYPES); $j++)
{
	if ($SCHEMAFIELD_TYPES[$j] =~ /date/i)
	{
		$DATEFIELD_IDX = $j;
		last;
	}
}
if ($DATEFIELD_IDX == -1)
{
	print ("Error! No date field specified in config schema!\n");
	exit;
}

# Get a list of keys to the global STORAGE hash and sort them in chronological order
my @sorteddatekeys = sort bydate keys %STORAGE;

# Now we can start printing stuf ...
# Print TSV column titles
if ($outputflag eq "")
{
	printf ("\nOffset"); # start with file offset column title
	for (my $j=0; $j < scalar(@SCHEMAFIELD_NAMES); $j++)
	{
		if ($SCHEMAFIELD_PRINTS[$j] != 0)
		{
			printf ("\t%s", $SCHEMAFIELD_NAMES[$j]);
		}
	}
	printf ("\n");
}
else
{
	# Printing to column titles to file not screen
	printf ($outputfile "Offset"); # start with file offset column title
	for (my $j=0; $j < scalar(@SCHEMAFIELD_NAMES); $j++)
	{
		if ($SCHEMAFIELD_PRINTS[$j] != 0)
		{
			printf ($outputfile "\t%s", $SCHEMAFIELD_NAMES[$j]);
		}
	}
	printf ($outputfile "\n");
}

# Now we can print stored results (which were previously sorted by date order)
foreach my $hit (@sorteddatekeys)
{
	if ($outputflag eq "")
	{
		print get_hit_string($hit);
	}
	else
	{
		print $outputfile get_hit_string($hit);
	}
}

#dump \%STORAGE;

printf ("\n%d hits found, %d hits processed/printed\n", scalar(@hits), $VALIDPRINT);

# ends main section

# =================
# FUNCTIONS SECTION
# =================
# Used to sort %STORAGE keys by the 1st datefield (for printing)
sub bydate { $STORAGE{$a}[$DATEFIELD_IDX] <=> $STORAGE{$b}[$DATEFIELD_IDX] }

# Function takes a Unix epoch time and returns a human readable string.
# Android stores times in ms since UTC where as iPhones store times as seconds since UTC.
# We use the PHONETYPE variable to decide how to scale.
sub get_UTC_string {
	my $time = shift;
	my $scale=1;
	if ($PHONETYPE eq "Android") {$scale = 1000;}
	if ($time > 0)
	{
		my ($sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst) = gmtime($time/$scale);
		return sprintf("%04d-%02d-%02d %02d:%02d:%02d", $year+1900, $mon+1, $mday, $hour, $min, $sec);
	}
	return "";
}

# Given a file offset, this function looks up the data and forms the corresponding string.
# The string can then be printed to the screen or file.
sub get_hit_string {
	my $hitoffset = shift;
	my $stringoutput = sprintf ("0x%X", $hitoffset); # Always start string with the file offset ...
	
	# For each field to be printed, we look up the field type and add the field value to the print string
	for (my $j=0; $j < scalar(@SCHEMAFIELD_PRINTS); $j++)
	{
		if ($SCHEMAFIELD_PRINTS[$j] != 0) # assume non-zero print flag value means print
		{
			if ($SCHEMAFIELD_TYPES[$j] =~ /date/i)
			{
				$stringoutput .= sprintf("\t%s", get_UTC_string($STORAGE{$hitoffset}[$j]));
			}
			elsif ($SCHEMAFIELD_TYPES[$j] =~ /text/i)
			{
				$stringoutput .= sprintf("\t%s", $STORAGE{$hitoffset}[$j]);
			}
			elsif ($SCHEMAFIELD_TYPES[$j] =~ /integer/i)
			{
				$stringoutput .= sprintf("\t%d", $STORAGE{$hitoffset}[$j]);
			}
		}
		if ($j == scalar(@SCHEMAFIELD_PRINTS) - 1)
		{
			$stringoutput .= "\n"; # last field gets a newline appended
		}
	}
	return $stringoutput;
}

# Function will take an offset to the phone number field,
# then skips the preceeding payload data ($previous_data_size bytes) and 
# then skips the header data type varints until it gets to the cell header size field.
# Once it knows the cell header size offset, it interprets the full cell header for field sizes &
# stores each field.
# WARNING: If the sms header size value is larger than 
# (NUMSCHEMAFIELDS+FUDGE+size of cell header size field) bytes, this function will fail! 
# The FUDGE allows us to sanity check the cell header size field.
sub process_sms {
	my $filehandle = shift;
	my $fileoffset = shift;
	my $previous_data_size = shift; # number of data bytes between last cell header varint and address field (should be 1 or 2) 

	my $FUDGE=5;
	my $offset = $fileoffset - $previous_data_size - 1; # sets initial position to be lsb of last cell header field 

	# Now work backwards thru cell header fields
	for (my $i=0; $i < $NUMSCHEMAFIELDS; $i++)
	{
		my $numbytes = calculate_varint_bytes_from_lsb($filehandle, $offset);
		$offset -= $numbytes; # work our way backwards to previous field type varint
	}
	my $hdrsizeoffset = $offset; # should now be at cell header size
	my ($hdrsize, $hdrsizeval) = read_varint_from_msb($filehandle, $hdrsizeoffset);
	
	# Now we can try to read the cell header which tells us the actual sizes of each cell data field
	my @payloaditemsizes;
	if ($hdrsizeoffset < $fileoffset-1) # we better have gone backwards!
	{
		my $cursor = 1;
		# Read the cell header size (in bytes) to test the hdr
		my ($hdrsize, $hdrsizeval) = read_varint_from_msb($filehandle, $hdrsizeoffset);
		#printf ("hdrsizeval = $hdrsizeval at 0x%x\n", $hdrsizeoffset);
		# Range check the cell header size value
		if (($hdrsizeval >= $NUMSCHEMAFIELDS+$hdrsize) and ($hdrsizeval <= $NUMSCHEMAFIELDS+$FUDGE+$hdrsize))
		{
			# For each field in cell header (skipping the 1st byte = hdrsizeval),
			# store the no. bytes required in @payloaditemsizes. 
			# Starts from first field after cell header size.
			for (my $j=0; $j < $NUMSCHEMAFIELDS; $j++)
			{
				my ($varsize, $var) = read_varint_from_msb($filehandle, $hdrsizeoffset+$cursor);
				# Depending on the cell header field value, a certain number of bytes will be required
				if (($var <= 4) and ($var >= 0))
				{
					push(@payloaditemsizes, $var);
				}
				elsif ($var == 5)
				{
					push(@payloaditemsizes, 6); # eg any Unix Epoch dates
				}
				elsif (($var == 6) or ($var == 7))
				{
					push(@payloaditemsizes, 8);
				}
				elsif ($var == 8)
				{
					push(@payloaditemsizes, 888); # hack to let data read section know value = 0
				}
				elsif ($var == 9)
				{
					push(@payloaditemsizes, 999); # hack to let data read section know value = 1
				}
				elsif (($var >= 12) and ($var % 2 == 0))
				{
					# Blob - can be used for iPhone headers/recipients fields
					push(@payloaditemsizes, ($var-12)/2);
				}
				elsif (($var >= 13) and ($var % 2 == 1))
				{
					# strings such as text, subject, address do not include null terminator
					push(@payloaditemsizes, ($var-13)/2);
				}
				$cursor += $varsize;
			}

			# Now @payloaditemsizes should contain a list of sizes we can use
			# to read/print the actual payload
			my $bytecount = 0; # keep track of the bytes read
			my $buffer;
			my $loop = 0; # keeps track of the cell field loop we are up to (0 ... no. fields-1)
			if ( (scalar(@payloaditemsizes)) != $NUMSCHEMAFIELDS) # quick sanity check
			{
				printf ("Error! Number of cell header fields does not equal declared schema! %d vs %d\n", (scalar(@payloaditemsizes)), $NUMSCHEMAFIELDS);
				return;
			}

			foreach my $itemsize (@payloaditemsizes)
			{
				if ( ($itemsize > 0) and ($hdrsizeoffset+$hdrsizeval+$bytecount < $filesize) ) # these fields will have actual data written after the header section
				{
					if (($SCHEMAFIELD_TYPES[$loop] =~ /date/i) and ($itemsize == 6))
					{
						# Handle Unix epochs
						# Some date_sent fields can have size = 1 but that 1 byte has content = 0x00
						# So we only bother with date/date_sent fields with the full 6 byte size
						my $timeval = 0;
						my $invalidtime = 0;
						my $timeidx = $hdrsizeoffset + $hdrsizeval + $bytecount;
						# read in each byte and then multiply by powers of 256 to get ms (Android) or secs (iPhone) since UTC
						for (my $dloop = 0; $dloop < 6; $dloop++)
						{
							sysseek($filehandle, $timeidx++, 0);
							sysread($filehandle, $buffer, 1);
							my $byteval = unpack("C", $buffer);
							if (not defined $byteval) 
							{
								$invalidtime = 1;
								last;
							}
							$timeval = $timeval + $byteval*256**(5-$dloop); 
						}
						if (not $invalidtime) 
						{
							$STORAGE{$fileoffset}[$loop] = $timeval; # store it	
						}
						else {$STORAGE{$fileoffset}[$loop] = 0;} # set invalid times to 0
					}
					else # read fields which are not a unix time (ie TEXT, INTEGER)
					{
						if ($SCHEMAFIELD_TYPES[$loop] =~ /text/i)
						{
							sysseek($filehandle, $hdrsizeoffset+$hdrsizeval+$bytecount, 0);
							sysread($filehandle, $buffer, $itemsize); 
							$buffer =~ s/\n/ /g; # eat any newlines so they don't interfere with output formatting
							$buffer =~ s/[[:cntrl:]]//g; # just in case, get rid of any control chars
							$STORAGE{$fileoffset}[$loop] = $buffer;
						}
						elsif ($SCHEMAFIELD_TYPES[$loop] =~ /integer/i)
						{
						    if ($itemsize == 888)
						    {
						        $STORAGE{$fileoffset}[$loop] = 0;
						    }
						    elsif ($itemsize == 999)
						    {
						        $STORAGE{$fileoffset}[$loop] = 1;
						    }
						    else
						    {
							    my $intval = read_payload_int($filehandle, $hdrsizeoffset+$hdrsizeval+$bytecount, $itemsize);
							    if (defined $intval) 
							    {
								    $STORAGE{$fileoffset}[$loop] = $intval;
							    } # what to print for an undef int value ???
							}
						}
						else
						{
							$STORAGE{$fileoffset}[$loop] = 0; # if blob or any other type, set value to zero
						}
					}
				}
				elsif ($hdrsizeoffset+$hdrsizeval+$bytecount >= $filesize)
				{
					# value is truncated (runs past EOF), we should set any empty strings to "" & any dates to 0;
					#printf ("Field %s is TRUNCATED\n", $SCHEMAFIELD_NAMES[$loop]);
					if ($SCHEMAFIELD_TYPES[$loop] =~ /date/i)
					{
						$STORAGE{$fileoffset}[$loop] = 0;
					}
					elsif ($SCHEMAFIELD_TYPES[$loop] =~ /text/i)
					{
						$STORAGE{$fileoffset}[$loop] = "TRUNCATED";
					}
					else
					{
						$STORAGE{$fileoffset}[$loop] = -999; # if blob or any other type
					}
				}
				else
				{
					# itemsize = 0, so value is NULL, we should set any empty strings to "" & any dates to 0;
					#printf ("Field %s is NULL\n", $SCHEMAFIELD_NAMES[$loop]);
					if ($SCHEMAFIELD_TYPES[$loop] =~ /date/i)
					{
						$STORAGE{$fileoffset}[$loop] = 0;
					}
					elsif ($SCHEMAFIELD_TYPES[$loop] =~ /text/i)
					{
						$STORAGE{$fileoffset}[$loop] = "";
					}
					else
					{
						$STORAGE{$fileoffset}[$loop] = 0; # if blob or any other type, set value to zero
					}
				}
				
				$loop++; # keeps track of the cell field loop we are up to
				
				if (($itemsize == 888) or ($itemsize == 999))
				{
				    $itemsize = 0; # ensure the $bytecount is accurate 
				    # ie we did not actually read anything
				    # this field info comes from the cell header NOT the data
				}
				#printf("itemsize = %d\n", $itemsize);
				
				$bytecount += $itemsize; # keep track of the total bytes read from all fields
			}
			$VALIDPRINT++; # keep track of how many we print
		}
		else { printf ("### Cell header size is out of range (0x%X) - Not a valid sms! Skipping hit (0x%X)\n", $hdrsizeval, $fileoffset); }
	}
	else { printf ("### Could not determine Cell header offset - Not a valid sms! Skipping hit (0x%X)\n", $fileoffset); }
}

# Given size, will read in payload (signed) integer data field
# inputs = filehandle, offset, size of data field
# outputs = value
sub read_payload_int {
	my $filehandle = shift;
	my $offset = shift;
	my $size = shift;
	my $intval=0;

	sysseek($filehandle, $offset, 0);

	my $vbuffer;
	my $vbytes = sysread($filehandle, $vbuffer, $size);

	if ($size == 1) # 8 bit signed (most of integer fields should be this)
	{
		my $bytestr = substr($vbuffer, 0, 1);
		my $byteval = unpack("c", $bytestr);
		return $byteval;
	}
	elsif ($size == 2) # 16 bit signed big endian
	{
		my $bytestr = substr($vbuffer, 0, 2);
		my $byteval = unpack("n", $bytestr);
		return $byteval;
	}
	elsif ($size == 4) # 32 bit signed big endian
	{
		my $bytestr = substr($vbuffer, 0, 4);
		my $byteval = unpack("N", $bytestr);
		return $byteval;
	}
#	elsif ($size == 8) # 64 bit signed big endian. 32 bit Perl on SIFT is unable to handle "q"s
#	{
#		my $bytestr = substr($vbuffer, 0, 8);
#		my $byteval = unpack("q", $bytestr);
#		return $byteval;
#	}
	else # could be 24 or 48 or 64 bit integer (INCOMPLETE - but not likely to see this in sms)
	{
		# Note: 6 byte date fields handled in process_sms (not here)
		for (my $j=0; $j < $size; $j++)
		{
			my $bytestr = substr($vbuffer, $j, 1);
			my $byteval = unpack("C", $bytestr);
			$intval += $byteval*256**($size-$j-1); 
		}
		return $intval; #TBD: handle sign
	}
}

# Varint reader function reads all possible 9 bytes at given offset to most significant byte
# inputs = filehandle, offset
# outputs = number of bytes used by varint, varint value
sub read_varint_from_msb {
	my $filehandle = shift;
	my $offset = shift;

	sysseek($filehandle, $offset, 0);

	my $vbuffer;
	my $vbytes = sysread($filehandle, $vbuffer, 9);

	my $byte1str = substr($vbuffer, 0, 1);
	my $byte1 = unpack("C", $byte1str);
	if ($byte1 < 128)
	{
		return (1, $byte1);
	}
	# otherwise, there must be more bytes in the varint
	my $byte1value = ($byte1 & 0b01111111); # store the value for future
	
	my $byte2str = substr($vbuffer, 1, 1);
	my $byte2 = unpack("C", $byte2str);
	my $byte2value = ($byte2 & 0b01111111);
	if ($byte2 < 128)
	{
		# shifting 7 bits left = multiplying by 128
		my $value = $byte1value*128 + $byte2value;
		#print ("returning byte2 = $value\n");
		return (2, ($byte1value*128 + $byte2value));		
	}
	
	# for 3rd byte
	my $byte3str = substr($vbuffer, 2, 1);
	my $byte3 = unpack("C", $byte3str);
	my $byte3value = ($byte3 & 0b01111111);
	if ($byte3 < 128)
	{
		return (3, ($byte1value*128*128 + $byte2value*128 + $byte3value)); 
	}

	# for 4th byte
	my $byte4str = substr($vbuffer, 3, 1);
	my $byte4 = unpack("C", $byte4str);
	my $byte4value = ($byte4 & 0b01111111);
	if ($byte4 < 128)
	{
		return (4, ($byte1value*128*128*128 + $byte2value*128*128 + $byte3value*128 + $byte4value)); 
	}

	# for 5th byte
	my $byte5str = substr($vbuffer, 4, 1);
	my $byte5 = unpack("C", $byte5str);
	my $byte5value = ($byte5 & 0b01111111);
	if ($byte5 < 128)
	{
		return (5, ($byte1value*128**4 + $byte2value*128**3 + $byte3value*128**2 + $byte4value*128 + $byte5value)); 
	}
	
	# for 6th byte
	my $byte6str = substr($vbuffer, 5, 1);
	my $byte6 = unpack("C", $byte6str);
	my $byte6value = ($byte6 & 0b01111111);
	if ($byte6 < 128)
	{
		return (6, ($byte1value*128**5 + $byte2value*128**4 + $byte3value*128**3 + $byte4value*128**2 + $byte5value*128 + $byte6value)); 
	}

	# for 7th byte
	my $byte7str = substr($vbuffer, 6, 1);
	my $byte7 = unpack("C", $byte7str);
	my $byte7value = ($byte7 & 0b01111111);
	if ($byte7 < 128)
	{
		return (7, ($byte1value*128**6 + $byte2value*128**5 + $byte3value*128**4 + $byte4value*128**3 + $byte5value*128**2 + $byte6value*128 + $byte7value)); 
	}

	# for 8th byte
	my $byte8str = substr($vbuffer, 7, 1);
	my $byte8 = unpack("C", $byte8str);
	my $byte8value = ($byte8 & 0b01111111);
	if ($byte8 < 128)
	{
		return (8, ($byte1value*128**7 + $byte2value*128**6 + $byte3value*128**5 + $byte4value*128**4 + $byte5value*128**3 + $byte6value*128**2 + $byte7value*128 + $byte8value)); 
	}

	# for 9th byte
	my $byte9str = substr($vbuffer, 8, 1);
	my $byte9 = unpack("C", $byte9str); # all 8 bits of 9th byte are used (no masking required)
	return (9, ($byte1value*128**8 + $byte2value*128**7 + $byte3value*128**6 + $byte4value*128**5 + $byte5value*128**4 + $byte6value*128**3 + $byte7value*128**2 + $byte8value*128 + $byte9)); 
}

# Given a file handle and an offset to a varint's least significant byte, 
# this function calculate the number of bytes the varint is using.
# Varints can be a max of 9 bytes.
# So grab the previous 9 bytes and figure out how many bytes are being used. 
# The trick for varints is that any single byte value greater than 128
# indicates another lesser significant byte is required. eg "0x128" "0x50" means a 2 byte varint 
# We don't really care about the least significant byte value (eg "0x50").
# But if any of the preceding bytes are greater than or equal 128, they must also be part of the varint.
# If the preceding byte, is ever less than 128 then we can stop trying - 
# we must have just gone past the most significant byte of the varint.
sub calculate_varint_bytes_from_lsb {
	my $file = shift;
	my $offset = shift;
	
	my $buf;
	my $numbytes;
	for (my $i=0; $i < 9; $i++)
	{
		sysseek($file, $offset-$i, 0);
		sysread($file, $buf, 1);
		my $val = unpack("C", $buf);
		if (($val < 128) and ($i ne 0))
		{
			last;
		}
		$numbytes++;
	}
	return $numbytes;
}


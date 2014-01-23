
"SquirrelGripper" ("SG") is a Perl script to extract ExifTool metadata into an SQLite Database.
It was developed on/for SANS SIFT virtual machines (v2.12) but it has also been used successfully with ActiveState Perl on Windows XP/7.

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

Thanks
======
This project was motivated by the positive encouragement/feedback from some more experienced DFIR'ers.
Corey Harrell made some great suggestions and also provided testing feedback from ActiveState Perl (v5.12) on Windows 7 (32/64). 
Also consulted were Brad Garnett, Cindy Murphy, Gerald Combs, "Girl, Unallocated" and Ken Pryor. Having an audience for my email updates provided both structure and motivation for my thoughts.
So, Thankyou everyone!

About SquirrelGripper
=====================
In Australia, to grab a bloke by his "nuts" (accidentally or on purpose or sometimes both) is also known as "the Squirrel Grip". This has been known to happen in the heat of battle/whilst tackling an opponent during a Rugby or Aussie Rules match. 
The idea behind the name is that "SquirrelGripper" (aka "SG") will lead analysts to the low hanging fruit right at the crux of the matter ;)
In polite(r) company (eg client briefing), one could say that "SquirrelGripper" finds all the little nuts/nuggets of information.

By running this script an analyst will hopefully save time. Rather than having to launch the ExifTool exe multiple times for different files/metadata, they can launch this script once and then perform SQL queries for retrieving/presenting their metadata of interest.

As far as I know, this capability does not currently exist (at least for open source) so I think this script could prove handy for several different types of investigations. For example: fraud, e-discovery processing/culling, processing jpgs (eg exploitation).


Installing SquirrelGripper
==========================
The Image::ExifTool Perl package is already installed on SIFT v2.12. However due to some internal label changes to Image::ExifTool, we need to grab the latest version (v8.90) for our script.
We can do this on SIFT by typing: "sudo cpan Image::ExifTool".

We have been using the DBI Perl package to interface with SQLite databases.
You grab the latest DBI package from CPAN by typing: "sudo cpan DBI".

Next, you can download/unzip/copy "squirrelgripper.pl" (from http://code.google.com/p/cheeky4n6monkey/) to "/usr/local/bin" and make it executable (by typing "sudo chmod a+x /usr/local/bin/squirrelgripper.pl")

Now you should be ready to run "SquirrelGripper" on SIFT in all its glory ...

To run on Windows, install ActiveState Perl (http://www.activestate.com/activeperl/downloads) and use the Perl Package Manager to download the ExifTool package (v8.90). DBI should already be installed. Next, copy the "squirrelgripper.pl" script to the directory of your choice.

On Windows, you should now be able to run SG at the command prompt by typing something like: 
"perl c:\squirrelgripper.pl -newdb -db nutz2u.sqlite -case caseABC -tag fraud-docs -dir c:\squirrel-testdata\subdir1"

Don't worry about the arguments for now - they're all explained in the next section.

Running SquirrelGripper
=======================
For my test scenario, I have various .doc, .docx, .xls, .xlsx, .ppt, .pptx, .pdf files in the "/home/sansforensics/squirrel-testdata/subdir1" directory.
I have also copied various .jpg files to the "/home/sansforensics/squirrel-testdata/subdir2" directory

It is assumed that a new database will be created for each case. However, the same database can be also used for multiple iterations of the script.

The script recursively searches thru sub-directories so please ensure you've pointed it at the right level before launching. It is also possible to mark different subdirectories with different case tags. eg Launch script with one directory using the case tag "2012-04-18-caseA-companyA". Then launch the script a second time pointing to another directory using the case tag "2012-04-18-caseA-companyB". 
SG can also handle multiple -dir arguments in case you need to extract data from more than one directory (eg "-dir naughty/pics -dir naughty/docs"). If a "-tag" argument is specified, it will apply to files from both directories.

The first example uses "-newdb" to create the "nutz2u.sqlite" database in the current directory. It also tags all "subdir1" files with the "fraud-docs" user tag (you can see the user tag value in the "FileIndex" table). Currently, the "-db", "-case" and "-dir" arguments are mandatory.
Note: the -dir directory can be an absolute path or a relative one.

squirrelgripper.pl -newdb -db nutz2u.sqlite -case caseABC -tag fraud-docs -dir /home/sansforensics/squirrel-testdata/subdir1/

The second call assumes the "nutz2u.sqlite" database already exists and tags all "subdir2" files with the "fraud-pics" tag.

squirrelgripper.pl -db nutz2u.sqlite -case caseABC -tag fraud-pics -dir /home/sansforensics/squirrel-testdata/subdir2

Once the metadata has been extracted to the SQLite database we can use SQL queries to find specific files of interest. This can be done via the "sqlite3" client and/or the Firefox "SQLite Manager" plugin.

Some example SQL queries:

Finding pictures from a particular camera model and order it by datetime of the original
SELECT * FROM JPEGFiles WHERE Model='Canon PowerShot SX130 IS' ORDER BY DateTimeOriginal;

Finding .docs by same author and sorting by page count
SELECT * FROM DOCFiles WHERE Author='Joe Friday' ORDER BY PageCount;

Sorting Powerpoint files by Revision Number
SELECT * FROM PPTFiles ORDER BY RevisionNumber;

Finding all "fraud-pics" user tagged .JPEGs
SELECT * FROM JPEGFiles, FileIndex WHERE JPEGFiles.AbsFileName=FileIndex.AbsFileName AND FileIndex.UserTag='fraud-pics';

There are a LOT more fields to sort by - way too many for a README. You can see them for yourself in the code by searching for the "CREATE TABLE" strings or create your own example database and browse it.
Where possible, I have used the same field names as the ExifTool exe prints to the command line.

For more details please refer to http://cheeky4n6monkey.blogspot.com/

For adding new metadata fields/file types or just saying hello you can reach me at cheeky4n6monkey@gmail.com or on Twitter @cheeky4n6monkey.

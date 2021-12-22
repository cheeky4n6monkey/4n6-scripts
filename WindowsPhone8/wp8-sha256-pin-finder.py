# Python script determines a salted SHA256 hashed Windows Phone 8 PIN.
#
# Authors: Francesco Picasso <francesco.picasso@gmail.com> &
#          Adrian Leong <cheeky4n6monkey@gmail.com>
#
# Based (HEAVILY) on the work of Francesco "dfirfpi" Picasso <francesco.picasso@gmail.com>
# http://blog.digital-forensics.it/2015/07/windows-phone-pin-cracking.html
#
# This script does not have any external library dependencies so it should run with a base Python 2.7+ install
# However, it also requires the user manually view the SOFTWARE hive's \Microsoft\Comms\Security\DeviceLock\ sub keys
# and find/extract the relevant CurrentCredentialHash and CredentialActualLength hex values before running. 
# AccessData's Registry Viewer is recommended for extracting the salt and hash (see Francesco's post 
# for further details on which byte offsets of CurrentCredentialHash correspond to the hash and salt).
#
# Some Background:
# Windows Phone 8 stores the salted hash of its PIN in the SOFTWARE Registry hive under
# \Microsoft\Comms\Security\DeviceLock\ObjectXX. 
# The specific sub key location seems to vary - we have seen it stored under
# \Microsoft\Comms\Security\DeviceLock\Object31 but others in the forensic community have reported seeing it in
# \Microsoft\Comms\Security\DeviceLock\Object21.
# Basically, we are looking for the ObjectXX which contains both the "CredentialHash" and "CredentialActualLength" values.
#
# For one case image, there was no "CredentialActualLength" found so the recommended plan would be 
# to extract the salt and hash and then try the script with various NUM_PIN_DIGITS (eg 4, 5, 6, 7 etc) until a PIN is found.
#
# Usage Examples:
# python wp8-sha256-pin-finder.py SALT HASH NUM_PIN_DIGITS
#
# Note: Space between args.
#
# python wp8-sha256-pin-finder.py 0EA631F7C9A47158207CC14DD5B155AF870E951C357CF4A20E4F83A5261FD9011D25AB2DD15BD2FED4DC7E4933862BE5A3B91F6DA759A0310B59A7E35930511C4FB5EC8F7ED09A07A7A28B26A7CC15F0FCAFF7E4247DA09E0BEB2B78505BDA5BB6C676C305BBBC2C069EE000393BED24E686D35D21A1E89D99C37067C9F4DDED F9CDB590E87D9F881E6AFF5EC9BB5C0B277E21489D9B893F8413823AA99D1036 4
# will result in the 4 digit PIN 5338 being output.

import hashlib
import itertools
import argparse

version_string = "wp8-sha256-pin-finder.py v2015-07-30"
print "\nRunning " + version_string + "\n"

parser = argparse.ArgumentParser(description='Determines a salted SHA256 hashed Windows Phone 8 PIN')
parser.add_argument("salt", help='128 hex character Salt string from CurrentCredentialHash')
parser.add_argument("hash", help='32 hex character Hash string from CurrentCredentialHash')
parser.add_argument("length", type=int, help="CredentialActualLength value (ie number of digits in PIN)")

args = parser.parse_args()

salt = args.salt.decode('hex') # get binary value of hex string eg 'a'.decode('hex') = 61
hash = args.hash.decode('hex')

# Try hashing every combination of numbers 0-9 for the specified PIN length
for i in itertools.product('0123456789', repeat=args.length):
    pin = ''.join(i)
    t = '\x00'.join(i) + '\x00' # String = NULL + PIN string (eg '1234') + NULL
    t += salt # Binary value of extracted salt
    # Hash algorithm is currently ass-umed to be SHA256.
    # (There should be a UTF-16LE "SHA256" string between salt and hash in CurrentCredentialHash) 
    hashy = hashlib.sha256(t)
    if hashy.digest() == hash:
        print 'PIN code is ' + str(pin)
        exit(1)

print 'No PIN found!'
exit(0)



import sys
import getopt
import xml.etree.ElementTree as ET
import re
import os
import pandas as pd
from modules import cdconv
from modules import xmload
cdv = cdconv.convdump

# Get full command-line arguments
full_cmd_arguments = sys.argv

# Keep all but the first
argument_list = full_cmd_arguments[1:]

# set the command line options
short_options = "hno:x:o:c:d:m:i"
long_options = ["help", "xml=", "ccf=", "output=", "dump=", "dump_format=", "can_id="]

help_text = ("\nccfparser options:\n"
             "   -x / --xml <filename> ......  SDD XML CCF_DATA file containing CCF values\n"
             "   -o / --output <filename> ...  filename for outputting the result, default is to stdout\n"
             "   -c / --ccf <ccf> ...........  ccf hexadecimal string to be decoded\n"
             "   -d / --dump <filename>......  file to be decoded, this will override any -ccf setting\n"
             "   -m / --dump_format .........  format of dump data, valid options are:\n"
             "                                   cd = can_utils candump format (default)\n"
             "                                   st = a hexadecimal string\n"
             "   -i / --can_id...............  canID (decimal) used in the can dump to broadcast CCF, default = 401\n\n"
             "XML file must be specified and either a string containing the CCF or a dump file to process\n")

# The following are things that need to exist in order for this to work, so set them to None and we'll check if they get data shoved in them later
ccf_data_file = None
ccf = None
dumpf = "cd"
dump = "examples/can.msg"
ccfid = "401" # set this as a default canID for the CCF broadcast

# test for command line options
try:
    arguments, values = getopt.getopt(argument_list, short_options, long_options)
except getopt.error as err:
    # Output error, and return with an error code
    print(str(err))
    sys.exit(2)

# Evaluate given arguments
for current_argument, current_value in arguments:
    if current_argument in ("-h", "--help"):
        print(help_text)
        sys.exit(2)
    elif current_argument in ("-x", "--xml"):
        ccf_data_file = current_value
    elif current_argument in ("-c", "--ccf"):
        ccf = current_value
    elif current_argument in ("-o", "--output"):
        of = current_value
    elif current_argument in ("-d", "--dump"):
        dump = current_value
    elif current_argument in ("-m", "--dump_format"):
        dumpf = current_value
    elif current_argument in ("-i", "--can_id"):
        ccfid = current_value

ccf_data_file = 'examples/CCF_DATA_X250.exml.XML'

# We can't do anything unless we have the CCF XML and some CCF data to process, so check we have those
if ccf_data_file == None or (ccf == None and dump == None):
    print("SSD XML CCF_DATA file must be specified along with either a string containing the CCF or a dump file to process")
    sys.exit(2)

# Load the XML CCF data file
print('Processing', ccf_data_file)
root_node = ET.parse(ccf_data_file).getroot()

# Convert the SDD CCF_DATA into a more useful array of settings 
ccf_set = xmload.sddxconv(root_node)

# Check if we got any CCF settings from the XML, if not throw a wobbly
if ccf_set.empty:
    print('ERROR: No CCF data found in', ccf_data_file, '- aborting')
    sys.exit(2)
else:
    print('Processed', ccf_data_file)

# If we've got this far then we have a CCF XML file to play with so now lets read in the CCF itself.
# The job here is to have a normalised hexadeciaml string, start with checking if there is a dump file being used
# Currently this only supports options of candump format or a hex string, but made it extenable for future use by other ways of catching the CCF on the can.
if  ccf == None and (dump == None or os.path.isfile(dump) == False):
    print('CCF dump file was not found - aborting')
    sys.exit(2)
    
if dumpf == "cd":
    # candump format has been set so turn this into a long hexadeciemal string
    ccf = cdv(dump,ccfid)
elif dumpf == "st":
    # CCF string is in a file
    ccf_file = open(dump, "r")
    # read dump to a string
    ccf = ccf_file.read()
    ccf_file.close()

# Check we got something in the CCF string to play with
if ccf == None:
    print('CCF is empty - aborting')
    sys.exit(2)

# At this point we should have a CCF in a big old string, lets check its not garbage first
if re.search('[^A-F0-9]', ccf) != None:
    # CCF seems to have something that isn't hex in it, abort.
    print('Invalid CCF format, invalid hexadecimal character(s) found - abort')
    sys.exit(2)

# Now for the fun bit, where we try to match the settings to the CCF values
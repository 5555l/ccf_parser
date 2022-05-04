import sys
import getopt
import xml.etree.ElementTree as ET
import re
import os
import pandas as pd
from modules import cdconv
from modules import xmload

# Get full command-line arguments
full_cmd_arguments = sys.argv

# Keep all but the first
argument_list = full_cmd_arguments[1:]

# set the command line options
short_options = "hno:x:j:o:c:d:m:i"
long_options = ["help", "xml=", "json=", "ccf=", "output=", "dump=", "dump_format=", "can_id="]

help_text = ("\nccfparser options:\n"
             "   -x / --xml <filename> ......  SDD XML CCF_DATA file containing CCF values\n"
             "   -j / --json <filename> .....  Export CCF_DATA as JSON\n"
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
json_file = None
ccf = None
dumpf = None
dump = None
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
        if os.path.isfile(ccf_data_file) == False:
            print('CCF_DATA file not found at', ccf_data_file,'- aborting')
            sys.exit(2)
    elif current_argument in ("-j", "--json"):
        json_file = current_value
    elif current_argument in ("-c", "--ccf"):
        ccf = current_value
    elif current_argument in ("-o", "--output"):
        of = current_value
    elif current_argument in ("-d", "--dump"):
        dump = current_value
        if os.path.isfile(dump) == False:
            print('Dump file not found at', dump,'- aborting')
            sys.exit(2)
    elif current_argument in ("-m", "--dump_format"):
        dumpf = current_value
    elif current_argument in ("-i", "--can_id"):
        ccfid = current_value

# We can't do anything unless we have the CCF XML and some CCF data to process, so check we have those
if ccf_data_file == None or (ccf == None and dump == None):
    print("SSD XML CCF_DATA file must be specified along with either a string containing the CCF or a dump file to process")
    sys.exit(2)
elif dump != None and dumpf == None:
    # Dump file provided but not its format
    print('Dump file', dump, 'was specified but not its format')
    print(help_text)
    sys.exit(2)

# Load the XML CCF data file
print('Loading', ccf_data_file)
root_node = ET.parse(ccf_data_file).getroot()

# Convert the SDD CCF_DATA into a more useful array of settings 
ccf_set = xmload.sddxconv(root_node)
ccf_set.to_json(r'ccf_set.json')

# Check if we got any CCF settings from the XML, if not throw a wobbly
if ccf_set.empty:
    print('ERROR: No CCF data found in', ccf_data_file, '- aborting')
    sys.exit(2)
else:
    print('Processed', ccf_data_file)

# If the CCF_DATA export arg is set then export the settings as a JSON object
if json_file != None:
    print('Exporting CCF_DATA as JSON to', json_file)
    # Lets get rid of any old files from previous runs
    if os.path.exists(json_file):
        os.remove(json_file)
    ccf_set.to_json(r''+ json_file)

# If we've got this far then we have a CCF XML file to play with so now lets read in the CCF itself.
# The job here is to have a normalised hexadeciaml string, start with checking if there is a dump file being used
# Currently this only supports options of candump format or a hex string, but made it extenable for future use by other ways of catching the CCF on the can.
if ccf != None and dump == None and re.search('[^A-F0-9]', ccf) != None:
    # CCF was provided but seems to have something that isn't hex in it, no dump file was supplied either, so abort.
    print('Invalid CCF format, invalid hexadecimal character(s) found - abort')
    sys.exit(2)
elif ccf == None and (dump == None or os.path.isfile(dump) == False):
    # A CCF string wasn't provided and no dump file was specified or present, there's nothing to do here so stop.
    print('CCF data not found - aborting')
    sys.exit(2)
elif dump != None and dumpf == "cd":
    # dump file provided and candump format has been set so turn this into a long hexadeciemal string
    ccf = cdconv.convdump(dump,ccfid)
elif dump != None and dumpf == "st":
    # # dump file provided and string format has been set so load it from a file
    ccf_file = open(dump, "r")
    # read dump to a string
    ccf = ccf_file.read()
    ccf_file.close()

# Check we got something in the CCF string to play with
if ccf == None:
    print('CCF is empty - aborting')
    sys.exit(2)

# Now for the fun bit, where we try to match the settings to the CCF values
# We'll do this by terating through the df, setting by setting
for set in ccf_set.index:
    # Grab a setting
    idx = ccf_set.index.get_loc(set)
    ofs = ccf_set["offsets"][idx]
    msk = bin(int(ccf_set["mask"][idx], 16))
    opts = ccf_set["options"][idx]
    ttl = ccf_set["title"][idx]
    name = ccf_set["name"][idx]

    # Data offsets in CCF are as follows:
    # nnn nnn nnn nnn = 'start byte' 'end byte' 'start bit' 'end bit'
    sb = int(ofs[:3])
    eb = int(ofs[3:6])
    st = bin(int(ofs[6:9]))
    et = bin(int(ofs[9:12]))
    
    cs = ccf[sb:eb]
    print(sb, eb, st, et, msk, 'CCF', cs)
    
    if sb == 35: break

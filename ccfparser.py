import sys
import getopt
import xml.etree.ElementTree as ET
import re
import os
import pandas as pd
import numpy as np
from modules import cdconv
from modules import xmload

def findopt(optrow):
    if optrow.empty:
        op_conf='No valid setting found'
    elif optrow['option'].iloc[0] != '':
        op_conf=optrow['option'].iloc[0]
    elif optrow['tm'].iloc[0] != '':
        op_conf=optrow['tm'].iloc[0]
    elif optrow['tmid'].iloc[0] != '':
        op_conf=optrow['tmid'].iloc[0]
    return op_conf

# Get full command-line arguments
full_cmd_arguments = sys.argv

# Keep all but the first
argument_list = full_cmd_arguments[1:]

# set the command line options
short_options = "hno:x:jno:o:e:c:d:m:i"
long_options = ["help", "xml=", "json", "ccf=", "output=", "export=", "dump=", "dump_format=", "can_id="]

help_text = ("\nccfparser options:\n"
             "   -x / --xml <filename> ......  SDD XML CCF_DATA file containing CCF values\n"
             "   -j / --json ................  sets the output file format to json, default is a string\n"
             "   -o / --output <filename> ...  filename for outputting the result\n"
             "   -e / --export <filename> ...  filename for exporting CCF_DATA as json\n"
             "   -c / --ccf <ccf> ...........  ccf hexadecimal string to be decoded\n"
             "   -d / --dump <filename>......  file to be decoded, this will override any -ccf setting\n"
             "   -m / --dump_format <format>.  format of dump data, valid options are:\n"
             "                                   cd = can_utils candump format (default)\n"
             "                                   st = a hexadecimal string\n"
             "   -i / --can_id <canid>.......  canID (decimal) used in the can dump to broadcast CCF, default = 401\n\n"
             "XML file must be specified and either a string containing the CCF or a dump file to process\n")

# The following are things that need to exist in order for this to work, so set them to None and we'll check if they get data shoved in them later
ccf_data_file = None
of = ex = json = dump = None
ccf = None
dumpf = "cd" # set this as default format
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
        json = True
    elif current_argument in ("-c", "--ccf"):
        ccf = current_value
    elif current_argument in ("-o", "--output"):
        of = current_value
    elif current_argument in ("-e", "--export"):
        ex = current_value
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
    print(help_text)
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

# Check if we got any CCF settings from the XML, if not throw a wobbly
if ccf_set.empty:
    print('ERROR: No CCF data found in', ccf_data_file, '- aborting')
    sys.exit(2)
else:
    print('Processed', ccf_data_file)

###############################################################################
# If we've got this far then we have the settings from a CCF_DATA XML file
# to play with so now lets read in the CCF itself. The job here is to have a
# normalised hexadeciaml string, start with checking if there is a dump file
# being used. Currently this only supports options of candump format or a
# hex string, but made it extenable for future use by other ways of catching 
# the CCF on the can.
###############################################################################

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
    print('CCF is empty, either no CCF data was found or incorrect canID was used - aborting')
    sys.exit(2)

# The CCF is currently a hex string but it needs to be broken into a list of bytes
ccfhx = []
strccf=ccf
while True:
    # Grab first two characters in the string
    c = strccf[0:2]
    # Append them to lhx as a byte
    ccfhx.append(c)
    # drop the first two characters from the string
    strccf = strccf[2:]
    # Repeat until there are no more characters left in the string
    if strccf == '': 
        break

###############################################################################
# Now for the fun bit, where we try to match the settings in the CCF values
# We'll do this by iterating through the CCF_DATA, one by one and pulling the
# values from the CCF to see what its set too
###############################################################################


COLconfig = ["offsets", "mask", "ccfval", "title", "name", "setting"]
ve_config = pd.DataFrame(columns=COLconfig)

for set in ccf_set.index:
    # Get the index location of this setting
    idx = ccf_set.index.get_loc(set)
    # Grab the setting options
    ofs = ccf_set["offsets"][idx]
    # Make sure it knows the mask is a hex value
    msk = int(ccf_set["mask"][idx], 16)
    opts = ccf_set["options"][idx]
    typ = ccf_set["type"][idx]

    # Data offsets in CCF are as follows:
    # nnn nnn nnn nnn = 'start byte' 'end byte' 'start bit' 'end bit'
    sb = int(ofs[:3]) # start byte in CCF
    eb = int(ofs[3:6]) # end byte in CCF
    
    # Get the relevent data from the CCF based on the offset
    # python substring is an inclusive start but exclusive end position, so need to incremenet end byte by 1
    cs = ccfhx[sb:eb+1]

    # Put the things we know into the configuration
    ve_config.loc[idx] = ccf_set.loc[idx]
    ve_config["ccfval"][idx] = cs

    # Depending on the 'type' the bits mean different things
    if typ == "ASCII":
        # This is an ASCII string that is stored in hex, we need to turn that into standard text
        
        if '00' in cs:
            # If the setting is 0 that means its not set or not applicable
            ve_conf = "N/A"
        else:
            # Convert all values in the list into strings and join them together
            st = [str(i).zfill(2) for i in cs]

            # Join the whole thing together and convert to ASCII
            bta = bytearray.fromhex("".join(st))
            ve_conf = bta.decode()
    elif typ == "ENUM" or typ == "BOOL":
        # If its an enurmated list, the list of values is in the options, defined by bitmask the CCF value
        # If its a boolean its TRUE or FALSE, i.e. a maximum of two possible options per bit in the CCF byte defined by the mask
        # First turn the values into an int
        cn = [str(i).zfill(2) for i in cs]
        ci = int("".join(cn),16)
        # Apply the mask to the CCF to see what option is set
        opt_val = np.bitwise_and(ci, msk)
        
        # Format it so that it looks like a hex string
        opk='0x'+(hex(opt_val).lstrip('0x').zfill(2)).upper()
        # Go find out what option that is, reset the index 
        # There might be lots of ways to describe the setting, try and find the best one
        ve_conf=findopt(opts[opts["ccfval"] == opk].reset_index(drop=True))
    elif typ == "BIN":
        # This holds some sort of value to be used, such as a delay time or target tyre pressure
        cn = [str(i).zfill(2) for i in cs]
        ci = int("".join(cn),16)
        # Apply the mask to the CCF to see what option is set
        opt_val = np.bitwise_and(ci, msk)
        ve_conf = opt_val
    ve_config["setting"][idx] = ve_conf

# We now should have the car configuration lets dump it out somewhere
# If an export has been requested, dump the CCF_DATA to a file
if ex !=None:
    print('Exporting CCF_DATA to', ex)
    # Lets get rid of any old files from previous runs
    if os.path.exists(ex): os.remove(ex)
    ccf_set.to_json(r''+ ex)

# If an output filename is given then write it to the file
if of != None:
    print('Exporting CCF settings to', of)
    # Lets get rid of any old files from previous runs
    if os.path.exists(of): os.remove(of)
    # Default output is a csv, but optionally can be a json
    if json == True:
        ve_config.to_json(r''+ of)
    else:
        ve_config.to_csv(r''+ of)
else:
    # otherwise output to stdout
    print(ve_config.to_string())
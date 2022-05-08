import sys
import getopt
import xml.etree.ElementTree as ET
import re
import os
import pandas as pd
import numpy as np
from modules import cdconv
from modules import xmload
from modules import ccfdatavals

def findopt(optrow):
    if optrow.empty:
        op_conf='No valid setting found'
    elif optrow['tmid'].iloc[0] != None:
        op_conf=optrow['tmid'].iloc[0]
    elif optrow['tm'].iloc[0] != None:
        op_conf=optrow['tm'].iloc[0]    
    elif optrow['option'].iloc[0] != None:
        op_conf=optrow['option'].iloc[0]
    return op_conf

# Get full command-line arguments
full_cmd_arguments = sys.argv

# Keep all but the first
argument_list = full_cmd_arguments[1:]

# set the command line options
short_options = "hno:x:jno:o:e:c:f:d:m:i:r:t:"
long_options = ["help", "xml=", "json", "output=", "export=", "ccfhex=", "ccf=", "dump=", "dump_format=", "can_id=", "readable=", "tdir="]

help_text = ("\nccfparser options:\n"
             "   -x / --xml <filename> ......  SDD XML CCF_DATA file containing CCF options\n"
             "   -j / --json ................  sets the CCF setting output file format to json, default is csv\n"
             "   -o / --output <filename> ...  filename for outputting the result\n"
             "   -e / --export <filename> ...  filename for exporting CCF_DATA as json\n"
             "   -c / --ccfhex <ccf> ........  CCF hexadecimal string to be decoded\n"
             "   -f / --ccf <filename>.......  filename for exporting CCF hex string\n"
             "   -d / --dump <filename>......  file to be decoded, this will override any -ccf setting\n"
             "   -m / --dump_format <format>.  format of dump data, valid options are:\n"
             "                                   cd = can_utils candump format (default)\n"
             "                                   st = a hexadecimal string\n"
             "   -i / --can_id <canid>.......  canID (decimal) used in the can dump to broadcast CCF, default = 401 (JLR)\n\n"
             "   -r / --readable <language>..  Use human readable values in the output.\n"
             "                                 For this to work a settings cache must exist or -t must be set\n"
             "   -t / --tdir <directory>.....  Location of IDS/SDD/XML/text used to build human readable values\n"
             "The CCF_DATA XML file must be specified along with either a string containing the CCF or a dump file to process.\n"
             "If a human readable values cache is present it will convert CCF settings to English by default (equivalent to -r eng)\n")

# The following are things that need to exist in order for this to work, so set them to None and we'll check if they get data shoved in them later
ccf_data_file = None
ccfout = of = ex = json = dump = tdir = None
ccf = ccf_vr = None
dumpf = "cd" # set this as default format
ccfid = "401" # set this as a default canID for the CCF broadcast
dlang = vlang = "eng" # set this as a default
cachefile = ".__@values_cache__"

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
    elif current_argument in ("-c", "--ccfhex"):
        ccf = current_value
    elif current_argument in ("-f", "--ccf"):
        ccfout = current_value
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
    elif current_argument in ("-r", "--readable"):
        vlang = current_value.lower()
    elif current_argument in ("-t", "--tdir"):
        tdir = current_value

# We can't do anything unless we have the CCF_DATA XML and some CCF data to process, so check we have those
if ccf_data_file == None or (ccf == None and dump == None):
    print("SSD XML CCF_DATA file must be specified along with either a string containing the CCF or a dump file to process")
    print(help_text)
    sys.exit(2)

# Convert the SDD CCF_DATA into a more useful array of settings 
ccf_set = xmload.sddxconv(ccf_data_file)

# Check if we got any CCF settings from the XML, if not throw a wobbly
if ccf_set.empty:
    print('ERROR: No CCF_DATA found in', ccf_data_file, '- aborting')
    sys.exit(2)
else:
    print('Processed', ccf_data_file)

###############################################################################
# If we've got this far then we have the settings from a CCF_DATA XML file
# to play with so now lets read in the CCF itself. The job here is to have a
# normalised hexadecimal string, start with checking if there is a dump file
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
    print('No CCF data found. Either it was not provided or dump file does not exist - aborting')
    sys.exit(2)
elif dump != None and dumpf == "cd":
    # dump file provided and candump format has been set so turn this into a long hexadecimal string
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
    # python substring is an inclusive start but exclusive end position, so need to increment end byte by 1
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
        # If its an enumerated list, the list of values is in the options, defined by bitmask the CCF value
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
    # Store the config in the dataframe
    ve_config["setting"][idx] = ve_conf

# We now should have the car configuration 
# If a values cache file exists use that to turn all the reference keys into 
# natural language.

if ccfdatavals.checkcache(cachefile):
    # cache file exists so load the values
    print('Found cache file - loading values')
    ccf_vr=ccfdatavals.readcache(cachefile)
elif tdir != None:
    # IDS/XML/text directory has been provided so attempt to build the cache
    print('No cache file found but SDD directory provided, attempting to build new cache')
    ccfdatavals.buildcache(tdir,cachefile)
    ccf_vr=ccfdatavals.readcache(cachefile)

if ccf_vr.size != 0:
    # Lets try and translate the options settings into human readable words
    print('Attempting to convert tags to words using langauge', vlang)
    # First test that the lang setting makes sense
    if not vlang in ccf_vr.columns:
        print('Specified langauge' , vlang, 'not supported, changing to', dlang)
        flang = ccf_vr.columns.values.tolist()
        flang.remove('tmid')
        del flang[0]
        print('Supporting languages are', flang)
        # If the lang isn't there use the default 
        vlang=dlang
    
    # Turn the dataframe into a list for ease of finding indexes
    # There's probably a neater way to do this but I don't know what it is
    tmid_vals = ccf_vr['tmid'].values.tolist()
    tmid_lang = ccf_vr[vlang].values.tolist()

    # Let's see if we can find values for the settings and titles we discovered
    for stx in ve_config.index:
        stf = ve_config.index.get_loc(stx)
        
        sval = ve_config['setting'][stf]
        
        try:
            sv=tmid_vals.index(sval)
        except ValueError:
            sv = ''
        if sv !='':
            # if we got some shove them into the dataframe
            ve_config['setting'][stf] = tmid_lang[sv]
        
        # Do the same thing again but for the titles
        tval = ve_config['title'][stf]
        
        try:
            tv=tmid_vals.index(tval)
        except ValueError:
            tv = ''
        if tv !='':
            ve_config['title'][stf] = tmid_lang[tv]
    # All done with translations!
else:
    print('No language cache found and no SDD directory provided, skipping translating values step')


# If an export has been requested, dump the CCF_DATA to a file

if ccfout !=None:
    print('Exporting CCF hex string to', ccfout)
    # Lets get rid of any old files from previous runs
    if os.path.exists(ccfout): os.remove(ccfout)
    f = open(ccfout, "w")
    f.write(ccf)
    f.close()

if ex !=None:
    print('Exporting CCF_DATA to', ex)
    # Lets get rid of any old files from previous runs
    if os.path.exists(ex): os.remove(ex)
    ccf_set.to_json(r''+ ex)

# If an setting output filename is given then write it to the file
if of != None:
    print('Writing CCF settings to', of)
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
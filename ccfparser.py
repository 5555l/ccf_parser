import sys
import getopt
import xml.etree.ElementTree as ET
import re
import os
import pandas as pd
import numpy as np
from modules import cdconv
from modules import ccfdataload
from modules import ccfdatatext
from modules import vinload

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

def ccf_to_bytes(strccf):
    c_bytes = []
    while True:
        # Grab first two characters in the string
        c = strccf[0:2]
        # Append them to lhx as a byte
        c_bytes.append(c)
        # drop the first two characters from the string
        strccf = strccf[2:]
        # Repeat until there are no more characters left in the string
        if strccf == '': 
            break
    return(c_bytes)

# Get full command-line arguments
full_cmd_arguments = sys.argv

# Keep all but the first
argument_list = full_cmd_arguments[1:]

# set the command line options
short_options = "hno:x:jno:o:e:c:f:d:m:i:u:l:t:bno:v:y:"
long_options = ["help", "xml=", "json", "output=", "export=", "ccfhex=", "ccf=", "dump=", "dump_format=", "can_id=", "can_id_eucd=", "lang=", "tdir=", "rebuild", "vin=", "xdir="]

help_text = ("\noptions:\n"
             "   -x / --xml <filename>.......  SDD XML CCF_DATA file containing CCF options\n"
             "   -j / --json.................  sets the CCF setting output file format to json, default is csv\n"
             "   -o / --output <filename>....  filename for outputting the result\n"
             "   -e / --export <filename>....  filename for exporting CCF_DATA as json\n"
             "   -c / --ccfhex <ccf>.........  CCF hexadecimal string to be decoded\n"
             "   -f / --ccf <filename>.......  filename for exporting CCF hex string\n"
             "   -d / --dump <filename>......  can dump file to be decoded, this will override any -ccf setting\n"
             "   -m / --dump_format <format>.  format of dump data, valid options are:\n"
             "                                   cd = can_utils candump format (default)\n"
             "                                   st = a hexadecimal string\n"
             "   -i / --can_id <canid>.......  canID used in the can dump to broadcast CCF, default = 401 (JLR)\n"
             "   -u / --can_id_eucd <canid>..  canID used in the can dump to broadcast CCF_EUCD, default = 402 (JLR)\n"
             "   -l / --lang <language>......  use human readable values in <language> in the output.\n"
             "                                 For this to work a settings cache must exist or -t must be set.\n"
             "                                 <language> must be of type supported by SDD otherwise it defaults to 'eng'\n"
             "   -t / --tdir <directory>.....  location of IDS/SDD/XML/text used to build human readable values\n"
             "   -b / --rebuild..............  rebuild the settings cache data, -t must also be set\n"
             "   -v / --vin <VIN>............  use manually provided VIN instead of automatically detecting it from the CCF\n"
             "   -y / --xdir <directory>.....  location of IDS/XML where CCF_DATA, VINDECODE and VEHICLE_MANIFEST files are\n"
             "The CCF_DATA XML file must be specified along with either a string containing the CCF or a dump file to process.\n")

# The following are things that need to exist in order for this to work, so set them to None and we'll check if they get data shoved in them later
ccf_data_file = None
ccfout = of = ex = json = dump = tdir = vin= xmlpath = manifest = None
ccf = ccf_vr = model_data = ccf_eucd= None
rbv = rebuild = False
dumpf = "cd" # set this as default format
ccfid = "401" # set this as a default canID for the CCF broadcast
ccfeucdid = "402" # set this as a default canID for the CCF_EUCD broadcast
dlang = vlang = "eng" # set this as a default
cachefile = ".__@values_cache__"

#####################################################################################
# Test for command line options
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
    elif current_argument in ("-u", "--can_id_eucd"):
        ccfeucdid = current_value
    elif current_argument in ("-l", "--lang"):
        vlang = current_value.lower()
        rbv = True
    elif current_argument in ("-t", "--tdir"):
        tdir = current_value
    elif current_argument in ("-r", "--rebuild"):
        rebuild = True
    elif current_argument in ("-v", "--vin"):
        vin = current_value
    elif current_argument in ("-y", "--xdir"):
        xmlpath = current_value

#####################################################################################
# Thats the end of the boring arguments stuff, lets check what we've been asked to do makes sense
# But we can't do anything unless we have the CCF_DATA XML and some CCF data to process, so check we have those
if (ccf_data_file == None and xmlpath == None) or (ccf == None and dump == None):
    print("SSD XML CCF_DATA file (--xml) or directory for XML files (--xdir) must be specified along with either a string containing the CCF or a dump file to process")
    print(help_text)
    sys.exit(2)

# Check we haven't been asked to rebuild the cache but forgotten to provide the tdir location
if rebuild == True and tdir == None:
    print("Rebuild requested but no target directory (--tdir) provided")
    print(help_text)
    sys.exit(2)

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
    # See if we can find the EUCD settings from the dump file too
    ccf_eucd = cdconv.convdump(dump,ccfeucdid)
elif dump != None and dumpf == "st":
    # dump file provided and string format has been set so load it from a file
    ccf_file = open(dump, "r")
    # read dump to a string
    ccf = ccf_file.read()
    ccf_file.close()

# Check we got something in the CCF string to play with
if ccf == None:
    print('CCF is empty, either no CCF data was found or incorrect canID was used')
    sys.exit(2)
if ccf_eucd == None:
    print('No EUCD data found - skipping EUCD data extraction')

#####################################################################################
# Ok, we seem to have enough to work with so lets have a go.
# The CCF is currently a long string but it needs to be broken into a list of bytes
ccfhx = ccf_to_bytes(ccf)
if ccf_eucd != None: eucdhx = ccf_to_bytes(ccf_eucd)

# If the XML path is given find the VINDecode and Vehicle Manifest files needed
if xmlpath != None:
    # See if we can find the vindecode and manifest XML files
    for root, dirs, files in os.walk(xmlpath):
        for file in files:
            if re.search('^VINDECODE\..*XML.*', file.upper()):
                vinxml = os.path.join(root,file)
            if re.search('^VEHICLE_MANIFEST\..*XML.*', file.upper()):
                manifest = os.path.join(root,file)

if vin == None and vinxml != None:
    # First we're going to grab the VIN from the CCF and decode it to find out what vehicle we're dealing with
    vinloc='003019000135' # This is the default for Jag, not sure how it knows this so its hardcoded atm
    
    vin_s = int(vinloc[:3]) # start of vin bytes
    vin_e = int(vinloc[3:6]) # end of vin bytes

    # Get the vin data from the CCF based on the offset
    # python substring is an inclusive start but exclusive end position, so need to increment end byte by 1
    vin_hex = ccfhx[vin_s:vin_e+1]
    v_st = [str(i).zfill(2) for i in vin_hex]

    # Check if the data looks anything like a VIN, it should be ascii codes for A-Z 0-9
    vin_detect=False
    for asc in v_st:
        if int(asc,16) >= 48 and int(asc,16) <=90:
            vin_detect = True
        else:
            vin_detect = False
        if vin_detect == False: break

    if vin_detect == True:
        # Join the whole thing together and convert to ASCII
        v_bta = bytearray.fromhex("".join(v_st))
        vin = v_bta.decode()
        print('Detected VIN:', vin)
    else:
        print('VIN not automatically detected, please provide manually - aborting')
        sys.exit(2)

#####################################################################################
# Next get the model_info and date from the VINDecode XML file and find the correct data file
if vin != None and vinxml != None:
    model_info,model_data=vinload.vindecode(vin,vinxml)

if model_info["Model"] != '' :
    # pull the data together
    model = model_info["Model"]
    myear = model_data.loc[model_data["title_text"] == "ModelYear"]["setting_text"][1]
    eng = model_data.loc[model_data["title_text"] == "Engine"]["setting_text"][1]
    if model != '' and myear !='' and eng !='':
        print('Found model:', model, 'year:', myear, 'engine:', eng)
        mident={"Model":model,"ModelYear":myear, "Engine": eng, "Brand": model_info["Brand"]}

        # If no CCF_DATA file is given, go and find the correct one - XML path must be set
        if ccf_data_file == None and xmlpath != None and manifest != None:
            
            ve_manifest = vinload.findccfdataid(manifest,mident,vin)
            ve_ccf = ve_manifest.get('XML_CCF_TEMPLATE')

            # Now we know the CCF_DATA file we need see if we can find it in the file system
            src_ccf = '^' + ve_manifest.get('XML_CCF_TEMPLATE').replace('.xml','') + '\..*XML.*'
            for root, dirs, files in os.walk(xmlpath):
                for file in files:
                    if re.search(src_ccf.upper(), file.upper()):
                        ccf_data_file = os.path.join(root,file)
                        print('Found target CFF_DATA file:', ccf_data_file)
        else:
            print('Can not process manifest: no CCF data file given, manifest detected or XML path set')
            sys.exit(2)
    else:
        print('Failed to find model, year and/or engine type from VIN')
        sys.exit(2)

#####################################################################################
# Convert the SDD CCF_DATA into a more useful array of settings 
ccf_set = ccfdataload.param(ccf_data_file,"CCF")

# Check if we got any CCF settings from the XML, if not throw a wobbly
if ccf_set.empty:
    print('ERROR: No CCF_DATA found in', ccf_data_file, '- aborting')
    sys.exit(2)
else:
    # See if we also need to grab the CCF_EUCD data and if so go and get them
    if ccf_eucd !=None: 
        ccf_set = pd.concat([ccf_set, ccfdataload.param(ccf_data_file,"EUCD")],ignore_index=True)

print('Processed', ccf_data_file)

###############################################################################
# Now for the fun bit, where we try to match the settings in the CCF values
# We'll do this by iterating through the CCF_DATA, one by one and pulling the
# values from the CCF to see what its set too
###############################################################################

# Create the arrays we're going to keep stuff in
COLconfig = ["src", "offsets", "mask", "ccfval", "title", "title_text","name", "setting","setting_text"]
ve_config = pd.DataFrame(columns=COLconfig)

# Process values against CCF_DATA
for set in ccf_set.index:
    # Get the index location of this setting
    idx = ccf_set.index.get_loc(set)
    # Grab the setting options
    ofs = ccf_set["offsets"][idx]
    src = ccf_set['src'][idx]
    # Make sure it knows the mask is a hex value
    msk = int(ccf_set["mask"][idx], 16)
    opts = ccf_set["options"][idx]
    typ = ccf_set["type"][idx]


    # Data offsets in CCF are as follows:
    # nnn nnn nnn nnn = 'start byte' 'end byte' 'start bit' 'end bit'
    sb = int(ofs[:3]) # start byte in CCF
    eb = int(ofs[3:6]) # end byte in CCF
    
    # Get the relevant data from the CCF based on the offset and source (CCF/CCF_EUCD)
    # python substring is an inclusive start but exclusive end position, so need to increment end byte by 1
    if src == "CCF":
        cs = ccfhx[sb:eb+1]
    elif src == "EUCD":
        cs = eucdhx[sb:eb+1]

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
        # Go find out what option that is
        ve_conf=findopt(opts[opts["ccfval"] == opk])
    elif typ == "BIN":
        # This holds some sort of value to be used, such as a delay time or target tyre pressure
        cn = [str(i).zfill(2) for i in cs]
        ci = int("".join(cn),16)
        # Apply the mask to the CCF to see what option is set
        opt_val = np.bitwise_and(ci, msk)
        ve_conf = opt_val
    # Store the ccf setting in the dataframe
    if "@" in str(ve_conf):
        ve_config["setting"][idx] = ve_conf
    else: 
        ve_config["setting_text"][idx] = ve_conf
    ve_config["src"][idx] = src

# Merge in information taken from model_data into the main ve_config and sort it
if len(model_data) !=0:
    ve_config = pd.concat([ve_config, model_data] ,ignore_index=True)
    ve_config = ve_config.sort_values(by=["src","offsets"], ascending=True).reset_index(drop=True)

# We now should have the car configuration 
# If a values cache file exists and --lang is set use that to turn all the reference keys into 
# natural language.
cache_present = False
if ccfdatatext.checkcache(cachefile) == True and rbv == True and rebuild == False:
    # cache file exists so load the values
    print('Found cache file - loading values')
    ccf_vr=ccfdatatext.readcache(cachefile)
    cache_present = True
elif (tdir != None and rbv == True and ccfdatatext.checkcache(cachefile) == False) or (tdir != None and rbv == True and ccfdatatext.checkcache(cachefile) == True and rebuild == True):
    # IDS/XML/text directory has been provided so attempt to build the cache
    print('IDS/SDD/XML/text directory provided, attempting to build new cache')
    ccf_vr = ccfdatatext.buildcache(tdir,cachefile)
    cache_present = True

# If we have values in ccf_vr that means somewhere we got asked to make things human readable
if cache_present == True:
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
            # if we got some data shove them into the dataframe
            ve_config['setting_text'][stf] = tmid_lang[sv]
        
        # Do the same thing again but for the titles
        tval = ve_config['title'][stf]
        
        try:
            tv=tmid_vals.index(tval)
        except ValueError:
            tv = ''
        if tv !='':
            ve_config['title_text'][stf] = tmid_lang[tv]
    # All done with translations!
else:
    print('No language cache found and no SDD directory provided, skipping translating values step')

# If an export has been requested, dump the CCF_DATA to a file

if ccfout !=None:
    print('Exporting CCF hex string')
    # Lets get rid of any old files from previous runs
    if os.path.exists(ccfout): os.remove(ccfout)
    f = open(ccfout, "w")
    f.write(ccf)
    f.close()
    if ccf_eucd != None:
        if os.path.exists(ccfout + '_eucd'): os.remove(ccfout)
        f = open(ccfout + '_eucd', "w")
        f.write(ccf_eucd)
        f.close()

if ex !=None:
    print('Exporting CCF_DATA to', ex)
    # Lets get rid of any old files from previous runs
    if os.path.exists(ex): os.remove(ex)
    ccf_set.to_json(r''+ ex,index=False)

# If an setting output filename is given then write it to the file
if of != None:
    print('Writing CCF settings to', of)
    # Lets get rid of any old files from previous runs
    if os.path.exists(of): os.remove(of)
    # Default output is a csv, but optionally can be a json
    if json == True:
        ve_config.to_json(r''+ of)
    else:
        ve_config.to_csv(r''+ of,index=False)
else:
    # otherwise output to stdout
    print(ve_config.to_string(index=False))
###############################################################################
# Read all SDD XML files that contain the human readable versions of the
# settings. Running this directly will build the cache
# If you have SDD it should be under <SDD parent dir>IDS/XML/text. These must 
# have been decrypted from exml to xml before using this
###############################################################################
import pandas as pd
import os
import re
from lxml import etree as et

def buildcache(td,cf):
    # We're going to try and make a list of all the files that have labels in.
    print('Locating SSD values files in', td) 
    fl = []
    for root, dirs, files in os.walk(td):
        for file in files:
            if re.search('^\@.*XML$', file.upper()):
                fl.append(os.path.join(root,file))
    
    # Righto, lets step through everyone of those files and get some values
    print('Found',len(fl),'files')

    # Initialise values settings df
    ccf_hr = pd.DataFrame()
    # Go through every file we found
    print('Processing XML files, we may be some time....')

    for fn in fl:
        tree = et.parse(fn)
        root = tree.getroot()
        if fl.index(fn) % 25 == 0:
            print(f'',fl.index(fn), fn, end='                                            \r')
        
        # Start by finding the tm id in the XML file
        if root.attrib['id'] != '':
            tmid = root.attrib['id']
            # Make some temp lists
            ht = [tmid]
            cl = ["tmid"]
            # Cycle through all the "tu" options
            for tu in root.findall("tu"):
                # Randomly SDD sometimes seems to have CRLF in the middle of the tag text
                ht.append(tu.text.replace('\n', ' '))
                cl.append(tu.nsmap["lang"].lower())
            # Shove it into a temp dataframe
            nt=[ht]
            dft = pd.DataFrame(nt)
            dft.columns = [cl]
            # If the ccf_hr is empty fill it with data from the first file, otherwise append to existing
            if ccf_hr.empty:
                ccf_hr=dft
            else:
                ccf_hr=pd.concat([ccf_hr, dft], ignore_index=True)

    # Lets get rid of any old files from previous runs
    if os.path.exists(cf): os.remove(cf)
    
    print('\nFound',ccf_hr.size,'entries\nWriting to cache', cf)
    # Write to the cache file
    ccf_hr.to_csv(r''+ cf)
    # Read it back in again to make sure it works
    cache = readcache(cf)
    return (cache)

def checkcache(cf):
    # Check if the cache file is present. 
    if os.path.isfile(cf):
        c = True
    else:
        c = False
    return c

def readcache(cf):
    cache = pd.read_csv(cf)
    return cache

if __name__ == '__main__':
    import sys
    import getopt

    # This will build a values cache at the specified location

    # Get full command-line arguments
    full_cmd_arguments = sys.argv

    # Keep all but the first
    argument_list = full_cmd_arguments[1:]

    # set the command line options
    short_options = "hno:t:c:"
    long_options = ["help", "tdir=", "cache="]

    help_text = ("\noptions:\n"
                "   -t / --tdir <directory>......  Location of IDS/SDD/XML/text\n"
                "   -c / --cache <filename>......  Filename for cache\n"
                "All options are mandatory\n")

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
        elif current_argument in ("-t", "--tdir"):
            dir = current_value
            if os.path.isdir(dir) == False:
                print('Directory not found or access denied at', dir,'- aborting')
                sys.exit(2)
        elif current_argument in ("-c", "--cache"):
            cache_file = current_value
    
    # We can't do anything unless we have the <SDD parent dir>/IDS/XML/text and a cache file specified
    if dir == None :
        print("\nLocation of IDS/SDD/XML/text not provided - aborting\n\n")
        print(help_text)
        sys.exit(2)
    if cache_file == None :
        print("\nLocation of cache file not provided - aborting\n\n")
        print(help_text)
        sys.exit(2)
    
    # Build the cache 
    cache = buildcache(dir,cache_file)
    if len(cache) !=0: print('Built cache successfully')
    
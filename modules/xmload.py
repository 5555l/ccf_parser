###############################################################################
# Turn an SDD XML CCF_DATA files into an array of settings
# This is a nightmarish mish mash of some confusing XML but it gets there in the end
###############################################################################

import pandas as pd

def sddxconv(root):
    # Set out the format of the dataframes we want to use
    CCFcols = ["offsets", "title", "name", "mask", "type", "options"]
    OPTcols = ["ccfval", "option", "tm", "tmid"]
    
    tag = None 
    
    # Initlise settings df
    settings = pd.DataFrame(columns=CCFcols)

    # We're going to extract all the possible CCF options for this vehicle
    # Start by finding the <parameters> in CCF section of the XML file
    for tag in root.findall("block[@name='CCF']/group/parameter"):
         # Get the attributes of the <parameters> for this vehicle type
        offsets = tag.attrib['id'].replace('_','')

        # Grab the <parameter_title>, if there isn't set make it None 
        title = None
        ptitle = tag.find('parameter_title')
        if ptitle != None: 
            # Sometimes there is no text for the title, but there is an id=, so use that if there is no text
            t = ptitle.find('tm').text
            try:
                d = ptitle.find('tm').attrib['id']
            except KeyError:
                d = None
            if t != None:
                title = t
            else:
                title = d
        
        # Create a dataframe for the options
        opt = pd.DataFrame(columns=OPTcols)

        # For each <parameter>, check if there are mulitple allowable <options> (sometimes there are none for a particular vehicle)
        for option in tag.findall('select/option'):
            value = option.attrib['value']
            optname = option.attrib['name']

            # Check if there is a <tm> element (it sometimes has more human readable version of the option)
            tmtext = option.find('tm').text
            try:
                tmid = option.find('tm').attrib['id']
            except KeyError:
                tmid = None

            # Put the option together
            optdata = {
                "ccfval" : [value],
                "option": [optname],
                "tm": [tmtext],
                "tmid" : [tmid],
            }

            # Push this into the options dataframe
            opt = opt.append(pd.DataFrame(optdata), ignore_index=True)

        # Put the setting data together
        data1 = {
            "offsets" : [offsets],
            "title": [title],
            "name": [tag.attrib['name']],
            "mask" : [tag.attrib['mask']],
            "type" : [tag.attrib['type']],
            "options": [opt],
        }
        # Create a df in the same format as the settings df
        cfs = pd.DataFrame(data1, columns=CCFcols)
        # Append the found settings to the settings df
        settings = settings.append(cfs, ignore_index=True)
    
    # We're all done here, we should no have a big dataframe of settings to play with
    return settings
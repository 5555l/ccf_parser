###############################################################################
# Turn an SDD XML CCF_DATA files into an array of settings
# This is a nightmarish mish mash of some confusing XML but it gets there in the end
###############################################################################
import re
import pandas as pd
from lxml import etree as ET

def sddxconv(xfn):
    # Set out the format of the dataframes we want to use
    CCFcols = ["offsets", "title", "name", "mask", "type", "options"]
    OPTcols = ["ccfval", "option", "tm", "tmid"]
    
    # Load the XML CCF_DATA file
    print('Loading', xfn)

    root = ET.parse(xfn).getroot()

    tag = None 
    
    # Initialise settings df
    settings = pd.DataFrame(columns=CCFcols)

    # We're going to extract all the possible CCF options for this vehicle
    # Start by finding the <parameters> in CCF section of the XML file
    for tag in root.findall("block[@name='CCF']/group/parameter"):
         # Get the attributes of the <parameters> for this vehicle type
        offsets = tag.attrib['id'].replace('_','')

        # Grab the <parameter_title>, if there isn't set make it None 
        #title = None
        ptitle = tag.find('parameter_title')
        if ptitle != None: 
            # Sometimes there is no id=, so use text if there instead
            try:
                title = ptitle.find('tm').attrib['id']
            except KeyError:
                title = ptitle.find('tm').text
        else:
            title = None
        # Create a dataframe for the options
        opt = pd.DataFrame(columns=OPTcols)

        # For each <parameter>, check if there are multiple allowable <options> (sometimes there are none for a particular vehicle)
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
        
        # Sometimes the mask is messed up, it needs to be in 0x00 format, so lets get it and check its ok    
        mk = tag.attrib['mask']
        if not re.search('\A0x[A-F0-9]{2}\Z', mk):
            print('Mask appears badly formatted, got', mk + ', normalising to ', end='')
            mk = '0x'+(mk.lstrip('0x').zfill(2)).upper()
            print(mk)

        # Put the setting data together
        data1 = {
            "offsets" : [offsets],
            "title": [title],
            "name": [tag.attrib['name']],
            "mask" : [mk],
            "type" : [tag.attrib['type']],
            "options": [opt],
        }
        # Create a df in the same format as the settings df
        cfs = pd.DataFrame(data1, columns=CCFcols)
        # Append the found settings to the settings df
        settings = settings.append(cfs, ignore_index=True)
    
    # We're all done here, we should no have a big dataframe of settings to play with
    return settings
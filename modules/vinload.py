###############################################################################
# Decode VIN based on SDD XML VINDecode
# Return as CCF setting
###############################################################################
from distutils.command.sdist import sdist
import sys
import pandas as pd
from lxml import etree as ET

def vinchar(ch):
    if ch.count(',') != 0:
        # string has start and end bytes
        bt=ch.split(',', 1)
        sc = int(bt[0])
        ec = int(bt[1])
    else:
        # Else its just one value
        sc = ec = int(ch)
    rtr = [sc,ec]
    return rtr

def checkchar(cp,vn):
    # Test the thing we've learnt against the vin. 
    # Get the byte position(s) we're going to test
    cr=vinchar(cp)
    # Get the thing we are going to test
    test = vn[cr[0]-1:cr[1]]
    
    return test

def vindecode(vin,dx):
    vincols = ["src","offsets", "mask", "ccfval", "title", "title_text","name", "setting","setting_text"]
    vin=vin.upper()

    # Load the XML VINdecode file
    print('Checking', dx,'for VIN', vin)

    root = ET.parse(dx).getroot()

    model = None 

    # We're going to work out what vehicle this is
    # Start by finding the <DecodeModel> in CCF section of the XML file
    for tag in root.findall("Models/VIN"):
         # Get the model_id for this vehicle type
        model_id = tag.attrib['DecodeModel']

        is_model = False
        
        # For each <test>, get the rules that decide what the model is
        for mdl in tag.findall('Test'):
            charpos = mdl.attrib['CharPos']
            opt = mdl.attrib['Operator'].upper()
            charval= mdl.attrib['CharValue'].upper()
          
            # Get the thing we are going to test
            val_test = checkchar(charpos,vin)
            
            if opt == 'EQUAL':
                # Test is positive match
                if val_test == charval:
                    is_model = True
                else:
                    is_model = False
            elif opt == 'NOT_EQUAL':
                if val_test != charval:
                    is_model = True
                else:
                    is_model = False

            # As soon as anything is false, this isn't our model, so move on.
            if is_model == False:
                break
        # If we find a matching model then store that and exit
        if is_model == True:
            model=model_id

            break
    # We've now got the model ID so we need to look up what that is

    model_data=pd.DataFrame(columns=vincols)
    model_info = {}

    if model != '':
        print('Found matching model id:' + model)
        # Get the config data for this model
        for decm in root.findall("Decodes/DecodeModel[@id='" + model + "']/Attribute"):
            name = decm.attrib['Name']
            try:
                decode = decm.attrib['Decode'].strip()
            except KeyError:
                decode = ''
            try:
                char_val = decm.attrib['Char']
            except KeyError:
                char_val = ''

            tdv=pd.DataFrame(columns=vincols,index=[1])

            # If there is a char set then need to compare it to the vin            
            if char_val != '':
                val = checkchar(char_val,vin)
                decode = decm.find("Value[@Value='" + val + "']").attrib['Decode'].strip()
                oft = vinchar(char_val)
                
                # Work out the offsets
                vin_oft = str(oft[0]).zfill(3) + str(oft[1]).zfill(3) + str((((oft[1]-oft[0])+1)*8-1)).zfill(6) 
                
                tdv["offsets"][1] = vin_oft
                tdv["mask"][1] = "0xFF"
                
                # Check if its more than one character, if so split it into single characters; always store it in ASCII
                if len(val) >= 2:
                    lst=[]
                    for l in val:
                        lst.append(l.encode('utf-8').hex())
                    tdv["ccfval"][1] = lst
                else:
                    tdv["ccfval"][1] = [val.encode('utf-8').hex()]

                tdv["title_text"][1] = name
                tdv["setting_text"][1] = decode 
                model_data = pd.concat([model_data,tdv])
            else:
                # If char is nothing then its some descriptive text about the model, put that in a dict for later
                model_info.update({name:decode})
    else:
        print('No model found - aborting')
        sys.exit(2)
    model_data["src"] = "CCF"
    return (model_info,model_data)

def findccfdataid(manf,mident,vin):
    # Read the XML in
    root = ET.parse(manf).getroot()

    # Find a tag that matches the brand 
    
    is_model = False
    manifest_id = None

    for tag in root.findall("vehicle_range[@brand='" + mident["Brand"].lower() + "']/vehicle"):

        # Check if this matches the model, if not break and try the next one
        try:
            tag.find("model[@id='" + mident["Model"] + "']").attrib['id'] == mident["Model"]
        except AttributeError:
            continue
        
        for vrnt in tag.findall('variant'):
            # Check the VIN range for the variant
            # Get the last part of the VIN
            s_vin=vin[11:17]
            
            # Get the VIN range for the variant
            min_vin=vrnt.find('vin/min').text
            max_vin=vrnt.find('vin/max').text
            
            # Test if the VIN is in range
            if not s_vin[:1] == min_vin[:1] and s_vin[2:] >= min_vin[2:] and s_vin[2:] <= max_vin:
                continue

            # For each <decode>, get the rules that decide what the model is
            for cdf in vrnt.findall('vin/decode/attribute'):
                my_gt = False
                opt = cdf.attrib['decode'].upper()
                name = cdf.attrib['name']
                val = cdf.attrib['value'].upper()
                mtype = cdf.attrib['type']

                # Not sure how type 2 works, seems to be if its singular is means equal or greater than, if its a list then its any of those
                if mtype == "2" and name == "ModelYear" and ";" not in val:
                    if int(mident[name]) >= int(val):
                        my_gt = True

                # Test this against what we got from decoding the VIN         
                if opt == 'TRUE':
                    # Test is positive match 
                    if mident[name].upper() in val or my_gt == True:
                        is_model = True
                    else:
                        is_model = False
  
            # If we find a matching model then store that and exit
            if is_model == True:
                manifest_id=vrnt.find('file_manifest').attrib['id']
                print('Found model in manifest')
                break
            is_model = False

        if manifest_id == None:
            print('No models found')
    
    # If we found a manifest_id, go and find all the files we need to actually read what the CCF means
    if manifest_id != None:
        manifest_info={}
        # Look for the matching manifest_id section and collect all the file data needed
        for fmt in root.findall("file_manifest/manifest[@id='" + manifest_id + "']/file"):
            manifest_info.update({fmt.attrib['type']:fmt.text})  
    else:
        manifest_info = None
        print('Failed to find manifest data')

    return (manifest_info)

if __name__ == '__main__':
    import sys
    import getopt
    import re
    import os

    # This will decode the VIN and tell you its options
    vin = vinxml = xmlpath = None

    # Get full command-line arguments
    full_cmd_arguments = sys.argv

    # Keep all but the first
    argument_list = full_cmd_arguments[1:]

    # set the command line options
    short_options = "hno:v:7:"
    long_options = ["help", "vin=", "xdir="]

    help_text = ("\noptions:\n"
                "   -v / --vin <string>..........  VIN to decode (mandatory)\n"
                "   -x / --xml <filename>........  VINDecode XML file\n"
                "   -y / --xdir <directory>......  location of IDS/XML where CCF_DATA, VINDECODE and VEHICLE_MANIFEST files are\n")

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
        elif current_argument in ("-v", "--vin"):
            vin = current_value
        elif current_argument in ("-x", "--xml"):
            vinxml = current_value
        elif current_argument in ("-y", "--xdir"):
            xmlpath = current_value

    # We can't do anything unless we have the VIN
    if vin == None or (vinxml == None and xmlpath == None):
        print("\nEither VIN or XML file not provided - aborting\n\n")
        print(help_text)
        sys.exit(2)

    for root, dirs, files in os.walk(xmlpath):
        for file in files:
            if re.search('^VINDECODE\..*XML.*', file.upper()):
                vinxml = os.path.join(root,file)
            if re.search('^VEHICLE_MANIFEST\..*XML.*', file.upper()):
                manifest = os.path.join(root,file)
    
    # decode the vin
    model_info,model_data=vindecode(vin, vinxml)
    print(model_info)
    print(model_data)

    if manifest != None: 
        model = model_info["Model"]
        myear = model_data.loc[model_data["title_text"] == "ModelYear"]["setting_text"][1]
        eng = model_data.loc[model_data["title_text"] == "Engine"]["setting_text"][1]
        mident={"Model":model,"ModelYear":myear, "Engine": eng, "Brand": model_info["Brand"]}
        ve_manifest = findccfdataid(manifest,mident,vin)
        if ve_manifest != None:
            ve_ccf = ve_manifest.get('XML_CCF_TEMPLATE')
            print('Manifest:', ve_ccf)
        else:
            print('ended with no manifest')
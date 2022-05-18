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
    vincols = ["offsets", "mask", "ccfval", "title", "title_text","name", "setting","setting_text"]
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
            if is_model != True:
                break
        # If we find a matching model then store that and exit
        if is_model == True:
            model=model_id

            break
    # We've not got the model ID so now we need to look up what that is

    model_data=pd.DataFrame(columns=vincols)
    model_info = {}

    if model != '':
        print('Found matching model id:' + model)
        # Get the config data for this model
        for decm in root.findall("Decodes/DecodeModel[@id='" + model + "']/Attribute"):
            name = decm.attrib['Name']
            try:
                decode = decm.attrib['Decode']
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
                decode = decm.find("Value[@Value='" + val + "']").attrib['Decode']
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
                model_data = model_data.append(tdv)
            else:
                # If char is nothing then its some descriptive text about the model, put that in a dict for later
                model_info.update({name:decode})
    else:
        print('No model found - aborting')
        sys.exit(2)

    return (model_info,model_data)

def findccfdataid(manf,mident,vin):
    # Read the XML in
    root = ET.parse(manf).getroot()

    # Find a tag that matches the brand 
    
    is_model = manifest_id = False

    for tag in root.findall("vehicle_range[@brand='" + mident["Brand"].lower() + "']/vehicle"):

        # Check if this matches the model, if not break and try the next one
        try:
            tag.find("model[@id='" + mident["Model"] + "']").attrib['id'] == mident["Model"]
        except AttributeError:
            break
        
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
                opt = cdf.attrib['decode'].upper()
                name = cdf.attrib['name']
                val = cdf.attrib['value'].upper()

                # Test this against what we got from decoding the VIN         
                if opt == 'TRUE':
                    # Test is positive match
                    if mident[name].upper() in val:
                        is_model = True
                    else:
                        is_model = False
                elif opt == 'FALSE':
                    if not mident[name].upper() in val:
                        is_model = True
                    else:
                        is_model = False
  
            # If we find a matching model then store that and exit
            if is_model == True:
                manifest_id=vrnt.find('file_manifest').attrib['id']
                print('Found model in manifest')
                break
        if is_model == False:
            print('No models found')
    
    # If we found a manifest_id, go and find all the files we need to actually read what the CCF means
    if manifest_id != None:
        manifest_info={}
        # Look for the matching manifest_id section and collect all the file data needed
        for fmt in root.findall("file_manifest/manifest[@id='" + manifest_id + "']/file"):
            manifest_info.update({fmt.attrib['type']:fmt.text})        
    return (manifest_info)

if __name__ == '__main__':
    import sys
    import getopt

    # This will decode the VIN and tell you its options
    vin = xf = None

    # Get full command-line arguments
    full_cmd_arguments = sys.argv

    # Keep all but the first
    argument_list = full_cmd_arguments[1:]

    # set the command line options
    short_options = "hno:v:"
    long_options = ["help", "vin="]

    help_text = ("\noptions:\n"
                "   -v / --vin <string>..........  VIN to decode (mandatory)\n"
                "   -x / --xml <filename>........  VINDecode XML file\n")

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
            xf = current_value

    # We can't do anything unless we have the VIN
    if vin == None or xf == None:
        print("\nEither VIN or XML file not provided - aborting\n\n")
        print(help_text)
        sys.exit(2)

        # decode the vin
    model_info,model_data=vindecode(vin, xf)
    print(model_info)
    print(model_data)
# Turn an SDD XML CCF_DATA files into an array of settings
# This is a nightmarish mish mash of some confusing XML but it gets there in the end

def sddxconv(root):

    tag = None 

    # We're going to extract all the possible CCF options for this vehicle
    # Start by finding the <parameters> in CCF section of the XML file
    for tag in root.findall("block[@name='CCF']/group/parameter"):
        # Get the attributes of the <parameters> for this vehicle type
        offset = tag.attrib['id'].split('_')
        # break the offest into its constituent parts
        startof = offset[0]
        endof = offset[1]
        sb = offset[2]
        eb = offset[3]
        name = tag.attrib['name']
        mask = tag.attrib['mask'] 
        type = tag.attrib['type']
        
        # Grab the <parameter_title>, if there isn't set make it None 
        ptitle = tag.find('parameter_title')
        if ptitle != None: 
            title = ptitle.find('tm').text
        else:
            title = None

        print(startof, endof, sb, eb, '/ Title:', title,'/ Name:', name, '/ Mask:', mask, '/ Type:', type, end=' ')
        
        option = None
        fo = 0

        # For each <parameter>, check if there are mulitple allowable <options> (sometimes there are none for a particular vehicle)
        for option in tag.findall('select/option'):
            value = option.attrib['value']
            optname = option.attrib['name']
            if fo == 0:
                print('/ Value:', value, '/ Option:', optname, end=' ')
            else:
                print(startof, endof, sb, eb, '/ Title:', title,'/ Name:', name, '/ Mask:', mask, '/ Type:', type, '/ Value:', value, '/ Option:', optname, end=' ')
            fo += 1

            # For each option check if there is a <tm> element (it sometimes has more human readable version of the option)
            for tmx in option.findall('tm'):
                tmid = tmx.attrib.get('id')
                tmtext = tmx.text
                print('/ tm:', tmid, '/', tmtext, end=' ')
            
            qmp = None
            # For each option check if there is a <qualifier_map> (not sure what its used for)
            for qmp in option.findall('qualifier_map'):
                qmap = qmp.attrib.get('id')
                qmapv = qmp.attrib.get('id_value')
                print('/ Quail:', qmap, '/', qmapv)
            
            if qmp == None:
                print('')
        if option == None:
            print('')
    return tag
import re

def convdump(fn,canid):

    ###############################################################################
    # Turn a candump into a CCF hexadecimal string. The format for this is
    # (seconds.milliseconds) <can_interface> <can_id>#<sequence byte><7 bytes of data>
    # Only the <can_id> onwards matters for this to work
    ###############################################################################

    print('Processing can dump', fn, 'for canid',canid)
    ccfl = []
    
    # Open the dump file
    with open(fn) as cf:
        while True:
            # Read each line from the dump file
            line = cf.readline().upper()
            # When there are no more lines, stop
            if not line:
                break
            # Find the can message with the correct can ID for the CCF that is in the correct format and extract it
            c = re.search(canid+'#[A-F0-9]{16}', line)
            
            # Remove the can ID and # in the process
            if c !=None: 
                cm = c.group().replace(canid +'#','')
         
                # The first two bytes is the sequence identifier, convert it from a string to a hex number and make it an int to use as the index
                # Note that the sequence goes from 01 but indexes go from 0, so take 1 away in order to put it in a list          
                idx = int('0x'+cm[:2],16)-1

                # Shove the rest of the message in as data
                dt = cm[2:16]

                # Sometimes CAN messages can get lost so they might not be in the right order due to a resend
                # We need to make sure we reorder all the CCF messages by their sequence ID, going to use an indexed list for this
                # First check if the list is large enough to put the CCF data into, if not use insert to increase the size of the list
                # Get the size of the ccfl list
                crl = (len(ccfl))
                
                if crl < idx + 1:
                    ccfl.insert(idx, dt)
                else:
                    # If the list is already big enough, push the CCF data into its correct position.
                    # This will overwrite existing values where they are repeated broadcasts of the CCF in the can dump
                    ccfl[idx] = dt

    # Lets do some integrity checks to make sure it isn't total rubbish we've just made up and turn it into a string
    # Check the list entries one by one in order
    ccf = ''
    for cfd in range(len(ccfl)):
        # Check that its 14bytes of data
        if len(ccfl[cfd]) != 14:
            print('CCF data appears incomplete for sequence', cfd+1)
            break
        elif re.search('[^A-F0-9]', ccf) != None:
            # CCF seems to have something that isn't hex in it, abort.
            print('Invalid CCF format, invalid hexadecimal character(s) found - abort')
            ccf = None
            break
        else:
            # Create the CCF string by appending the CCF data from the list in its correct order
            ccf=ccf+str(ccfl[cfd])
    # We're all done, we should now have a long string containing the CCF
    return ccf

if __name__ == '__main__':
    import sys
    import getopt

    cdump = can_id = None

    # Get full command-line arguments
    full_cmd_arguments = sys.argv

    # Keep all but the first
    argument_list = full_cmd_arguments[1:]

    # set the command line options
    short_options = "d:i:"
    long_options = ["dump=", "can_id="]

    help_text = ("\noptions:\n"
                "   -d / --dump <filename>......  can dump file to be decoded, this will override any -ccf setting\n"
                "   -i / --can_id <canid>.......  canID (decimal) used in the can dump to broadcast CCF, default = 401 (JLR)\n")

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
        elif current_argument in ("-d", "--dump"):
            cdump = current_value
        elif current_argument in ("-i", "--can_id"):
            can_id = current_value

    # We can't do anything unless we have the argument set
    if can_id == None or cdump == None:
        print("\nEither --dump or --can_id not provided - aborting\n\n")
        print(help_text)
        sys.exit(2)

    ccf=convdump(cdump,can_id)
    print(ccf)
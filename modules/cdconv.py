###############################################################################
# Turn a candump into a CCF hexadecimal string
# The format for this is (seconds.milliseconds) <can_interface> <can_id>#<sequence byte><7 bytes of data>
# Only the <can_id> onwards matters for this to work
###############################################################################
from operator import lt
import re

def convdump(fn,canid):
    print('Processing CCF dump from', fn)
    ccfl = []
    # Open the dump file
    with open(fn) as cf:
        while True:
            # Read each line from the dump file
            line = cf.readline()
            # When there are no more lines, stop
            if not line:
                break
            # Find the can message with the correct can ID for the CCF that is in the correct format and extract it
            c = re.search(canid+'#[A-F0-9]{16}', line)
            
            # Remove the can ID and # in the process
            if c !=None: cm = c.group().replace(canid +'#','')
            
            crl = (len(ccfl))
            
            # The first two bytes is the sequence identifier, convert it from a string to a hex number and make it an int to use as the index
            # Note that the sequence goes from 01 but indexes go from 0, so take 1 away in order to put it in a list          
            idx = int('0x'+cm[:2],16)-1

            # Shove the rest of the message in as data
            dt = cm[2:16]

            # Sometimes CAN messages can get lost so they might not be in the right order due to a resend
            # We need to make sure we reorder all the CCF messages by their sequence ID, going to use an indexed list for this
            # First check if the list is large enough to put the CCF data into, if not use insert to increase the size of the list
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
        else:
            # Create the CCF string by appending the CCF data from the list in its correct order
            ccf=ccf+str(ccfl[cfd])
    # We're all done, we should now have a long string containing the CCF
    return ccf

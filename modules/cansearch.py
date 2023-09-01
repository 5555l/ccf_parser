import re

def cansearch(fn,ids):

    ###############################################################################
    # Search a candump for a specific can ID. Format is:
    # (seconds.milliseconds) <can_interface> <can_id>#<sequence byte><7 bytes of data>
    # Only the <can_id> onwards matters for this to work
    ###############################################################################

    print('Processing can dump', fn, 'for canid', ' '.join(ids))
    
    # Open the dump file
    with open(fn) as cf:
        while True:
            # Read each line from the dump file
            line = cf.readline().upper()
            # When there are no more lines, stop
            if not line:
                break
            for canid in ids:
                # Find the can message with the correct can ID that is in the correct format and extract it
                c = None
                c = re.search(canid+'#[A-F0-9]{16}', line)
                if c !=None: 
                    print(c.group(0))

    return 

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
                "   -d / --dump <filename>......  can dump file to be read\n"
                "   -i / --can_id <canid>.......  canID (decimal) used in the can dump that you want to find, to find more than one use \",\" to seperate with no whitespace\n")

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

    can_ids = can_id.split(',')
    cansearch(cdump,can_ids)

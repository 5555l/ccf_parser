# ccf_parser

Decodes Ford/Volvo/JLR CCF messages taken from the canbus and tells you the current car configuration

For this to work you must have the CCF_DATA EXML file for your vehicle and decrypted it

ccfparser useage:
   -x / --xml <filename> ......  SDD XML CCF_DATA file containing possible CCF values

   -o / --output <filename> ...  filename for outputting the result, default is to stdout

   -c / --ccf <ccf> ...........  ccf hexadecimal string to be decoded

   -d / --dump <filename>......  file to be decoded, this will override any -ccf setting.
                                 Use this if you have the CCF as a string somewhere or a candump with it in

   -m / --dump_format .........  format of dump data, valid options are:
                                   cd = can_utils candump format (default)
                                   st = a hexadecimal string

   -i / --can_id...............  canID (decimal) used in the can dump to broadcast CCF, default = 401 (JLR)

SDD XML file must be specified as well as either a string containing the CCF or a dump file to process
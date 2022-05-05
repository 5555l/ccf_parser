# ccf_parser

Decodes Ford/Volvo/JLR CCF messages taken from the canbus and tells you the current car configuration

For this to work you must have the CCF_DATA EXML file that matches your vehicle and decrypted it to an XML file

By default it must be given the CCF_DATA and the CCF to decode, output will be return to stdout as a string

## ccfparser options

| Option | Type | Description |
|:------|:-----|:------------|
|`-x / --xml <filename>`|XML file|SDD XML CCF_DATA file containing possible CCF values|
|`-o / --output <filename>`|file|output the CCF settings result to a file, default is to stdout|
|`-c / --ccf <ccf>`|string|a string of hexadecimal CCF values to be decoded|
|`-d / --dump <filename>`|file|a file of hexadecimal CCF values to be decoded. This will override any -ccf setting, replacing any values provided in `-ccf`. Use this if you have the CCF as a string somewhere or a candump with it in|
|`-m / --dump_format`|string| specifies the format of the data in `--dump` file, valid options are: `cd` = can_utils candump format (default) and `st` = a hexadecimal string|
|`-i / --can_id`|string|canID (decimal) used in the can dump to broadcast CCF, default = `401` (JLR)|
|`-j / --json`|operator|sets the CCF setting output file format to json, default is a string|
|`-e / --export <filename>`|file|output the CCF_DATA options to a json file|

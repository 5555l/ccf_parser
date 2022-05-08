# ccf_parser

Decodes Ford/Volvo/JLR CCF messages taken from the canbus and tells you the current car configuration

For this to work you must have the CCF_DATA EXML file that matches your vehicle and decrypted it to an XML file

By default it must be given the CCF_DATA and the CCF to decode, output will be returned to stdout as a string.

Optionally it can provide user friendly text for the settings, for that to work it must map the CCF setting parameters to human friendly text using the SDD definitions in `IDS/SDD/XML/text`. Any EXML files in that folder and sub folders must also be converted to XML before use. Once it has done this it creates a list of values in a `__@values_cache__` and all subsequent uses of `-r` will use the cache values. The cache can be rebuilt using `-b`.

## ccfparser options

| Option | Type | Description |
|:------|:-----|:------------|
|`-x / --xml <filename>`|XML file|SDD XML CCF_DATA file containing CCF options|
|`-o / --output <filename>`|file|filename for outputting the result|
|`-f / --ccf <filename>`|file|filename for exporting CCF hex string|
|`-c / --ccfhex <ccf>`|string|CCF hexadecimal string to be decoded|
|`-d / --dump <filename>`|file|can dump file to be decoded, this will override any -ccf setting -ccf setting, replacing any values provided in `-ccf`. Use this if you have the CCF as a string somewhere or a candump with it in|
|`-m / --dump_format`|string|format of dump data, valid options are: `cd` = can_utils candump format (default) and `st` = a hexadecimal string|
|`-i / --can_id`|decimal|canID used in the can dump to broadcast CCF, default = `401` (JLR MS CAN)|
|`-j / --json`|operator|sets the CCF setting output file format to json, default is csv|
|`-e / --export <filename>`|file|output the CCF_DATA options to a json file|
|`-r / --readable <language>`|string|Use human readable values of `<language>` the output. For this to work a settings cache must exist or `-t` must be set. `<language>` must be of type supported by SDD otherwise it defaults to `eng`|
|`-t / --tdir <directory>`|file|Location of `IDS/SDD/XML/text` used to build human readable values, automatically sets -r to `eng` if -r was not provided|
|`-b / --rebuild`|operator|rebuild the settings cache data, -t must also be set|

# ccfparser

Decodes Ford/Volvo/JLR CCF messages taken from the canbus and tells you the current car configuration.

As a minimum you must have the CCF_DATA EXML file that matches your vehicle and decrypted it to an XML file (handy util for that here: https://github.com/smartgauges/exml). This file can be discovered automatically or must be specified using `--xml` argument. It must be given the CCF to decode, by default output will be returned to stdout as a string. If a `VIN` is not specified it tries to grab it from the CCF directly itself.

It can work out the correct CCF_DATA file to use and provide user friendly text for the settings, for that to work it must map the CCF setting parameters to human friendly text using the SDD definitions in `IDS/SDD/XML/text`. All EXML files in the `SDD/XML` folder and sub folders must be converted to XML before use. It will create a list of values in a `__@values_cache__` and all subsequent uses of `-r` will use the cached values. The cache can be rebuilt using `-b`.

When trying to detect the vehicle automatically the `--xdir` argument must be set to where the CCF_DATA, VINDecode and VEHICLE_MANIFEST files are.

By default it uses a CAN_ID of 401 to discover the CCF and 402 to discover the CCF_EUCD from a candump log. This is the default IDs for Jaguar medium speed CAN. Other ID's can be specified by using `--can_id`, this is always a hexadecimal value.

## ccfparser arguments

| Option | Type | Description |
|:------|:-----|:------------|
|`-x / --xml <filename>`|XML file|SDD XML CCF_DATA file containing CCF options|
|`-o / --output <filename>`|file|filename for outputting the result|
|`-f / --ccf <filename>`|file|filename for exporting CCF hex string|
|`-c / --ccfhex <ccf>`|string|CCF hexadecimal string to be decoded|
|`-d / --dump <filename>`|file|can dump file to be decoded, this will override any -ccf setting -ccf setting, replacing any values provided in `-ccf`. Use this if you have the CCF as a string somewhere or a candump with it in|
|`-m / --dump_format`|string|format of dump data, valid options are: `cd` = can_utils candump format (default) and `st` = a hexadecimal string|
|`-i / --can_id`|string|canID used in the can dump to broadcast CCF, default = `401` (JLR MS CAN)|
|`-u / --can_id_eucd`|string|canID used in the can dump to broadcast CCF_EUCD, default = `402` (JLR MS CAN)|
|`-j / --json`|operator|sets the CCF setting output file format to json, default is csv|
|`-e / --export <filename>`|file|output the CCF_DATA options to a json file|
|`-l / --lang <language>`|string|Use human readable values of `<language>` the output. For this to work a settings cache must exist or `-t` must be set. `<language>` must be of type supported by SDD otherwise it defaults to `eng`|
|`-t / --tdir <directory>`|directory|Location of `IDS/SDD/XML/text` used to build human readable values, automatically sets -r to `eng` if -r was not provided|
|`-b / --rebuild`|operator|rebuild the settings cache data, -t must also be set|
|`-v / --vin <VIN>`|string|use manually provided VIN instead of automatically detecting it from the CCF|
|`-y / --xdir`|directory|location of IDS/XML where CCF_DATA, VINDecode and VEHICLE_MANIFEST files are|

---

## How it works

When detecting the VIN and CCF_DATA automatically it starts by extracting the `VIN` from the CCF and uses it with the VINDecode XML to find the `model_id`. It then uses the `VIN` and `model_id` to find the `Brand`, `Model`, `ModelName`, `ModelYear` and `Engine` (plus some other stuff) from VINDecode.

It then uses the `VIN`, `Model`, `ModelYear` and `Engine` in the VEHICLE_MANIFEST XML to find the `variant_id`, and in turn uses that to find out which CCF_DATA file matches the vehicle.

Once it has a target CCF_DATA file to use (either from automatically detecting it or specified by `--xml` argument) it parses all of the CCF to discover the vehicle settings. By default this produces some cryptic values which are internal SDD references and not that obvious. Optionally it turn these into human readable values in any language supported by SDD.

To make the settings more readable it scans all of the files in `SDD/XML/text` to produce a lookup table of all the parameter references, to build this table `--tdir` argument must have been provided. This is quite an intensive task as there are thousands of files, so to save time in the future it stores the lookup table as a cache (`--tdir` is not needed if the cache exists).  Once it has this lookup table it converts the internal references to the human readable values, if an unsupported language is given it defaults to doing it in English.

If it successfully decodes the CCF it will output it as a string to stdout. Optionally it can be exported to a csv file using `--output`, it can also be exported in json by adding the `--json` option.

If there is an CCF_EUCD broadcast too, then it will repeat all of this for that data too.

Optionally it can also export the discovered CCF to a file, this is useful if you simply have a candump log from the vehicle, as it will scan all the messages in the log to find the CCF for you. If it finds an CCF_EUCD too, it will export that with the suffix _eucd.

---

## Bonus material

Some of the modules can be executed independently of the main ccf_parser:

* `vinload.py`: decodes the `VIN` to find the `model_id`, `Brand`, `Model`, `ModelName`, `ModelYear` and `Engine` (plus some other stuff).

* `ccfdatatext.py`: can build/rebuild the parameter reference cache.

* `cdconv.py`: to extract the CCF from a candump log.

---

## Tested configurations

| Brand | Range | Model Year |
|:------|:-----|:------------|
|Jaguar|X250|2008|
|Jaguar|X250|2010|

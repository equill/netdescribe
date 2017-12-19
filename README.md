NetDescribe
============

A set of scripts for performing discovery against devices, and returning the results in a predictable data structure.
This can then be used for populating a network management system.

Currently supports SNMP only, though Netconf/OpenConfig support are intended for the future. Frankly, the important thing here is getting management/topology data from devices; if `ssh` and `expect` are the only practical ways of getting it from a particular model, pull-requests will be considered.

Distributed under the Apache 2.0 license. Use it as you will, but constructive feedback and well-formatted pull-requests are welcome.

Developed and tested on Ubuntu Linux; bug reports about misbehaviour on other platforms are welcome.


# Usage

## Intended use

It's intended to be used as a library that returns a Python data structure, which can then be queried or iterated over, e.g. to populate a network inventory database.
```
#!/usr/bin/env python3

import logging
import netdescribe.demo
import netdescribe.snmp.device_discovery

RESULT = netdescribe.snmp.device_discovery.exploreDevice(
             "amchitka", netdescribe.demo.create_logger(logging.DEBUG))

<now iterate over RESULT>
```

## Data structure

`exploreDevice`, the main SNMP discovery function, returns a nest of dicts as follows:

```
- sysinfo
    - sysName       # Hostname. Should be the FDQN, but don't count on it.
    - sysDescr      # Detailed text description of the system.
    - sysObjectID   # Vendor's OID identifying the device.
    - sysServices   # Network-layer services offered by this device.
                    # Uses weird maths, but may be usable.
- network
    - interfaces
        - <SNMP index>
            - ifName    # Short name of the interface, in contrast to ifDescr
            - ifDescr   # Detailed text description of the interface
            - ifAlias   # Description string as configured by an administrator for this interface.
            - ifType    # IANA-specified interface type
            - ifSpeed   # reports the max speed in bits/second.
                        # If a 32-bit gauge is too small to report the speed, this should be
                        # set to the max possible value (4,294,967,295) and ifHighSpeed must
                        # be used instead.
            - ifHighSpeed   # ifHighSpeed is an estimate of the interface's current bandwidth
                            # in units of 1,000,000 bits per second. Zero for subinterfaces
                            # with no concept of bandwidth.
            - ifPhysAddress    # E.g. MAC address for an 802.x interface
    - ifIfaceAddrMap      # Mapping of addresses to interface indices
        - interface index (relative to ifTable)
            - list of dicts:
                - address = IP address for interface
                - netmask = netmask for interface address
    # The following entries will be None if ifStackTable is not implemented on the target device.
    # They're explicitly set this way to make it simpler for client code to test for them.
    - ifStackTable      # Contents of the ifStackTable SNMP table
```


## Examples

### demo.py

`demo.py` is included in the source code; it will perform discovery on a device, and send JSON-formatted output to either standard out or a file, depending on whether you specify a file. It defaults to using `public` for the SNMP community string.

You'll find it under the `netdescribe` subdirectory.

Usage:
`./demo.py <hostname> [--community <SNMP community>] [--file </path/to/output/file.json>]`

```
#!/usr/bin/env python3

"""
Example usage of the Netdescribe library.
Performs discovery, and sends JSON-formatted output to either standard out or a file,
depending on whether the --file parameter is supplied.
"""


#   Copyright [2017] [James Fleming <james@electronic-quill.net]
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

# From this package
import netdescribe.files
import netdescribe.stdout
from netdescribe.utils import create_logger

# Included batteries
import argparse


def basic_demo():
    """
    Enable this to be run as a CLI script, as well as used as a library.
    Mostly intended for testing or a basic demo.
    """
    # Get the command-line arguments
    parser = argparse.ArgumentParser(description='Perform SNMP discovery on a host, \
    returning its data in a single structure.')
    parser.add_argument('hostname',
                        type=str,
                        help='The hostname or address to perform discovery on')
    parser.add_argument('--community',
                        type=str,
                        action='store',
                        dest='community',
                        default='public',
                        help='SNMP v2 community string')
    parser.add_argument('--file',
                        type=str,
                        action='store',
                        dest='filepath',
                        default=None,
                        help='Filepath to write the results to. If this is not specified, \
                        STDOUT will be used.')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()
    # Set debug logging, if requested
    if args.debug:
        logger = create_logger(loglevel="debug")
    # Normal logging if we're writing to a file
    elif args.filepath:
        logger = create_logger()
    # Suppress INFO output if we're returning it to STDOUT:
    # don't require the user to filter the output to make it useful.
    else:
        logger = create_logger(loglevel="warning")
    # Perform SNMP discovery on a device,
    # sending the result to STDOUT or a file, depending on what the user told us.
    if args.filepath:
        netdescribe.files.snmp_to_json(args.hostname, args.community, args.filepath, logger)
    else:
        netdescribe.stdout.snmp_to_json(args.hostname, args.community, logger)

if __name__ == '__main__':
    basic_demo()
```


# Compatibility

Known to work with:
- Juniper
    - SRX100
    - SRX550
- Cisco
    - 3750
- Linux
    - Ubuntu 16.10

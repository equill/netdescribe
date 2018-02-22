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

import netdescribe.snmp.device_discovery
from netdescribe.utils import create_logger

RESULT = netdescribe.snmp.device_discovery.exploreDevice(
             "amchitka", netdescribe.demo.create_logger(loglevel="debug"))

<now do stuff with RESULT>
```

## Data structure

`exploreDevice`, the main SNMP discovery function, returns an object. Its `as_dict()` method returns a nest of dicts as follows:

```
- sysinfo
    - sysName       # Usually either the hostname or the host's FQDN.
    - sysDescr      # Detailed text description of the system.
                    # On Linux, this is the output of `uname -a`.
    - sysObjectID   # Vendor's OID identifying the device, which should correspond to make/model.
    - sysLocation   # Physical location of the device
- interfaces
    - <SNMP index>
        - ifIndex   # Index for this interface in ifTable and ifXTable
        - ifDescr   # Detailed text description of the interface
        - ifType    # IANA-specified interface type
        - ifSpeed   # reports the max speed in bits/second.
                    # If a 32-bit gauge is too small to report the speed, this should be
                    # set to the max possible value (4,294,967,295) and ifHighSpeed must
                    # be used instead.
        - ifPhysAddress    # E.g. MAC address for an 802.x interface
        - ifName    # Short name of the interface, in contrast to ifDescr
        - ifHighSpeed   # ifHighSpeed is an estimate of the interface's current bandwidth
                        # in units of 1,000,000 bits per second. Zero for subinterfaces
                        # with no concept of bandwidth.
        - ifAlias   # Description string, as configured by an administrator for this interface.
    - ipIfaceAddrMap      # Mapping of addresses to interface indices
        - interface index (relative to ifTable, matches <SNMP index> from the `interfaces` section)
            - list of ipaddress objects, of type IPv4Interface or IPv6Interface
```

The `as_json()` method renders this structure in JSON format, handling conversion of `ipaddress.IPv4Interface` and `ipaddress.IPv6Interface` objects to text.

Of course, you can also query its attributes directly. These include:

- `sys_name`
- `sys_descr`
- `sys_object_id`
- `sys_location`
- `network`

Currently there's only the base class of `Mib2`, representing a generic device conforming closely enough to MIB-II. However, this design is intended to enable the graceful (enough) handling of the multitude of SNMP implementations.

### Interface objects

`IPv4Interface` and `IPv6Interface` are [interface objects](https://docs.python.org/3.5/library/ipaddress.html#interface-objects) from the [ipaddress module](https://docs.python.org/3.5/library/ipaddress.html).

What makes them so useful is the convenient way you can get different representations of them:

- `addr.ip` returns the address by itself, as an `ipaddress.IPv4Address` or `ipaddress.IPv6Address` object
    - these can be converted to strings, via `str(addr.ip)`
- `addr.with_prefixlen` returns the CIDR representation of an address, e.g. '192.0.2.5/24'
- `addr.with_netmask` shows the network portion as a netmask, e.g: '192.0.2.5/255.255.255.0'


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

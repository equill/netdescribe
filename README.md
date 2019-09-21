NetDescribe
============

A set of scripts for performing discovery against devices, and returning the results in a predictable data structure.
This can then be used for populating a network management system.

Currently supports SNMP only, though Netconf/OpenConfig support are intended for the future. Frankly, the important thing here is getting management/topology data from devices; if `ssh` and `expect` are the only practical ways of getting it from a particular model, pull-requests will be considered.

Distributed under the Apache 2.0 license. Use it as you will, but constructive feedback and well-formatted pull-requests are welcome.

Developed and tested on Python37 on Nixos (Linux); bug reports about misbehaviour on other platforms are welcome.


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

`demo.py` is included in the source code, under the `netdescribe` subdirectory.
It will perform discovery on a device, and send JSON-formatted output to either standard out or a file, depending on whether you specify a file. It defaults to querying localhost, and using `public` for the SNMP community string.

Usage:
`./demo.py [--hostname <hostname>] [--community <SNMP community>] [--file </path/to/output/file.json>]`


In case you don't already have a running `snmpd` instance, there's also a basic config file in that directory as well. It listens on all IPv4 addresses, and accepts the community string "public". To use it, install `net_snmp` and run `sudo snmpd -c snmpd.conf -f` in a terminal window.


# Building

## Dependencies

Currently, `pysnmp` is the only Python library depended on. Version 4.4.11 is currently used for development and testing.

To do it the systematic way, ensure you have Python3.7, `pip` and `virtualenv` installed; if you're running Nixos, just run `nix-shell` in this directory. Then set up virtualenv and install the dependencies via `pip`:
```
virtualenv -p python3.7 venv
source venv/bin/activate
pip install -r requirements.txt
```


## Build process

`./setup.py build` will produce a pip-installable tarball in the `dist` subdirectory.


## Nixos notes

Note that you need to execute `unset SOURCE_DATE_EPOCH` in the shell before running `pip install -r requirements.txt`, to prevent Zip failing with a timestamp error when building wheels. See [the Nixos docs for python-setup](https://nixos.org/nixpkgs/manual/#python-setup.py-bdist_wheel-cannot-create-.whl) for details.

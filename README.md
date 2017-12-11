NetDescribe
============

A set of scripts for performing discovery against devices, and presenting the results in a predictable data structure.
This can then be used for populating a network management system, such as [Syscat](https://github.com/equill/syscat)

Currently supports SNMP only, though it's intended to incorporate better protocols once it's mature enough.

Distributed under the Apache 2.0 license.


# Usage

## Basic demo

`netdescribe/device_discovery.py` can be invoked as a script, which returns unformatted data to standard output:
```
./device_discovery.py <hostname> [--community <community string>] [--debug]
```

`community` defaults to `public`, so only needs to be specified if you've set a different read-only string.


## Intended use

It's intended to be used as a library that returns a Python data structure, which can then be queried or iterated over, e.g. to populate a network inventory database.
```
#!/usr/bin/env python3

import logging
import netdescribe.demo
import netdescribe.snmp.device_discovery

RESULT = netdescribe.snmp.device_discovery.exploreDevice("amchitka", netdescribe.demo.create_logger(logging.DEBUG))

<now iterate over RESULT>
```


# Compatibility

Known to work with:
- Juniper
    - SRX100
    - SRX550
- Cisco
    - 3750
